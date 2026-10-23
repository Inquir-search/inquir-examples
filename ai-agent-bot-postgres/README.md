# AI assistant in Telegram with PostgreSQL · ИИ-ассистент в Telegram с PostgreSQL

[Русский](#русский) · [English](#english)

## Русский

Тот же бот, что в [`ai-agent-bot`](../ai-agent-bot), но вместе со своей базой PostgreSQL: история чатов переживает перезапуски и обновления. Оба сервиса описаны в одном файле [`inquir-compose.yaml`](inquir-compose.yaml) и разворачиваются одной командой — это **стек** ([документация](https://inquir.org/ru/docs/compose)).

- `db` — PostgreSQL 17 (официальный образ, закреплён по digest) с томом на 1 ГБ. Пароль генерирует сервер при первом развёртывании; он нигде не печатается.
- `bot` — папка [`bot/`](bot): `Dockerfile`, `bot.py` и свой `inquir.yaml` (регион `nl`, всегда включён, без публичного адреса). Запускается, когда база уже работает, и получает `DATABASE_URL`.

Стеки пока в предварительном доступе: их включают для рабочего пространства по запросу в поддержку. `inquir compose validate` работает у всех. Для `up`, `status` и `down` нужен CLI 0.4.5 или новее — он скоро будет опубликован; до этого стек можно только проверить.

### Что понадобится

- Аккаунт Inquir ([регистрация](https://inquir.org/register)) и CLI: `npm i -g @inquir/compute-cli@latest`, затем `inquir login`.
- Токен бота от [@BotFather](https://t.me/BotFather) (`/newbot`) и ключ API провайдера модели (OpenAI или любой OpenAI-совместимый API).

### Значения: файл .env

Создайте рядом файл `.env` (он в `.gitignore`, не коммитьте его):

```sh
TELEGRAM_BOT_TOKEN=123456789:AA...
OPENAI_API_KEY=...
# необязательно:
# OPENAI_BASE_URL=https://api.openai.com/v1
# MODEL=gpt-5-mini
# ALLOWED_USER_IDS=12345,67890
```

Без `--input-file` CLI в терминале спросит обязательные значения сам (секреты не отображаются).

### Развёртывание

Прямо из GitHub, без клонирования:

```sh
inquir compose up https://github.com/Inquir-search/inquir-examples:ai-agent-bot-postgres --name ai-agent-bot-postgres --input-file .env
```

Или из своей копии:

```sh
git clone https://github.com/Inquir-search/inquir-examples.git
cd inquir-examples/ai-agent-bot-postgres
inquir compose validate
inquir compose up --input-file .env
```

`up` создаёт проект `ai-agent-bot-postgres` (имя стека задаёт `--name`; из папки по умолчанию это имя папки), в нём приложения `ai-agent-bot-postgres-db` и `ai-agent-bot-postgres-bot`, ждёт, пока база заработает, затем собирает и запускает бота. Отправьте боту `/start`; в логах (`inquir apps logs ai-agent-bot-postgres-bot`) будет `history in PostgreSQL`.

### Обновление, статус, остановка

```sh
inquir compose up --input-file .env      # снова: пароль и введённые значения сохраняются, неизменённые сервисы не трогаются
inquir compose status ai-agent-bot-postgres
inquir compose down ai-agent-bot-postgres                                        # остановить; данные остаются
inquir compose down ai-agent-bot-postgres --delete --confirm ai-agent-bot-postgres   # удалить (приложения в архиве 30 дней)
```

`--delete-volumes` вместе с `--delete` сразу удаляет и данные базы.

## English

The same bot as [`ai-agent-bot`](../ai-agent-bot), together with its own PostgreSQL: chat history survives restarts and updates. Both services are described in one file, [`inquir-compose.yaml`](inquir-compose.yaml), and deploy with one command: a **stack** ([docs](https://inquir.org/docs/compose)).

- `db`: PostgreSQL 17 (the official image, pinned by digest) with a 1 GB volume. The server generates its password on the first deploy; it is never printed.
- `bot`: the [`bot/`](bot) folder: `Dockerfile`, `bot.py` and its own `inquir.yaml` (location `nl`, always on, no public address). It starts once the database serves and gets `DATABASE_URL`.

Stacks are in preview: they are enabled per workspace, on request to support. `inquir compose validate` works for everyone. `up`, `status` and `down` need CLI 0.4.5 or newer, which will be published soon; until then you can only validate the stack.

### What you need

- An Inquir account ([sign up](https://inquir.org/register)) and the CLI: `npm i -g @inquir/compute-cli@latest`, then `inquir login`.
- A bot token from [@BotFather](https://t.me/BotFather) (`/newbot`) and your model provider's API key (OpenAI or any OpenAI-compatible API).

### Values: the .env file

Create a `.env` file next to it (it is in `.gitignore`; never commit it):

```sh
TELEGRAM_BOT_TOKEN=123456789:AA...
OPENAI_API_KEY=...
# optional:
# OPENAI_BASE_URL=https://api.openai.com/v1
# MODEL=gpt-5-mini
# ALLOWED_USER_IDS=12345,67890
```

Without `--input-file`, the CLI asks for the required values at a terminal (secrets are not echoed).

### Deploy

Straight from GitHub, no clone needed:

```sh
inquir compose up https://github.com/Inquir-search/inquir-examples:ai-agent-bot-postgres --name ai-agent-bot-postgres --input-file .env
```

Or from your copy:

```sh
git clone https://github.com/Inquir-search/inquir-examples.git
cd inquir-examples/ai-agent-bot-postgres
inquir compose validate
inquir compose up --input-file .env
```

`up` creates the project `ai-agent-bot-postgres` (`--name` sets the stack name; from a folder it defaults to the folder name) with the applications `ai-agent-bot-postgres-db` and `ai-agent-bot-postgres-bot`, waits for the database to serve, then builds and starts the bot. Send `/start` to the bot; its logs (`inquir apps logs ai-agent-bot-postgres-bot`) say `history in PostgreSQL`.

### Update, status, stop

```sh
inquir compose up --input-file .env      # again: the password and your values are kept, unchanged services are left alone
inquir compose status ai-agent-bot-postgres
inquir compose down ai-agent-bot-postgres                                        # stop; the data stays
inquir compose down ai-agent-bot-postgres --delete --confirm ai-agent-bot-postgres   # delete (applications archived for 30 days)
```

`--delete-volumes` together with `--delete` also deletes the database's data at once.
