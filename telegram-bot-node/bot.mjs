// Telegram bot on grammY: /start, /help, echo, and notes in PostgreSQL.
//
// Configuration (Variables of the app; nothing else is read):
//   TELEGRAM_BOT_TOKEN  required. The token @BotFather gave you.
//   BOT_MODE            polling (default) or webhook.
//   WEBHOOK_URL         webhook mode: the app's public HTTPS address, e.g.
//                       https://my-bot.example.com (Networking -> generate a domain).
//   WEBHOOK_SECRET      optional; checked on every webhook call. Derived from the
//                       token when unset.
//   DATABASE_URL        optional. Set when a PostgreSQL service is connected:
//                       turns on /note and /notes.
//   PORT                the HTTP port (default 8080): GET /healthz, and the
//                       webhook in webhook mode.
//   TELEGRAM_API_URL    optional: a self-hosted Bot API server instead of
//                       https://api.telegram.org.
//
// Exit codes: 64 = a variable is missing or malformed, 78 = Telegram refused the token.
import { createHmac } from 'node:crypto';
import { createServer } from 'node:http';
import { setTimeout as sleep } from 'node:timers/promises';
import { Bot, GrammyError, HttpError, webhookCallback } from 'grammy';
import pg from 'pg';

const WEBHOOK_PATH = '/telegram/webhook';
const MAX_WEBHOOK_BODY = 1024 * 1024;
const MAX_NOTE_LENGTH = 1000;
const NOTES_SHOWN = 10;
const NOTE_PREVIEW = 300; // ten previews stay below Telegram's 4096 characters

const env = process.env;
const token = (env.TELEGRAM_BOT_TOKEN ?? '').trim();
let webhookSecret = (env.WEBHOOK_SECRET ?? '').trim();

// Never lets a secret reach the logs.
const secrets = [token, webhookSecret].filter((secret) => secret.length >= 6); // a shorter one would garble every line
const redact = (text) => secrets.reduce((out, secret) => out.split(secret).join('***'), String(text));
const log = (level, message) => console[level === 'error' ? 'error' : 'log'](`${new Date().toISOString()} ${level.toUpperCase()} ${redact(message)}`);
const fail = (message, code) => { log('error', message); process.exit(code); };
/** What an error may say in Logs: its name, code and Telegram's status, never its message (a request URL holds the token). */
const describe = (error) => error instanceof GrammyError ? `${error.error_code} ${error.description}`
  : [error?.name, error?.error?.code ?? error?.code].filter(Boolean).join(' ') || 'error';
// Whatever escapes is reported the same way, instead of Node printing the raw error.
process.on('uncaughtException', (error) => fail(`stopped: ${describe(error)}`, 1));
process.on('unhandledRejection', (error) => fail(`stopped: ${describe(error)}`, 1));

if (!token) fail('set TELEGRAM_BOT_TOKEN in Variables (the token from @BotFather), then redeploy', 64);
if (!/^\d+:[\w-]+$/.test(token)) fail('TELEGRAM_BOT_TOKEN does not look like a token from @BotFather (digits:letters)', 64);
const mode = (env.BOT_MODE ?? '').trim().toLowerCase() || 'polling';
if (mode !== 'polling' && mode !== 'webhook') fail(`BOT_MODE must be polling or webhook, got "${mode}"`, 64);
const webhookUrl = (env.WEBHOOK_URL ?? '').trim().replace(/\/+$/, '');
if (mode === 'webhook' && !webhookUrl.startsWith('https://')) {
  fail("webhook mode needs WEBHOOK_URL, the app's public https:// address (Networking -> generate a domain)", 64);
}
if (!webhookSecret) {
  webhookSecret = createHmac('sha256', token).update('inquir-telegram-webhook').digest('hex');
  secrets.push(webhookSecret);
}
if (!/^[A-Za-z0-9_-]{16,256}$/.test(webhookSecret)) fail('WEBHOOK_SECRET must be 16-256 characters of A-Z, a-z, 0-9, _ and -', 64);
const port = Number(env.PORT || 8080);
if (!Number.isInteger(port) || port < 1 || port > 65535) fail('PORT must be a number', 64);

