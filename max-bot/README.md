# MAX bot · Бот для MAX

[Русский](#русский) · [English](#english)

## Русский

Бот для мессенджера [MAX](https://max.ru) на официальном SDK [`@maxhub/max-bot-api`](https://github.com/max-messenger/max-bot-api-client-ts) (Node.js 22): `/start` (и кнопка «Начать»), `/help`, эхо текста и заметки `/note` / `/notes` в PostgreSQL.

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

Создавать ботов в MAX могут верифицированные организации, ИП и самозанятые — резиденты РФ ([документация MAX](https://dev.max.ru/docs)).

1. Подключитесь к [платформе MAX для партнёров](https://business.max.ru) и пройдите верификацию.
2. Создайте бота; после модерации он станет доступен пользователям.
3. Токен: **Чат-боты → ⋮ → Настройки**. Это секрет: не публикуйте его и не коммитьте в git.

### 2. Код

```sh
git clone https://github.com/Inquir-search/inquir-examples.git
cd inquir-examples/max-bot
```

Или нажмите **Use this template** / **Fork** на GitHub и склонируйте свою копию — так удобнее менять код.

### 3. Приложение и секреты

```sh
inquir apps create my-max-bot --set MAX_BOT_TOKEN=<токен>
inquir apps update my-max-bot --location ru
```

Секреты задаются переменными приложения (`--set`) и хранятся зашифрованными; их можно менять и в консоли: приложение → **Переменные**. `create` сам создаст проект для приложения и напишет его имя (`project: my-max-bot (my-max-bot-xxxxxxxx)`).

Регион: MAX — российский сервис, поэтому бот размещается в России. `--location ru` — настройка приложения (в консоли: «Настройки → Масштабирование → Регион»), она применяется при развёртывании.

### 4. Развёртывание

Из папки примера:

```sh
inquir apps deploy my-max-bot
```

CLI упакует папку, соберёт образ по `Dockerfile` и выпустит релиз. Сборка занимает около минуты:

```text
Build ... queued for my-max-bot
  Build succeeded in ...
Release ... queued for my-max-bot (build ...)
Release ... is serving
  no reachable endpoint — the ports are internal to the host
```

«no reachable endpoint» — это нормально: боту не нужен публичный адрес, он сам ходит в MAX.

### 5. Проверка

```sh
inquir apps logs my-max-bot
```

Через несколько секунд после старта в логах появится строка вида:

```text
INFO @your_bot is running (polling mode)
```

Откройте бота в MAX и нажмите «Начать», затем отправьте любой текст — бот его повторит. Выйти из логов — Ctrl+C (или `inquir apps logs my-max-bot --no-follow`).

### 6. Обновление

- Изменили код (bot.mjs): снова `inquir apps deploy my-max-bot` из папки примера.
- Изменили переменную: `inquir apps update my-max-bot --set КЛЮЧ=значение`, затем `inquir apps redeploy my-max-bot` — переменные применяются с новым релизом.

### 7. PostgreSQL (необязательно)

С базой заработают `/note` и `/notes`.

```sh
inquir apps create my-max-bot-db --template postgres --project <проект бота>
inquir apps connect my-max-bot-db my-max-bot
inquir apps redeploy my-max-bot
```

`<проект бота>` — имя проекта из вывода `inquir apps create` (шаг 3). `connect` записывает в бота переменную `DATABASE_URL`. Если он ответит «has no verified private address yet», база ещё запускается — повторите через минуту. После `redeploy` в строке `is running` появится `PostgreSQL`.

### 8. Вебхук вместо long polling (необязательно)

```sh
inquir apps update my-max-bot --ingress public
inquir apps status my-max-bot
```

`status` покажет публичный адрес (`production: https://my-max-bot-xxxxxx.apps.inquir.org`). Затем:

```sh
inquir apps update my-max-bot --set BOT_MODE=webhook --set WEBHOOK_URL=https://my-max-bot-xxxxxx.apps.inquir.org
inquir apps redeploy my-max-bot
```

Бот сам зарегистрирует вебхук в MAX (MAX рекомендует вебхуки для продакшена) и проверяет секрет каждого запроса. Секрет выводится из токена; свой можно задать в `WEBHOOK_SECRET` — 16–256 символов `A-Z a-z 0-9 _ -`, иначе бот остановится с кодом 64. Обратно на long polling: `inquir apps update my-max-bot --set BOT_MODE=polling`, `inquir apps redeploy my-max-bot`, при желании `inquir apps update my-max-bot --ingress private`.

### Если что-то не так

- **`MAX refused MAX_BOT_TOKEN (401 Unauthorized)`** в логах — неверный токен. Скопируйте его заново и выполните `inquir apps update my-max-bot --set MAX_BOT_TOKEN=<токен>` и `inquir apps redeploy my-max-bot`.
- **`cannot reach the MAX API`** повторяется — проверьте регион: `inquir apps status my-max-bot` должен показывать `location: Russia`. Если нет — `inquir apps update my-max-bot --location ru` и `inquir apps redeploy my-max-bot`.
- **Бот молчит, хотя `is running` есть** — тот же токен используется где-то ещё (например, бот запущен локально): Остановите второй экземпляр.
- **Почему приложение не запускается** — `inquir apps describe my-max-bot` объясняет состояние реплик и последние события.

### Развёртывание из своего форка на GitHub

Скоро. Сейчас развёртывание из GitHub доступно не всем workspace; пользуйтесь CLI, как выше.

### Удалить

```sh
inquir apps delete my-max-bot
inquir apps delete my-max-bot-db   # если добавляли базу
```

Пустой проект можно архивировать в консоли.

Полная инструкция: [Как задеплоить бота](https://inquir.org/docs/apps#telegram-bot).

### TLS

Сертификат `platform-api2.max.ru` выпущен Russian Trusted Root CA (Минцифры), и MAX просит клиентов доверять этому корню. Бот доверяет ему (`russian-trusted-root-ca.pem`, SHA-256 `D2:6D:2D:02:31:B7:C3:9F:92:CC:73:85:12:BA:54:10:35:19:E4:40:5D:68:B5:BD:70:3E:97:88:CA:8E:CF:31`, опубликован на gu-st.ru) только в своих запросах к MAX API, не на уровне системы.

## English

A bot for the [MAX](https://max.ru) messenger on the official SDK [`@maxhub/max-bot-api`](https://github.com/max-messenger/max-bot-api-client-ts) (Node.js 22): `/start` (and the Start button), `/help`, text echo, and `/note` / `/notes` saved in PostgreSQL.

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

MAX gives bots to verified organizations, sole proprietors and self-employed residents of Russia ([MAX docs](https://dev.max.ru/docs)).

1. Join the [MAX partner platform](https://business.max.ru) and get verified.
2. Create the bot; it becomes available to users after moderation.
3. Token: **Chat bots → ⋮ → Settings**. It is a secret: do not publish it or commit it to git.

### 2. Code

```sh
git clone https://github.com/Inquir-search/inquir-examples.git
cd inquir-examples/max-bot
```

Or press **Use this template** / **Fork** on GitHub and clone your copy, which is handier for changing the code.

### 3. App and secrets

```sh
inquir apps create my-max-bot --set MAX_BOT_TOKEN=<token>
inquir apps update my-max-bot --location ru
```

Secrets are app variables (`--set`), stored encrypted; you can also change them in the console: the app → **Variables**. `create` makes a project for the app and prints its name (`project: my-max-bot (my-max-bot-xxxxxxxx)`).

Location: MAX is a Russian service, so the bot runs in Russia. `--location ru` is a setting of the app (in the console: Settings → Scale → Region), applied when you deploy.

### 4. Deploy

From the example's folder:

```sh
inquir apps deploy my-max-bot
```

The CLI packs the folder, builds the image from the `Dockerfile` and releases it. The build takes about a minute:

```text
Build ... queued for my-max-bot
  Build succeeded in ...
Release ... queued for my-max-bot (build ...)
Release ... is serving
  no reachable endpoint — the ports are internal to the host
```

"no reachable endpoint" is expected: the bot needs no public address, it connects to MAX itself.

### 5. Check

```sh
inquir apps logs my-max-bot
```

A few seconds after start the logs show a line like:

```text
INFO @your_bot is running (polling mode)
```

Open the bot in MAX and press Start, then send any text: the bot repeats it. Leave the logs with Ctrl+C (or use `inquir apps logs my-max-bot --no-follow`).

### 6. Updates

- Changed the code (bot.mjs): run `inquir apps deploy my-max-bot` again from the example's folder.
- Changed a variable: `inquir apps update my-max-bot --set KEY=value`, then `inquir apps redeploy my-max-bot`: variables apply with a new release.

### 7. PostgreSQL (optional)

With a database, `/note` and `/notes` start working.

```sh
inquir apps create my-max-bot-db --template postgres --project <the bot's project>
inquir apps connect my-max-bot-db my-max-bot
inquir apps redeploy my-max-bot
```

`<the bot's project>` is the project name printed by `inquir apps create` (step 3). `connect` sets the bot's `DATABASE_URL`. If it answers "has no verified private address yet", the database is still starting: retry in a minute. After `redeploy`, the `is running` line mentions `PostgreSQL`.

### 8. Webhook instead of long polling (optional)

```sh
inquir apps update my-max-bot --ingress public
inquir apps status my-max-bot
```

`status` shows the public address (`production: https://my-max-bot-xxxxxx.apps.inquir.org`). Then:

```sh
inquir apps update my-max-bot --set BOT_MODE=webhook --set WEBHOOK_URL=https://my-max-bot-xxxxxx.apps.inquir.org
inquir apps redeploy my-max-bot
```

The bot registers the webhook with MAX (MAX recommends webhooks in production) itself and checks the secret on every request. The secret is derived from the token; to set your own, use `WEBHOOK_SECRET` with 16–256 characters of `A-Z a-z 0-9 _ -`, or the bot stops with exit code 64. Back to long polling: `inquir apps update my-max-bot --set BOT_MODE=polling`, `inquir apps redeploy my-max-bot`, and optionally `inquir apps update my-max-bot --ingress private`.

### Troubleshooting

- **`MAX refused MAX_BOT_TOKEN (401 Unauthorized)`** in the logs: the token is wrong. Copy it again, then `inquir apps update my-max-bot --set MAX_BOT_TOKEN=<token>` and `inquir apps redeploy my-max-bot`.
- **`cannot reach the MAX API`** keeps repeating: check the location. `inquir apps status my-max-bot` should say `location: Russia`; if not, `inquir apps update my-max-bot --location ru` and `inquir apps redeploy my-max-bot`.
- **The bot is silent although `is running` is there**: the same token is used elsewhere (a copy running locally, say). Stop the other instance.
- **Why the app does not start**: `inquir apps describe my-max-bot` explains the replicas' state and recent events.

### Deploy from your GitHub fork

Coming soon. Deploying from GitHub is not available to every workspace yet; use the CLI as above.

### Delete

```sh
inquir apps delete my-max-bot
inquir apps delete my-max-bot-db   # if you added the database
```

Archive the empty project in the console.

Full guide: [How to deploy a bot](https://inquir.org/docs/apps#telegram-bot).

### TLS

`platform-api2.max.ru` has a certificate from the Russian Trusted Root CA (Минцифры), which MAX asks clients to trust. The bot trusts that root (`russian-trusted-root-ca.pem`, SHA-256 `D2:6D:2D:02:31:B7:C3:9F:92:CC:73:85:12:BA:54:10:35:19:E4:40:5D:68:B5:BD:70:3E:97:88:CA:8E:CF:31`, published at gu-st.ru) for its own MAX API requests only, never system-wide.
