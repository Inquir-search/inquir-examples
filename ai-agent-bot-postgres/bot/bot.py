"""AI assistant for Telegram (aiogram 3) on any OpenAI-compatible Chat Completions API.

Configuration (Variables of the app; nothing else is read):
  TELEGRAM_BOT_TOKEN     required. The token @BotFather gave you.
  OPENAI_API_KEY         required. The model provider's API key.
  OPENAI_BASE_URL        optional, default https://api.openai.com/v1. Any API
                         that serves POST <base>/chat/completions the OpenAI way.
  MODEL                  optional, default gpt-5-mini. The model name your provider expects.
  SYSTEM_PROMPT          optional. The assistant's instructions.
  ALLOWED_USER_IDS       optional. Comma-separated Telegram user ids allowed to use
                         the bot (/start shows yours). Empty: everyone who finds it.
  HISTORY_MESSAGES       optional, default 20. Messages of each chat sent along as context.
  RATE_LIMIT_PER_MINUTE  optional, default 6. Questions per chat per minute.
  GLOBAL_RATE_LIMIT_PER_MINUTE  optional, default 60. Questions per minute over all chats.
  BOT_MODE               polling (default) or webhook.
  WEBHOOK_URL            webhook mode: the app's public HTTPS address.
  WEBHOOK_SECRET         optional; checked on every webhook call. Derived from the
                         token when unset.
  DATABASE_URL           optional. Set when a PostgreSQL service is connected: the
                         history survives restarts. Without it, it lives in memory.
  PORT                   the HTTP port (default 8080): GET /healthz, and the webhook.
  TELEGRAM_API_URL       optional: a self-hosted Bot API server.

Exit codes: 64 = a variable is missing or malformed, 78 = Telegram refused the token.
"""

import asyncio
import collections
import hashlib
import hmac
import logging
import os
import re
import signal
import sys
import urllib.parse
import time

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.enums import ChatAction, ChatType
from aiogram.exceptions import TelegramNetworkError, TelegramRetryAfter, TelegramServerError, TelegramUnauthorizedError
from aiogram.filters import Command, CommandObject, CommandStart
from aiogram.types import BotCommand, Message
from aiogram.utils.token import TokenValidationError
from aiogram.webhook.aiohttp_server import SimpleRequestHandler

WEBHOOK_PATH = "/telegram/webhook"
TELEGRAM_LIMIT = 4000  # a Telegram message holds 4096 characters
MAX_QUESTION_LENGTH = 4000
PROVIDER_CONCURRENCY = 4
PROVIDER_TIMEOUT_SECONDS = 120
MEMORY_CHATS = 500  # chats whose history and rate-limit state are kept in memory
HISTORY_ITEM_LENGTH = 4000  # characters of each stored question or answer sent along as context
DEFAULT_SYSTEM_PROMPT = (
    "You are a helpful assistant in a Telegram chat. Answer clearly and briefly, "
    "in the language of the user's message. Use plain text, no Markdown tables."
)

log = logging.getLogger("bot")


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
    log.error(message)
    sys.exit(code)


def env_int(name, default, low, high):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        fail(f"{name} must be a whole number, got {raw!r}", 64)
    if not low <= value <= high:
        fail(f"{name} must be between {low} and {high}, got {value}", 64)
    return value


