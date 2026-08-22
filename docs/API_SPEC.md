# API Specification

| Campo | Valor |
|-------|-------|
| Versão | v1 (canais) + legado sem prefixo |
| Base URL | `http://127.0.0.1:8001` (dev) |
| Última actualização | 2026-07-28 |

## Autenticação

| Endpoint | Auth |
|----------|------|
| `GET /v1/health` | none |
| `POST /v1/chat` | Bearer canal (`ACL_API_BEARER_TOKEN` / `ACL_CHANNEL_API_KEYS`) quando `ACL_REQUIRE_API_AUTH` ou `KERNELBOT_ENV=production` |
| `GET /health` | none |
| `POST /chat` | Bearer canal (idem); Bearer **reload** se `message` for `/reload` |
| `POST /search` | Mesmo Bearer de canal que `/chat` (quando auth exigida) |
| `GET /health/catalog` | Bearer `ACL_RELOAD_BEARER_TOKEN` (operacional) |
| `/internal/*` | Bearer `ACL_INTERNAL_BEARER_TOKEN` (em production **obrigatório e ≠ reload**) |
| `POST /internal/traces/events` | Bearer interno (idem) |
| `GET/POST /traces/login`, `GET /traces`, `GET /traces/dashboard`, `GET /traces/{trace_id}`, exports ZIP | Cookie `trace_auth` (valor = token interno) após login |
| Curriculum | none (metadados de catálogo) |

Em development, auth de canal é opcional (CLI local). Em production o boot falha sem tokens de canal + internal.

---

## API v1 — contrato multi-canal (Must — Kernel↔Orbit)

Contrato **recomendado** para adapters (Orbit WhatsApp, Discord futuro). Endpoints legados sem prefixo mantêm-se para compatibilidade.

### ChannelContext

| Campo | Tipo | Obrigatório | Notas |
|-------|------|-------------|-------|
| `platform` | string | sim | Plataforma lógica: `whatsapp`, `discord`, `cli`, `telegram`, … (1–64). Mapeia para `channel` interno legado. |
| `user_id` | string | sim | Identificador do utilizador **no canal** (1–256). Sem PII extra obrigatória. |
| `channel_id` | string | sim | Identificador da conversa/thread na plataforma (1–256). **Não** confundir com `platform`. |
| `session_id` | string \| null | não | Opaco `[A-Za-z0-9_-]{8,128}`; se omitido, o Kernel deriva um estável a partir de `platform`+`user_id`+`channel_id`. |

**Proibido** no schema: `jid`, `phone`, `guild_id`, `baileys_*`, ou qualquer campo vendor-specific. Dados extras → `metadata` (limites actuais).

### GET /v1/health

**Descrição:** Liveness versionado para probes do adapter.

**Autenticação:** none

**Response 200:**

```json
{
  "status": "ok"
}
```

### POST /v1/chat

**Descrição:** Chat multi-canal. Encaminha para o mesmo pipeline de `POST /chat` (orquestração + RAG + LLM).

**Autenticação:** Bearer de canal quando auth exigida (igual a `/chat`).

**Request:**

```json
{
  "context": {
    "platform": "whatsapp",
    "user_id": "5511999999999",
    "channel_id": "5511888888888",
    "session_id": null
  },
  "message": "O que é normalização SQL?",
  "discipline": null,
  "history": [],
  "metadata": {},
  "stream": false
}
```

| Campo | Tipo | Obrigatório | Notas |
|-------|------|-------------|-------|
| `context` | ChannelContext | sim | ver tabela acima |
| `message` | string | sim | 1–16000 chars |
| `discipline` | string \| null | não | filtro de silo |
| `history` | array | não | máx. 40; roles `user`/`assistant` |
| `metadata` | object | não | ≤32 chaves, profundidade ≤2, ≤4096 bytes |
| `stream` | boolean | não | default `false` (JSON). `true` = SSE legado opt-in |
| `reset_context` | boolean | não | default `false`; limpa transcript + pin da chave `context` antes de processar o turno (G3) |

**Response 200 (`stream=false`):** mesmo `ChatResponse` canónico de `POST /chat`.

**Mapeamento interno:**

| v1 | Legado interno |
|----|----------------|
| `context.platform` | `channel` |
| `context.user_id` | `user_id` |
| `context.session_id` ou derivado | `session_id` |
| `message` / `history` / `discipline` / `metadata` / `stream` | iguais |

**Erros:** 401 (auth), 422 (validação), 429 (rate limit), 503 (serviços).

**Nota Orbit:** `/reload` **não** faz parte de `/v1/chat`. Comandos administrativos locais ficam no Orbit; reload operacional continua no legado `POST /chat` com Bearer reload.

### Consumo Orbit — KernelProvider (contrato)

O Orbit substitui o provider LLM directo por HTTP:

```text
Orbit (Baileys) → formata texto → POST /v1/chat → lê answer → envia WhatsApp
```

