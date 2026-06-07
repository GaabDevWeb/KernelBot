#!/usr/bin/env bash
# Sobe MySQL staging e garante o schema knowledge.
# Nota: o seed de massa mista e o teste E2E de dev foram removidos da main pública.
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

echo "==> 1/2 MySQL staging (porta 3307)"
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

# Init SQL só corre na 1ª criação do volume — aplicar schema sempre.
echo "==> 2/2 Garantir schema knowledge"
chmod +x "$ROOT/bin/staging-apply-schema.sh"
"$ROOT/bin/staging-apply-schema.sh"

# O seed de massa mista (seed_mixed_mass.py) e o E2E de reload (run_e2e_reload.py)
# faziam parte de scripts/ (dev only) e foram removidos da main pública.

echo ""
echo "Staging OK (MySQL + schema). Próximo passo:"
echo "  ./bin/staging-serve.sh"
echo "  Abre http://127.0.0.1:8001 e testa no chat."
