# Benchmark — ContextRouter

| Campo | Valor |
|-------|-------|
| Data | 2026-08-09 |
| Baseline | `optimization/baseline.md` |
| Routing | `optimization/routing.md` |
| Flag | `ACL_CONTEXT_ROUTER` |

## Metodologia

1. **Antes:** cohort pós-camadas n=12 em `data/traces.sqlite3` + medição live `ContextBuilder.build_layers()` sem route (~6403 tok overhead).
2. **Depois (camadas):** medição live com `ContextRouter.route` + `build_layers(route=…)` — mesma base/identity/ficheiros em disco.
3. **Depois (suite):** `pytest tests/test_context_*.py tests/test_context_router*.py` (hard gates).
4. **Depois (E2E LLM com flag on):** **TBD** — requer Kernel reiniciado com `ACL_CONTEXT_ROUTER=1` e ≥20 novos traces; ver `results.md`.

Tokens de camada usam heurística `chars/4` (igual ao store estimado). Tokens de snapshot LLM usam `tokens_json.prompt_tokens` (estimated).

## Cenários

| ID | Query | Perfil esperado | Medição |
|----|-------|-----------------|---------|
| B1 | `que horas são chefe?` | FAST | live layers + teste hard gate |
| B2 | `Que dia é hoje?` | FAST | live + teste |
| B3 | `oi` | FAST | live + teste |
| B4 | `Quando é a próxima prova?` | NORMAL calendar-only | live + teste caps |
| B5 | `e o AT?` (history=4) | NORMAL deixis | live |
| B6 | `o que é list comprehension?` | NORMAL RAG | live |
| B7 | `explica o TP … com base nos materiais` | DEEP | live |
| B8 | `que dia e hoje e qual a politica de faltas?` | NORMAL + rules | teste SEC-001 |
| B9 | Flag off | legado | teste regressão |

## Métricas

- Overhead camadas (sem RAG/transcript/grounding extra)
- `institutional_files` count / `calendar_events_used` count
- `rag_skipped` + reason
- `transcript_max_turns`
- Suite pytest pass/fail
- (E2E) prompt_tokens / total_ms p50 — quando cohort router-on existir

## Critério go/no-go

Hard gates de `routing.md` § Hard gates devem passar em testes + medição live.  
Go-live da flag só com hard gates verdes; cohort E2E ≥20 documentada em `results.md`.
