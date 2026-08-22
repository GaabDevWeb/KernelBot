# ATTACK_SURFACE_MAP — True Kernel

| Campo | Valor |
|-------|-------|
| Data | 2026-07-26 |
| Branch | `security-audit` |

## 1. Diagrama de superfície

```text
                    Internet / Canais
                           │
          ┌────────────────┼────────────────┐
          ▼                ▼                ▼
     WhatsApp         Discord/Telegram    Moodle/Web/Mobile
     adapter              adapter            adapter
          │                │                │
          └────────────────┼────────────────┘
                           ▼
                 ┌───────────────────┐
                 │  Kernel HTTP :8001 │
                 │  (FastAPI/Uvicorn) │
                 └─────────┬─────────┘
           ┌───────────────┼───────────────┐
           ▼               ▼               ▼
      Públicos         Ops Bearer      Internal Bearer
   /chat /search      /reload          /internal/*
   /health            /health/catalog  (prompts, pipeline)
   /api/*             (token)          (token ou fallback reload)
           │               │               │
           ▼               ▼               ▼
      OpenRouter/Cursor   MySQL BM25    PipelineRecorder (RAM)
      API keys            knowledge     pin sessions (RAM)
```

## 2. Vetores de entrada

| Vetor | Controlo actual | Risco |
|-------|-----------------|-------|
| `POST /chat` body | Pydantic + rate 30/IP | LLM cost, injection, pin |
| `POST /search` body | Pydantic + rate 30/IP | Scraping RAG |
| `session_id` | Regex only | Cross-user pin |
| `history[]` | roles limitados | Prompt injection / size DoS |
| `metadata{}` | sem bound | Memory DoS |
| `discipline` | whitelist ou global | Escopo curricular |
| `Authorization` Bearer | ops/internal | Privilege se vazado |
| `X-Request-Id` | aceite se ≤128 | Baixo (correlação) |
| OpenAPI `/docs` | público default | Reconhecimento |
| Cursor workspace | env flag | FS / tool abuse |
| MySQL staging ports | compose publish | Credenciais conhecidas |

## 3. Endpoints por zona de confiança

### Zona 0 — Anónimo (público)

| Método | Path | Auth | Rate limit |
|--------|------|------|------------|
| GET | `/health` | não | não |
| GET | `/api/public-config` | não | não |
| GET | `/api/curriculum` | não | não |
| GET | `/api/curriculum/{id}` | não | não |
| POST | `/chat` | não* | sim |
| POST | `/search` | não | sim |
| GET | `/openapi.json`, `/docs`, `/redoc` | não | não |

\*excepto `message=/reload` → Bearer

### Zona 1 — Operações

| Método | Path | Auth |
|--------|------|------|
| GET | `/health/catalog` | Bearer reload |
| POST | `/chat` + `/reload` | Bearer reload |

### Zona 2 — Observabilidade interna

| Path prefix | Auth |
|-------------|------|
| `/internal/*` | Bearer internal **ou** reload (fallback) |

Inclui: system, disciplines, rag, rag/query, context, **prompt**, pipeline, models, metrics, health/deep, memory/session, requests/recent.

## 4. Dependências críticas

| Dependência | Tipo de risco |
|-------------|---------------|
| `OPENROUTER_API_KEY` / `CURSOR_API_KEY` | Abuso financeiro |
| MySQL `knowledge` | Confidencialidade do corpus |
| `ACL_RELOAD_BEARER_TOKEN` | Integridade índice + (fallback) prompts |
| `ACL_INTERNAL_BEARER_TOKEN` | Confidencialidade observabilidade |
| `cursor-sdk` | Superfície agente local |
| Uvicorn workers | Amplificação rate-limit |

## 5. Fluxos de risco (cadeias)

### Cadeia A — Esgotar LLM
`URL pública` → `POST /chat` × N IPs/réplicas → provider API → **custo/indisponibilidade**

### Cadeia B — Contornar LMS
`Moodle auth` by-pass → `POST /search` directo ao Kernel → **snippets do índice**

### Cadeia C — Cross-user pin
`Adapter session_id=user_id` → atacante reutiliza ID → **contexto RAG alheio**

### Cadeia D — Token CI
`ACL_RELOAD_BEARER_TOKEN` leak → `/internal/prompt/*` + `/reload` → **prompts + sabotagem índice**

### Cadeia E — Cursor workspace
`ACL_LLM_PROVIDER=cursor` + chat-only false → injection → **leitura FS do host**

## 6. Activos vs ameaças (resumo STRIDE-lite)

| Activo | Spoofing | Tampering | Repudiation | Info disclosure | DoS | EoP |
|--------|----------|-----------|-------------|-----------------|-----|-----|
| /chat | n/a (open) | history | logs fracos | injection/RAG | tokens | — |
| /search | n/a | — | — | snippets | CPU BM25 | — |
| pin store | session_id | pin overwrite | — | via internal | RAM | — |
| /internal | Bearer | — | — | prompts | — | reload token |
| LLM keys | — | — | — | logs? | abuse | — |

## 7. Premissas de segurança futuras (multi-canal)

Adapters **devem** ser a fronteira de AuthN/AuthZ. O Kernel actual **não** isola tenants. Expor o Kernel na Internet sem gateway viola essa premissa.
