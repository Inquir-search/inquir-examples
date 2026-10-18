// Bot for the MAX messenger on the official SDK (@maxhub/max-bot-api):
// /start, /help, echo, and notes in PostgreSQL.
//
// Configuration (Variables of the app; nothing else is read):
//   MAX_BOT_TOKEN    required. The bot's token: business.max.ru -> Чат-боты -> ⋮ -> Настройки.
//   BOT_MODE         polling (default) or webhook. MAX recommends webhooks in
//                    production; long polling suits development and small bots.
//   WEBHOOK_URL      webhook mode: the app's public HTTPS address on port 443, e.g.
//                    https://my-bot.example.com (Networking -> generate a domain).
//   WEBHOOK_SECRET   optional; MAX sends it in X-Max-Bot-Api-Secret on every call.
//                    Derived from the token when unset.
//   DATABASE_URL     optional. Set when a PostgreSQL service is connected: turns on
//                    /note and /notes.
//   MAX_API_URL      optional, default https://platform-api2.max.ru (the address the
//                    MAX docs name).
//   PORT             the HTTP port (default 8080): GET /healthz, and the webhook.
//
// TLS: platform-api2.max.ru has a certificate from the Russian Trusted Root CA
// (Минцифры), which is not in the usual trust stores; MAX asks clients to trust
// it. This bot trusts it only for its own requests to the MAX API, next to the
// usual roots (russian-trusted-root-ca.pem, see the Dockerfile); every other
// connection keeps the default trust store.
//
// Exit codes: 64 = a variable is missing or malformed, 78 = MAX refused the token.
import { createHmac } from 'node:crypto';
import { readFileSync } from 'node:fs';
import { createServer } from 'node:http';
import { rootCertificates } from 'node:tls';
import { setTimeout as sleep } from 'node:timers/promises';
import { Bot, MaxError } from '@maxhub/max-bot-api';
import pg from 'pg';
import { Agent, fetch as undiciFetch } from 'undici';

const WEBHOOK_PATH = '/max/webhook';
const MAX_WEBHOOK_BODY = 1024 * 1024;
const MAX_NOTE_LENGTH = 1000;
const NOTES_SHOWN = 10;
const NOTE_PREVIEW = 300; // ten previews stay below MAX's 4000 characters
const UPDATE_TYPES = ['message_created', 'bot_started'];

const env = process.env;
const token = (env.MAX_BOT_TOKEN ?? '').trim();
let webhookSecret = (env.WEBHOOK_SECRET ?? '').trim();

// Never lets a secret reach the logs.
const secrets = [token, webhookSecret].filter((secret) => secret.length >= 6); // a shorter one would garble every line
const redact = (text) => secrets.reduce((out, secret) => out.split(secret).join('***'), String(text));
const log = (level, message) => console[level === 'error' ? 'error' : 'log'](`${new Date().toISOString()} ${level.toUpperCase()} ${redact(message)}`);
const fail = (message, code) => { log('error', message); process.exit(code); };
// The SDK prints some errors itself (console.error); they pass through the same redaction.
const sdkConsoleError = console.error.bind(console);
console.error = (...parts) => sdkConsoleError(redact(parts.map((part) => part instanceof Error ? `${part.name}: ${part.message}` : String(part)).join(' ')));
/** What an error may say in Logs: status and code, or its name and system code, never its message. */
const reason = (error) => error instanceof MaxError ? `${error.status} ${error.code}` : error?.cause?.code ?? error?.code ?? error?.name ?? 'error';
// Whatever escapes is reported the same way, instead of Node printing the raw error.
process.on('uncaughtException', (error) => fail(`stopped: ${reason(error)}`, 1));
process.on('unhandledRejection', (error) => fail(`stopped: ${reason(error)}`, 1));