const TEXTS = {
  ru: {
    start: (name, help) => `Привет, ${name}! Я эхо-бот: пришлите текст, и я его повторю.\n\n${help}`,
    help: 'Команды:\n/start — начать\n/help — эта справка\n/note <текст> — сохранить заметку\n/notes — последние заметки',
    noDb: 'Заметкам нужна база данных: добавьте PostgreSQL в проект и подключите её к боту (переменная DATABASE_URL).',
    dbError: 'База данных сейчас недоступна, попробуйте позже.',
    noteUsage: 'Напишите текст после команды: /note купить хлеб',
    noteLong: (limit) => `Заметка длиннее ${limit} символов.`,
    noteSaved: (count) => `Сохранено. Всего заметок: ${count}.`,
    notesEmpty: 'Заметок пока нет. Добавьте: /note текст',
    notes: (items) => `Последние заметки:\n${items}`,
    notText: 'Я понимаю только текст.',
  },
  en: {
    start: (name, help) => `Hi, ${name}! I am an echo bot: send me text and I will repeat it.\n\n${help}`,
    help: 'Commands:\n/start - start\n/help - this help\n/note <text> - save a note\n/notes - recent notes',
    noDb: 'Notes need a database: add PostgreSQL to the project and connect it to the bot (variable DATABASE_URL).',
    dbError: 'The database is unavailable right now, try again later.',
    noteUsage: 'Put the text after the command: /note buy bread',
    noteLong: (limit) => `The note is longer than ${limit} characters.`,
    noteSaved: (count) => `Saved. Notes in total: ${count}.`,
    notesEmpty: 'No notes yet. Add one: /note text',
    notes: (items) => `Recent notes:\n${items}`,
    notText: 'I only understand text.',
  },
};
const texts = (ctx) => (ctx.from?.language_code ?? '').toLowerCase().startsWith('ru') ? TEXTS.ru : TEXTS.en;

/** Notes in PostgreSQL. Connects on first use and again after a failure. */
class Notes {
  constructor(connectionString) {
    this.pool = new pg.Pool({ connectionString, max: 4, connectionTimeoutMillis: 10_000, idleTimeoutMillis: 30_000 });
    // An idle connection that breaks must not crash the bot.
    this.pool.on('error', (error) => log('warn', `database connection lost: ${error.code ?? error.name}`));
    this.ready = null;
  }

  schema() {
    this.ready ??= (async () => {
      await this.pool.query(
        'CREATE TABLE IF NOT EXISTS bot_notes (id BIGSERIAL PRIMARY KEY, chat_id BIGINT NOT NULL, text TEXT NOT NULL,'
        + ' created_at TIMESTAMPTZ NOT NULL DEFAULT now())',
      );
      await this.pool.query('CREATE INDEX IF NOT EXISTS bot_notes_chat ON bot_notes (chat_id, id)');
    })().catch((error) => { this.ready = null; throw error; });
    return this.ready;
  }

  async add(chatId, text) {
    await this.schema();
    await this.pool.query('INSERT INTO bot_notes (chat_id, text) VALUES ($1, $2)', [chatId, text]);
    const { rows } = await this.pool.query('SELECT count(*)::int AS count FROM bot_notes WHERE chat_id = $1', [chatId]);
    return rows[0].count;
  }

  async recent(chatId) {
    await this.schema();
    const { rows } = await this.pool.query('SELECT text FROM bot_notes WHERE chat_id = $1 ORDER BY id DESC LIMIT $2', [chatId, NOTES_SHOWN]);
    return rows.map((row) => row.text);
  }

  close() { return this.pool.end(); }
}

const databaseUrl = (env.DATABASE_URL ?? '').trim();
const notes = databaseUrl ? new Notes(databaseUrl) : null;
const apiRoot = (env.TELEGRAM_API_URL ?? '').trim().replace(/\/+$/, '');
if (apiRoot && !/^https?:\/\/[^/\s]+/.test(apiRoot)) fail('TELEGRAM_API_URL must be an http(s):// address', 64);
// 60 s per request: above long polling's 30 s, far below grammY's default of 500 s for an unreachable host.
const bot = new Bot(token, { client: { timeoutSeconds: 60, ...(apiRoot ? { apiRoot } : {}) } });

bot.command('start', (ctx) => ctx.reply(texts(ctx).start(ctx.from?.first_name ?? 'there', texts(ctx).help)));
bot.command('help', (ctx) => ctx.reply(texts(ctx).help));
bot.command('note', async (ctx) => {
  const t = texts(ctx);
  if (!notes) return ctx.reply(t.noDb);
  const text = ctx.match.trim();
  if (!text) return ctx.reply(t.noteUsage);
  if (text.length > MAX_NOTE_LENGTH) return ctx.reply(t.noteLong(MAX_NOTE_LENGTH));
  let count;
  try {
    count = await notes.add(ctx.chat.id, text);
  } catch (error) {
    log('warn', `could not save a note: ${error.code ?? error.name}`);
    return ctx.reply(t.dbError);
  }
  return ctx.reply(t.noteSaved(count));
});
bot.command('notes', async (ctx) => {
  const t = texts(ctx);
  if (!notes) return ctx.reply(t.noDb);
  let items;
  try {
    items = await notes.recent(ctx.chat.id);
  } catch (error) {
    log('warn', `could not read notes: ${error.code ?? error.name}`);
    return ctx.reply(t.dbError);
  }
  const preview = (item) => item.length > NOTE_PREVIEW ? `${item.slice(0, NOTE_PREVIEW)}…` : item;
  return ctx.reply(items.length ? t.notes(items.map((item) => `- ${preview(item)}`).join('\n')) : t.notesEmpty);
});
// Echo in private chats only: in a group, service messages (joins, pins) and chatter are not for the bot.
const privateChat = bot.chatType('private');
privateChat.on('message:text', (ctx) => ctx.reply(ctx.message.text));
privateChat.on('message', (ctx) => ctx.reply(texts(ctx).notText));
bot.catch(({ error, ctx }) => log('warn', `update ${ctx.update.update_id} failed: ${describe(error)}`));

