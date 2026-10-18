"""Telegram bot on aiogram 3: /start, /help, echo, and notes in PostgreSQL.

Configuration (Variables of the app; nothing else is read):
  TELEGRAM_BOT_TOKEN  required. The token @BotFather gave you.
  BOT_MODE            polling (default) or webhook.
  WEBHOOK_URL         webhook mode: the app's public HTTPS address, e.g.
                      https://my-bot.example.com (Networking -> generate a domain).
  WEBHOOK_SECRET      optional; checked on every webhook call. Derived from the
                      token when unset.
  DATABASE_URL        optional. Set when a PostgreSQL service is connected:
                      turns on /note and /notes.
  PORT                the HTTP port (default 8080): GET /healthz, and the
                      webhook in webhook mode.
  TELEGRAM_API_URL    optional: a self-hosted Bot API server instead of
                      https://api.telegram.org.

Exit codes: 64 = a variable is missing or malformed, 78 = Telegram refused the token.
"""

import asyncio
import hashlib
import hmac
import logging
import os
import re
import signal
import sys
import urllib.parse

from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter, TelegramServerError, TelegramUnauthorizedError
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import BotCommand, Message
from aiogram.utils.token import TokenValidationError
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

WEBHOOK_PATH = "/telegram/webhook"
MAX_NOTE_LENGTH = 1000
NOTES_SHOWN = 10
NOTE_PREVIEW = 300  # ten previews stay below Telegram's 4096 characters


class RedactingFormatter(logging.Formatter):
    """Never lets a secret reach the logs, tracebacks included."""

    def __init__(self):
        super().__init__("%(asctime)s %(levelname)s %(name)s: %(message)s")
        self.secrets = []

    def hide(self, *secrets):
        self.secrets.extend(s for s in secrets if s and len(s) >= 6)  # a shorter one would garble every line

    def format(self, record):
        text = super().format(record)
        for secret in self.secrets:
            text = text.replace(secret, "***")
        return text


REDACT = RedactingFormatter()
_handler = logging.StreamHandler(sys.stdout)
_handler.setFormatter(REDACT)
logging.basicConfig(level=logging.INFO, handlers=[_handler], force=True)


def database_password(url):
    try:
        return urllib.parse.urlsplit(url).password
    except ValueError:
        return None


def fail(message, code):
    logging.getLogger("bot").error(message)
    sys.exit(code)


TEXTS = {
    "ru": {
        "start": "Привет, {name}! Я эхо-бот: пришлите текст, и я его повторю.\n\n{help}",
        "help": "Команды:\n/start — начать\n/help — эта справка\n/note <текст> — сохранить заметку\n/notes — последние заметки",
        "no_db": "Заметкам нужна база данных: добавьте PostgreSQL в проект и подключите её к боту (переменная DATABASE_URL).",
        "db_error": "База данных сейчас недоступна, попробуйте позже.",
        "note_usage": "Напишите текст после команды: /note купить хлеб",
        "note_long": "Заметка длиннее {limit} символов.",
        "note_saved": "Сохранено. Всего заметок: {count}.",
        "notes_empty": "Заметок пока нет. Добавьте: /note текст",
        "notes": "Последние заметки:\n{items}",
        "not_text": "Я понимаю только текст.",
    },
    "en": {
        "start": "Hi, {name}! I am an echo bot: send me text and I will repeat it.\n\n{help}",
        "help": "Commands:\n/start - start\n/help - this help\n/note <text> - save a note\n/notes - recent notes",
        "no_db": "Notes need a database: add PostgreSQL to the project and connect it to the bot (variable DATABASE_URL).",
        "db_error": "The database is unavailable right now, try again later.",
        "note_usage": "Put the text after the command: /note buy bread",
        "note_long": "The note is longer than {limit} characters.",
        "note_saved": "Saved. Notes in total: {count}.",
        "notes_empty": "No notes yet. Add one: /note text",
        "notes": "Recent notes:\n{items}",
        "not_text": "I only understand text.",
    },
}


def t(message: Message, key: str, **values) -> str:
    language = (message.from_user.language_code or "") if message.from_user else ""
    texts = TEXTS["ru"] if language.lower().startswith("ru") else TEXTS["en"]
    return texts[key].format(**values)


