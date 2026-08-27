# V1 Scope — Kernel / Orbit

| Campo | Valor |
|-------|-------|
| Versão alvo | V1 (freeze arquitectural) |
| Branch hardening | `feature/v1-hardening` |
| Data | 2026-08-27 |

## IN (escopo V1)

- WhatsApp via Orbit (Baileys adapter)
- Kernel monólito FastAPI (`POST /v1/chat`, `/v1/groups/*`, `/internal/*`)
- RAG BM25 lexical (Knowledge silo — MySQL + índice in-process)
- Group Memory (SQLite isolado por `platform:channel_id`)
- Group Profile (derivado, não fonte oficial)
- Contexto recente Orbit → metadata (separado de RAG query)
- Context Router + Context Budget (`ACL_CONTEXT_ROUTER`)
- Contexto temporal + calendário académico
- Transcript in-process (Kernel SSOT)
- Pin de sessão
- Tracing operacional (SQLite + painel `/traces`)
- Idempotência (`X-Message-Id` + store in-memory)
- Rate limit in-memory (chat/search/groups/internal)
- Invocação contextual `@orbit` vazio em grupos
- Apresentação por grupo (`introduction_sent`)
- Automações/comms (scheduler + Orbit outbound)
- Ops Center (`/ops/*`)
- Provider LLM (Cursor SDK / OpenRouter fallback chain)

## OUT (explicitamente fora da V1)

- Vector DB / embeddings / RAG híbrido denso
- Redis, Kafka, filas persistentes de chat
- Microserviços / multi-node Kernel
- Múltiplos LLMs por domínio
- Agentes autónomos / memória episódica avançada
- Fine-tuning
- Cache de respostas LLM (quebra transcript)
- UI web de chat (True Kernel — ADR-0001)

## Premissas de deploy V1

- **Single worker** Uvicorn (transcript, idempotency, rate limit in-memory)
- Orbit **single process** (userLock in-memory)
- SQLite runtime (`data/*.sqlite3`) **fora do Git**
- Timezone: `America/Sao_Paulo` (`KERNEL_TIMEZONE`)

## Kill switches (env)

| Flag | Default | Efeito |
|------|---------|--------|
| `KERNEL_GROUP_MEMORY_ENABLED` | true | Desliga store + injecção GM |
| `KERNEL_GROUP_PROFILE_ENABLED` | true | Desliga profile block |
| `KERNEL_IDEMPOTENCY_ENABLED` | true | Desliga store idempotência |
| `ACL_CONTEXT_ROUTER` | false | Router off = budgets legado parcial |
| `ACL_TRACE_ENABLED` | true | Desliga trace bus |
| `ACL_CATALOG_ENABLED` | false | Catálogo lexical |
| `ACL_DISAMBIGUATION_ENABLED` | false | Desambiguação RAG |

## Contratos congelados

1. Kernel = cérebro; Orbit = adapter transporte
2. Knowledge RAG ≠ Group Memory (source_type distinto)
3. Recent context ≠ RAG query
4. Group Profile = percepção social, nunca fonte oficial
5. Hierarquia: temporal/calendar > institucional > RAG > transcript > modelo geral
