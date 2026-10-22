# Node.js API (Express) · API на Node.js (Express)

[Русский](#русский) · [English](#english)

## Русский

API на [Express](https://expressjs.com) 5 (Node.js 22): `GET /api/hello`, проверка работоспособности `GET /healthz`, порт из переменной `PORT`, которую задаёт Inquir, и аккуратное завершение по SIGTERM. Fastify, Hono или NestJS — так же: меняется только `CMD`.

Пошагово, с подключением Postgres: [готовые рецепты](https://inquir.org/ru/docs/recipes#node-api).

### Развёртывание

Нужны аккаунт Inquir ([регистрация](https://inquir.org/register), 14 дней бесплатно) и CLI (`npm i -g @inquir/compute-cli@latest`, `inquir login`).

```sh
git clone https://github.com/Inquir-search/inquir-examples.git
cd inquir-examples/node-api

inquir apps create my-api --ingress public
inquir apps deploy my-api --promote

curl https://my-api-xxxxxx.apps.inquir.org/api/hello
```

Порт (3000) задан в `inquir.yaml`; если меняете его, поменяйте и значение по умолчанию в `server.js`. Логи: `inquir apps logs my-api --tail 100`.

### Локально

```sh
npm ci
npm start   # http://localhost:3000/api/hello
```

## English

An [Express](https://expressjs.com) 5 API (Node.js 22): `GET /api/hello`, the health check `GET /healthz`, the port from the `PORT` variable Inquir sets, and a clean shutdown on SIGTERM. Fastify, Hono or NestJS work the same way: only `CMD` changes.

Step by step, with Postgres: [deploy recipes](https://inquir.org/docs/recipes#node-api).

### Deploy

You need an Inquir account ([sign up](https://inquir.org/register), 14 days free) and the CLI (`npm i -g @inquir/compute-cli@latest`, `inquir login`).

```sh
git clone https://github.com/Inquir-search/inquir-examples.git
cd inquir-examples/node-api

inquir apps create my-api --ingress public
inquir apps deploy my-api --promote

curl https://my-api-xxxxxx.apps.inquir.org/api/hello
```

The port (3000) is set in `inquir.yaml`; if you change it, change the default in `server.js` too. Logs: `inquir apps logs my-api --tail 100`.

### Locally

```sh
npm ci
npm start   # http://localhost:3000/api/hello
```
