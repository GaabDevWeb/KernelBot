#!/usr/bin/env bash
# Arranca o KernelBot com MySQL staging (3307).
# DB: variáveis exportadas abaixo. OPENROUTER_API_KEY: lida pelo Python (dotenv) do .env — não fazer source .env no bash.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ ! -f .env.staging.local ]]; then
  echo "ERRO: falta .env.staging.local — corre primeiro: ./bin/staging-setup.sh"
  exit 1
fi

if [[ ! -f .env ]]; then
  echo "ERRO: falta .env com OPENROUTER_API_KEY (copia de .env.example)"
  exit 1
fi

if [[ ! -d .venv ]]; then
  echo "ERRO: falta .venv — corre: ./bin/staging-setup.sh"
  exit 1
fi

export KERNELBOT_ENV=staging
export ACL_CATALOG_ENABLED=false

# Só staging no shell (formato KEY=value simples). O .env principal é carregado por Settings.load() / python-dotenv.
set -a
# shellcheck disable=SC1091
source .env.staging.local
set +a

echo "==> KernelBot STAGING"
echo "    MySQL: ${DB_HOST}:${DB_PORT}/${DB_NAME}"
echo "    URL:   http://127.0.0.1:8001"
echo "    (OPENROUTER_API_KEY vem do .env via Python — não source .env no bash)"
echo ""
echo "    Sugestões de pergunta:"
echo "      - modelo hierárquico rede relacional  (aula legacy)"
echo "      - transformers                         (keyword B2 → chunk 0)"
echo ""

exec .venv/bin/python main.py
