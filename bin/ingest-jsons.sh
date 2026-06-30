#!/usr/bin/env bash
# UPSERT jsons/<discipline>/*.json → MySQL knowledge (aulas ISS espelhadas).
# Staging: KERNELBOT_ENV=staging ./bin/ingest-jsons.sh
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -d .venv ]]; then
  echo "ERRO: falta .venv — python3 -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

if [[ "${KERNELBOT_ENV:-}" == "staging" ]]; then
  if [[ ! -f .env.staging.local ]]; then
    echo "ERRO: falta .env.staging.local"
    exit 1
  fi
  set -a
  # shellcheck disable=SC1091
  source .env.staging.local
  set +a
fi

"$ROOT/.venv/bin/pip" install -q pymysql 2>/dev/null || true
exec "$ROOT/.venv/bin/python" -m engine.jsons_ingest
