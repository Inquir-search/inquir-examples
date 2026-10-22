# React site (Vite) · Сайт на React (Vite)

[Русский](#русский) · [English](#english)

## Русский

Приложение на React, собранное [Vite](https://vite.dev), и nginx, который его отдаёт. Ссылки вида `/about` открываются напрямую (возврат к `index.html`), файлы из `/assets/` сжимаются и кешируются на год, `index.html` — без кеша, `/healthz` отвечает `ok`.

Пошагово, с вариантами для Create React App и Next.js: [готовые рецепты](https://inquir.org/ru/docs/recipes#react-vite).

### Что понадобится

- Аккаунт Inquir: [регистрация](https://inquir.org/register), 14 дней бесплатно, без карты.
- Inquir CLI (Node.js 22+): `npm i -g @inquir/compute-cli@latest`, затем `inquir login`.

Docker на компьютере не нужен: сборка идёт на Inquir.

### Файлы

| Файл | Зачем |
|---|---|
| `Dockerfile` | собирает сайт (`npm run build`) и кладёт `dist/` в nginx (не от root, порт 8080) |
| `nginx.conf` | порт 8080, `/healthz`, сжатие, кеш для `/assets/`, возврат к `index.html` |
| `inquir.yaml` | порт, проверка работоспособности, 0.25 vCPU и 128 МБ |
| остальное | обычный проект `npm create vite@9.2.1 -- --template react` |

Свой проект на Vite: скопируйте в него `Dockerfile`, `nginx.conf` и `inquir.yaml`.

### Развёртывание

```sh
git clone https://github.com/Inquir-search/inquir-examples.git
cd inquir-examples/static-react-vite

inquir apps create my-site --ingress public
inquir apps deploy my-site --promote
```

В конце команда напечатает адрес вида `https://my-site-xxxxxx.apps.inquir.org`. После изменений — снова `inquir apps deploy my-site --promote`.

Из консоли: отправьте папку в свой репозиторий GitHub, затем **Приложения → проект → Создать → Репозиторий GitHub**, **Внутренний HTTP-порт** `8080`, **Развернуть приложение**; публичный адрес — **Настройки → Сеть → Публичный доступ → Создать адрес**.

Свой домен: `inquir apps domain my-site www.example.com`, добавьте показанные DNS-записи, затем `inquir apps domain my-site www.example.com --verify`. Подробно: [собственные домены](https://inquir.org/ru/docs/apps#custom-domains).

### Локально

```sh
npm install
npm run dev
```

## English

A React app built with [Vite](https://vite.dev) and served by nginx. Links like `/about` open directly (fallback to `index.html`), files under `/assets/` are compressed and cached for a year, `index.html` is never cached, `/healthz` answers `ok`.

Step by step, with Create React App and Next.js variants: [deploy recipes](https://inquir.org/docs/recipes#react-vite).

### You need

- An Inquir account: [sign up](https://inquir.org/register), 14 days free, no card.
- The Inquir CLI (Node.js 22+): `npm i -g @inquir/compute-cli@latest`, then `inquir login`.

No Docker on your computer: the build runs on Inquir.

### Files

| File | Why |
|---|---|
| `Dockerfile` | builds the site (`npm run build`) and puts `dist/` into nginx (non-root, port 8080) |
| `nginx.conf` | port 8080, `/healthz`, compression, caching for `/assets/`, fallback to `index.html` |
| `inquir.yaml` | the port, the health check, 0.25 vCPU and 128 MB |
| the rest | a plain `npm create vite@9.2.1 -- --template react` project |

Your own Vite project: copy `Dockerfile`, `nginx.conf` and `inquir.yaml` into it.

### Deploy

```sh
git clone https://github.com/Inquir-search/inquir-examples.git
cd inquir-examples/static-react-vite

inquir apps create my-site --ingress public
inquir apps deploy my-site --promote
```

The command ends with an address like `https://my-site-xxxxxx.apps.inquir.org`. After a change, run `inquir apps deploy my-site --promote` again.

From the console: push the folder to your GitHub repository, then **Apps → a project → Create → GitHub repository**, **Internal HTTP port** `8080`, **Deploy application**; a public address: **Settings → Networking → Public access → Generate address**.

Your own domain: `inquir apps domain my-site www.example.com`, add the DNS records it prints, then `inquir apps domain my-site www.example.com --verify`. Details: [custom domains](https://inquir.org/docs/apps#custom-domains).

### Locally

```sh
npm install
npm run dev
```
