# Static HTML site · Статический HTML-сайт

[Русский](#русский) · [English](#english)

## Русский

Самый короткий способ выложить HTML, CSS и JavaScript: nginx (не от root, порт 8080) отдаёт папку `public/`. Положите туда свои файлы — `index.html` обязателен.

Пошагово: [готовые рецепты](https://inquir.org/ru/docs/recipes#static-html).

### Развёртывание

Нужны аккаунт Inquir ([регистрация](https://inquir.org/register), 14 дней бесплатно) и CLI (`npm i -g @inquir/compute-cli@latest`, `inquir login`).

```sh
git clone https://github.com/Inquir-search/inquir-examples.git
cd inquir-examples/static-html

inquir apps create my-page --ingress public
inquir apps deploy my-page --promote
```

В конце команда напечатает адрес вида `https://my-page-xxxxxx.apps.inquir.org`.

Без терминала: в консоли **Приложения → Создать в браузере**, создайте в редакторе `Dockerfile`, `inquir.yaml` и `public/index.html`, вставьте содержимое и нажмите **Развернуть**; публичный адрес — **Настройки → Сеть → Публичный доступ → Создать адрес**.

Нужны сжатие и кеширование или одностраничное приложение? Возьмите `nginx.conf` из [`static-react-vite`](../static-react-vite).

## English

The shortest way to put HTML, CSS and JavaScript online: nginx (non-root, port 8080) serves the `public/` folder. Put your files there — `index.html` is required.

Step by step: [deploy recipes](https://inquir.org/docs/recipes#static-html).

### Deploy

You need an Inquir account ([sign up](https://inquir.org/register), 14 days free) and the CLI (`npm i -g @inquir/compute-cli@latest`, `inquir login`).

```sh
git clone https://github.com/Inquir-search/inquir-examples.git
cd inquir-examples/static-html

inquir apps create my-page --ingress public
inquir apps deploy my-page --promote
```

The command ends with an address like `https://my-page-xxxxxx.apps.inquir.org`.

Without a terminal: in the console **Apps → Create in browser**, create `Dockerfile`, `inquir.yaml` and `public/index.html` in the editor, paste their contents and press **Deploy**; a public address: **Settings → Networking → Public access → Generate address**.

Need compression and caching, or a single-page app? Take `nginx.conf` from [`static-react-vite`](../static-react-vite).
