# Estrutura do código

[← Índice](README.md)

## Árvore do repositório

```
KernelBot/
├── main.py                      # Boot: Settings, SearchEngine.rebuild(), Uvicorn :8001
├── app/
│   ├── factory.py               # FastAPI app, static, lifespan
│   └── state.py                 # AppServices dataclass
├── api/
│   └── routes.py                # GET /, POST /chat, GET /health/catalog
├── core/
│   ├── config.py                # Settings.load(), env ACL_*
│   ├── logging_config.py        # Text/JSON formatters, SecretRedactingFilter
│   ├── structured_log.py        # log_event(), redact_secrets()
│   └── systemPrompt/            # system_prompt, grounding_strict, catalog_router, sticky (ver wiki §17)
├── engine/
│   ├── search.py                # SearchEngine, silos BM25
│   ├── database.py              # fetch_db_chunks, _chunk_text, _split_meta_block
│   ├── retrieval.py             # build_decision, post_generation_flags
│   ├── context.py               # ContextManager, hard_stop_message
│   ├── chat_provider.py         # OpenRouter streaming, ACL_META
│   ├── catalog_sync.py          # bootstrap_catalog_state, refresh keys
│   ├── lesson_catalog.py        # Catálogo lexical ISS
│   └── pinned_store.py          # PinnedSessionStore
├── templates/index.html
├── frontend/src/                # ui.js, api.js, components/
├── bin/                         # staging-setup.sh, staging-serve.sh, …
├── docs/wiki/                   # Esta documentação
├── docker-compose.staging.yml
├── TESTE-LOCAL.md
├── .env / .env.example
└── .env.staging.local           # MySQL local :3307 (não commitar)
```

## Responsabilidades por módulo

### `main.py`

- `configure_logging()`
- `Settings.load()` — falha sem `OPENROUTER_API_KEY` e prompts
- `SearchEngine.rebuild()` no import (índice no boot)
- `bootstrap_catalog_state()` — catálogo + chaves indexadas
- `uvicorn.run("main:app", host=127.0.0.1, port=8001)`

### `engine/database.py`

| Export / função | Responsabilidade |
|-----------------|------------------|
| `fetch_db_chunks` | SELECT `active=1` → lista de dicts `{text, source, discipline}` |
| `_split_meta_block` | Separa bloco meta B2 do body |
| `_chunk_text` | Janelas 500/50; meta só `chunk_index==0` |
| `fetch_indexed_lesson_keys` | DISTINCT discipline, slug para drift/CI |

### `engine/search.py`

| Método | Responsabilidade |
|--------|------------------|
| `rebuild()` | Carrega chunks do MySQL, tokeniza, BM25Okapi por silo |
| `search_candidates()` | Query → candidatos com `raw_score`, `matched_terms` |
| `chunks` / `chunks_for_scope` | Introspecção do índice |

### `engine/retrieval.py`

| Função | Responsabilidade |
|--------|------------------|
| `build_decision()` | Aplica MIN_SCORE, margin, coverage, MIN_TERMS, vague_but_high_risk |
| `post_generation_flags()` | Sanity check pós-LLM |
| `normalize_and_tokenize()` | Tokenização alinhada ao índice |

### `engine/context.py`

| Responsabilidade |
|------------------|
| Parse comandos de escopo (`/doc`, `/python`, …) |
| Integração catálogo (`index_gap`) |
| Montagem de mensagens para OpenRouter |
| Hard stop messages por `reason` |
| Pin: save/load via `PinnedSessionStore` |

### `engine/chat_provider.py`

| Responsabilidade |
|------------------|
| Streaming OpenRouter com fallback de modelos |
| Emissão `ACL_META` v=3 |
| Override `post_generation_misalignment` |

## Frontend (`frontend/src/`)

| Ficheiro | Papel |
|----------|-------|
| `main.js` | Entry da UI |
| `api.js` | `fetch /chat`, parse SSE, `ACL_META` |
| `ui.js` | Chat loop, markdown, IndexGapAlert, DisambiguationChips |
| `utils/sessionId.js` | UUID em `sessionStorage` |

## Scripts operacionais (`bin/`)

| Script | Função |
|--------|--------|
| `staging-docker-up.sh` | MySQL Docker porta 3307 |
| `staging-apply-schema.sh` | DDL `knowledge` idempotente |
| `staging-setup.sh` | Schema + seed + E2E |
| `staging-serve.sh` | Bot com `KERNELBOT_ENV=staging` |
| `staging-ingest-iss.sh` | Ingest ISS completo no MySQL local |

## Código legado / não integrado

| Item | Nota |
|------|------|
| `engine/watcher.py` | Não dispara rebuild automático |
| `content/` no KernelBot | Não alimenta BM25 no fluxo actual |

## Ver também

- [04-dados-e-mysql.md](04-dados-e-mysql.md)
- [07-apis-e-sse.md](07-apis-e-sse.md)
