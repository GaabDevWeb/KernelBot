# KERNEL_FLOW — Pipeline completo

| Campo | Valor |
|-------|-------|
| Data | 2026-07-26 |
| Princípio | Só comportamento evidenciado no código |

## Diagrama mestre (alvo arquitectural)

```text
Request (POST /chat)
        ↓
Validação Pydantic ChatRequest
        ↓
Rate limit (30/IP/60s)
        ↓
AppServices.resolve
        ↓
┌── message == "/reload"? ──yes──► Bearer ──► rebuild BM25 ──► SSE status ──► [DONE]
│
no
        ↓
ContextManager.build_messages
        ↓
Parse comandos (/doc, /content, /disciplina, /reset)
        ↓
Pin begin_turn (session_id)
        ↓
Truncate history
        ↓
select_mode (sempre strict no path actual)
        ↓
LessonCatalog.match (se enabled)
        ↓
Normalize / resolve discipline filter
        ↓
SearchEngine.search_candidates   ← BLOQUEADO: _search_kernel (ver § Bloqueio)
        ↓
retrieval.build_decision
        ↓
Select grounding + assemble system
        ↓
Merge: system → history → user
        ↓
ChatProvider.stream_response
        ├── hard_stop trace? → stream texto local (sem LLM)   [raro: allow_generation sempre True no RAG]
        ├── cursor → Cursor SDK bridge
        └── openrouter → HTTP stream + fallback modelos
        ↓
Pós-geração (flags / override strict)
        ↓
        ├── stream=true  → StreamingResponse SSE (ACL_META + tokens + DONE)
        └── stream=false → aggregate_sse → ChatResponse JSON
        ↓
Response
```

## 1. Entrada HTTP

Ficheiro: `api/routes.py::chat`

1. FastAPI instancia `ChatRequest` (422 se inválido).
2. `_allow_rate_limited_request("chat")`.
3. `_services(request)` → 503 se DI ausente.
4. Branch `/reload` (ver API_MAP).

## 2. Orquestração (`ContextManager.build_messages`)

Ficheiro: `kernel/orchestrator/context.py`

Ordem real de passos no método:

1. Strip / normalização da mensagem; detectar `/reset`, `/limpar`, `/doc`, `/content`.
2. Match comando de disciplina (`command_prefixes`, longest-first).
3. `normalize_discipline(discipline_filter)` via SearchEngine.
4. `PinnedSessionStore.begin_turn(session_id)` — decrementa TTL.
5. Truncar history (`ACL_CHAT_HISTORY_MAX_TURNS/CHARS`).
6. `select_mode(...)` → `"strict"` (flag assistive só se explícita; path actual não a usa).
7. `LessonCatalog.match(query)` se catálogo activo — pode estreitar disciplina/aula.
8. **Retrieval** → ver § Bloqueio.
9. `build_decision(...)` → `RetrievalDecision` + reasons.
10. Catalog rescue (só se `ambiguous_retrieval` e match confiante).
11. Merge pin chunks + selected candidates; cap `ACL_PINNED_MAX_CHARS`.
12. `_select_grounding` + `_assemble_system_content`.
13. Opcional: actualizar pin (`set_pinned`).
14. Retorna `BuildMessagesResult(messages, trace, decision)`.

## 3. RAG detalhado

```text
Consulta (+ discipline_filter?)
        ↓
Por silo BM25Okapi: scores crus; drop ≤0; top candidate_k por silo
        ↓
Merge global por raw_score → cut candidate_k (default 8)
        ↓
build_decision:
  sort raw_score → max_per_source (2) → top_k (4)
  metrics: score, margin, coverage, coverage_weighted, min_terms
  reasons: ok | insufficient_context | underspecified_query |
           ambiguous_retrieval | low_confidence | …
        ↓
selected_candidates → textos [Fonte: …] no system
```