if (!token) fail('set MAX_BOT_TOKEN in Variables (business.max.ru -> Чат-боты -> Настройки), then redeploy', 64);
const mode = (env.BOT_MODE ?? '').trim().toLowerCase() || 'polling';
if (mode !== 'polling' && mode !== 'webhook') fail(`BOT_MODE must be polling or webhook, got "${mode}"`, 64);
const webhookUrl = (env.WEBHOOK_URL ?? '').trim().replace(/\/+$/, '');
if (mode === 'webhook' && !webhookUrl.startsWith('https://')) {
  fail("webhook mode needs WEBHOOK_URL, the app's public https:// address (Networking -> generate a domain)", 64);
}
if (!webhookSecret) {
  // MAX accepts 5-256 characters of [A-Za-z0-9_-].
  webhookSecret = createHmac('sha256', token).update('inquir-max-webhook').digest('hex');
  secrets.push(webhookSecret);
}
if (!/^[A-Za-z0-9_-]{16,256}$/.test(webhookSecret)) fail('WEBHOOK_SECRET must be 16-256 characters of A-Z, a-z, 0-9, _ and -', 64);
const apiUrl = (env.MAX_API_URL ?? '').trim().replace(/\/+$/, '') || 'https://platform-api2.max.ru';
if (!/^https:\/\/|^http:\/\/(127\.0\.0\.1|localhost)[:/]/.test(apiUrl)) fail('MAX_API_URL must start with https://', 64);
const port = Number(env.PORT || 8080);
if (!Number.isInteger(port) || port < 1 || port > 65535) fail('PORT must be a number', 64);

// The usual roots plus the Russian Trusted Root CA, for the MAX API only.
const russianRoot = readFileSync(new URL('./russian-trusted-root-ca.pem', import.meta.url), 'utf8');
const maxAgent = new Agent({ connect: { ca: [...rootCertificates, russianRoot] } });
const maxFetch = (url, init) => undiciFetch(url, { ...init, dispatcher: maxAgent });

const TEXTS = {
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
};

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
const bot = new Bot(token, { clientOptions: { baseUrl: apiUrl, fetch: maxFetch } });

const greet = (ctx) => ctx.reply(TEXTS.start(ctx.user?.first_name || ctx.user?.name || 'друг', TEXTS.help));
// "Начать" in a new chat with the bot arrives as bot_started, not as a message.
bot.on('bot_started', greet);
bot.command('start', greet);
bot.command('help', (ctx) => ctx.reply(TEXTS.help));
bot.command(/^note(?:\s+([\s\S]*))?$/, async (ctx) => {
  if (!notes) return ctx.reply(TEXTS.noDb);
  const text = (ctx.match?.[1] ?? '').trim();
  if (!text) return ctx.reply(TEXTS.noteUsage);
  if (text.length > MAX_NOTE_LENGTH) return ctx.reply(TEXTS.noteLong(MAX_NOTE_LENGTH));
  let count;
  try {
    count = await notes.add(ctx.chatId, text);
  } catch (error) {
    log('warn', `could not save a note: ${error.code ?? error.name}`);
    return ctx.reply(TEXTS.dbError);
  }
  return ctx.reply(TEXTS.noteSaved(count));
});
bot.command('notes', async (ctx) => {
  if (!notes) return ctx.reply(TEXTS.noDb);
  let items;
  try {
    items = await notes.recent(ctx.chatId);
  } catch (error) {
    log('warn', `could not read notes: ${error.code ?? error.name}`);
    return ctx.reply(TEXTS.dbError);
  }
  const preview = (item) => item.length > NOTE_PREVIEW ? `${item.slice(0, NOTE_PREVIEW)}…` : item;
  return ctx.reply(items.length ? TEXTS.notes(items.map((item) => `- ${preview(item)}`).join('\n')) : TEXTS.notesEmpty);
});
bot.on('message_created', (ctx) => {
  if (ctx.message.sender?.is_bot) return undefined; // never answer a bot, ourselves included
  // Echo in dialogs only: in a group chat, other members' messages are not for the bot.
  if (ctx.message.recipient?.chat_type && ctx.message.recipient.chat_type !== 'dialog') return undefined;
  const text = ctx.message.body?.text;
  return ctx.reply(text ? text : TEXTS.notText);
});
bot.catch((error, ctx) => log('warn', `update ${ctx.update?.update_type ?? '?'} failed: ${reason(error)}`));

