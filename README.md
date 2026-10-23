# Inquir examples

[Русский](#русский) · [English](#english)

## Русский

Примеры приложений для [Inquir Compute](https://inquir.org) с пошаговыми инструкциями по развёртыванию. Каждая папка — отдельный пример: код, `Dockerfile`, `inquir.yaml` и `README.md` (у стека — `inquir-compose.yaml` и папка на каждый сервис).

| Пример | Что это |
|---|---|
| [`telegram-bot-python`](telegram-bot-python) | Telegram-бот на Python (aiogram 3): эхо, `/start`, `/help`, заметки в PostgreSQL |
| [`telegram-bot-node`](telegram-bot-node) | Telegram-бот на Node.js (grammY): то же самое |
| [`max-bot`](max-bot) | бот для мессенджера MAX на официальном SDK (Node.js) |
| [`ai-agent-bot`](ai-agent-bot) | ИИ-ассистент в Telegram через любой OpenAI-совместимый API |
| [`ai-agent-bot-postgres`](ai-agent-bot-postgres) | тот же ИИ-ассистент со своей PostgreSQL: стек из двух сервисов в одном `inquir-compose.yaml` |
| [`static-react-vite`](static-react-vite) | сайт на React (Vite), который отдаёт nginx: прямые ссылки, сжатие, кеш |
| [`static-html`](static-html) | статический HTML-сайт из папки `public/` |
| [`node-api`](node-api) | API на Node.js (Express) |
| [`python-fastapi`](python-fastapi) | API на Python (FastAPI) |

Инструкции: [Как задеплоить бота](https://inquir.org/ru/docs/apps#telegram-bot), [готовые рецепты для сайтов и API](https://inquir.org/ru/docs/recipes), [стеки из нескольких сервисов](https://inquir.org/ru/docs/compose).

Коротко: зарегистрируйтесь на [inquir.org](https://inquir.org/register) (14 дней бесплатно), установите CLI (`npm i -g @inquir/compute-cli`, `inquir login`), склонируйте репозиторий и следуйте `README.md` нужного примера.

В репозитории нет секретов: токены и ключи задаются переменными приложения и хранятся зашифрованными.

Pull request’ы с новыми примерами приветствуются: папка с кодом, `Dockerfile` (базовый образ закреплён по digest, процесс не от root), `inquir.yaml` и `README.md` на русском и английском. Перед PR: `make check` (или `node scripts/check.mjs`).

Лицензия — [MIT](LICENSE).

## English

Example applications for [Inquir Compute](https://inquir.org) with step-by-step deploy guides. Each folder is one example: the code, a `Dockerfile`, an `inquir.yaml` and a `README.md` (a stack: an `inquir-compose.yaml` and one folder per service).

| Example | What it is |
|---|---|
| [`telegram-bot-python`](telegram-bot-python) | Telegram bot in Python (aiogram 3): echo, `/start`, `/help`, notes in PostgreSQL |
| [`telegram-bot-node`](telegram-bot-node) | Telegram bot in Node.js (grammY): the same |
| [`max-bot`](max-bot) | a bot for the MAX messenger on its official SDK (Node.js) |
| [`ai-agent-bot`](ai-agent-bot) | an AI assistant in Telegram through any OpenAI-compatible API |
| [`ai-agent-bot-postgres`](ai-agent-bot-postgres) | the same AI assistant with its own PostgreSQL: a stack of two services in one `inquir-compose.yaml` |
| [`static-react-vite`](static-react-vite) | a React (Vite) site served by nginx: direct links, compression, caching |
| [`static-html`](static-html) | a static HTML site from a `public/` folder |
| [`node-api`](node-api) | a Node.js API (Express) |
| [`python-fastapi`](python-fastapi) | a Python API (FastAPI) |

Guides: [How to deploy a bot](https://inquir.org/docs/apps#telegram-bot), [deploy recipes for sites and APIs](https://inquir.org/docs/recipes), [stacks of several services](https://inquir.org/docs/compose).

In short: sign up at [inquir.org](https://inquir.org/register) (14 days free), install the CLI (`npm i -g @inquir/compute-cli`, `inquir login`), clone this repository and follow the example's `README.md`.

There are no secrets in this repository: tokens and keys are app variables, stored encrypted.

Pull requests with new examples are welcome: a folder with the code, a `Dockerfile` (base image pinned by digest, a non-root process), an `inquir.yaml` and a `README.md` in Russian and English. Before a PR: `make check` (or `node scripts/check.mjs`).

License: [MIT](LICENSE).
