# Telegram bot (Node.js) · Telegram-бот (Node.js)

[Русский](#русский) · [English](#english)

## Русский

Telegram-бот на [grammY](https://grammy.dev/) (Node.js 22): `/start`, `/help`, эхо текста и заметки `/note` / `/notes` в PostgreSQL. Работает через long polling, поэтому домен не нужен.

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

### 2. Код

```sh
git clone https://github.com/Inquir-search/inquir-examples.git
cd inquir-examples/telegram-bot-node
```

Или нажмите **Use this template** / **Fork** на GitHub и склонируйте свою копию — так удобнее менять код.

### 3. Приложение и секреты

```sh
inquir apps create my-bot --set TELEGRAM_BOT_TOKEN=<токен>
inquir apps update my-bot --location nl
```

Секреты задаются переменными приложения (`--set`) и хранятся зашифрованными; их можно менять и в консоли: приложение → **Переменные**. `create` сам создаст проект для приложения и напишет его имя (`project: my-bot (my-bot-xxxxxxxx)`).

Регион: Telegram-боты размещаются в Нидерландах. `--location nl` — настройка приложения (в консоли: «Настройки → Масштабирование → Регион»), она применяется при развёртывании.

### 4. Развёртывание

Из папки примера:

```sh
inquir apps deploy my-bot
```

CLI упакует папку, соберёт образ по `Dockerfile` и выпустит релиз. Сборка занимает около минуты:

```text
Build ... queued for my-bot
  Build succeeded in ...
Release ... queued for my-bot (build ...)
Release ... is serving
  no reachable endpoint — the ports are internal to the host
```

«no reachable endpoint» — это нормально: боту не нужен публичный адрес, он сам ходит в Telegram.

### 5. Проверка

```sh
inquir apps logs my-bot
```

Через несколько секунд после старта в логах появится строка вида:

```text
INFO @your_bot is running (polling mode)
```

Откройте бота в Telegram и отправьте `/start`, затем любой текст — бот его повторит. Выйти из логов — Ctrl+C (или `inquir apps logs my-bot --no-follow`).

### 6. Обновление

- Изменили код (bot.mjs): снова `inquir apps deploy my-bot` из папки примера.
- Изменили переменную: `inquir apps update my-bot --set КЛЮЧ=значение`, затем `inquir apps redeploy my-bot` — переменные применяются с новым релизом.

### 7. PostgreSQL (необязательно)

С базой заработают `/note` и `/notes`.

```sh
inquir apps create my-bot-db --template postgres --project <проект бота>
inquir apps connect my-bot-db my-bot
inquir apps redeploy my-bot
```

`<проект бота>` — имя проекта из вывода `inquir apps create` (шаг 3). `connect` записывает в бота переменную `DATABASE_URL`. Если он ответит «has no verified private address yet», база ещё запускается — повторите через минуту. После `redeploy` в строке `is running` появится `PostgreSQL`.

### 8. Вебхук вместо long polling (необязательно)

```sh
inquir apps update my-bot --ingress public
inquir apps status my-bot
```

`status` покажет публичный адрес (`production: https://my-bot-xxxxxx.apps.inquir.org`). Затем:

```sh
inquir apps update my-bot --set BOT_MODE=webhook --set WEBHOOK_URL=https://my-bot-xxxxxx.apps.inquir.org
inquir apps redeploy my-bot
```

Бот сам зарегистрирует вебхук в Telegram и проверяет секрет каждого запроса. Секрет выводится из токена; свой можно задать в `WEBHOOK_SECRET` — 16–256 символов `A-Z a-z 0-9 _ -`, иначе бот остановится с кодом 64. Обратно на long polling: `inquir apps update my-bot --set BOT_MODE=polling`, `inquir apps redeploy my-bot`, при желании `inquir apps update my-bot --ingress private`.

### Если что-то не так

- **`Telegram refused TELEGRAM_BOT_TOKEN (401 Unauthorized)`** в логах — неверный токен. Скопируйте его заново и выполните `inquir apps update my-bot --set TELEGRAM_BOT_TOKEN=<токен>` и `inquir apps redeploy my-bot`.
- **`cannot reach api.telegram.org`** повторяется — проверьте регион: `inquir apps status my-bot` должен показывать `location: Netherlands`. Если нет — `inquir apps update my-bot --location nl` и `inquir apps redeploy my-bot`.
- **Бот молчит, хотя `is running` есть** — тот же токен используется где-то ещё (например, бот запущен локально): в логах будет `Conflict`. Остановите второй экземпляр.
- **Почему приложение не запускается** — `inquir apps describe my-bot` объясняет состояние реплик и последние события.

### Развёртывание из своего форка на GitHub

Скоро. Сейчас развёртывание из GitHub доступно не всем workspace; пользуйтесь CLI, как выше.

### Удалить

```sh
inquir apps delete my-bot
inquir apps delete my-bot-db   # если добавляли базу
```

Пустой проект можно архивировать в консоли.

Полная инструкция: [Как задеплоить бота](https://inquir.org/docs/apps#telegram-bot).

## English

A Telegram bot on [grammY](https://grammy.dev/) (Node.js 22): `/start`, `/help`, text echo, and `/note` / `/notes` saved in PostgreSQL. It uses long polling, so it needs no domain.

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

### 2. Code

```sh
git clone https://github.com/Inquir-search/inquir-examples.git
cd inquir-examples/telegram-bot-node
```

Or press **Use this template** / **Fork** on GitHub and clone your copy, which is handier for changing the code.

### 3. App and secrets

```sh
inquir apps create my-bot --set TELEGRAM_BOT_TOKEN=<token>
inquir apps update my-bot --location nl
```

Secrets are app variables (`--set`), stored encrypted; you can also change them in the console: the app → **Variables**. `create` makes a project for the app and prints its name (`project: my-bot (my-bot-xxxxxxxx)`).

Location: Telegram bots run in the Netherlands. `--location nl` is a setting of the app (in the console: Settings → Scale → Region), applied when you deploy.

### 4. Deploy

From the example's folder:

```sh
inquir apps deploy my-bot
```

The CLI packs the folder, builds the image from the `Dockerfile` and releases it. The build takes about a minute:

```text
Build ... queued for my-bot
  Build succeeded in ...
Release ... queued for my-bot (build ...)
Release ... is serving
  no reachable endpoint — the ports are internal to the host
```

"no reachable endpoint" is expected: the bot needs no public address, it connects to Telegram itself.

### 5. Check

```sh
inquir apps logs my-bot
```

A few seconds after start the logs show a line like:

```text
INFO @your_bot is running (polling mode)
```

Open the bot in Telegram and send `/start`, then any text: the bot repeats it. Leave the logs with Ctrl+C (or use `inquir apps logs my-bot --no-follow`).

### 6. Updates

- Changed the code (bot.mjs): run `inquir apps deploy my-bot` again from the example's folder.
- Changed a variable: `inquir apps update my-bot --set KEY=value`, then `inquir apps redeploy my-bot`: variables apply with a new release.

### 7. PostgreSQL (optional)

With a database, `/note` and `/notes` start working.

```sh
inquir apps create my-bot-db --template postgres --project <the bot's project>
inquir apps connect my-bot-db my-bot
inquir apps redeploy my-bot
```

`<the bot's project>` is the project name printed by `inquir apps create` (step 3). `connect` sets the bot's `DATABASE_URL`. If it answers "has no verified private address yet", the database is still starting: retry in a minute. After `redeploy`, the `is running` line mentions `PostgreSQL`.

### 8. Webhook instead of long polling (optional)

```sh
inquir apps update my-bot --ingress public
inquir apps status my-bot
```

`status` shows the public address (`production: https://my-bot-xxxxxx.apps.inquir.org`). Then:

```sh
inquir apps update my-bot --set BOT_MODE=webhook --set WEBHOOK_URL=https://my-bot-xxxxxx.apps.inquir.org
inquir apps redeploy my-bot
```

The bot registers the webhook with Telegram itself and checks the secret on every request. The secret is derived from the token; to set your own, use `WEBHOOK_SECRET` with 16–256 characters of `A-Z a-z 0-9 _ -`, or the bot stops with exit code 64. Back to long polling: `inquir apps update my-bot --set BOT_MODE=polling`, `inquir apps redeploy my-bot`, and optionally `inquir apps update my-bot --ingress private`.

### Troubleshooting

- **`Telegram refused TELEGRAM_BOT_TOKEN (401 Unauthorized)`** in the logs: the token is wrong. Copy it again, then `inquir apps update my-bot --set TELEGRAM_BOT_TOKEN=<token>` and `inquir apps redeploy my-bot`.
- **`cannot reach api.telegram.org`** keeps repeating: check the location. `inquir apps status my-bot` should say `location: Netherlands`; if not, `inquir apps update my-bot --location nl` and `inquir apps redeploy my-bot`.
- **The bot is silent although `is running` is there**: the same token is used elsewhere (a copy running locally, say), the logs show `Conflict`. Stop the other instance.
- **Why the app does not start**: `inquir apps describe my-bot` explains the replicas' state and recent events.

### Deploy from your GitHub fork

Coming soon. Deploying from GitHub is not available to every workspace yet; use the CLI as above.

### Delete

```sh
inquir apps delete my-bot
inquir apps delete my-bot-db   # if you added the database
```

Archive the empty project in the console.

Full guide: [How to deploy a bot](https://inquir.org/docs/apps#telegram-bot).
