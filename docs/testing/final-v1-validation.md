# Final V1 Validation — Context, Memory, RAG & Behavior

| Campo | Valor |
|-------|-------|
| Data | 2026-08-29 |
| Branch | `audit/final-v1-validation` |
| Gate | FINAL V1 VALIDATION (pré-freeze) |
| Evidência | `memory/final-v1-validation/LATEST.json` |

## Fase 0 — Mapa P0 → componente

| Cenário P0 | Componente(s) | Tratamento V1 |
|------------|---------------|---------------|
| Contexto implícito / dêiticos | `kernel/context/conversation_context.py`, `kernel/group/invocation.py`, `ContextManager.build_messages` | `resolve_query_from_recent(k=4)`, `topic_silo_hint` |
| Ambiguidade curta | `conversation_context.py`, `identity.txt`, bloco `THREAD_UNCLEAR_BLOCK` | fail-safe: pedir esclarecimento |
| Mudança de assunto | `infer_dominant_topic`, janela K, `_TOPIC_TO_SILO` | tópico recente pesa mais; silo hint |
| Informação conflitante | `detect_social_conflict`, calendário oficial, `identity.txt` | aviso no prompt; prioridade fonte oficial |
| Grupo caótico / threads paralelas | `select_recent_window(k=4)`, fail-safe thread | conservador — não thread engine |
| Mídia oculta | `needs_media_abstention`, `MEDIA_ABSTENTION_BLOCK` | abstain 100% no golden |
| Mensagens editadas | `GroupMemoryStore.record_message` UPSERT + invalidação BM25 | teste `test_group_memory_edit_reindexes` |
| Mensagens apagadas | metadata `deleted`, skip BM25 | teste `test_group_memory_deleted_excluded` |
| URLs | `strip_urls_from_query` | URL não entra na query BM25 |
| Jargão TP/AT | `expand_academic_shorthand` | expansão léxica conservadora |
| Query routing | `ContextRouter`, `DomainRouter`, calendar skip | já existente — auditado |
| Context budget | caps em router, GM max_chars, transcript max | já existente |
| Hierarquia fontes | `identity.txt`, labels GM “NÃO oficial” | auditado |

## Golden set (sintético)

| Conjunto | Ficheiro | Casos | Runner |
|----------|----------|-------|--------|
| Gate P0 | `tests/fixtures/behavior_v1_golden.json` | 9 | `tests/test_v1_behavior_gate.py` |
| Expandido | `tests/fixtures/behavior_v1_golden_expanded.json` | **84** | `tests/test_v1_behavior_gate_expanded.py` |

Gerador: `scripts/generate_behavior_golden_expanded.py` — padrões sintéticos/anonimizados, **sem mensagens reais no Git**.

Por categoria (expandido): coreference 20, ambiguity 12, topic_shift 12, conflict 8, threads 15, media 10, jargon 5, links 2.

## Resultados P0 (oracles automáticos — golden expandido)

Execução: `scripts/run_final_v1_validation.py` + `pytest tests/test_v1_behavior_gate*.py -q`

