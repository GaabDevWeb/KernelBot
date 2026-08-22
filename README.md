# Kernel API

Kernel HTTP reutilizável para busca BM25 e conversa RAG sobre aulas indexadas. Não inclui interface web: adapters de Discord, Moodle, CLI ou outros consumidores usam exclusivamente JSON/SSE.

## Requisitos

- Python 3.11+
- MySQL (índice `knowledge`)
- Chave LLM: OpenRouter ou Cursor SDK (`ACL_LLM_PROVIDER`)

## Setup rápido

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env          # preencher credenciais
python3 main.py               # http://127.0.0.1:8001
```

### Staging local (MySQL Docker)

```bash
./bin/staging-setup.sh   # primeira vez
./bin/staging-serve.sh
```

O staging define `ACL_CATALOG_ENABLED=false`; neste caso `GET /api/curriculum` responde **503**.

## Arquitetura

| Camada | Tecnologia |
|--------|------------|
| Backend | FastAPI, Uvicorn, PyMySQL, rank-bm25 |
| LLM | OpenRouter ou Cursor (`kernel/providers/chat_provider.py`) |
| RAG | BM25 + política de grounding (`kernel/rag/retrieval.py`) |
| Contexto | Camadas + `ContextRouter` (`docs/CONTEXT-ARCHITECTURE.md`, `optimization/`) |

Otimização de tokens/latência (baseline, routing, results): [`optimization/`](optimization/).

```
main.py → app/factory.py → api/routes.py
                         → kernel/ (domínio, RAG, providers e contratos)
```

## API

- `GET /health` — liveness.
- `POST /chat` — resposta JSON canónica; envie `"stream": true` para SSE legado.
- `POST /search` — retrieval sem chamada LLM.

Consulte [`docs/API_SPEC.md`](docs/API_SPEC.md) para contratos e exemplos.

## Deploy e produção

### Staging vs produção

| Aspeto | Staging (`./bin/staging-serve.sh`) | Produção |
|--------|--------------------------------------|----------|
| `KERNELBOT_ENV` | `staging` | `production` |
| `ACL_CATALOG_ENABLED` | `false` (fixo no script) | `true` |
| `GET /api/curriculum` | 503 (aceitável) | **200** com disciplinas |
| `ACL_RELOAD_BEARER_TOKEN` | opcional | **obrigatório** |

### Variáveis obrigatórias em produção

| Variável | Descrição |
|----------|-----------|
| `KERNELBOT_ENV=production` | Ambiente de produção |
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

```

## Status

Pronto para publicação pública. Documentação em [`documentation.md`](documentation.md) e [`docs/wiki/`](docs/wiki/README.md).

## Licença

ISC