| Parâmetro | Default env |
|-----------|-------------|
| `ACL_RETRIEVAL_CANDIDATE_K` | 8 |
| `ACL_RETRIEVAL_TOP_K` | 4 |
| `ACL_RETRIEVAL_MAX_CHUNKS_PER_SOURCE` | 2 |
| `ACL_RETRIEVAL_MIN_SCORE` | 1.5 |
| `ACL_RETRIEVAL_MIN_SCORE_MARGIN` | 0.15 |
| `ACL_RETRIEVAL_MIN_COVERAGE` | 0.34 |
| `ACL_RETRIEVAL_MIN_COVERAGE_WEIGHTED` | 0.34 |
| `ACL_RETRIEVAL_MIN_TERMS` | 2 |

**Chunking MySQL:** 500 palavras, overlap 50 (`database.py`).

**Importante:** `allow_generation` é **sempre True** em `build_decision` — gates são telemetria/grounding, não hard-stop pré-LLM.

## 4. Context / Prompt Builder

Ordem no **único** `system` (`_assemble_system_content`):

1. `system_prompt.txt`
2. `catalog_router.txt` + secção catálogo (se houver)
3. sticky pin (`sticky_instruction.txt`) se pin activo
4. grounding (`strict|anchored|permissive|disambiguation`)
5. chunks RAG (pin primeiro, depois retrieval)

Depois: `history` truncado → `user` actual.

Defaults history: 12 turns / 12000 chars; pin: 5 turns / 24000 chars.

## 5. Disciplinas — roteamento

Prioridade observada:

1. `/doc` → silo `doc` se existir chunks
2. Comando `/<disciplina>` (JSON SSOT)
3. Campo JSON `discipline` (se existir no MySQL)
4. Herança de pin (perguntas curtas)
5. Catálogo lexical estrito (pode sobrescrever)
6. Fallback: todos os silos

**Não há** classificador LLM de intenção/disciplina.

Sete disciplinas de UI/comandos + silo `doc` (wiki).

## 6. LLM Layer

| Provider | Trigger | Modelos | Params |
|----------|---------|---------|--------|
| Cursor | `ACL_LLM_PROVIDER=cursor` (default Settings) | `ACL_CURSOR_MODEL` default `composer-2.5` | sem temperature/top_p/max_tokens no código |
| OpenRouter | `openrouter` | lista **hardcoded** no provider (free-tier chain) | `temperature=0.7` fixo; sem top_p/max_tokens env |

Fallback: OpenRouter tenta próximo modelo em 429/erro; Cursor sem fallback de modelo.  
Pós-geração: `post_generation_flags`; override hard_stop só se `grounding_policy==strict`.

## 7. Memória

| Tipo | Onde | Chave | Persistente? |
|------|------|-------|--------------|
| History conversa | Cliente → body | — | Não no servidor |
| Pin RAG | `PinnedSessionStore` RAM | `session_id` | Não (process-local) |
| Knowledge | MySQL | discipline/slug | Sim |
| `user_id` | metadata eco | — | Não usado para storage |

## 8. ACL (significado no projecto)

**ACL = Agente de Contexto Local** (prompts + `ACL_META`), **não** RBAC.

Controlo de escopo:

- Grounding textual no prompt
- Filtro de silo BM25
- Metadados `reason`/`confidence`/`sources`
- Bearer só em ops

Limitações: disciplina inválida → busca **global** (fail-open); retrieval não bloqueia LLM.

## 9. Saída

### JSON (`stream=false`)
`aggregate_sse` lê `[ACL_META]` + texto → `ChatResponse` + eco `user_id`/`channel`/`session_id`/`request_metadata`.

### SSE (`stream=true`)
`data: [ACL_META]{v:3,...}` → `data: <chunk>` → `data: [DONE]`.

## 10. POST `/search` (sem LLM)

```text
SearchRequest → rate limit → search_candidates → build_decision → SearchResponse
```

Não passa por `ContextManager.build_messages` nem pelo bug `_search_kernel`.

## Bloqueio actual do fluxo `/chat`

```text
build_messages
    ↓
self._search_kernel.rag.search_candidates   # AttributeError
    ↓
(não alcança LLM nem Response canónica)
```

Estado verificado em `context.py` linhas ~789 e ~1037 vs init `self._search_engine` (~755).

## Fontes SA

SA3 Pipeline · SA4 RAG · SA5 Disciplinas · SA6 Context · SA7 LLM · SA8 Memória · SA9 ACL