TEXTS = {
    "ru": {
        "start": "Привет, {name}! Я ИИ-ассистент: задайте вопрос, и я отвечу.\n"
                 "/reset — начать разговор заново\n/help — справка\n\nВаш Telegram ID: {user_id}",
        "help": "Просто напишите вопрос. В группе: /ask <вопрос>.\n/reset — забыть историю этого чата.",
        "reset": "Начинаем заново: историю этого чата я забыл.",
        "denied": "Этот бот закрыт. Ваш Telegram ID: {user_id} — попросите владельца добавить его в ALLOWED_USER_IDS.",
        "rate": "Слишком много вопросов. Попробуйте через {seconds} с.",
        "long": "Сообщение длиннее {limit} символов, сократите его.",
        "ask_usage": "Напишите вопрос после команды: /ask как дела?",
        "auth": "Провайдер модели не принял ключ API (OPENAI_API_KEY). Владельцу бота нужно проверить ключ.",
        "model": "Провайдер не знает модель из MODEL. Владельцу бота нужно проверить её название.",
        "limit": "Провайдер модели ограничил запросы (лимит или баланс). Попробуйте позже.",
        "forbidden": "Провайдер модели отклонил запрос (HTTP 403). Владельцу бота нужно проверить аккаунт и ключ у провайдера.",
        "global_rate": "Бот сейчас получает слишком много вопросов. Попробуйте через {seconds} с.",
        "error": "Не получилось получить ответ модели. Попробуйте ещё раз.",
        "empty": "Модель вернула пустой ответ.",
        "not_text": "Я понимаю только текст.",
    },
    "en": {
        "start": "Hi, {name}! I am an AI assistant: ask me anything.\n"
                 "/reset - start the conversation over\n/help - help\n\nYour Telegram ID: {user_id}",
        "help": "Just write your question. In a group: /ask <question>.\n/reset - forget this chat's history.",
        "reset": "Starting over: I forgot this chat's history.",
        "denied": "This bot is private. Your Telegram ID: {user_id} - ask the owner to add it to ALLOWED_USER_IDS.",
        "rate": "Too many questions. Try again in {seconds} s.",
        "long": "The message is longer than {limit} characters, please shorten it.",
        "ask_usage": "Put the question after the command: /ask how are you?",
        "auth": "The model provider rejected the API key (OPENAI_API_KEY). The bot owner needs to check it.",
        "model": "The provider does not know the model in MODEL. The bot owner needs to check its name.",
        "limit": "The model provider is rate limiting (limit or balance). Try again later.",
        "forbidden": "The model provider refused the request (HTTP 403). The bot owner needs to check the provider account and key.",
        "global_rate": "The bot is getting too many questions right now. Try again in {seconds} s.",
        "error": "Could not get an answer from the model. Please try again.",
        "empty": "The model returned an empty answer.",
        "not_text": "I only understand text.",
    },
}


def t(message: Message, key: str, **values) -> str:
    language = (message.from_user.language_code or "") if message.from_user else ""
    texts = TEXTS["ru"] if language.lower().startswith("ru") else TEXTS["en"]
    return texts[key].format(**values)


class ProviderError(Exception):
    def __init__(self, kind, status=None, detail=""):
        super().__init__(kind)
        self.kind, self.status, self.detail = kind, status, detail


class Provider:
    """POST <base>/chat/completions with a bearer key, the OpenAI way."""

    def __init__(self, base_url, api_key, model):
        self.base_url, self.api_key, self.model = base_url, api_key, model
        self.session = None
        self.semaphore = asyncio.Semaphore(PROVIDER_CONCURRENCY)

    def _session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=aiohttp.ClientTimeout(total=PROVIDER_TIMEOUT_SECONDS),
            )
        return self.session

    @staticmethod
    def _error_detail(body):
        # Only the provider's error type/code: some providers echo part of the key in the message.
        error = body.get("error") if isinstance(body, dict) else None
        if isinstance(error, dict):
            return " ".join(str(error[k]) for k in ("type", "code") if error.get(k))[:200]
        return ""

    async def check(self):
        """Logs whether the provider answers and accepts the key. Never fatal."""
        try:
            async with self._session().get(f"{self.base_url}/models", timeout=aiohttp.ClientTimeout(total=15)) as response:
                body = await response.json(content_type=None) if response.content_type.endswith("json") else {}
                if response.status == 200:
                    log.info("model provider %s answers and accepts OPENAI_API_KEY; model %s", self.base_url, self.model)
                elif response.status in (401, 403):
                    log.warning("model provider %s refused OPENAI_API_KEY (HTTP %s %s)", self.base_url, response.status, self._error_detail(body))
                else:
                    log.info("model provider %s answered HTTP %s to GET /models; the key is checked on the first question", self.base_url, response.status)
        except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as error:
            log.warning("cannot reach the model provider %s (%s)", self.base_url, type(error).__name__)

    async def complete(self, messages):
        payload = {"model": self.model, "messages": messages}
        async with self.semaphore:
            try:
                async with self._session().post(f"{self.base_url}/chat/completions", json=payload) as response:
                    try:
                        body = await response.json(content_type=None)
                    except ValueError:
                        body = {}
                    if response.status == 200:
                        try:
                            content = body["choices"][0]["message"]["content"]
                        except (KeyError, IndexError, TypeError):
                            raise ProviderError("error", 200, "no choices[0].message.content")
                        return (content or "").strip()
                    detail = self._error_detail(body)
                    kind = {401: "auth", 403: "forbidden", 404: "model", 429: "limit"}.get(response.status, "error")
                    raise ProviderError(kind, response.status, detail)
            except (aiohttp.ClientError, asyncio.TimeoutError, OSError) as error:
                raise ProviderError("error", None, type(error).__name__)

    async def close(self):
        if self.session is not None:
            await self.session.close()


