#!/usr/bin/env bash
# Sobe MySQL staging com docker run (sem docker compose).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONTAINER="kernelbot-mysql-staging"
IMAGE="mysql:8.4"
PORT_HOST=3307

if ! command -v docker >/dev/null 2>&1; then
  echo "ERRO: Docker não instalado."
  exit 1
fi

if docker ps -a --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
    echo "A iniciar container existente..."
    docker start "$CONTAINER"
    sleep 3
  else
    echo "MySQL staging já está a correr ($CONTAINER)."
  fi
  "$ROOT/bin/staging-apply-schema.sh"
else
  echo "A criar MySQL staging (porta $PORT_HOST)..."
  docker run -d \
    --name "$CONTAINER" \
    -p "${PORT_HOST}:3306" \
    -e MYSQL_ROOT_PASSWORD=staging_root \
    -e MYSQL_DATABASE=kernelbot_staging \
    -e MYSQL_USER=kb_staging \
    -e MYSQL_PASSWORD=kb_staging_pw \
    -v kernelbot_staging_data:/var/lib/mysql \
    "$IMAGE"

  echo "A aguardar MySQL inicializar (até ~60s)..."
  for i in $(seq 1 30); do
    if docker exec "$CONTAINER" mysqladmin ping -h 127.0.0.1 -u root -pstaging_root --silent 2>/dev/null; then
      break
    fi
    sleep 2
  done

  "$ROOT/bin/staging-apply-schema.sh"
fi

echo "MySQL staging OK em 127.0.0.1:$PORT_HOST"
