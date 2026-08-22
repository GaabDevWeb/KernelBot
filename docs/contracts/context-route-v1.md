# Contrato — ContextRoute v1

| Campo | Valor |
|-------|-------|
| Versão | 1.0.0 |
| Data | 2026-08-09 |
| Routing | `optimization/routing.md` |
| Implementação | `kernel/context/router.py`, `kernel/context/types.py` (ou equivalente) |

## Flag de activação

| Env | Default | Efeito |
|-----|---------|--------|
| `ACL_CONTEXT_ROUTER` | `false` / unset | Comportamento legado: `build_layers()` always-on; `rag_skipped` só em `time_fact` |
| `ACL_CONTEXT_ROUTER=1` / `true` | — | ContextRouter decide perfil e camadas |

## Enums

```text
ContextProfile = FAST | NORMAL | DEEP

RagSkipReason =
  | temporal_fact          # time_fact (legado + FAST)
  | greeting_ack           # cumprimento / ack FAST
  | calendar_only          # agenda pura sem necessidade de docs
  | profile_fast           # FAST genérico
  | low_confidence_filter  # pós-retrieval: não injectar chunks
  | none                   # RAG correu / não aplicável
```

## ContextRoute (campos estáveis)

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `profile` | `ContextProfile` | Perfil efectivo |
| `include_identity` | bool | Bloco `identity.txt` (sempre true nesta v1) |
| `include_temporal` | bool | Bloco temporal (sempre true nesta v1) |
| `include_institutional` | bool | Se false → bloco institucional vazio |
| `institutional_files` | `list[str]` | Allowlist de basenames (`professors.md`, …); vazio = nenhum |
| `include_calendar` | bool | Se false → bloco agenda vazio |
| `calendar_budgets.max_events` | int | Cap futuros usados |
| `calendar_budgets.max_past_events` | int | Cap passados usados |
| `rag_skipped` | bool | Pré-retrieval: não executar BM25 |
| `rag_skip_reason` | `RagSkipReason` | Motivo estável para traces |
| `transcript_max_turns` | int | Turns máximos no prompt |
| `max_rag_sources` | int | Cap de fontes injectadas (0 se skip) |
| `filter_low_confidence_rag` | bool | Se true, `confidence=low` → sem chunks |
| `reasons` | `list[str]` | Sinais que ganharam (debug/trace) |

## Budgets por perfil (defaults v1)

| Campo | FAST | NORMAL | DEEP |
|-------|------|--------|------|
| `max_events` | 0 | 6 | 15 |
| `max_past_events` | 0 | 4 | 12 |
| `transcript_max_turns` | 2 | 8 | settings.chat_history_max_turns |
| `max_rag_sources` | 0 | 5 | 7 |
| `include_calendar` | false | true se calendar signal | true se calendar/deep |
| `include_institutional` | false* | selectivo | true até budget |

\* FAST com menção explícita a professor/disciplina pode activar allowlist mínima (1 ficheiro).

## API de montagem

```text
ContextBuilder.build_layers(*, route: ContextRoute | None = None) -> ContextLayers
```

- `route is None` ou router desligado → comportamento legado (todas as camadas).
- Com route: providers respeitam allowlists/caps; blocos vazios omitidos em `assemble_system_content`.

```text
InstitutionalContextProvider.prompt_block(*, files: Sequence[str] | None = None)
```

- `files is None` → todos (legado).
- `files` lista → só esses basenames (ordem `SECTION_FILES`).

```text
CalendarProvider.build_prompt_block(temporal, *, max_events, max_past_events, ...)
```

- Já existe; caller passa budgets da route (FAST: ambos 0 → bloco vazio / sem eventos).

```text
ContextRouter.route(query, *, signals: RouteSignals) -> ContextRoute
```

- Puro (sem I/O, sem LLM).
- `RouteSignals`: `force_doc`, `force_rag`, `discipline_from_command`, `history_turns`, `temporal_intent` (opcional pré-computado).

## Observabilidade

Estágios / `prompt.context` ganham (quando router on):

```json
{
  "context_profile": "FAST",
  "router_enabled": true,
  "include_institutional": false,
  "institutional_files": [],
  "include_calendar": false,
  "calendar_events_used": [],
  "rag_skipped": true,
  "rag_skip_reason": "temporal_fact",
  "transcript_turns_requested": 0,
  "transcript_turns_used": 0,
  "router_reasons": ["time_fact"]
}
```

## Compatibilidade

- Contrato HTTP `/v1/chat` **inalterado**.
- Com flag off: traces e tokens equivalentes ao baseline (regressão zero).
- Breaking change deste contrato → nova versão `context-route-v2`.