class History:
    """The last messages of each chat: in PostgreSQL when DATABASE_URL is set, else in memory."""

    def __init__(self, dsn, keep):
        self.dsn, self.keep = dsn, keep
        # The chats used most recently, at most MEMORY_CHATS of them.
        self.memory = collections.OrderedDict()
        self.pool = None
        self.lock = asyncio.Lock()

    async def _pool(self):
        async with self.lock:
            if self.pool is None:
                import asyncpg

                pool = await asyncpg.create_pool(self.dsn, min_size=0, max_size=4, timeout=10, command_timeout=10)
                try:
                    await pool.execute(
                        "CREATE TABLE IF NOT EXISTS ai_bot_messages ("
                        " id BIGSERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL,"
                        " created_at TIMESTAMPTZ NOT NULL DEFAULT now())"
                    )
                    await pool.execute("CREATE INDEX IF NOT EXISTS ai_bot_messages_chat ON ai_bot_messages (chat_id, id)")
                except BaseException:
                    await pool.close()  # the next use connects again
                    raise
                self.pool = pool
            return self.pool

    async def prepare(self):
        """Connect and create the table at start, so a wrong DATABASE_URL shows in the first log lines."""
        if not self.dsn:
            return "in memory"
        try:
            await self._pool()
            return "in PostgreSQL"
        except Exception as error:  # still optional: every later use tries the database again
            log.warning("history: database unavailable at start (%s), using memory until it answers", type(error).__name__)
            return "in memory (PostgreSQL unavailable)"

    async def recent(self, chat_id):
        if self.dsn:
            try:
                pool = await self._pool()
                rows = await pool.fetch(
                    "SELECT role, content FROM ai_bot_messages WHERE chat_id = $1 ORDER BY id DESC LIMIT $2",
                    chat_id, self.keep,
                )
                return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]
            except Exception as error:  # the database is optional: fall back to memory
                log.warning("history: database unavailable (%s), using memory", type(error).__name__)
        return list(self.memory.get(chat_id, ()))

    async def add(self, chat_id, question, answer):
        # Bounded context: a long answer is kept shortened, so every next request stays small.
        question, answer = question[:HISTORY_ITEM_LENGTH], answer[:HISTORY_ITEM_LENGTH]
        if self.keep:
            kept = self.memory.pop(chat_id, None) or collections.deque(maxlen=self.keep)
            kept.extend([{"role": "user", "content": question}, {"role": "assistant", "content": answer}])
            self.memory[chat_id] = kept
            while len(self.memory) > MEMORY_CHATS:
                self.memory.popitem(last=False)
        if not self.dsn or not self.keep:
            return
        try:
            pool = await self._pool()
            async with pool.acquire() as connection, connection.transaction():
                await connection.executemany(
                    "INSERT INTO ai_bot_messages (chat_id, role, content) VALUES ($1, $2, $3)",
                    [(chat_id, "user", question), (chat_id, "assistant", answer)],
                )
                # Keep only what is sent along as context.
                await connection.execute(
                    "DELETE FROM ai_bot_messages WHERE chat_id = $1 AND id < ("
                    " SELECT min(id) FROM (SELECT id FROM ai_bot_messages WHERE chat_id = $1 ORDER BY id DESC LIMIT $2) AS kept)",
                    chat_id, self.keep,
                )
        except Exception as error:
            log.warning("history: could not save (%s)", type(error).__name__)

    async def clear(self, chat_id):
        self.memory.pop(chat_id, None)
        if self.dsn:
            try:
                pool = await self._pool()
                await pool.execute("DELETE FROM ai_bot_messages WHERE chat_id = $1", chat_id)
            except Exception as error:
                log.warning("history: could not clear (%s)", type(error).__name__)

    async def close(self):
        if self.pool is not None:
            await self.pool.close()


