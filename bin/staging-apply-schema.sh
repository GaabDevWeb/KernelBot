#!/usr/bin/env bash
# Aplica schema knowledge no MySQL staging (idempotente — seguro repetir).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
CONTAINER="kernelbot-mysql-staging"
SQL="$ROOT/scripts/staging/init-knowledge.sql"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "ERRO: container $CONTAINER não está a correr. Corre: ./bin/staging-docker-up.sh"
  exit 1
fi

if [[ ! -f "$SQL" ]]; then
  echo "ERRO: falta $SQL"
  exit 1
fi

echo "A aplicar schema em $CONTAINER..."
docker exec -i "$CONTAINER" mysql -u root -pstaging_root < "$SQL"
echo "Schema OK (tabela knowledge em kernelbot_staging)."