Exemplo mínimo (`stream=false`):

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token-canal-whatsapp>" \
  -d '{
    "context": {
      "platform": "whatsapp",
      "user_id": "<wa-user-id>",
      "channel_id": "<wa-chat-id>"
    },
    "message": "ola"
  }'
```

O provider no Orbit deve:

1. Mapear identidade WhatsApp → `ChannelContext` (sem enviar campos Baileys crus no schema).
2. Usar `answer` da resposta como texto a entregar.
3. Tratar 429/401/5xx com retry/backoff local (política do Orbit).
4. **Não** implementar RAG/LLM no Orbit.
## Convenções

- Content-Type: `application/json`
- Datas em metadata: ISO 8601 UTC quando aplicável
- `channel`: string estável (`web`, `discord`, `telegram`, `whatsapp`, `moodle`, `cli`, `mobile`, `unknown`)
- Erros FastAPI: `{ "detail": "..." }` (compatível com estado actual)

## Endpoints mínimos (Must)

### GET /health

**Descrição:** Liveness para orquestradores/Docker.

**Autenticação:** none

**Response 200:**

```json
{
  "status": "ok"
}
```

---

### POST /chat

**Descrição:** Endpoint principal do Kernel. Orquestra escopo, RAG, políticas e LLM; devolve contrato universal.

**Autenticação:** none (rate limit 30 req / IP / 60s → 429)

**Request (contrato universal de entrada):**

```json
{
  "user_id": "123",
  "message": "O que é normalização SQL?",
  "channel": "discord",
  "metadata": {},
  "discipline": "sql-modelagem-relacional",
  "session_id": "sess_abc12345",
  "history": [
    { "role": "user", "content": "…" },
    { "role": "assistant", "content": "…" }
  ],
  "stream": false
}
```

| Campo | Tipo | Obrigatório | Notas |
|-------|------|-------------|-------|
| `message` | string | sim | max 16000 chars (limite actual) |
| `user_id` | string | não* | *recomendado; se omitido, adapters devem enviar ou usar `anonymous` |
| `channel` | string | não | default `unknown` |
| `metadata` | object | não | ≤32 chaves, profundidade ≤2, ≤4096 bytes JSON; ecoado em saída |
| `discipline` | string \| null | não | filtro de silo (compatível com API actual) |
| `session_id` | string \| null | não | `[A-Za-z0-9_-]{8,128}` opaco (UUID); **não** só dígitos; pin isola por `channel:user_id:session_id` |
| `history` | array | não | mesmas regras de normalização actuais |
| `stream` | boolean | não | default `false`; se `true`, resposta SSE |

**Response 200 (JSON canónico — `stream=false`):**

```json
{
  "answer": "…",
  "discipline": "sql-modelagem-relacional",
  "sources": ["db:sql-modelagem-relacional/…"],
  "confidence": 0.95,
  "metadata": {
    "user_id": "123",
    "channel": "discord",
    "decision": "answer",
    "reason": "ok",
    "label": "SQL — Modelagem Relacional",
    "source_details": [],
    "grounding_policy": "anchored",
    "llm_called": true,
    "tokens_used": 0,
    "session_id": "sess_abc12345",
    "request_metadata": {}
  }
}
```

**Response 200 (SSE — `stream=true`):** `text/event-stream` compatível com envelope legado:

- `data: [ACL_META]{…}`
- `data: <token>`
- `data: [DONE]`

**Erros:**

| Status | Descrição |
|--------|-----------|
| 422 | Validação Pydantic (JSON/campos inválidos ou ausentes) — padrão FastAPI |
| 401 | Bearer inválido em `/reload` |
| 413 | *(não usado)* limites de tamanho aplicados via schema → 422 |
| 429 | rate limit |
| 503 | reload token não configurado (só `/reload`) / serviços indisponíveis |

**Comando especial:** `message: "/reload"` — reconstrói BM25; exige Bearer (comportamento actual).

---

### POST /search

**Descrição:** Retrieval/RAG sem chamada LLM. Útil para adapters, debug e Moodle/LMS que só precisam de fontes.

**Autenticação:** none (aplicar rate limit alinhado a `/chat`)

**Request:**

```json
{
  "user_id": "123",
  "message": "normalização 3FN",
  "channel": "moodle",
  "discipline": "sql-modelagem-relacional",
  "session_id": null,
  "metadata": {},
  "top_k": 5
}
```

**Response 200:**

```json
{
  "discipline": "sql-modelagem-relacional",
  "decision": "answer",
  "reason": "ok",
  "confidence": 0.91,
  "sources": ["db:…"],
  "candidates": [
    {
      "source": "db:…",
      "score": 12.3,
      "score_normalized": 0.87,
      "snippet": "…"
    }
  ],
  "metadata": {
    "user_id": "123",
    "channel": "moodle",
    "label": "…"
  }
}
```

**Erros:** 422, 429 (mesma família de `/chat`).

---

## Endpoints operacionais / compatibilidade (Should)

Mantidos se úteis a adapters sem reintroduzir UI:

| Método | Path | Notas |
|--------|------|-------|
| GET | `/api/public-config` | flags públicas (ex.: `catalog_enabled`) |
| GET | `/api/curriculum` | lista disciplinas do catálogo |
| GET | `/api/curriculum/{discipline_id}` | aulas |
| GET | `/health/catalog` | drift catálogo↔índice (Bearer) |

**Removidos (Must):** `GET /`, mounts `/src`, `/assets`, `/favicon.ico`, export estático de disciplines sob `/src/config/…`.

Disciplines SSOT passa a ser consumida só via código Kernel (e, se necessário, endpoint JSON dedicado sob `/api/…` — não sob `/src`).

## Schemas partilhados

### ChatRequest

Ver tabela em `POST /chat`.

### ChatResponse

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| answer | string | sim | texto final agregado |
| discipline | string \| null | sim | silo efectivo |
| sources | string[] | sim | identificadores de fonte |
| confidence | number | sim | 0..1 (da decisão RAG / meta) |
| metadata | object | sim | telemetria + eco de canal/user |

### SearchResponse

Ver `POST /search`.

---

## Operational Trace (fatias A+B — Must)

Identidade ponta a ponta: header **`X-Trace-Id`** (UUID). Coexiste com `X-Request-Id` / `request_id`.

### Header `X-Trace-Id`

| Actor | Comportamento |
|-------|---------------|
| Orbit | Gera UUID por mensagem; envia em `/v1/chat` e em ingest |
| Kernel | Usa o header se presente; senão gera; ecoa em `metadata.trace_id` (Should) |

### `POST /internal/traces/events`

Auth: Bearer `ACL_INTERNAL_BEARER_TOKEN`.

Body (evento único ou batch):

```json
{
  "events": [
    {
      "trace_id": "uuid",
      "timestamp": "2026-07-28T12:00:00.000Z",
      "service": "orbit",
      "stage": "MESSAGE_RECEIVED",
      "data": {}
    }
  ]
}
```

Também aceite um único objecto evento (sem wrapper `events`).

Resposta: `202 Accepted` (ingest assíncrono) ou `200` com `{ "queued": N }`.

Stages Orbit (mínimo): `MESSAGE_RECEIVED`, `MESSAGE_PARSED`, `REQUEST_SENT_TO_KERNEL`, `RESPONSE_RECEIVED_FROM_KERNEL`, `MESSAGE_SENT_TO_WHATSAPP`, `ERROR`.

Stages Kernel (mínimo): `REQUEST_RECEIVED`, `TRANSCRIPT_LOADED`, `PIN_LOADED`, `RAG_STARTED`, `RAG_FINISHED`, `LLM_STARTED`, `LLM_FINISHED`, `RESPONSE_GENERATED`, `RESPONSE_RETURNED`, `ERROR`.

### Painel

| Método | Path | Auth | Descrição |
|--------|------|------|-----------|
| GET | `/traces/login` | none | Form login |
| POST | `/traces/login` | none | Token → cookie HttpOnly `trace_auth` |
| GET | `/traces/dashboard` | cookie | Métricas + recentes (24h) |
| GET | `/traces` | cookie | Lista com filtros (`q`, `phone`, `group`, `text`, `since`, `until`, `errors`) |
| GET | `/traces/{trace_id}` | cookie | Detalhe: conversa + RAG + timeline com Δms |
| GET | `/traces/{trace_id}/export.zip` | cookie | ZIP do trace |
| GET | `/traces/export.zip` | cookie | ZIP `scope=all\|period\|filtered` (+ query filtros) |

ZIP contém: `traces.json`, `events.json`, `messages.json`, `orbit.log`, `kernel.log`, `metadata.json`.

### Persistência

- Env: `ACL_TRACE_DB_PATH` (default `data/traces.sqlite3`); mkdir automático do parent.
- Escrita: `asyncio.Queue` + worker; ERROR prioritário; falha de trace não falha chat.

## Versionamento e breaking changes

- Prefixo `/v1` é o contrato estável para adapters multi-canal (Orbit primeiro).
- Rotas sem prefixo (`/chat`, `/health`, `/search`) permanecem nesta versão (compatibilidade).
- SSE deixa de ser o default em ambos; permanece opt-in.
- Breaking futuro (fora desta missão): deprecar `/chat` flat em favor exclusivo de `/v1/chat`.

## Referências

- PRD: `docs/prd/2026-07-28-kernel-orbit-integration.md`
- PRD Trace: `docs/prd/2026-07-28-operational-trace.md`
- PRD Trace B: `docs/prd/2026-07-28-operational-trace-fatia-b.md`
- PRD anterior: `docs/prd/2026-07-24-true-kernel.md`
- ADR-0003: `docs/adr/0003-operational-trace-store.md`
- ADR-0002: `docs/adr/0002-kernel-v1-channel-api.md`
- ADR-0001: `docs/adr/0001-true-kernel-monolith.md`