let ready = false;
// onTimeout 'return': a slow update answers Telegram and keeps running instead of throwing.
const handleWebhook = mode === 'webhook' ? webhookCallback(bot, 'http', { secretToken: webhookSecret, onTimeout: 'return' }) : null;
const server = createServer((req, res) => {
  const path = (req.url ?? '').split('?')[0];
  if (req.method === 'GET' && path === '/healthz') {
    res.writeHead(ready ? 200 : 503, { 'content-type': 'application/json' });
    return res.end(JSON.stringify({ ok: ready, mode }));
  }
  if (handleWebhook && req.method === 'POST' && path === WEBHOOK_PATH) {
    const length = Number(req.headers['content-length']);
    if (!Number.isFinite(length) || length > MAX_WEBHOOK_BODY) {
      res.writeHead(Number.isFinite(length) ? 413 : 411);
      return res.end();
    }
    return Promise.resolve(handleWebhook(req, res)).catch((error) => {
      log('warn', `webhook update failed: ${describe(error)}`);
      if (!res.headersSent) res.writeHead(500);
      res.end();
    });
  }
  res.writeHead(404);
  res.end();
});
server.listen(port, '0.0.0.0');

let stopping = false;
async function shutdown() {
  if (stopping) return;
  stopping = true;
  ready = false;
  log('info', 'shutting down');
  if (mode === 'polling' && bot.isRunning()) await bot.stop().catch(() => {});
  await new Promise((resolve) => server.close(resolve));
  if (notes) await notes.close().catch(() => {});
  process.exit(0);
}
process.once('SIGTERM', shutdown);
process.once('SIGINT', shutdown);

/** getMe until it answers: a refused token ends the process, a network error is retried. */
async function authenticate() {
  for (let delay = 2; !stopping; delay = Math.min(delay * 2, 60)) {
    try {
      // getMe directly: bot.init() would retry network errors silently, forever.
      bot.botInfo = await bot.api.getMe();
      return true;
    } catch (error) {
      if (error instanceof GrammyError && error.error_code === 401) {
        fail('Telegram refused TELEGRAM_BOT_TOKEN (401 Unauthorized). Copy the token from @BotFather into Variables and redeploy.', 78);
      }
      if (error instanceof GrammyError && error.error_code === 429) delay = Math.max(delay, error.parameters.retry_after ?? delay);
      else if (error instanceof HttpError) {
        log('warn', `cannot reach api.telegram.org (${describe(error)}); retrying in ${delay} s`);
      } else log('warn', `getMe failed (${describe(error)}); retrying in ${delay} s`);
    }
    await sleep(delay * 1000);
  }
  return false;
}

// A failure below (setWebhook refused, say) is logged by name and code only.
async function run() {
  if (!await authenticate()) return;
  await bot.api.setMyCommands([
    { command: 'start', description: 'Start' },
    { command: 'help', description: 'Help' },
    { command: 'note', description: 'Save a note' },
    { command: 'notes', description: 'Recent notes' },
  ]).catch((error) => log('warn', `could not set the command menu: ${describe(error)}`));
  const allowedUpdates = ['message'];
  const started = () => {
    ready = true;
    log('info', `@${bot.botInfo.username} is running (${mode} mode)${notes ? ', notes in PostgreSQL' : ''}`);
  };
  if (mode === 'webhook') {
    await bot.api.setWebhook(`${webhookUrl}${WEBHOOK_PATH}`, { secret_token: webhookSecret, allowed_updates: allowedUpdates });
    started();
    return;
  }
  // bot.start() removes a webhook left from webhook mode, then long-polls until bot.stop().
  await bot.start({ allowed_updates: allowedUpdates, drop_pending_updates: false, onStart: started });
}
run().catch((error) => { if (!stopping) fail(`stopped: ${describe(error)}`, 1); });
