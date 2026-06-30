#!/usr/bin/env bash
# Ingestão ISS completa para o MySQL staging (opcional — além do seed misto).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ISS="${ISS_ROOT:-$ROOT/../ISS}"
cd "$ISS"

if [[ ! -f .github/scripts/ingest-knowledge.py ]]; then
  echo "ERRO: ISS não encontrado em $ISS"
  exit 1
fi

if [[ ! -d "$ROOT/.venv" ]]; then
  echo "ERRO: corre primeiro $ROOT/bin/staging-setup.sh"
  exit 1
fi

set -a
# shellcheck disable=SC1091
source "$ROOT/.env.staging.local"
set +a

export DB_HOST DB_PORT DB_NAME DB_USER DB_PASSWORD

echo "==> Ingest ISS → MySQL staging ($DB_HOST:$DB_PORT)"
"$ROOT/.venv/bin/pip" install -q pymysql 2>/dev/null || true
"$ROOT/.venv/bin/python" .github/scripts/ingest-knowledge.py

echo "OK. Reinicia o bot ou POST /reload se já estiver a correr."
