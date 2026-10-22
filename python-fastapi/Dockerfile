FROM python:3.12.15-slim@sha256:cb33f7f771ecec2ef1225cf39b159591a040391bd73e4c01f00fdfc4c47611d2
ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /app
COPY requirements.txt ./
RUN pip install --require-hashes --only-binary=:all: -r requirements.txt
COPY . .
# Run as a regular user, not root
RUN useradd --create-home --uid 10001 app
USER app
EXPOSE 8000
# The platform sets PORT to runtime.port from inquir.yaml
CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
