# Data Model

| Campo | Valor |
|-------|-------|
| SGBD | MySQL (runtime RAG) |
| Última actualização | 2026-07-28 |

## Diagrama ER (descrição)

```text
knowledge (MySQL) 1──N chunks_in_memory (BM25 RAM, por silo/disciplina)
LessonCatalog (JSON ISS, opcional) ──drift── indexed_lesson_keys (snapshot MySQL)
PinnedSessionStore (process memory) N──1 session_id
```

Não há ORM: leitura via PyMySQL; índice BM25 é reconstruído em memória.

## Entidades

### knowledge (tabela MySQL — existente)

Fonte canónica do RAG. Campos exactos conforme `engine/database.py` / `docker/init-knowledge.sql` (chunking 500 palavras, overlap 50).

| Campo (lógico) | Tipo | Null | Descrição |
|----------------|------|------|-----------|
| id / chave | — | — | identificação da linha activa |
| discipline / silo | string | NO | disciplina indexada |
| content / text | text | NO | conteúdo a chunkar |
| metadata de aula | — | — | slug/path usados em `source` |

**Índices:** os do schema MySQL existente; rebuild BM25 em boot e `/reload`.

**Regras:**

- Só linhas activas entram no índice
- Silo `doc` usado para wiki ingest

### RetrievalCandidate (domínio in-memory)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| source | string | id de fonte (`db:disciplina/slug…`) |
| score | float | BM25 raw |
| score_normalized | float | normalizado |
| text / snippet | string | excerto |
| matched terms | — | cobertura lexical |

### RetrievalDecision / Trace

| Campo | Tipo | Descrição |
|-------|------|-----------|
| decision | string | ex.: `answer`, `hard_stop` |
| reason | string | telemetria (`ok`, `ambiguous_retrieval`, …) |
| confidence | float | 0..1 |
| allow_generation | bool | contrato legado; na prática RAG actual mantém True |
| sources | list | fontes seleccionadas |
| label | string | label de disciplina |

### ChannelContext / ChatRequest v1 / ChatResponse (API)

Ver `docs/API_SPEC.md`. Não persistem no MySQL; history vem do cliente.

| Entidade | Persistência | Notas |
|----------|--------------|-------|
| `ChannelContext` | nenhuma (por request) | `platform`, `user_id`, `channel_id`, `session_id?` |
| `ChatRequest` v1 | nenhuma | contém `context` + `message` (+ opcionais) |
| `ChatRequest` legado | nenhuma | campos flat (`channel`, `user_id`, …) |
| `ChatResponse` | nenhuma | `answer`, `discipline`, `sources`, `confidence`, `metadata` |

**Integridade lógica (legado):** chave de memória pin = `platform:user_id:session_id` (após mapeamento v1→interno, `memory_session_key`). `channel_id` entra na derivação de `session_id` quando este é omitido; não é por si a chave de pin.

**Integridade lógica (v1 — `POST /v1/chat`):** `TranscriptStore` e `PinnedSessionStore` usam a **mesma** chave `v1_memory_key(platform, user_id, channel_id, session_id)` — nunca `None`, ao contrário da chave legada. Ver `TranscriptStore` abaixo para o detalhe de encoding.

### PinnedSession

| Campo | Tipo | Descrição |
|-------|------|-----------|
| session_id | string | chave |
| chunks / texto pinado | — | contexto sticky |
| turns remaining | int | expiração por turnos |
| max chars | int | limite |

**Regras:** memória de processo; não partilhada entre workers.

### TranscriptStore (in-memory, v1)

Histórico de turnos de `POST /v1/chat` — `kernel/memory/transcript_store.py`. Não existe para o `/chat` legado (G5: transcript é exclusivo de `/v1/chat`).

| Campo | Tipo | Descrição |
|-------|------|-----------|
| key | string | `v1_memory_key(platform, user_id, channel_id, session_id)` — ver nota de chave abaixo |
| turns | `deque[{role, content}]` | janela deslizante, oldest-first, `maxlen = 2 × max_turns` |
| max_turns | int | `ACL_TRANSCRIPT_MAX_TURNS` (default 16, clamp 1–100 em `kernel/config.py`); passado pelo chamador a cada `append_pair`, nunca lido de `Settings` dentro da store |

**Regras:**

- Memória de processo; não partilhada entre workers nem persistida em reinícios/deploys (mesma limitação de `PinnedSessionStore`).
- Só regista um par quando o turno é bem-sucedido em modo JSON (`stream=false`); `stream=true` nunca escreve no transcript (par entregue via SSE, sem passar pelo agregador que produz o texto final no handler).
- `reset_context: true` em `POST /v1/chat` limpa `TranscriptStore` **e** `PinnedSessionStore` da mesma chave — sempre **depois** da autenticação de canal (nunca antes, para não ser vetor de DoS não autenticado).

