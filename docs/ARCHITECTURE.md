# Architecture

| Campo | Valor |
|-------|-------|
| Sistema | Kernel (ex-KernelBot) |
| Última actualização | 2026-08-27 (V1 hardening) |

## Visão geral

Produto = **Kernel de IA educacional** exposto por API HTTP. Adapters (Orbit/WhatsApp, Discord, …) vivem fora do núcleo e consomem preferencialmente **`/v1/*`**.

```text
Adapters                     Runtime monólito Kernel
┌─────────────┐              ┌──────────────────────────────────┐
│ Orbit WA    │──┐           │  api/                            │
│ Discord     │  │ /v1/chat  │   routes (legado) + v1 router    │
│ Telegram    │──┼──────────►│         │                        │
│ CLI / outros│  │ JSON      │  kernel/                         │
└─────────────┘──┘           │   orchestrator · rag · memory    │
                             │   knowledge · policies · providers│
                             │         │                        │
                             │  MySQL knowledge · LLM providers │
                             └──────────────────────────────────┘
```

**Fronteira Orbit:** transporte Baileys, sessão WhatsApp, formatação, comandos admin locais.  
**Fronteira Kernel:** chat, RAG, memória pin, grounding, providers LLM.

## Estado actual (antes)

```text
main.py → app/factory.py → api/routes.py
                         → frontend/ + templates/   ← remover
                         → engine/ + core/          ← virar kernel/
```

## Arquitectura alvo

```text
kernel/
├── orchestrator/     # ContextManager / build_messages
├── rag/              # search BM25 + retrieval policy
├── memory/           # pinned session + normalização history
├── knowledge/        # MySQL, ingest, lesson catalog
├── disciplines/      # disciplines.json + helpers
├── policies/         # grounding prompts + post_generation
├── tools/            # catalog refresh, reload helpers
├── providers/        # Cursor SDK / OpenRouter
└── schemas/          # contratos de domínio

api/
├── routes/           # chat, search, health (+ ops)
├── middleware/       # security headers, rate limit
└── dependencies/     # AppServices / DI

adapters/             # placeholder + README (sem UI)
```

A estrutura exacta pode usar moves a partir de `engine/` e `core/` com shims temporários para não partir imports a meio do refactor.

## Camadas

| Camada | Responsabilidade | Tecnologia |
|--------|------------------|------------|
| Adapters | Traduzir canal → ChatRequest | fora do núcleo (futuro) |
| API | HTTP, validação, rate limit, auth ops | FastAPI |
| Orchestrator | Escopo, pin, montagem de mensagens | Python (`kernel/orchestrator`) |
| RAG | BM25 + decisão | rank-bm25, `retrieval` |
| Knowledge | Chunks MySQL + catálogo ISS | PyMySQL |
| Policies | Grounding / prompts | `systemPrompt/` |
| Providers | Stream/aggregate LLM | cursor-sdk / httpx OpenRouter |
| Memory | Pin in-process (legado) + transcript in-process (v1) | `PinnedSessionStore`, `TranscriptStore` |

## O que o Kernel NÃO conhece

HTML, CSS, JS de interface, menus, layouts, navegação, frameworks frontend, templates Jinja, mounts estáticos de UI.

## Fluxos principais

### Fluxo 1 — Chat v1 (JSON, multi-canal)

1. Adapter (ex.: Orbit) envia `POST /v1/chat` com `ChannelContext` + `message`
2. API valida schema v1 (`extra="forbid"`), aplica rate limit e auth de canal — **nesta ordem, antes de qualquer leitura/limpeza de estado** (`reset_context` não pode agir sem auth prévia)
3. Deriva `v1_key = v1_memory_key(platform, user_id, channel_id, session_id)` (percent-encoded por segmento — SEC-001, ver `docs/DATA-MODEL.md`)
4. Se `reset_context=true`: limpa `PinnedSessionStore` e `TranscriptStore` da `v1_key`
5. Lê `TranscriptStore.get(v1_key)` como `conversation_history`; `history` do corpo da requisição é sempre ignorado (G7)
6. Orchestrator resolve disciplina/pin/catálogo (`ContextManager.build_messages`, via `api/chat_pipeline.py::run_chat_pipeline`, partilhado com `/chat`)
7. RAG: `search_candidates` → `build_decision`
8. Policies: grounding + system prompts
9. Provider gera resposta (agregada se `stream=false`)
10. Em sucesso `stream=false`: `TranscriptStore.append_pair(v1_key, message, answer, transcript_max_turns)` — `stream=true` não persiste (SSE não passa pelo agregador no handler)
11. API devolve `ChatResponse` canónico (mesmo shape de `/chat`)

