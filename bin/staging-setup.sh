#!/usr/bin/env bash
# Sobe MySQL staging, popula massa mista (legacy + B2) e corre teste E2E.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> KernelBot staging setup"
echo "    $ROOT"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERRO: Docker não encontrado. Instala Docker ou usa MySQL nativo na porta 3307."
  exit 1
fi

if ! docker info >/dev/null 2>&1; then
  echo "ERRO: sem permissão no Docker (socket)."
  echo "      sudo usermod -aG docker \$USER && newgrp docker"
  echo "      ou: sudo ./bin/staging-setup.sh"
  exit 1
fi

if [[ ! -f .env.staging.local ]]; then
  echo "ERRO: falta .env.staging.local (copia de .env.staging.example)"
  exit 1
fi

echo "==> 1/4 MySQL staging (porta 3307)"
if docker compose version >/dev/null 2>&1; then
  docker compose -f docker-compose.staging.yml up -d
  for i in $(seq 1 60); do
    status="$(docker inspect --format='{{.State.Health.Status}}' kernelbot-mysql-staging 2>/dev/null || echo starting)"
    [[ "$status" == "healthy" ]] && break
    sleep 2
  done
elif command -v docker-compose >/dev/null 2>&1; then
  docker-compose -f docker-compose.staging.yml up -d
  sleep 15
else
  "$ROOT/bin/staging-docker-up.sh"
fi

# Init SQL só corre na 1ª criação do volume — aplicar schema sempre antes do seed.
echo "==> 2/4 Garantir schema knowledge"
chmod +x "$ROOT/bin/staging-apply-schema.sh"
"$ROOT/bin/staging-apply-schema.sh"

echo "==> 3/4 Python venv + dependências"
if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
.venv/bin/pip install -q -r requirements.txt

echo "==> 4/4 Seed + E2E"
.venv/bin/python scripts/staging/seed_mixed_mass.py
.venv/bin/python scripts/staging/run_e2e_reload.py

echo ""
echo "Staging OK. Próximo passo:"
echo "  ./bin/staging-serve.sh"
echo "  Abre http://127.0.0.1:8001 e testa no chat."
