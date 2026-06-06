# APIs e protocolo SSE

[← Índice](README.md)

**Última revisão:** junho/2026 (alinhado a `api/routes.py` + `engine/chat_provider.py`).

## Endpoints HTTP

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| `GET` | `/` | — | UI (`templates/index.html`) |
| `POST` | `/chat` | — | Chat SSE (e comandos `/reload`, `/reset` via `message`) |
| `GET` | `/health/catalog` | `Bearer` | Drift catálogo vs índice (CI / operadores) |

> **Não existe** rota `POST /reload` dedicada. `/reload` e `/reset` são **mensagens** enviadas no corpo de `POST /chat` (campo `message`). Ver [secção `/reload`](#reload-comando-administrativo).

## `POST /chat`

### Request body (JSON)

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `message` | string | **sim** | Texto do utilizador (pergunta **atual**); vazio → 400 |
| `session_id` | string | não | ID da sessão (8–128 caracteres `[A-Za-z0-9_-]`); habilita pin e logs por sessão |
| `history` | array | não | Turnos anteriores `{ role, content }` — ver abaixo |
| `discipline` | string | não | Filtro de silo (equivalente a comando `/<disciplina>`) |

> `session_id` é **opcional** mas recomendado: sem ele, o servidor não fixa pin nem associa o turno a uma sessão (`api/routes.py`). Formato inválido → 400.

### Campo `history` (POC memória de conversa)

Lista opcional de mensagens **anteriores** à pergunta em `message` (`engine/context.py::_normalize_conversation_history`):

```json
"history": [
  { "role": "user", "content": "..." },
  { "role": "assistant", "content": "..." }
]
```

| Regra | Valor | Origem |
|-------|-------|--------|
| Roles permitidos | `user`, `assistant` | `_VALID_HISTORY_ROLES` |
| `role: system` do cliente | **rejeitado** (400) | reservado ao servidor |
| Máx. itens na entrada | **40** | `_MAX_HISTORY_ITEMS_RAW` (acima → 400) |
| Máx. chars por item | **8192** (truncado server-side) | `_MAX_HISTORY_CONTENT_LEN` |
| Truncamento no prompt | `ACL_CHAT_HISTORY_MAX_TURNS` (12), `ACL_CHAT_HISTORY_MAX_CHARS` (12000) | `core/config.py` |

Ordem no prompt do LLM: `system` (RAG + grounding) → `history` truncado → `user` (mensagem atual).

**POC:** sem autenticação — o cliente pode forjar `history`; aceitável para demo local.

**Persistência UI:** `localStorage` chave `acl_conversation_v1` (sobrevive a refresh / fechar aba).

**Limpar:** `/reset` ou `/limpar` (no `message`) limpa o pin no servidor; o botão «Nova conversa» no header limpa o storage + gera novo `session_id` + envia `/reset`.

### Response

- `Content-Type: text/event-stream`
- Linhas SSE no formato `data: <conteúdo>\n\n`

## Protocolo SSE

Todo o stream sai como linhas `data:`. Não há tipos de evento nomeados (`event:`); o cliente distingue pelo **prefixo** do payload (`engine/chat_provider.py`):

| Linha | Quando | Formato |
|-------|--------|---------|
| Meta | Início do stream (e opcional pós-geração) | `data: [ACL_META]{json}\n\n` |
| Texto | Durante a geração | `data: <fragmento>\n\n` (quebras de linha escapadas como `\n`) |
| Fim | Sempre, no final | `data: [DONE]\n\n` |

O `ACL_META` inicial sai **antes** de qualquer texto. Um **segundo** `[ACL_META]` pode ser emitido pós-geração para override/advisory ou desambiguação (ver [06](06-gates-e-decisoes.md)). O provider LLM pode ser Cursor SDK (default) ou OpenRouter (`ACL_LLM_PROVIDER`) — o contrato SSE é idêntico.

### `[ACL_META]` v=3 — campos sempre presentes

| Campo | Significado |
|-------|-------------|
| `v` | Versão do contrato (`3`) |
| `label` | Rótulo do escopo (ex.: «Assistente geral», silo) |
| `sources` | Lista `db:discipline/slug` dos chunks usados |
| `decision` | `answer` \| `hard_stop` |
| `reason` | `DecisionReason` (ver [06](06-gates-e-decisoes.md)) |
| `confidence` | `high` \| `medium` \| `low` |
| `allow_generation` | `true` quando `decision == answer` |
| `llm_called` | Se o LLM foi efetivamente chamado |
| `tokens_used` | Fragmentos/tokens acumulados |
| `mode` | Modo do trace |
| `pinned_active` / `pinned_display` / `pin_chunks_used` | Estado do pin no turno |

### `[ACL_META]` v=3 — campos opcionais

| Campo | Quando aparece |
|-------|----------------|
| `grounding_policy` | Sempre que há `trace` (`strict` \| `anchored` \| `hybrid`) |
| `scope_hint` / `suggested_scope_command` | Pin diverge da disciplina inferida na query |
| `sources_note` | Busca atual traz fontes além do pin |
| `pinned_scope_key` | Pin com escopo definido |
| `catalog_match` / `payload` | `decision == hard_stop` (ex.: `index_gap`, `ambiguous_retrieval`) |
| `disambiguation_options` | Resposta com opções estruturadas detetadas |
| `post_generation_advisory` / `post_generation_flags` | Aviso suave (`anchored`/`hybrid`) |
| `post_generation_override` / `misalignment` | Override destrutivo (`strict`) |

Construído em `engine/chat_provider.py::_build_meta`.

## Hard stop no SSE

Quando `allow_generation=false` (ex.: `provider_error`, override `strict`):

- O stream pode conter apenas `[ACL_META]` + texto fixo de hard stop (sem chamada ao LLM nos casos operacionais).
- A UI renderiza conforme `reason` — ver [08-frontend-ui.md](08-frontend-ui.md).

## `/reload` (comando administrativo)

`/reload` reconstrói o índice BM25 a partir do MySQL. É enviado como `message` no `POST /chat` e exige Bearer:

| Aspecto | Valor |
|---------|-------|
| Como enviar | `POST /chat` com `{"message": "/reload"}` |
| Auth | `Authorization: Bearer <ACL_RELOAD_BEARER_TOKEN>` |
| Token ausente no servidor | 503 (`reload token not configured`) |
| Token inválido | 401 |
| Efeito | `SearchEngine.rebuild()` + `refresh_indexed_lesson_keys_state()` |
| Resposta | SSE com `data: <status>` + `data: [DONE]` |

O alias legado `KERNELBOT_RELOAD_TOKEN` também é aceite como token (`core/config.py`). O workflow ISS `sync-kernelbot-knowledge` envia o mesmo valor.

```bash
curl -sS -N -X POST "http://127.0.0.1:8001/chat" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ACL_RELOAD_BEARER_TOKEN" \
  -d '{"message": "/reload"}'
```

## `GET /health/catalog`

Protegido por Bearer (mesmo token de `/reload`). Resposta JSON (`api/routes.py::health_catalog`):

| Campo | Uso |
|-------|-----|
| `catalog_enabled` | Valor de `ACL_CATALOG_ENABLED` |
| `indexed_lesson_keys_count` | Aulas no índice BM25 |
| `catalog_lesson_keys_count` | Aulas no catálogo ISS |
| `catalog_only_count` | Aulas no catálogo sem row no MySQL (drift) |
| `catalog_only_sample` | Até 10 chaves de exemplo do drift |

Consumido pelo workflow ISS de verificação de sync.

## Exemplo — turno de chat com histórico

```bash
curl -sS -N -X POST "http://127.0.0.1:8001/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "/python O que são variáveis?",
    "session_id": "00000000-0000-4000-8000-000000000001",
    "history": [
      {"role": "user", "content": "Oi"},
      {"role": "assistant", "content": "Olá! Em que posso ajudar?"}
    ]
  }'
```

Resposta (stream SSE, resumido):

```text
data: [ACL_META]{"v":3,"label":"Python","decision":"answer","reason":"ok","allow_generation":true,"llm_called":true,"sources":["db:python/variaveis-tipos-estilo-python"], ...}

data: Variáveis em Python são nomes que apontam para valores...

data: [DONE]
```

## Cliente (`frontend/src/api.js`)

| Função | Papel |
|--------|-------|
| `streamChat(message, opts)` | `fetch` + `ReadableStream`, parser SSE incremental |

Callbacks aceites (`opts`):

| Callback | Disparo |
|----------|---------|
| `onDelta(fullText)` | A cada fragmento de texto (texto acumulado) |
| `onMeta(payload)` | A cada linha `[ACL_META]` |
| `onDone()` | No `[DONE]` |
| `onError(err)` | Falha de rede/parse |
| `onInactivity()` | Sem dados por `DEFAULT_STREAM_INACTIVITY_MS` (45 s) |

## Ver também

- [06-gates-e-decisoes.md](06-gates-e-decisoes.md)
- [08-frontend-ui.md](08-frontend-ui.md)
- [09-fluxos-operacionais.md](09-fluxos-operacionais.md)