### Fluxo 1b — Chat legado

1. Cliente envia `POST /chat` (schema flat)
2. Auth/rate-limit (mesma lógica); sem `ChannelContext`, sem `TranscriptStore`/`reset_context` (G5 — transcript é exclusivo de `/v1/chat`)
3. `history` do corpo (se enviado) alimenta directamente `conversation_history` (ao contrário do v1, onde é ignorado)
4. Orchestrator/RAG/Policies/Provider — mesmos passos 6–9 do Fluxo 1 (via `run_chat_pipeline` partilhado)
5. API devolve `ChatResponse` canónico

### Fluxo 2 — Search only

1. `POST /search`
2. Mesmos passos 2–4
3. Resposta sem provider LLM

### Fluxo 3 — Reload índice

1. `POST /chat` com `message=/reload` + Bearer
2. `SearchEngine.rebuild()` + refresh chaves catálogo

## Integrações externas

| Sistema | Protocolo | Propósito |
|---------|-----------|-----------|
| MySQL | TCP/SQL | tabela `knowledge` |
| OpenRouter | HTTPS streaming | LLM |
| Cursor SDK | SDK async | LLM (default actual) |
| Catálogo ISS (JSON) | filesystem | curriculum / rescue lexical |
| Trace SQLite | filesystem | painel operacional (`ACL_TRACE_DB_PATH`) |

## Decisões arquitecturais

| Decisão | ADR |
|---------|-----|
| Monólito Kernel + API; remoção UI; JSON canónico | ADR-0001 |
| API `/v1` canal-agnóstica; legado preservado; Orbit como cliente HTTP | ADR-0002 |
| Trace store + painel `/traces` no Kernel; Orbit só HTTP ingest | ADR-0003 |

## Considerações operacionais

- Deploy: Docker/Uvicorn sem copiar `frontend/`/`templates/` (excepto templates Jinja do painel `/traces`)
- Observabilidade: logs estruturados + `/internal/*` (Bearer) + **TRACE** persistente (`/traces`, SQLite)
- Escalabilidade: pin e rate-limit continuam in-process (limitação conhecida; fora de escopo nesta missão)
- Branches: integração `feature/kernel-orbit-integration`; tracing `feature/orbit-kernel-tracing`
## Segurança (visão arquitectural)

- Autenticação de canal: Bearer em `/v1/chat` e `/chat` (quando exigida)
- Ops: Bearer reload (`/reload`, `/health/catalog`); Bearer interno (`/internal/*`)
- Rate limit: `/v1/chat`, `/chat`, `/search`
- Headers de segurança genéricos (sem CSP de browser UI)

## Mapeamento de migração (referência)

| Origem | Destino conceptual |
|--------|-------------------|
| `engine/context.py` | `kernel/orchestrator` |
| `engine/search.py` + `retrieval.py` | `kernel/rag` |
| `engine/database.py` + ingest/catalog | `kernel/knowledge` |
| `engine/pinned_store.py` | `kernel/memory` |
| `engine/chat_provider.py` | `kernel/providers` |
| `core/disciplines*` | `kernel/disciplines` |
| `core/systemPrompt/` | `kernel/policies` |
| `core/config.py` | `kernel` bootstrap / settings |
| `api/routes.py` | `api/routes/*` |
| `frontend/`, `templates/` | **removido** |
| — | `adapters/` placeholder |

## V1 — decisões congeladas (2026-08-27)

Ver `docs/V1_SCOPE.md` e `docs/v1-readiness.md`.

- **Kernel** = cérebro (RAG, contexto, LLM, transcript SSOT, idempotência).
- **Orbit** = adapter WhatsApp (buffer recente, dedupe local, `X-Message-Id`, userLock por grupo).
- **Knowledge RAG** (MySQL/BM25) separado de **Group Memory** (SQLite por grupo).
- **Recent context** via `metadata.recent_context` — nunca concatenado como query RAG.
- **Context Router** + budgets quando `ACL_CONTEXT_ROUTER=1`.
- **Single worker** — transcript, idempotency e rate limit in-memory.
- **Deploy:** SQLite/traces/group memory em `data/` — nunca commitados.
