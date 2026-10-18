# A bot for the MAX messenger on the official SDK, @maxhub/max-bot-api
# (bot.mjs). No build arguments: settings are Variables of the app (see
# bot.mjs), read when the container starts.
#
# The base image is pinned by digest and every npm package by its integrity
# hash (package-lock.json; npm ci installs exactly that tree, without install
# scripts). The bot runs as the image's unprivileged `node` user and listens
# on 8080 for the health check (GET /healthz) and, in webhook mode, for MAX.
#
# russian-trusted-root-ca.pem is the Russian Trusted Root CA (Минцифры),
# the root of platform-api2.max.ru's certificate, as published at
# https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt
# (SHA-256 fingerprint D2:6D:2D:02:31:B7:C3:9F:92:CC:73:85:12:BA:54:10:35:19:E4:40:5D:68:B5:BD:70:3E:97:88:CA:8E:CF:31,
# valid until 2032-02-27). bot.mjs trusts it for its MAX API requests only;
# it is not added to the system trust store.
FROM node:22.23.3-alpine@sha256:0a7108bf6c7bf5de370ffb1a3ed6be93d405b43ff159f681a8d18c0e2bc2e402
ENV NODE_ENV=production
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --omit=dev --ignore-scripts --no-audit --no-fund && npm cache clean --force
COPY bot.mjs russian-trusted-root-ca.pem ./
USER node
EXPOSE 8080
CMD ["node", "bot.mjs"]
