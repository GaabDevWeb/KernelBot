# Routing — ContextRouter FAST | NORMAL | DEEP

| Campo | Valor |
|-------|-------|
| Data | 2026-08-09 |
| Estado | **congelado para implementação** (ID 1 do plano) |
| Baseline | `optimization/baseline.md` |
| Plano | `memory/kernel-context-optimization/PLAN.md` |
| Contrato | `docs/contracts/context-route-v1.md` |

## Princípio

O Kernel **não** envia tudo o que sabe. Decide **qual informação é necessária** para a pergunta corrente. Providers permanecem; o router controla *quando* e *quanto*.

**Proibido:** cache de respostas LLM que bypass o transcript (lição Orbit).

## Perfis

| Perfil | Uso | Overhead alvo (sem RAG/transcript) |
|--------|-----|-------------------------------------|
| **FAST** | Relógio/data civil; cumprimentos; ack curto | ≤ 2000 tok |
| **NORMAL** | Académico comum; calendário; follow-up | ≪ 4500 tok |
| **DEEP** | Multi-hop, “explica com base no material”, force RAG/doc | ≤ overhead baseline (~6400) + RAG |

## Sinais de entrada (determinísticos)

| Sinal | Fonte |
|-------|-------|
| `temporal_intent` | `detect_temporal_intent` → `time_fact` \| `calendar_fact` \| `None` |
| `force_doc` / `force_rag` / disciplina `/…` | ContextManager → força ≥ NORMAL com RAG |
| Cumprimento / ack | Heurística PT-BR fechada (`oi`, `olá`, `obrigado`, `valeu`, `tá on`…) |
| Deixis / follow-up | Anáforas (`isso`, `e o AT?`, `aquele`) ou query curta com history>0 |
| Menção institucional | Nomes em `professors.md` / títulos de disciplina |
| Pedido profundo | `explica`, `detalha`, `compara`, `por que`, multi-pergunta, “com base no” |
| Pós-RAG | `confidence=low` / `reason=context_misaligned` → não injectar chunks |

## Matriz perfil → camadas

| Camada | FAST | NORMAL | DEEP |
|--------|------|--------|------|
| base + `identity.txt` | on | on | on |
| temporal | on | on | on |
| institutional | **off** (excepto fatia se menção explícita classificada) | selectivo (`rules` se política; `professors`/`disciplines` por menção) | ranking até budget |
| calendar | **off** | on + caps + filtro | on + caps altos / disciplina |
| RAG | **skip** | on; skip se calendar-only puro | on; filtro low-conf |
| transcript turns | 0–2 | 2–8 (deixis↑) | até config max |
| catalog / sticky / grounding | grounding mínimo | actual | actual |

## Prioridade sinal → perfil (top-down)

1. `force_doc` \| `force_rag` \| disciplina explícita → **DEEP** (RAG obrigatório)
2. Marcadores profundos / multi-hop → **DEEP**
3. `time_fact` → **FAST**
4. Cumprimento/ack sem conteúdo → **FAST**
5. `calendar_fact` → **NORMAL** (calendar on; RAG só se não for calendar-only puro)
6. Deixis/follow-up curto → **NORMAL** (transcript↑)
7. Default académico → **NORMAL**

## Caps (derivados do baseline)

| Budget | FAST | NORMAL | DEEP |
|--------|------|--------|------|
| `max_calendar_events` (usados) | 0 | 6 | 15 |
| `max_past_events` | 0 | 4 | 12 |
| Institutional chars (aprox) | 0 | ≤4000 | ≤14323 |
| Transcript turns | 0–2 | 2–8 | ≤ `ACL_CHAT_HISTORY_MAX_TURNS` |
| RAG sources inject | 0 | ≤5 (0 se low-conf) | ≤7 |

## Golden (aceitação)

| Query | Perfil | institutional | calendar | rag_skipped | turns |
|-------|--------|---------------|----------|-------------|-------|
| `que horas são chefe?` | FAST | off | off | true | 0 |
| `Que dia é hoje?` | FAST | off | off | true | 0 |
| `oi` / `obrigado` | FAST | off | off | true | 0–1 |
| `Quando é a próxima prova?` | NORMAL | selectivo | on (caps) | true (calendar-only) | 0–4 |
| `e o AT?` (follow-up) | NORMAL | off/select | on filtrado | condicional | ≥2 |
| `explica o TP de projeto de bloco com base nos materiais` | DEEP | on/rank | on | false | até max |
| `o que é list comprehension?` | NORMAL | off/select | off | false | 0–2 |

## Hard gates (go-live com `ACL_CONTEXT_ROUTER=1`)

| Gate | Alvo |
|------|------|
| `time_fact` prompt_tokens | ≤ 2500 |
| `time_fact` `calendar_events_used` | 0 |
| `time_fact` `institutional_files` | 0 |
| Overhead FAST live | ≤ 2000 tok |
| `calendar_fact` eventos | ≤ 6 (NORMAL) |
| Capacidades removidas | 0 |

## Observabilidade obrigatória

Cada request com router activo regista em stages/snapshot:

- `context_profile`
- `include_institutional` / `institutional_files`
- `include_calendar` / `calendar_events_used` (count)
- `rag_skipped` + `rag_skip_reason`
- `transcript_turns_requested` / `transcript_turns_used`

## Flag de rollback

`ACL_CONTEXT_ROUTER` default **off** → comportamento actual (always-on layers + skip RAG só em `time_fact`).  
`=1` activa o router após hard gates verdes.