let ready = false;
let handleWebhook = null;
const server = createServer((req, res) => {
  const path = (req.url ?? '').split('?')[0];
  if (req.method === 'GET' && path === '/healthz') {
    res.writeHead(ready ? 200 : 503, { 'content-type': 'application/json' });
    return res.end(JSON.stringify({ ok: ready, mode }));
  }
  if (handleWebhook && req.method === 'POST' && path === WEBHOOK_PATH) {
    if (Number(req.headers['content-length']) > MAX_WEBHOOK_BODY) {
      res.writeHead(413);
      return res.end();
    }
    // A body without Content-Length (chunked) is counted as it arrives; the SDK reads the same chunks.
    let received = 0;
    req.on('data', (chunk) => {
      received += chunk.length;
      if (received > MAX_WEBHOOK_BODY) req.destroy();
    });
    return handleWebhook(req, res); // checks X-Max-Bot-Api-Secret, answers 404 when it does not match
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
  if (mode === 'polling') bot.stopPolling();
  await new Promise((resolve) => server.close(resolve));
  if (notes) await notes.close().catch(() => {});
  await maxAgent.close().catch(() => {});
  process.exit(0);
}
process.once('SIGTERM', shutdown);
process.once('SIGINT', shutdown);

/** GET /me until it answers: a refused token ends the process, a network error is retried. */
async function authenticate() {
  for (let delay = 2; !stopping; delay = Math.min(delay * 2, 60)) {
    try {
      bot.botInfo = await bot.api.getMyInfo();
      return true;
    } catch (error) {
      if (error instanceof MaxError && error.status === 401) {
        fail('MAX refused MAX_BOT_TOKEN (401 Unauthorized). Copy the token from business.max.ru (Чат-боты -> Настройки) into Variables and redeploy.', 78);
      }
      log('warn', `cannot reach the MAX API at ${apiUrl} (${reason(error)}); retrying in ${delay} s`);
    }
    await sleep(delay * 1000);
  }
  return false;
}

async function run() {
  if (!await authenticate()) return;
  await bot.api.setMyCommands([
    { name: 'start', description: 'Начать' },
    { name: 'help', description: 'Справка' },
    { name: 'note', description: 'Сохранить заметку' },
    { name: 'notes', description: 'Последние заметки' },
  ]).catch((error) => log('warn', `could not set the command menu: ${reason(error)}`));
  const name = bot.botInfo.username ? `@${bot.botInfo.username}` : bot.botInfo.first_name ?? bot.botInfo.name;
  if (mode === 'webhook') {
    // Subscribes WEBHOOK_URL + WEBHOOK_PATH (removing other subscriptions) and returns the request handler.
    handleWebhook = await bot.createWebhook({ domain: webhookUrl, path: WEBHOOK_PATH, secret: webhookSecret, allowedUpdates: UPDATE_TYPES });
    ready = true;
    log('info', `${name} is running (webhook mode)${notes ? ', notes in PostgreSQL' : ''}`);
    return;
  }
  ready = true;
  log('info', `${name} is running (polling mode)${notes ? ', notes in PostgreSQL' : ''}`);
  // Removes webhook subscriptions (updates would not reach long polling), then polls until stopPolling().
  // The SDK retries network errors and 429/5xx itself; anything else (a token revoked meanwhile) ends the
  // loop, and the process exits so the platform restarts it and the start-up check reports why.
  await bot.start({ mode: 'polling', options: { allowedUpdates: UPDATE_TYPES, retry: false } });
  if (!stopping) fail('polling stopped; restarting', 1);
}
run().catch((error) => fail(`stopped: ${reason(error)}`, 1));