**Chave v1 — percent-encoding (SEC-001):** cada segmento (`platform`, `user_id`, `channel_id`, `session_id`) é passado por `urllib.parse.quote(segment, safe="")` (escapa `:`/`/` e qualquer caractere) **antes** de ser unido por `:` (`kernel/memory/session_key.py::v1_memory_key`). Sem este encoding, um segmento com `:` embutido colidiria com uma tupla diferente — ex.: `channel_id="c:abcdef12"` sem `session_id` produziria a mesma chave que `channel_id="c"` + `session_id="abcdef12"`, quebrando o isolamento por utilizador/canal exigido por G4. Achado do gate de segurança S1 do plano `kernel-orbit-integration`, corrigido no código e coberto por `tests/test_v1_session_key.py::test_v1_memory_key_rejects_delimiter_injection_collision`.

### LessonCatalog (opcional)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| discipline | string | id |
| slug | string | aula |
| title / name | string | apresentação |
| order | int | ordenação curricular |

Fonte: `lessons.json` (+ `search-index.json` opcional) em `ACL_CATALOG_JSON_DIR`.

### DisciplineRegistry

SSOT: `core/disciplines.json` → `kernel/disciplines/`.

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | string | silo |
| command | string | prefixo `/python` etc. |
| label | string | UI/adapters |
| markers | list | detecção lexical |

## Relações

| De | Para | Cardinalidade | Notas |
|----|------|---------------|-------|
| knowledge row | BM25 chunk | 1:N | chunking em load |
| discipline | knowledge silo | 1:N | filtro de busca |
| session_id | pinned chunks | 1:1 | store volatil (legado) |
| v1_key | pinned chunks | 1:1 | `PinnedSessionStore`, só `/v1/chat` |
| v1_key | pares transcript | 1:N | `TranscriptStore`, janela deslizante |
| catalog lesson key | indexed key | 1:0..1 | drift report |
| `trace_id` | `trace_events` | 1:N | timeline operacional (SQLite traces) |

## Operational Trace (SQLite — fatia A)

Path: `ACL_TRACE_DB_PATH` (default `data/traces.sqlite3`). Independente do MySQL RAG.

```text
traces (1) ──N── trace_events
```

### traces

| Campo | Tipo | Descrição |
|-------|------|-----------|
| trace_id | TEXT PK | UUID |
| created_at | TEXT/ISO | primeiro evento |
| updated_at | TEXT/ISO | último evento |
| has_error | INTEGER | 0/1 |
| services | TEXT | ex. `orbit,kernel` (denormalizado leve) |
| summary | TEXT | opcional (primeiro stage / preview) |

### trace_events

| Campo | Tipo | Descrição |
|-------|------|-----------|
| id | INTEGER PK | autoincrement |
| trace_id | TEXT FK | |
| timestamp | TEXT/ISO | |
| service | TEXT | `orbit` \| `kernel` |
| stage | TEXT | ver API_SPEC |
| data_json | TEXT | JSON redacted |
| priority | INTEGER | ERROR > resto (fila) |

**Regras:** redact secrets antes de persistir; escrita via queue async; sem schema MySQL.

## Migrações previstas

| Ordem | Descrição | Breaking? |
|-------|-----------|-----------|
| 001 | Nenhuma alteração de schema MySQL nesta feature | Não |
| 002 | Remoção de artefactos UI (filesystem) | Sim (produto) |
| 003 | Reorganização pacotes Python | Sim (imports) — mitigar com shims se necessário |
| 004 | Novo ficheiro SQLite traces (sem migração MySQL) | Não |

## Considerações de performance

- Hot path: `POST /chat` → BM25 in-RAM + LLM remoto
- `POST /search` evita custo LLM
- Cache: índice BM25 em memória do processo
- Limitação: multi-worker não partilha pin/rate-limit
- Trace: write path fora do hot path (Queue); reads só no painel

## Referências

- API: `docs/API_SPEC.md`
- ADR: `docs/adr/0001-true-kernel-monolith.md`, `docs/adr/0002-kernel-v1-channel-api.md`, `docs/adr/0003-operational-trace-store.md`
- PRD Trace: `docs/prd/2026-07-28-operational-trace.md`
- Plano/gate S1 (SEC-001): `memory/kernel-orbit-integration/plan.md`
- Wiki existente: `docs/wiki/04-dados-e-mysql.md`, `docs/wiki/05-bm25-chunking.md`
