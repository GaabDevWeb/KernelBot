# PRD — Operational Trace Panel (Fatia A / S2)

| Campo | Valor |
|-------|-------|
| Data | 2026-07-28 |
| Autor | MegaBrain / missão utilizador |
| Status | draft |
| Versão | 1.0 (fatia A) |
| Branch | `feature/orbit-kernel-tracing` |

## Contexto

**Proveniência:** missão `/MegaBrain` tracing Orbit+Kernel; grill-me Q1–Q4 (2026-07-28).

Problema: falhas Orbit↔Kernel difíceis de diagnosticar sem correlação ponta a ponta. Existe `kernel/inspect` (ring buffer RAM + `/internal/*` + `request_id`), insuficiente para debug de conversa persistente.

## Objectivo (fatia A)

Depurar uma conversa completa WhatsApp → Orbit → Kernel → WhatsApp o mais rápido possível.

**Unidade SSOT:** `TRACE` (não log line). Identificador: `trace_id` UUID partilhado.

## Decisões grill-me (congeladas)

| ID | Decisão |
|----|---------|
| G1 | Kernel-hosted: SQLite + painel no mesmo FastAPI; Orbit só HTTP ingest |
| G2 | Transporte `X-Trace-Id`; eco opcional `metadata.trace_id`; `request_id` coexiste |
| G3 | Painel: login cookie `trace_auth` = `ACL_INTERNAL_BEARER_TOKEN`; escrita async Queue |
| G4 | Escopo **S2**; path `ACL_TRACE_DB_PATH` default `data/traces.sqlite3` |

## Requisitos funcionais (fatia A)

| ID | Descrição | Prioridade | Critério de aceite |
|----|-----------|------------|-------------------|
| RF-001 | Orbit gera `trace_id` UUID por mensagem processada | Must | Header `X-Trace-Id` em `/v1/chat` e ingest |
| RF-002 | Kernel lê `X-Trace-Id` (gera se ausente) e associa eventos | Must | Todos eventos Kernel do turno partilham o id |
| RF-003 | `POST /internal/traces/events` ingest (Bearer interno) | Must | Orbit não toca SQLite |
| RF-004 | Store SQLite async (`asyncio.Queue` + worker); ERROR prioritário | Must | Chat não bloqueia se trace falhar; falhas logadas |
| RF-005 | Eventos Kernel mínimos: REQUEST_RECEIVED, TRANSCRIPT_LOADED, PIN_LOADED, RAG_STARTED, RAG_FINISHED, LLM_STARTED, LLM_FINISHED, RESPONSE_GENERATED, RESPONSE_RETURNED, ERROR | Must | Visíveis na timeline |
| RF-006 | Eventos Orbit mínimos: MESSAGE_RECEIVED, MESSAGE_PARSED, REQUEST_SENT_TO_KERNEL, RESPONSE_RECEIVED_FROM_KERNEL, MESSAGE_SENT_TO_WHATSAPP, ERROR | Must | Ingestidos via RF-003 |
| RF-007 | Painel Jinja: `/traces/login`, `/traces`, `/traces/{trace_id}` | Must | Cookie auth; lista + detalhe + timeline |
| RF-008 | Redact tokens/Authorization/API keys em `data` persistido | Must | Secrets nunca em SQLite |
| RF-009 | Eco `metadata.trace_id` na resposta chat (aditivo) | Should | Não altera `answer` |

## Fora de escopo (fatia A)

- Export ZIP avançado
- Dashboards elaborados / métricas agregadas 24h
- Filtros complexos (telefone/grupo/texto/período — lista básica por recentes + busca por `trace_id` OK)
- Polish visual / frontend-pro Vision
- Serviço separado, Elasticsearch, Redis, login multi-user, RBAC
- Contaminar body de `/v1/chat` com campos de observabilidade (só header)

## Arquitectura alvo (fatia A)

```text
Orbit ──X-Trace-Id──► POST /v1/chat ──► Kernel pipeline ──► eventos → Queue → SQLite
   └──POST /internal/traces/events ─────────────────────────────────────┘
Operador ──/traces/login (cookie)──► /traces ──► /traces/{id} timeline
```

## Dependências e riscos

| Item | Tipo | Mitigação |
|------|------|-----------|
| Latência chat | risco | Queue async; best-effort |
| Volume SQLite | risco | Fatia A sem retenção agressiva; path configurável |
| Conflito com `request_id` | — | Coexistem; documentar |
| Auth cookie = token interno | risco aceite | Só rede privada; SameSite=Lax |

## Referências

- ADR: `docs/adr/0003-operational-trace-store.md`
- API: `docs/API_SPEC.md` (secção Trace)
- Grill: `.agent_history.md` 2026-07-28 Trace Q1–Q4