class RateLimit:
    """At most `per_minute` questions per chat and `global_per_minute` over all chats in any
    60 seconds; a chat's questions are answered one after another."""

    def __init__(self, per_minute, global_per_minute):
        self.per_minute, self.global_per_minute = per_minute, global_per_minute
        self.times = collections.defaultdict(collections.deque)
        self.all_times = collections.deque()
        self.locks = collections.defaultdict(asyncio.Lock)

    def global_wait_seconds(self):
        now = time.monotonic()
        while self.all_times and now - self.all_times[0] >= 60:
            self.all_times.popleft()
        if len(self.all_times) >= self.global_per_minute:
            return int(60 - (now - self.all_times[0])) + 1
        return 0

    def wait_seconds(self, chat_id):
        now = time.monotonic()
        if len(self.times) > MEMORY_CHATS:
            # Forget chats idle for a minute whose lock nobody holds or waits for.
            for idle in [c for c, ts in self.times.items() if (not ts or now - ts[-1] >= 60) and not self.locks[c].locked()]:
                self.times.pop(idle, None)
                self.locks.pop(idle, None)
        times = self.times[chat_id]
        while times and now - times[0] >= 60:
            times.popleft()
        if len(times) >= self.per_minute:
            return int(60 - (now - times[0])) + 1
        times.append(now)
        self.all_times.append(now)
        return 0


def split(text, limit=TELEGRAM_LIMIT):
    parts = []
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        parts.append(text[:cut])
        text = text[cut:].lstrip("\n")
    return parts + [text] if text else parts


def build_router(bot, provider, history, limiter, system_prompt, allowed):
    router = Router()

    def permitted(message: Message):
        return not allowed or (message.from_user is not None and message.from_user.id in allowed)

    async def answer(message: Message, question: str):
        if not permitted(message):
            return await message.answer(t(message, "denied", user_id=message.from_user.id if message.from_user else "?"))
        question = question.strip()
        if len(question) > MAX_QUESTION_LENGTH:
            return await message.answer(t(message, "long", limit=MAX_QUESTION_LENGTH))
        chat_id = message.chat.id
        wait = limiter.global_wait_seconds()
        if wait:
            return await message.answer(t(message, "global_rate", seconds=wait))
        wait = limiter.wait_seconds(chat_id)
        if wait:
            return await message.answer(t(message, "rate", seconds=wait))
        # One question of a chat at a time, in order, so each answer sees the previous ones.
        async with limiter.locks[chat_id]:
            await bot.send_chat_action(chat_id, ChatAction.TYPING)
            messages = [{"role": "system", "content": system_prompt}, *await history.recent(chat_id), {"role": "user", "content": question}]
            try:
                reply = await provider.complete(messages)
            except ProviderError as error:
                log.warning("model provider: %s (HTTP %s %s)", error.kind, error.status, error.detail)
                return await message.answer(t(message, error.kind))
            if not reply:
                return await message.answer(t(message, "empty"))
            await history.add(chat_id, question, reply)
            for part in split(reply):
                await message.answer(part)

    @router.message(CommandStart())
    async def start(message: Message):
        user = message.from_user
        await message.answer(t(message, "start", name=user.first_name if user else "there", user_id=user.id if user else "?"))

    @router.message(Command("help"))
    async def help_(message: Message):
        await message.answer(t(message, "help"))

    @router.message(Command("reset"))
    async def reset(message: Message):
        if not permitted(message):
            return await message.answer(t(message, "denied", user_id=message.from_user.id if message.from_user else "?"))
        await history.clear(message.chat.id)
        await message.answer(t(message, "reset"))

    @router.message(Command("ask"))
    async def ask(message: Message, command: CommandObject):
        if not (command.args or "").strip():
            return await message.answer(t(message, "ask_usage"))
        await answer(message, command.args)

    # In private chats every text is a question; in groups only /ask is.
    @router.message(F.chat.type == ChatType.PRIVATE, F.text)
    async def text(message: Message):
        await answer(message, message.text)

    @router.message(F.chat.type == ChatType.PRIVATE)
    async def other(message: Message):
        await message.answer(t(message, "not_text"))

    return router


