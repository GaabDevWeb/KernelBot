# Kernel — Assistente de Estudo

Assistente educacional com busca contextual (BM25) nas aulas indexadas, interface web em tempo real (SSE) e suporte a múltiplas disciplinas.

## Requisitos

- Python 3.11+
- MySQL (índice `knowledge`)
- Node.js (apenas para compilar Tailwind CSS)
- Chave LLM: OpenRouter ou Cursor SDK (`ACL_LLM_PROVIDER`)

## Setup rápido

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium   # smoke test frontend
cp .env.example .env          # preencher credenciais
python main.py                # http://127.0.0.1:8001
```

### Staging local (MySQL Docker)

```bash
./bin/staging-setup.sh   # primeira vez
./bin/staging-serve.sh
```

O staging define `ACL_CATALOG_ENABLED=false` (ver `bin/staging-serve.sh`). É **esperado** que `GET /api/curriculum` responda **503** e que o frontend desative o mapa curricular via `catalog_enabled` em `/api/public-config` — sem erro no console.

## Arquitetura

| Camada | Tecnologia |
|--------|------------|
| Backend | FastAPI, Uvicorn, PyMySQL, rank-bm25 |
| Frontend | Vanilla JS (ES modules), Tailwind CSS v4 |
| LLM | OpenRouter ou Cursor (`engine/chat_provider.py`) |
| RAG | BM25 + política de grounding (`engine/retrieval.py`) |

```
main.py → app/factory.py → api/routes.py
                         → frontend/ (static /src, /assets)
                         → engine/ (search, context, chat)
```

## Deploy e produção

### Staging vs produção

| Aspeto | Staging (`./bin/staging-serve.sh`) | Produção |
|--------|--------------------------------------|----------|
| `KERNELBOT_ENV` | `staging` | `production` |
| `ACL_CATALOG_ENABLED` | `false` (fixo no script) | `true` |
| `GET /api/curriculum` | 503 (aceitável) | **200** com disciplinas |
| `ACL_RELOAD_BEARER_TOKEN` | opcional | **obrigatório** |
| Cache `/src/` | `no-store` (dev middleware ativo) | sem `no-store` forçado |

### Variáveis obrigatórias em produção

| Variável | Descrição |
|----------|-----------|
| `KERNELBOT_ENV=production` | Desativa middleware `no-store` em `/src/` |
| `ACL_RELOAD_BEARER_TOKEN` | Protege `GET /health/catalog` e `POST /chat` com `message: "/reload"` |
| `ACL_CATALOG_ENABLED=true` | Habilita catálogo ISS e `GET /api/curriculum` |
| `ACL_CATALOG_JSON_DIR` | Diretório com `lessons.json` / `search-index.json` do ISS |
| `DB_*` | MySQL com tabela `knowledge` indexada |
| `KERNELBOT_FORCE_HSTS=true` | Recomendado atrás de proxy HTTPS |

### Catálogo curricular (pós-deploy)

1. Definir no `.env` de produção:

```bash
ACL_CATALOG_ENABLED=true
ACL_CATALOG_JSON_DIR=/caminho/para/ISS/content
```

2. Reiniciar o serviço e verificar:

```bash
curl -sS http://127.0.0.1:8001/api/public-config
# → "catalog_enabled": true

curl -sS -o /dev/null -w "%{http_code}\n" http://127.0.0.1:8001/api/curriculum
# → 200
```

3. Confirmar drift catálogo ↔ índice (CI / operadores):

```bash
curl -sS -H "Authorization: Bearer SEU_TOKEN" \
  http://127.0.0.1:8001/health/catalog
# → 200 com catalog_enabled, contagens e amostra catalog_only
```

Sem token configurado, `/health/catalog` responde **503** (`reload token not configured`).

### Docker

```bash
cp .env.docker.example .env   # preencher MySQL + LLM + token
docker build -t kernelbot:latest .
docker compose up -d --build
curl -sS http://127.0.0.1:8001/health
```

Runbook completo: [`docs/wiki/20-deploy-railway.md`](docs/wiki/20-deploy-railway.md) (Railway, VPS, Coolify, rollback).

### Rate limit

`POST /chat` está limitado a **30 requisições por IP a cada 60 segundos** (código em `api/routes.py`). Acima disso: HTTP **429**. Não é configurável por `.env`.

## Testes

```bash
# Backend
PYTHONPATH=. pytest tests/ -q

# Smoke frontend (servidor em :8001, Chromium)
python3 bin/validate-frontend.py

# Cross-browser — Chromium + Firefox (CI recomendado)
playwright install chromium firefox
SMOKE_BROWSERS=chromium,firefox python3 bin/validate-frontend.py
```

| Browser | Suporte smoke | Notas |
|---------|---------------|-------|
| Chromium | ✅ padrão | `playwright install chromium` |
| Firefox | ✅ `SMOKE_BROWSERS=firefox` | `playwright install firefox` |
| Edge | manual | `SMOKE_BROWSERS=msedge` se Playwright encontrar o channel |
| WebKit | opcional | proxy Safari; `SMOKE_BROWSERS=webkit` |

Variáveis úteis: `SMOKE_BASE_URL` (default `http://127.0.0.1:8001`), `SMOKE_BROWSERS` ou `SMOKE_BROWSER`.

## Segurança (CSP)

A política em `app/factory.py` usa `unsafe-inline` em `script-src` e `style-src` porque o template e módulos ES ainda dependem de handlers inline. Em produção atrás de reverse proxy, o caminho recomendado é **nonces por request** (middleware ou Nginx que reescreve `index.html`) em vez de ampliar `script-src`. GSAP permanece em `cdnjs.cloudflare.com` até self-host opcional.

## Status

Pronto para publicação pública. Documentação em [`documentation.md`](documentation.md) e [`docs/wiki/`](docs/wiki/README.md).

## Licença

ISC
