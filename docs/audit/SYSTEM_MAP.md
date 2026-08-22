# SYSTEM_MAP — KernelBot True Kernel

| Campo | Valor |
|-------|-------|
| Data | 2026-07-26 |
| Branch | `kernel-observability-audit` |
| Escopo | Working tree True Kernel (frontend removido) |
| Modo | Somente leitura — sem alteração de comportamento |

## 1. Visão geral

O produto actual é um **monólito FastAPI** cujo domínio vive em `kernel/`. Não há UI servida pelo processo. Consumidores externos (CLI, adapters futuros) usam HTTP JSON/SSE.

```text
Adapter/CLI ──HTTP──► api/routes.py
                          │
                          ▼
                     AppServices (DI)
                          │
          ┌───────────────┼───────────────┐
          ▼               ▼               ▼
   ContextManager   SearchEngine    ChatProvider
   (orchestrator)      (RAG)         (LLM)
          │               │               │
          └──────► MySQL knowledge ◄──────┘
                   (+ LessonCatalog ISS opcional)
```

## 2. Árvore relevante

```text
KernelBot/
├── main.py                 # composition root + Uvicorn
├── app/
│   ├── factory.py          # FastAPI, lifespan, security headers
│   └── state.py            # AppServices dataclass
├── api/
│   ├── routes.py           # todos os endpoints
│   └── rate_limit.py       # token-bucket in-process
├── kernel/
│   ├── config.py           # Settings / env
│   ├── structured_log.py   # log_event JSON
│   ├── logging_config.py
│   ├── orchestrator/context.py   # build_messages (orquestração)
│   ├── rag/{search,retrieval}.py
│   ├── providers/{chat_provider,aggregate,disambiguation_parse}.py
│   ├── knowledge/{database,lesson_catalog,catalog_sync,jsons_ingest,wiki_doc}.py
│   ├── memory/pinned_store.py
│   ├── disciplines/{disciplines.py,disciplines.json}
│   ├── policies/systemPrompt/*.txt
│   └── schemas/{chat,search}.py
├── adapters/README.md
├── bin/{chat-cli,staging-*,ingest-*}.sh
├── docker/, Dockerfile, docker-compose*.yml
└── docs/
```

## 3. Pontos de entrada

| Entrada | Mecanismo |
|---------|-----------|
| Produção | `uvicorn main:app` (Dockerfile) |
| Local | `python main.py` ou `./bin/staging-serve.sh` |
| CLI chat | `bin/chat-cli.sh` → `POST /chat` |
| Ingest aulas | `bin/ingest-jsons.sh` → `kernel.knowledge.jsons_ingest` |
| Ingest wiki | `bin/ingest-wiki-doc.sh` → `kernel.knowledge.wiki_doc` |

**Boot:** `create_app(services_factory=build_services)` — serviços criados no **lifespan**, não na importação do módulo.

## 4. Dependências

### Python (`requirements.txt`)

`fastapi`, `pydantic`, `uvicorn`, `httpx`, `python-dotenv`, `rank-bm25`, `PyMySQL`, `cryptography`, `PyYAML`, `jsonschema`, `cursor-sdk`, `pytest`

### Externas

| Sistema | Uso |
|---------|-----|
| MySQL `knowledge` | Corpus RAG (chunks BM25 in-RAM) |
| OpenRouter | LLM (`ACL_LLM_PROVIDER=openrouter`) |
| Cursor SDK | LLM (`ACL_LLM_PROVIDER=cursor`, default Settings) |
| ISS `lessons.json` | Catálogo lexical opcional |

## 5. Responsabilidades por módulo

| Módulo | Responsabilidade |
|--------|------------------|
| `api/routes` | Validação HTTP, rate limit, wiring |
| `orchestrator/context` | Escopo, pin, catálogo, RAG call, montagem prompt |
| `rag/search` | BM25Okapi por silo/disciplina |
| `rag/retrieval` | Gates classificatórios + selecção top_k |
| `providers/chat_provider` | Stream LLM + ACL_META + pós-geração |
| `providers/aggregate` | SSE → JSON canónico |
| `memory/pinned_store` | Pin RAG por `session_id` (RAM) |
| `knowledge/*` | MySQL, ingest, catálogo ISS |
| `disciplines/*` | SSOT de comandos/labels/markers (JSON) |
| `policies/systemPrompt` | Textos de system/grounding |

## 6. Fluxo principal (alvo)

```text
POST /chat (ChatRequest)
  → rate limit
  → ContextManager.build_messages
       → comandos / disciplina / pin / history
       → LessonCatalog (opcional)
       → SearchEngine.search_candidates
       → retrieval.build_decision
       → assemble system + history + user
  → ChatProvider.stream_response
  → aggregate_sse (se stream=false) | StreamingResponse (se true)
  → ChatResponse / SSE
```

## 7. Achado bloqueante (evidência)

Em `kernel/orchestrator/context.py`:

- `__init__` define `self._search_engine`
- `build_messages` e `_try_catalog_rescue` chamam `self._search_kernel.rag.search_candidates(...)`

**Efeito:** o caminho normal de `/chat` lança `AttributeError` antes do retrieval/LLM.  
`/search` e `/reload` **não** usam esse atributo e permanecem executáveis.

> Auditoria: **documentar apenas** — correção fora de escopo desta missão.

## 8. Subagentes e evidências

| ID | Área | Agent |
|----|------|-------|
| SA1 | Arquitectura | [SA1](a20fb5da-b88a-4107-86ec-2f00b9eca506) |
| SA2 | API | [SA2](cfc833f7-7389-44c8-9640-85c8b1e2ef38) |
| SA3 | Pipeline | [SA3](b81d1d06-b43f-4b18-957d-4d06633afd20) |
| SA4 | RAG | [SA4](6015292a-8fe7-4cbd-ab09-0f89289de2b8) |
| SA5 | Disciplinas | [SA5](fb7c72af-9b02-483d-bf19-dfbf986dcc31) |
| SA6 | Context | [SA6](a47658b3-0d9f-40d6-9fa5-11daa21e56ed) |
| SA7 | LLM | [SA7](5083d1e2-f109-4188-a4ea-08dbddf947c4) |
| SA8 | Memória | [SA8](9278020d-2a71-4d99-ada4-4f9c7baa1eb8) |
| SA9 | ACL/Segurança | [SA9](27f372f4-0285-44ef-8ca4-0340a33d0251) |
| SA10 | Observabilidade | [SA10](5de58611-577b-47ba-80b0-a259e9695ab7) |

## 9. Documentos irmãos

- [`API_MAP.md`](API_MAP.md)
- [`KERNEL_FLOW.md`](KERNEL_FLOW.md)
- [`OBSERVABILITY_API_PROPOSAL.md`](OBSERVABILITY_API_PROPOSAL.md)