class Notes:
    """Notes in PostgreSQL. Connects on first use and again after a failure."""

    def __init__(self, dsn):
        self.dsn = dsn
        self.pool = None
        self.lock = asyncio.Lock()

    async def _pool(self):
        async with self.lock:
            if self.pool is None:
                import asyncpg

                pool = await asyncpg.create_pool(self.dsn, min_size=0, max_size=4, timeout=10, command_timeout=10)
                try:
                    await pool.execute(
                        "CREATE TABLE IF NOT EXISTS bot_notes ("
                        " id BIGSERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, text TEXT NOT NULL,"
                        " created_at TIMESTAMPTZ NOT NULL DEFAULT now())"
                    )
                    await pool.execute("CREATE INDEX IF NOT EXISTS bot_notes_chat ON bot_notes (chat_id, id)")
                except BaseException:
                    await pool.close()  # the next use connects again
                    raise
                self.pool = pool
            return self.pool

    async def add(self, chat_id, text):
        pool = await self._pool()
        async with pool.acquire() as connection:
            await connection.execute("INSERT INTO bot_notes (chat_id, text) VALUES ($1, $2)", chat_id, text)
            return await connection.fetchval("SELECT count(*) FROM bot_notes WHERE chat_id = $1", chat_id)

    async def recent(self, chat_id):
        pool = await self._pool()
        rows = await pool.fetch(
            "SELECT text FROM bot_notes WHERE chat_id = $1 ORDER BY id DESC LIMIT $2", chat_id, NOTES_SHOWN
        )
        return [row["text"] for row in rows]

    async def close(self):
        if self.pool is not None:
            await self.pool.close()


def build_router(notes):
    router = Router()
    log = logging.getLogger("bot")

    @router.message(CommandStart())
    async def start(message: Message):
        name = message.from_user.first_name if message.from_user else "there"
        await message.answer(t(message, "start", name=name, help=t(message, "help")))

    @router.message(Command("help"))
    async def help_(message: Message):
        await message.answer(t(message, "help"))

    @router.message(Command("note"))
    async def note(message: Message, command: CommandObject):
        if notes is None:
            return await message.answer(t(message, "no_db"))
        text = (command.args or "").strip()
        if not text:
            return await message.answer(t(message, "note_usage"))
        if len(text) > MAX_NOTE_LENGTH:
            return await message.answer(t(message, "note_long", limit=MAX_NOTE_LENGTH))
        try:
            count = await notes.add(message.chat.id, text)
        except Exception as error:  # the database is optional: answer, log, keep running
            log.warning("could not save a note: %s", type(error).__name__)
            return await message.answer(t(message, "db_error"))
        await message.answer(t(message, "note_saved", count=count))

    @router.message(Command("notes"))
    async def list_notes(message: Message):
        if notes is None:
            return await message.answer(t(message, "no_db"))
        try:
            items = await notes.recent(message.chat.id)
        except Exception as error:
            log.warning("could not read notes: %s", type(error).__name__)
            return await message.answer(t(message, "db_error"))
        if not items:
            return await message.answer(t(message, "notes_empty"))
        preview = lambda item: item if len(item) <= NOTE_PREVIEW else item[:NOTE_PREVIEW] + "…"
        await message.answer(t(message, "notes", items="\n".join(f"- {preview(item)}" for item in items)))

    # Echo in private chats only: in a group, service messages (joins, pins) and chatter are not for the bot.
    @router.message(F.chat.type == ChatType.PRIVATE, F.text)
    async def echo(message: Message):
        await message.answer(message.text)

    @router.message(F.chat.type == ChatType.PRIVATE)
    async def other(message: Message):
        await message.answer(t(message, "not_text"))

    return router


async def authenticate(bot, stop):
    """getMe until it answers: a refused token ends the process, a network error is retried."""
    log = logging.getLogger("bot")
    delay = 2
    while not stop.is_set():
        try:
            return await bot.get_me()
        except TelegramUnauthorizedError:
            fail("Telegram refused TELEGRAM_BOT_TOKEN (401 Unauthorized). Copy the token from @BotFather into Variables and redeploy.", 78)
        except TelegramRetryAfter as error:
            delay = max(delay, error.retry_after)
        except (TelegramNetworkError, TelegramServerError, OSError) as error:
            log.warning("cannot reach api.telegram.org (%s); retrying in %s s", type(error).__name__, delay)
        try:
            await asyncio.wait_for(stop.wait(), timeout=delay)
        except asyncio.TimeoutError:
            pass
        delay = min(delay * 2, 60)
    return None


