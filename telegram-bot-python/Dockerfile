# A Telegram bot on aiogram 3 (bot.py). No build arguments: settings are
# Variables of the app (see bot.py), read when the container starts.
#
# The base image is pinned by digest and every Python package by SHA-256
# (requirements.txt), so a rebuild installs the same files. The bot runs as an
# unprivileged user and listens on 8080 for the health check (GET /healthz)
# and, in webhook mode, for Telegram.
FROM python:3.13.16-slim@sha256:70729b46c69b4f1e97c4822c1af3df53a1476cf5ddc6c087c0c10bc3a5678c2f
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_NO_CACHE_DIR=1 PIP_ROOT_USER_ACTION=ignore
WORKDIR /app
COPY requirements.txt .
RUN pip install --require-hashes --only-binary=:all: -r requirements.txt \
    && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin bot
COPY bot.py .
USER 10001
EXPOSE 8080
CMD ["python", "bot.py"]
