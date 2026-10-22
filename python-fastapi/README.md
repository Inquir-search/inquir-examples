# Python API (FastAPI) · API на Python (FastAPI)

[Русский](#русский) · [English](#english)

## Русский

API на [FastAPI](https://fastapi.tiangolo.com) под uvicorn (Python 3.12): `GET /api/hello`, проверка работоспособности `GET /healthz`, интерактивная документация на `/docs`. Порт приходит в переменной `PORT`, которую задаёт Inquir.

Пошагово, с подключением Postgres: [готовые рецепты](https://inquir.org/ru/docs/recipes#python-fastapi).

`requirements.txt` здесь закреплён по версиям и SHA-256 всех пакетов, и Dockerfile ставит их с `--require-hashes`, поэтому каждая сборка использует ровно те же файлы. В рецепте в документации — короткий вариант из двух строк (`fastapi`, `uvicorn[standard]`) без хешей; он тоже работает.

### Развёртывание

Нужны аккаунт Inquir ([регистрация](https://inquir.org/register), 14 дней бесплатно) и CLI (`npm i -g @inquir/compute-cli@latest`, `inquir login`).

```sh
git clone https://github.com/Inquir-search/inquir-examples.git
cd inquir-examples/python-fastapi

inquir apps create my-api --ingress public
inquir apps deploy my-api --promote

curl https://my-api-xxxxxx.apps.inquir.org/api/hello
```

Новый пакет: добавьте его в `requirements.txt` вместе с хешами (их печатает `pip-compile --generate-hashes`). Логи: `inquir apps logs my-api --tail 100`.

### Локально

```sh
python -m venv .venv && . .venv/bin/activate
pip install fastapi==0.141.1 "uvicorn[standard]==0.54.0"
uvicorn main:app --reload   # http://localhost:8000/docs
```

## English

A [FastAPI](https://fastapi.tiangolo.com) API served by uvicorn (Python 3.12): `GET /api/hello`, the health check `GET /healthz`, interactive docs at `/docs`. The port comes in the `PORT` variable Inquir sets.

Step by step, with Postgres: [deploy recipes](https://inquir.org/docs/recipes#python-fastapi).

`requirements.txt` here pins every package by version and SHA-256, and the Dockerfile installs with `--require-hashes`, so every build uses exactly the same files. The recipe in the docs uses the short two-line version (`fastapi`, `uvicorn[standard]`) without hashes; it works too.

### Deploy

You need an Inquir account ([sign up](https://inquir.org/register), 14 days free) and the CLI (`npm i -g @inquir/compute-cli@latest`, `inquir login`).

```sh
git clone https://github.com/Inquir-search/inquir-examples.git
cd inquir-examples/python-fastapi

inquir apps create my-api --ingress public
inquir apps deploy my-api --promote

curl https://my-api-xxxxxx.apps.inquir.org/api/hello
```

A new package: add it to `requirements.txt` with its hashes (`pip-compile --generate-hashes` prints them). Logs: `inquir apps logs my-api --tail 100`.

### Locally

```sh
python -m venv .venv && . .venv/bin/activate
pip install fastapi==0.141.1 "uvicorn[standard]==0.54.0"
uvicorn main:app --reload   # http://localhost:8000/docs
```