async def main():
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    webhook_secret = os.environ.get("WEBHOOK_SECRET", "").strip()
    database_url = os.environ.get("DATABASE_URL", "").strip()
    REDACT.hide(token, webhook_secret, database_password(database_url))
    log = logging.getLogger("bot")

    if not token:
        fail("set TELEGRAM_BOT_TOKEN in Variables (the token from @BotFather), then redeploy", 64)
    mode = os.environ.get("BOT_MODE", "polling").strip().lower() or "polling"
    if mode not in ("polling", "webhook"):
        fail(f"BOT_MODE must be polling or webhook, got {mode!r}", 64)
    webhook_url = os.environ.get("WEBHOOK_URL", "").strip().rstrip("/")
    if mode == "webhook" and not webhook_url.startswith("https://"):
        fail("webhook mode needs WEBHOOK_URL, the app's public https:// address (Networking -> generate a domain)", 64)
    if not webhook_secret:
        webhook_secret = hmac.new(token.encode(), b"inquir-telegram-webhook", hashlib.sha256).hexdigest()
    REDACT.hide(webhook_secret)
    if not re.fullmatch(r"[A-Za-z0-9_-]{16,256}", webhook_secret):
        fail("WEBHOOK_SECRET must be 16-256 characters of A-Z, a-z, 0-9, _ and -", 64)
    try:
        port = int(os.environ.get("PORT", "8080"))
    except ValueError:
        fail("PORT must be a number", 64)

    api_url = os.environ.get("TELEGRAM_API_URL", "").strip().rstrip("/")
    if api_url and not re.match(r"https?://[^/\s]+", api_url):
        fail("TELEGRAM_API_URL must be an http(s):// address", 64)
    session = AiohttpSession(api=TelegramAPIServer.from_base(api_url)) if api_url else None
    try:
        bot = Bot(token, session=session)
    except TokenValidationError:
        fail("TELEGRAM_BOT_TOKEN does not look like a token from @BotFather (digits:letters)", 64)

    notes = Notes(database_url) if database_url else None
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(notes))

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # Windows, when run locally
            signal.signal(sig, lambda *_: loop.call_soon_threadsafe(stop.set))

    state = {"ready": False}

    async def healthz(_request):
        return web.json_response({"ok": state["ready"], "mode": mode}, status=200 if state["ready"] else 503)

    app = web.Application()
    app.router.add_get("/healthz", healthz)
    if mode == "webhook":
        SimpleRequestHandler(dispatcher=dispatcher, bot=bot, secret_token=webhook_secret).register(app, path=WEBHOOK_PATH)
    runner = web.AppRunner(app, access_log=None)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", port).start()

    polling = None
    try:
        me = await authenticate(bot, stop)
        if me is None:
            return
        try:
            await bot.set_my_commands([
                BotCommand(command="start", description="Start"),
                BotCommand(command="help", description="Help"),
                BotCommand(command="note", description="Save a note"),
                BotCommand(command="notes", description="Recent notes"),
            ])
        except Exception as error:
            log.warning("could not set the command menu: %s", type(error).__name__)
        allowed = dispatcher.resolve_used_update_types()
        if mode == "webhook":
            await bot.set_webhook(f"{webhook_url}{WEBHOOK_PATH}", secret_token=webhook_secret, allowed_updates=allowed)
        else:
            # A webhook left from webhook mode would make getUpdates fail with 409.
            await bot.delete_webhook(drop_pending_updates=False)
            polling = asyncio.create_task(
                dispatcher.start_polling(bot, handle_signals=False, close_bot_session=False, allowed_updates=allowed)
            )
        state["ready"] = True
        log.info("@%s is running (%s mode)%s", me.username, mode, ", notes in PostgreSQL" if notes else "")
        stopped = asyncio.create_task(stop.wait())
        await asyncio.wait([task for task in (polling, stopped) if task], return_when=asyncio.FIRST_COMPLETED)
        if polling and polling.done() and not stop.is_set():
            polling.result()  # polling ended by itself: surface its error
    finally:
        state["ready"] = False
        log.info("shutting down")
        if polling and not polling.done():
            try:
                await dispatcher.stop_polling()
            except RuntimeError:  # not started yet
                polling.cancel()
            await asyncio.wait([polling], timeout=10)
        await runner.cleanup()
        if notes:
            await notes.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (SystemExit, KeyboardInterrupt):
        raise
    except BaseException:  # through the redacting formatter, never the default hook
        logging.getLogger("bot").exception("stopped")
        sys.exit(1)
