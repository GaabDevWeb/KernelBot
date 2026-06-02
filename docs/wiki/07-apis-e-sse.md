# APIs e protocolo SSE

[← Índice](README.md)

## Endpoints HTTP

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| `GET` | `/` | — | UI (`templates/index.html`) |
| `POST` | `/chat` | — | Chat SSE |
| `GET` | `/health/catalog` | — | Drift catálogo vs índice |
| `POST` | `/reload` | `X-Reload-Token` | Rebuild BM25 |

## `POST /chat`

### Request body (JSON)

| Campo | Tipo | Obrigatório | Descrição |
|-------|------|-------------|-----------|
| `message` | string | sim | Texto do utilizador |
| `session_id` | string | sim | UUID da sessão (frontend gera) |
| `discipline` | string | não | Filtro de silo |
| `global_context` | string | não | Override de `ACL_GLOBAL_CONTEXT` |

### Response

- `Content-Type: text/event-stream`
- Eventos SSE com `data: {...}\n\n`

## Eventos SSE

| Tipo | Quando | Conteúdo |
|------|--------|----------|
| `ACL_META` | Início do stream | `v=3`, decisão, scores, fontes |
| `token` | Durante geração | Fragmento de texto |
| `[DONE]` | Fim | — |

O provider LLM pode ser OpenRouter ou Cursor SDK (`ACL_LLM_PROVIDER`), mas o contrato SSE é o mesmo: `ACL_META` sai **antes** de qualquer texto e o stream termina com `[DONE]`.

### `ACL_META` v=3 (campos principais)

| Campo | Significado |
|-------|-------------|
| `allow_generation` | Se o LLM foi chamado |
| `reason` | `DecisionReason` |
| `top_score` | Score BM25 do melhor candidato |
| `sources` | Lista `db:discipline/slug` |
| `matched_terms` | Termos que contribuíram |
| `index_gap` | Catálogo vs índice (se aplicável) |

Emitido em `engine/chat_provider.py` **antes** dos tokens.

## Hard stop no SSE

Quando `allow_generation=false`:

- Stream pode conter apenas `ACL_META` + mensagem de hard stop (sem tokens LLM).
- UI renderiza conforme `reason` — ver [08-frontend-ui.md](08-frontend-ui.md).

## `GET /health/catalog`

| Campo resposta | Uso |
|----------------|-----|
| `catalog_enabled` | `ACL_CATALOG_ENABLED` |
| `indexed_keys_count` | Tamanho do índice |
| `drift` | Aulas no catálogo sem row no MySQL / vice-versa |

Usado pelo workflow ISS Job 3 (`verify-kernelbot-sync.mjs`).

## `POST /reload`

| Header | Valor |
|--------|-------|
| `X-Reload-Token` | `ACL_RELOAD_TOKEN` do `.env` |

Efeito: `SearchEngine.rebuild()` + refresh de chaves indexadas.

## Cliente (`frontend/src/api.js`)

| Função | Papel |
|--------|-------|
| `streamChat` | `fetch` + `ReadableStream` parser SSE |
| Callbacks | `onMeta`, `onToken`, `onDone`, `onError` |

## Ver também

- [06-gates-e-decisoes.md](06-gates-e-decisoes.md)
- [09-fluxos-operacionais.md](09-fluxos-operacionais.md)
