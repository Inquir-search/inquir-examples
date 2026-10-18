# A Telegram bot on grammY (bot.mjs). No build arguments: settings are
# Variables of the app (see bot.mjs), read when the container starts.
#
# The base image is pinned by digest and every npm package by its integrity
# hash (package-lock.json; npm ci installs exactly that tree, without install
# scripts). The bot runs as the image's unprivileged `node` user and listens
# on 8080 for the health check (GET /healthz) and, in webhook mode, for Telegram.
FROM node:22.23.3-alpine@sha256:0a7108bf6c7bf5de370ffb1a3ed6be93d405b43ff159f681a8d18c0e2bc2e402
ENV NODE_ENV=production
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts --no-audit --no-fund && npm cache clean --force
COPY bot.mjs ./
USER node
EXPOSE 8080
CMD ["node", "bot.mjs"]
