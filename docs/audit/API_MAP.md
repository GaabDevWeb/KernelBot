# API_MAP — Catálogo de Endpoints

| Campo | Valor |
|-------|-------|
| Data | 2026-07-26 |
| Fonte | `api/routes.py`, `kernel/schemas/*`, `docs/API_SPEC.md` |
| Router | único `APIRouter` sem prefixo |

## Matriz completa

| Método | Rota | Request | Response | Serviços | Consumidor actual | Exposição | UI antiga? |
|--------|------|---------|----------|----------|-------------------|-----------|------------|
| GET | `/health` | — | `{"status":"ok"}` | nenhum | Docker/Railway/CLI | público liveness | Não |
| GET | `/api/public-config` | — | `iss_lesson_base`, `catalog_enabled` | Settings | docs/adapters | público | Não (flags) |
| GET | `/api/curriculum` | — | lista disciplinas+counts | LessonCatalog | adapters potenciais | público; 503 sem catálogo | Histórico curricular |
| GET | `/api/curriculum/{id}` | path id | aulas da disciplina | LessonCatalog | adapters | público; 404/503 | Histórico curricular |
| GET | `/health/catalog` | Bearer | drift catálogo↔índice | catalog state | CI/ops | **interno/ops** | Não |
| POST | `/chat` | `ChatRequest` | `ChatResponse` ou SSE | ContextManager, ChatProvider | `bin/chat-cli.sh`, adapters | público (+ `/reload` ops) | SSE legado opt-in |
| POST | `/search` | `SearchRequest` | `SearchResponse` | SearchEngine, build_decision | CLI, debug, LMS | público | Não |

## Schemas

### ChatRequest
`message` (1–16000), `user_id?`, `channel` default `unknown`, `metadata{}`, `discipline?`, `session_id?` `[A-Za-z0-9_-]{8,128}`, `history[]` max 40 (`user|assistant`), `stream` default `false`. `extra=forbid`.

### ChatResponse
`answer`, `discipline|null`, `sources[]`, `confidence` 0..1, `metadata{}`.

### SearchRequest
Como chat sem `history`/`stream`; `top_k` 1–20 default 5.

### SearchResponse
`discipline`, `decision`, `reason`, `confidence`, `sources`, `candidates[{source,score,score_normalized,snippet}]`, `metadata`.

## Controles transversais

| Controlo | Onde | Detalhe |
|----------|------|---------|
| Rate limit | `/chat`, `/search` | 30 req / IP / 60s; buckets separados `chat:` / `search:` |
| Bearer | `/health/catalog`, `message=/reload` | `ACL_RELOAD_BEARER_TOKEN`; `compare_digest`; 503 se não configurado |
| Headers | todas as respostas | nosniff, X-Frame-Options DENY, Referrer-Policy; HSTS se HTTPS/`KERNELBOT_FORCE_HSTS` |
| Auth global | — | **inexistente** |

## Comando especial `/reload`

Não há `POST /reload`. Equivale a:

```http
POST /chat
Authorization: Bearer <token>
{"message":"/reload"}
```

Resposta: SSE com status + `[DONE]` (mesmo se `stream=false`).  
Acções: `SearchEngine.rebuild()` + refresh `indexed_lesson_keys` + drift.

## Notas de auditoria

1. Frontend/templates/mounts **ausentes** no runtime — nenhum endpoint serve HTML.
2. `/chat` caminho normal está **bloqueado** por bug `_search_kernel` (ver SYSTEM_MAP §7); endpoints de search/reload/health não dependem desse atributo.
3. `user_id` é ecoado em metadata; **não** autentica nem isola dados.
4. Wiki antiga pode referir UI — não reflecte runtime actual.

## Referência

- Spec canónica: [`../API_SPEC.md`](../API_SPEC.md)
- SA2: [API endpoints](cfc833f7-7389-44c8-9640-85c8b1e2ef38)
