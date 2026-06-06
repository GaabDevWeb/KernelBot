# KernelBot (ACL) — imagem de produção
# Build:  docker build -t kernelbot:latest .
# Run:    docker compose up -d   (ver docker-compose.yml)

FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-prod.txt .
RUN pip install --no-cache-dir -r requirements-prod.txt

COPY api/ ./api/
COPY app/ ./app/
COPY core/ ./core/
COPY engine/ ./engine/
COPY frontend/ ./frontend/
COPY jsons/ ./jsons/
COPY templates/ ./templates/
COPY main.py .

RUN useradd --create-home --shell /usr/sbin/nologin kernelbot \
    && mkdir -p content \
    && chown -R kernelbot:kernelbot /app

USER kernelbot

# Railway injecta PORT em runtime; local/docker-compose usa 8001 por defeito.
ENV PORT=8001

EXPOSE 8001

HEALTHCHECK --interval=30s --timeout=5s --start-period=45s --retries=3 \
    CMD sh -c 'curl -fsS "http://127.0.0.1:${PORT:-8001}/health" || exit 1'

CMD ["sh", "-c", "exec uvicorn main:app --host 0.0.0.0 --port ${PORT:-8001}"]