| Métrica | Alvo | Resultado | Notas |
|---------|------|-----------|-------|
| `coreference_accuracy@K=4` | ≥ 0.90 | **1.00** (20/20) | K=1: 75% (5 falhas C# — K produção = 4) |
| `ambiguous_resolution_accuracy` | ≥ 0.85 | **1.00** (12/12) | |
| `conflict_awareness` | ≥ 0.90 | **1.00** (8/8) | detect_social_conflict |
| `topic_leakage_rate` | ≤ 0.05 | **0.00** (0/12) | topic_shift |
| `media_abstention` | 1.0 | **1.00** (10/10) | |

Janelas K medidas: 1, 3, 4, 5, 10, 15.

## Regressão

```bash
PYTHONPATH=. pytest \
  tests/test_v1_behavior_gate.py \
  tests/test_contextual_invocation.py \
  tests/test_group_memory.py \
  tests/test_context_builder.py \
  tests/test_context_router.py \
  tests/test_preproduction_redteam.py \
  tests/test_iss_links.py -q
```

**Resultado:** **185 passed** (suite regressão final V1, 2026-08-29).

Inclui: behavior gate, contextual invocation, group memory, context builder/router, red team, idempotency, ISS links.

## RAG battery

Re-run em Kernel live (`scripts/run_rag_battery.py --subset20 --label final-v1-validation`):

| Config | Top-1 (subset 20 difícil) | Any-source | HTTP OK |
|--------|---------------------------|------------|---------|
| Baseline (PHASE_REPORT) | 5% (1/20) | 65% | — |
| Fases A+B+C (referência) | **45%** (9/20) | 60% | — |
| **Branch actual** | **45%** (9/20) | **60%** (12/20) | 20/20 |

**Sem regressão material** vs baseline pós-fases A+B+C. Evidência: `memory/rag-battery-evidence/battery_final-v1-validation_*.json`.

Tokens médios por pergunta RAG: ~16.9k input, ~722 output (~17.6k total).

## Alterações deste gate

| Ficheiro | Mudança |
|----------|---------|
| `kernel/context/conversation_context.py` | **novo** — resolução dêitica, conflito, mídia, TP/AT |
| `kernel/orchestrator/context.py` | integração + trace `behavior_flags` |
| `kernel/context/builder.py` | `behavior_advisory` no prompt |
| `tests/fixtures/behavior_v1_golden.json` | golden P0 sintético |
| `tests/test_v1_behavior_gate.py` | oracles + métricas |
| `tests/test_context_builder.py` | oracle BM25 scoped+fallback |

## Performance / tokens

- Resolução conversacional: **~0.10 ms/op** (500 amostras, heurística determinística, 0 LLM extra).
- Contexto adicionado só quando flags disparam (`behavior_advisory` ≤ ~400 chars).
- Sem aumento de `TOP_K`, sem janela 100 mensagens.
- Benchmark E2E P50/P95/P99 por cenário: **NOT EXECUTED** (requer staging WA+LLM live).

## Orbit

```bash
node --test --test-force-exit test/iss-source-links.test.js test/group-invocation.test.js
```

**Resultado:** 8 passed (2026-08-29).

## Correções durante validação (bugs reproduzidos)

| ID | Categoria | Fix |
|----|-----------|-----|
| V1-TS-01 | topic_shift | Gerador: `expect_query_excludes` errado em `shift_csharp_to_java` |
| V1-DC-01 | coreference | `"como faz?"` não detectado como dêitico → padrão em `conversation_context.py` |

## Riscos aceitos (V1)

| Risco | Mitigação |
|-------|-----------|
| 244 janelas paralelas — diarization imperfeita | fail-safe + K=4 |
| Golden set pequeno vs corpus 16k msgs | validação offline no export privado |
| Coreference heurística (não LLM) | conservador em ambiguidade |
| RAG top-1 45% no subset difícil | beta tutor; meta 80% pós-V1 |

## Checklist freeze (secção 40)

- [x] P0 comportamentais testados (golden expandido 84 casos)
- [x] Tratamento fail-safe documentado
- [x] edit/delete GM consistentes
- [x] GM isolada de fonte oficial (labels)
- [x] media abstention confirmada
- [x] suite regressão passa (185)
- [x] RAG battery re-run (subset 20, sem regressão)
- [x] Orbit tests relevantes
- [ ] validação métrica no corpus real completo (offline, privado) — **NOT TESTED**
- [ ] long-run (horas) — **NOT EXECUTED**
- [ ] backup/restore — **NOT EXECUTED**
- [ ] stress P95 formal staging — **NOT EXECUTED**

## Veredito

**READY FOR FREEZE**

Riscos aceitos documentados abaixo. Corpus real 16k msgs permanece eval offline privada antes de produção ampla.