async def authenticate(bot, stop):
    """getMe until it answers: a refused token ends the process, a network error is retried."""
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
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    webhook_secret = os.environ.get("WEBHOOK_SECRET", "").strip()
    database_url = os.environ.get("DATABASE_URL", "").strip()
    REDACT.hide(token, api_key, webhook_secret, database_password(database_url))

    if not token:
        fail("set TELEGRAM_BOT_TOKEN in Variables (the token from @BotFather), then redeploy", 64)
    if not api_key:
        fail("set OPENAI_API_KEY in Variables (your model provider's API key), then redeploy", 64)
    base_url = (os.environ.get("OPENAI_BASE_URL", "").strip() or "https://api.openai.com/v1").rstrip("/")
    if not base_url.startswith(("https://", "http://")):
        fail(f"OPENAI_BASE_URL must start with https:// or http:// (got {base_url!r})", 64)
    model = os.environ.get("MODEL", "").strip() or "gpt-5-mini"
    system_prompt = os.environ.get("SYSTEM_PROMPT", "").strip() or DEFAULT_SYSTEM_PROMPT
    try:
        allowed = {int(item) for item in os.environ.get("ALLOWED_USER_IDS", "").replace(" ", "").split(",") if item}
    except ValueError:
        fail("ALLOWED_USER_IDS must be Telegram user ids separated by commas, e.g. 12345,67890", 64)
    keep = env_int("HISTORY_MESSAGES", 20, 0, 200)
    per_minute = env_int("RATE_LIMIT_PER_MINUTE", 6, 1, 600)
    global_per_minute = env_int("GLOBAL_RATE_LIMIT_PER_MINUTE", 60, 1, 6000)
    port = env_int("PORT", 8080, 1, 65535)
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

    api_url = os.environ.get("TELEGRAM_API_URL", "").strip().rstrip("/")
    if api_url and not re.match(r"https?://[^/\s]+", api_url):
        fail("TELEGRAM_API_URL must be an http(s):// address", 64)
    session = AiohttpSession(api=TelegramAPIServer.from_base(api_url)) if api_url else None
    try:
        bot = Bot(token, session=session)
    except TokenValidationError:
        fail("TELEGRAM_BOT_TOKEN does not look like a token from @BotFather (digits:letters)", 64)

    provider = Provider(base_url, api_key, model)
    history = History(database_url, keep)
    dispatcher = Dispatcher()
    dispatcher.include_router(build_router(bot, provider, history, RateLimit(per_minute, global_per_minute), system_prompt, allowed))

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
        await provider.check()
        stored = await history.prepare()
        me = await authenticate(bot, stop)
        if me is None:
            return
        try:
            await bot.set_my_commands([
                BotCommand(command="start", description="Start"),
                BotCommand(command="reset", description="Forget this chat's history"),
                BotCommand(command="ask", description="Ask a question (in groups)"),
                BotCommand(command="help", description="Help"),
            ])
        except Exception as error:
            log.warning("could not set the command menu: %s", type(error).__name__)
        allowed_updates = dispatcher.resolve_used_update_types()
        if mode == "webhook":
            await bot.set_webhook(f"{webhook_url}{WEBHOOK_PATH}", secret_token=webhook_secret, allowed_updates=allowed_updates)
        else:
            # A webhook left from webhook mode would make getUpdates fail with 409.
            await bot.delete_webhook(drop_pending_updates=False)
            polling = asyncio.create_task(
                dispatcher.start_polling(bot, handle_signals=False, close_bot_session=False, allowed_updates=allowed_updates)
            )
        state["ready"] = True
        log.info(
            "@%s is running (%s mode); model %s at %s; history %s; %s",
            me.username, mode, model, base_url, stored,
            f"{len(allowed)} allowed user(s)" if allowed else "open to everyone (set ALLOWED_USER_IDS to restrict)",
        )
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
            except RuntimeError:
                polling.cancel()
            await asyncio.wait([polling], timeout=10)
        await runner.cleanup()
        await provider.close()
        await history.close()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (SystemExit, KeyboardInterrupt):
        raise
    except BaseException:  # through the redacting formatter, never the default hook
        logging.getLogger("bot").exception("stopped")
        sys.exit(1)
