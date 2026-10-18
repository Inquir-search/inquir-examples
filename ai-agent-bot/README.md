# AI assistant in Telegram · ИИ-ассистент в Telegram

[Русский](#русский) · [English](#english)

## Русский

Telegram-бот на [aiogram 3](https://docs.aiogram.dev/), который отвечает с помощью ИИ-модели через любой OpenAI-совместимый Chat Completions API. Провайдера и ключ выбираете вы: `OPENAI_BASE_URL` — адрес API, `MODEL` — модель. Бот помнит короткую историю каждого чата и ограничивает частоту вопросов.

### Что понадобится

- Аккаунт Inquir: [регистрация](https://inquir.org/register), первые 14 дней бесплатно, без карты. Подтвердите email — без этого сервисы не создаются.
- [Node.js](https://nodejs.org) 22 или новее и git.
- Inquir CLI:

  ```sh
  npm i -g @inquir/compute-cli
  inquir login
  ```

  `inquir login` откроет браузер для входа. Проверить: `inquir whoami`.

### 1. Токен бота

1. В Telegram откройте [@BotFather](https://t.me/BotFather) и отправьте `/newbot`.
2. Придумайте имя бота и его username (должен заканчиваться на `bot`).
3. BotFather пришлёт токен вида `123456789:AA...`. Это секрет: не публикуйте его и не коммитьте в git.

Ещё понадобится **ключ API провайдера модели** (OpenAI или любой OpenAI-совместимый API). Для другого провайдера узнайте у него адрес OpenAI-совместимого API и название модели.

### 2. Код

```sh
git clone https://github.com/Inquir-search/inquir-examples.git
cd inquir-examples/ai-agent-bot
```

Или нажмите **Use this template** / **Fork** на GitHub и склонируйте свою копию — так удобнее менять код.

### 3. Приложение и секреты

```sh
inquir apps create my-assistant --set TELEGRAM_BOT_TOKEN=<токен> --set OPENAI_API_KEY=<ключ>
inquir apps update my-assistant --location nl
```

Секреты задаются переменными приложения (`--set`) и хранятся зашифрованными; их можно менять и в консоли: приложение → **Переменные**. `create` сам создаст проект для приложения и напишет его имя (`project: my-assistant (my-assistant-xxxxxxxx)`).

Другой провайдер: добавьте `--set OPENAI_BASE_URL=<адрес API> --set MODEL=<модель>`. Чтобы ботом пользовались только вы, добавьте `--set ALLOWED_USER_IDS=<ваш Telegram ID>` (бот покажет ID на `/start`).

Регион: Telegram-боты размещаются в Нидерландах. `--location nl` — настройка приложения (в консоли: «Настройки → Масштабирование → Регион»), она применяется при развёртывании.

### 4. Развёртывание

Из папки примера:

```sh
inquir apps deploy my-assistant
```

CLI упакует папку, соберёт образ по `Dockerfile` и выпустит релиз. Сборка занимает около минуты:

```text
Build ... queued for my-assistant
  Build succeeded in ...
Release ... queued for my-assistant (build ...)
Release ... is serving
  no reachable endpoint — the ports are internal to the host
```

«no reachable endpoint» — это нормально: боту не нужен публичный адрес, он сам ходит в Telegram.

### 5. Проверка

```sh
inquir apps logs my-assistant
```

Через несколько секунд после старта в логах появится строка вида:

```text
INFO bot: @your_bot is running (polling mode); model gpt-5-mini at https://api.openai.com/v1; history in memory; ...
```

Отправьте боту `/start`, затем любой вопрос. При старте бот пишет в логи, принял ли провайдер ключ. Выйти из логов — Ctrl+C (или `inquir apps logs my-assistant --no-follow`).

### 6. Обновление

- Изменили код (bot.py): снова `inquir apps deploy my-assistant` из папки примера.
- Изменили переменную: `inquir apps update my-assistant --set КЛЮЧ=значение`, затем `inquir apps redeploy my-assistant` — переменные применяются с новым релизом.

### 7. PostgreSQL (необязательно)

С базой история чатов переживает перезапуски.

```sh
inquir apps create my-assistant-db --template postgres --project <проект бота>
inquir apps connect my-assistant-db my-assistant
inquir apps redeploy my-assistant
```

`<проект бота>` — имя проекта из вывода `inquir apps create` (шаг 3). `connect` записывает в бота переменную `DATABASE_URL`. Если он ответит «has no verified private address yet», база ещё запускается — повторите через минуту. После `redeploy` в строке `is running` появится `PostgreSQL`.

### 8. Вебхук вместо long polling (необязательно)

```sh
inquir apps update my-assistant --ingress public
inquir apps status my-assistant
```

`status` покажет публичный адрес (`production: https://my-assistant-xxxxxx.apps.inquir.org`). Затем:

```sh
inquir apps update my-assistant --set BOT_MODE=webhook --set WEBHOOK_URL=https://my-assistant-xxxxxx.apps.inquir.org
inquir apps redeploy my-assistant
```

Бот сам зарегистрирует вебхук в Telegram и проверяет секрет каждого запроса. Секрет выводится из токена; свой можно задать в `WEBHOOK_SECRET` — 16–256 символов `A-Z a-z 0-9 _ -`, иначе бот остановится с кодом 64. Обратно на long polling: `inquir apps update my-assistant --set BOT_MODE=polling`, `inquir apps redeploy my-assistant`, при желании `inquir apps update my-assistant --ingress private`.

### Если что-то не так

- **`Telegram refused TELEGRAM_BOT_TOKEN (401 Unauthorized)`** в логах — неверный токен. Скопируйте его заново и выполните `inquir apps update my-assistant --set TELEGRAM_BOT_TOKEN=<токен>` и `inquir apps redeploy my-assistant`.
- **`cannot reach api.telegram.org`** повторяется — проверьте регион: `inquir apps status my-assistant` должен показывать `location: Netherlands`. Если нет — `inquir apps update my-assistant --location nl` и `inquir apps redeploy my-assistant`.
- **Бот молчит, хотя `is running` есть** — тот же токен используется где-то ещё (например, бот запущен локально): в логах будет `Conflict`. Остановите второй экземпляр.
- **Почему приложение не запускается** — `inquir apps describe my-assistant` объясняет состояние реплик и последние события.
- **Ответ «Провайдер модели не принял ключ API»** — проверьте `OPENAI_API_KEY`, `OPENAI_BASE_URL` и `MODEL`, затем `inquir apps redeploy my-assistant`.

### Развёртывание из своего форка на GitHub

Скоро. Сейчас развёртывание из GitHub доступно не всем workspace; пользуйтесь CLI, как выше.

### Удалить

```sh
inquir apps delete my-assistant
inquir apps delete my-assistant-db   # если добавляли базу
```

Пустой проект можно архивировать в консоли.

Полная инструкция: [Как задеплоить бота](https://inquir.org/docs/apps#telegram-bot).

### Переменные

| Переменная | Что делает |
|---|---|
| `TELEGRAM_BOT_TOKEN` | **обязательно**, токен от @BotFather |
| `OPENAI_API_KEY` | **обязательно**, ключ API провайдера модели |
| `OPENAI_BASE_URL` | адрес OpenAI-совместимого API, по умолчанию `https://api.openai.com/v1` |
| `MODEL` | модель, по умолчанию `gpt-5-mini` |
| `ALLOWED_USER_IDS` | Telegram ID через запятую; пусто — любой, кто найдёт бота, тратит ваш ключ |
| `SYSTEM_PROMPT` | инструкции ассистенту |
| `HISTORY_MESSAGES` | сколько последних сообщений чата передавать модели (20) |
| `RATE_LIMIT_PER_MINUTE` / `GLOBAL_RATE_LIMIT_PER_MINUTE` | вопросов в минуту на чат (6) и всего (60) |
| `BOT_MODE`, `WEBHOOK_URL`, `WEBHOOK_SECRET` | вебхук вместо long polling (шаг 8) |
| `DATABASE_URL` | PostgreSQL для истории (шаг 7) |

В личных чатах бот отвечает на любой текст, в группах — на `/ask <вопрос>`; `/reset` забывает историю чата.

## English

A Telegram bot on [aiogram 3](https://docs.aiogram.dev/) that answers with an AI model through any OpenAI-compatible Chat Completions API. You bring the provider and the key: `OPENAI_BASE_URL` is the API address, `MODEL` the model. It keeps a short history per chat and limits how often each chat can ask.

### What you need

- An Inquir account: [sign up](https://inquir.org/register), the first 14 days are free, no card. Confirm your email: services cannot be created before that.
- [Node.js](https://nodejs.org) 22 or newer, and git.
- The Inquir CLI:

  ```sh
  npm i -g @inquir/compute-cli
  inquir login
  ```

  `inquir login` opens the browser to sign in. Check with `inquir whoami`.

### 1. Bot token

1. In Telegram, open [@BotFather](https://t.me/BotFather) and send `/newbot`.
2. Pick the bot's name and username (it must end in `bot`).
3. BotFather replies with a token like `123456789:AA...`. It is a secret: do not publish it or commit it to git.

You also need your **model provider's API key** (OpenAI or any OpenAI-compatible API). For another provider, find its OpenAI-compatible API address and the model name.

### 2. Code

```sh
git clone https://github.com/Inquir-search/inquir-examples.git
cd inquir-examples/ai-agent-bot
```

Or press **Use this template** / **Fork** on GitHub and clone your copy, which is handier for changing the code.

### 3. App and secrets

```sh
inquir apps create my-assistant --set TELEGRAM_BOT_TOKEN=<token> --set OPENAI_API_KEY=<key>
inquir apps update my-assistant --location nl
```

Secrets are app variables (`--set`), stored encrypted; you can also change them in the console: the app → **Variables**. `create` makes a project for the app and prints its name (`project: my-assistant (my-assistant-xxxxxxxx)`).

Another provider: add `--set OPENAI_BASE_URL=<API address> --set MODEL=<model>`. To keep the bot to yourself, add `--set ALLOWED_USER_IDS=<your Telegram ID>` (the bot shows it on `/start`).

Location: Telegram bots run in the Netherlands. `--location nl` is a setting of the app (in the console: Settings → Scale → Region), applied when you deploy.

### 4. Deploy

From the example's folder:

```sh
inquir apps deploy my-assistant
```

The CLI packs the folder, builds the image from the `Dockerfile` and releases it. The build takes about a minute:

```text
Build ... queued for my-assistant
  Build succeeded in ...
Release ... queued for my-assistant (build ...)
Release ... is serving
  no reachable endpoint — the ports are internal to the host
```

"no reachable endpoint" is expected: the bot needs no public address, it connects to Telegram itself.

### 5. Check

```sh
inquir apps logs my-assistant
```

A few seconds after start the logs show a line like:

```text
INFO bot: @your_bot is running (polling mode); model gpt-5-mini at https://api.openai.com/v1; history in memory; ...
```

Send `/start` to the bot, then any question. At start the bot logs whether the provider accepted the key. Leave the logs with Ctrl+C (or use `inquir apps logs my-assistant --no-follow`).

### 6. Updates

- Changed the code (bot.py): run `inquir apps deploy my-assistant` again from the example's folder.
- Changed a variable: `inquir apps update my-assistant --set KEY=value`, then `inquir apps redeploy my-assistant`: variables apply with a new release.

### 7. PostgreSQL (optional)

With a database, the chat history survives restarts.

```sh
inquir apps create my-assistant-db --template postgres --project <the bot's project>
inquir apps connect my-assistant-db my-assistant
inquir apps redeploy my-assistant
```

`<the bot's project>` is the project name printed by `inquir apps create` (step 3). `connect` sets the bot's `DATABASE_URL`. If it answers "has no verified private address yet", the database is still starting: retry in a minute. After `redeploy`, the `is running` line mentions `PostgreSQL`.

### 8. Webhook instead of long polling (optional)

```sh
inquir apps update my-assistant --ingress public
inquir apps status my-assistant
```

`status` shows the public address (`production: https://my-assistant-xxxxxx.apps.inquir.org`). Then:

```sh
inquir apps update my-assistant --set BOT_MODE=webhook --set WEBHOOK_URL=https://my-assistant-xxxxxx.apps.inquir.org
inquir apps redeploy my-assistant
```

The bot registers the webhook with Telegram itself and checks the secret on every request. The secret is derived from the token; to set your own, use `WEBHOOK_SECRET` with 16–256 characters of `A-Z a-z 0-9 _ -`, or the bot stops with exit code 64. Back to long polling: `inquir apps update my-assistant --set BOT_MODE=polling`, `inquir apps redeploy my-assistant`, and optionally `inquir apps update my-assistant --ingress private`.

### Troubleshooting

- **`Telegram refused TELEGRAM_BOT_TOKEN (401 Unauthorized)`** in the logs: the token is wrong. Copy it again, then `inquir apps update my-assistant --set TELEGRAM_BOT_TOKEN=<token>` and `inquir apps redeploy my-assistant`.
- **`cannot reach api.telegram.org`** keeps repeating: check the location. `inquir apps status my-assistant` should say `location: Netherlands`; if not, `inquir apps update my-assistant --location nl` and `inquir apps redeploy my-assistant`.
- **The bot is silent although `is running` is there**: the same token is used elsewhere (a copy running locally, say), the logs show `Conflict`. Stop the other instance.
- **Why the app does not start**: `inquir apps describe my-assistant` explains the replicas' state and recent events.
- **"The model provider rejected the API key"**: check `OPENAI_API_KEY`, `OPENAI_BASE_URL` and `MODEL`, then `inquir apps redeploy my-assistant`.

### Deploy from your GitHub fork

Coming soon. Deploying from GitHub is not available to every workspace yet; use the CLI as above.

### Delete

```sh
inquir apps delete my-assistant
inquir apps delete my-assistant-db   # if you added the database
```

Archive the empty project in the console.

Full guide: [How to deploy a bot](https://inquir.org/docs/apps#telegram-bot).

### Variables

| Variable | What it does |
|---|---|
| `TELEGRAM_BOT_TOKEN` | **required**, the token from @BotFather |
| `OPENAI_API_KEY` | **required**, the model provider's API key |
| `OPENAI_BASE_URL` | an OpenAI-compatible API address, default `https://api.openai.com/v1` |
| `MODEL` | the model, default `gpt-5-mini` |
| `ALLOWED_USER_IDS` | comma-separated Telegram IDs; empty: anyone who finds the bot spends your key |
| `SYSTEM_PROMPT` | the assistant's instructions |
| `HISTORY_MESSAGES` | how many recent messages of a chat go to the model (20) |
| `RATE_LIMIT_PER_MINUTE` / `GLOBAL_RATE_LIMIT_PER_MINUTE` | questions per minute per chat (6) and in total (60) |
| `BOT_MODE`, `WEBHOOK_URL`, `WEBHOOK_SECRET` | a webhook instead of long polling (step 8) |
| `DATABASE_URL` | PostgreSQL for the history (step 7) |

In private chats it answers any text, in groups `/ask <question>`; `/reset` forgets the chat's history.
