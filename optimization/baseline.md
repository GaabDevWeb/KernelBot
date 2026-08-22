# Baseline — Pipeline de Contexto do Kernel

| Campo | Valor |
|-------|-------|
| Data | 2026-08-09 |
| Fonte | `data/traces.sqlite3` (Flight Recorder) + medição live dos providers |
| Comportamento alterado | **Não** — apenas observação |
| Artefacto bruto | `optimization/baseline_raw.json` |

## 1. Objectivo desta fase

Estabelecer o estado **antes** de qualquer otimização: latência, tokens e composição do contexto enviado ao LLM, com evidência de traces reais — sem assumir a causa.

## 2. Amostra

| Universo | N | Notas |
|----------|---|--------|
| Traces totais | 76 | Tabela `traces` |
| Com snapshot | 70 | `trace_snapshots` com tokens/performance |
| Cohort pós-camadas de contexto | **12** | Possuem eventos `TEMPORAL_CONTEXT` + `CALENDAR_LOOKUP` + `prompt.context` |
| Tokens estimados | sim | `tokens.estimated=true` (heurística do store; não billing do provider) |

A cohort de 12 é a amostra **válida** para o pipeline atual (Identity + Institutional + Temporal + Calendar + RAG + Transcript). Os 58 restantes são anteriores à feature de camadas ou sem esses stages.

Classificação heurística da amostra completa (70) — rótulos operacionais, não intents do Kernel:

| Classe | N | prompt_tokens p50 | total_ms p50 |
|--------|---|-------------------|--------------|
| outro | 41 | 7508 | 7554 |
| academica_rag | 14 | 8576 | 19182 |
| simples | 7 | 4464 | 4679 |
| calendario | 4 | 13407 | 20411 |
| temporal | 3 | 6908 | 2308 |
| contextual_longo | 1 | 4533 | 13285 |

Na cohort pós-camadas (12), intents reais do Kernel:

| Intent | N | rag_skipped | prompt_tokens |
|--------|---|-------------|---------------|
| `time_fact` | 2 | true | 6895 / 6908 |
| `calendar_fact` | 1 | false | 13319 |
| `null` (fluxo normal) | 9 | false | 10161–14339 |

## 3. Latência — onde o tempo é gasto

### 3.1 Universo com snapshot (n=70)

| Etapa | mean | p50 | p75 | p95 | p99 | max |
|-------|------|-----|-----|-----|-----|-----|
| **total_ms** | 17788 | 9110 | 21312 | 64196 | 112867 | 119511 |
| **llm_ms** | 17663 | 8994 | 21218 | 64108 | 112775 | 119357 |
| **rag_total_ms** | 77 | 71 | 115 | 179 | 207 | 259 |
| **prompt_build_ms** | 31 | 30 | 39 | 58 | 106 | 106 |

**Participação média no total:** LLM **97,8%** · RAG **1,3%** · restante (prompt build etc.) residual.

### 3.2 Cohort pós-camadas (n=12)

| Métrica | Valor |
|---------|-------|
| total_ms mean / p50 / p95 | 23685 / 13566 / 75752 |
| prompt_tokens mean / p50 / p95 | 11745 / 13360 / 14198 |

### 3.3 Conclusão de latência (evidenciada)

O gargalo de **tempo de parede** é o **LLM**, não o BM25 nem o CalendarProvider.

Implicação: reduzir tokens de entrada é a alavanca principal para latência *e* custo; otimizar só o RAG em milissegundos não move o p50/p95 de forma material.

Providers locais (temporal, calendar lookup, institutional read, prompt assemble) estão na ordem de dezenas de ms — **não** são o problema de latência.

## 4. Tokens — composição do custo

### 4.1 Universo com snapshot (n=70)

| Métrica | mean | p50 | p75 | p95 | min | max |
|---------|------|-----|-----|-----|-----|-----|
| prompt_tokens | 7766 | 7572 | 9995 | 13589 | 1053 | 14339 |
| completion_tokens | 258 | 94 | 416 | 936 | 5 | 1582 |
| total_tokens | 8023 | 7856 | 10131 | 13786 | 1086 | 14730 |

### 4.2 Overhead fixo das camadas (medição live 2026-08-09)

Reconstrução via `ContextBuilder` + ficheiros atuais em `context/` (sem LLM):

| Bloco | chars | ~tokens (chars/4) | Sempre montado? |
|-------|-------|-------------------|-----------------|
| `system_prompt.txt` (base) | 2709 | ~677 | sim |
| `identity.txt` | 2237 | ~559 | sim |
| Institucional (5× `.md`) | 14323 | **~3580** | **sim — 12/12 traces** |
| Temporal | 499 | ~124 | sim |
| Calendar (`calendar_block`) | 5840 | **~1460** | **sim — 27 eventos em 12/12** |
| **Soma camadas (sem RAG/grounding/transcript)** | 25615 | **~6403** | — |

Ficheiros institucionais no disco (contribuem ao bloco):

| Ficheiro | chars | ~tokens |
|----------|-------|---------|
| `disciplines.md` | 9507 | ~2376 |
| `rules.md` | 2049 | ~512 |
| `professors.md` | 1492 | ~373 |
| `identity.md` | 744 | ~186 |
| `faculty.md` | 147 | ~36 |
| `context.md` | 15202 | **não entra no prompt** (template humano) |

### 4.3 Prova crítica: pergunta temporal mínima

| Trace (msg) | intent | rag_skipped | transcript_turns | calendar_events_used | prompt_tokens |
|-------------|--------|-------------|------------------|----------------------|---------------|
| `que horas são chefe?` | time_fact | true | 0 | **27** | **6895** |
| `Que dia é hoje?` | time_fact | true | 0 | **27** | **6908** |

Evidência: o skip de RAG para `time_fact` **funciona**, mas o pedido ainda consome ~**6,9k tokens** — alinhado ao overhead fixo (~6,4k) + grounding/catálogo residual.  
**Calendar completo + institucional completo são enviados mesmo quando só o relógio basta.**

### 4.4 Perguntas de calendário / híbridas

| Msg | intent | rag_skipped | turns | rag sources | prompt_tokens |
|-----|--------|-------------|-------|-------------|---------------|
| `Quando é a próxima prova?` | calendar_fact | false | 4 | 7 | 13319 |
| `e que dia foi o primeiro tp de projeto de bloco?` | null | false | 6 | 7 | 13494 |
| `e o AT?` | null | false | 12 | 7 | 14082 |

Evidência: `calendar_fact` **mantém RAG** (conforme desenho atual em `docs/CONTEXT-ARCHITECTURE.md`). Em agenda sem eventos futuros, o sistema ainda injeta histórico completo (27) **e** chunks RAG (até 7 fontes), elevando o prompt para ~13k+.

### 4.5 Transcript

| Observação | Evidência |
|------------|-----------|
| Janela configurada | `ACL_TRANSCRIPT_MAX_TURNS` default 16; `ACL_CHAT_HISTORY_MAX_TURNS` 12; `ACL_CHAT_HISTORY_MAX_CHARS` 12000 |
| Cohort recente | 0–14 turns usados (`transcript_turns_used`) |
| Correlação | Nos 12 recentes, prompt_tokens sobe com turns (0→~6,9k; 14→~14,3k) **em cima** do overhead fixo |
| Universo antigo | Até 32 turns em snapshots pré-camadas |

Não há política adaptativa: a janela é a configurada, não o perfil da pergunta.

### 4.6 RAG

| Observação | Evidência |
|------------|-----------|
| Latência BM25 | p50 ~71 ms — irrelevante vs LLM |
| Skip | Só `time_fact` (2/12 na cohort) |
| `calendar_fact` | RAG ativo |
| Fontes injectadas | Tipicamente 3–7 mesmo com `confidence=low` / `reason=context_misaligned` |
| Candidatos | ~8 por pedido quando RAG corre |

## 5. Arquitetura actual (estado medido)

```text
POST /v1/chat
  → ContextManager
      → ContextBuilder.build_layers()     # identity + institutional + temporal + calendar SEMPRE
      → detect_temporal_intent(query)     # time_fact | calendar_fact | None
      → rag_skipped = (time_fact e sem escopo /doc…)
      → Transcript (janela fixa)
      → Pin
      → RAG/BM25 (salvo skip)
      → assemble_system_content (ordem canónica)
      → LLM
```

**Não existe ContextRouter / perfis FAST|NORMAL|DEEP.**  
Único roteamento determinístico: skip de RAG em `time_fact` (`kernel/context/intent.py`).

Nota de observabilidade: `system_prompt` no snapshot é truncado a **20000** chars (`kernel/trace/forensics.py`); `prompt_chars` / `prompt_tokens` reflectem o prompt **completo**. Por isso o bloco de agenda parece “curto” no JSON armazenado (~226 chars até ao corte) embora o bloco live tenha **5840** chars.

## 6. Gargalos reais (ordenados por evidência)

| # | Gargalo | Impacto | Evidência |
|---|---------|---------|-----------|
| 1 | **Institucional sempre-on (5 ficheiros, ~3,5k tok)** | Tokens em *todas* as requests da cohort | 12/12 com `institutional_files` length 5; `disciplines.md` sozinho ~2,4k tok |
| 2 | **Calendar sempre-on (27 eventos / ~1,5k tok)** | Tokens + ruído em perguntas não-calendário | 12/12 com `calendar_events_used=27`, incluindo `time_fact` |
| 3 | **RAG activo por defeito** (exceto `time_fact`) | Tokens + grounding fraco (`context_misaligned`) | 10/12 cohort com RAG; fontes irrelevantes em estágio/AT |
| 4 | **Transcript de janela fixa** | Tokens em follow-ups longos | Correlação turns↔prompt_tokens na cohort |
| 5 | **Latência LLM** | Tempo de parede | 97,8% do total_ms; correlacionada com prompts grandes |
| — | RAG latency / Calendar I/O | **Não priorizar** | dezenas–centenas de ms apenas |

## 7. O que **não** é desnecessário (não remover)

| Capacidade | Motivo |
|------------|--------|
| Temporal provider | Necessário para `time_fact` e deltas; bloco é barato (~124 tok) |
| Calendar provider | Necessário para provas/AT/TPs; o problema é **quando** e **quantos** eventos |
| Institucional | Necessário para professores/disciplinas; o problema é **enviar tudo sempre** |
| RAG/BM25 | Necessário para conteúdo académico; o problema é **correr/injectar sem necessidade** |
| Transcript | Necessário para follow-up/ambiguidade; o problema é **janela máxima sempre** |
| Tracing / painel | Sem degradação — base da medição |

## 8. Hipóteses para a fase seguinte (ainda não implementadas)

Derivadas **só** dos dados acima — a alterar após plano e testes:

1. **H1 — ContextRouter determinístico:** `time_fact` → temporal (+ identity mínima); sem institutional completo, sem calendar completo, sem RAG, transcript 0.
2. **H2 — Calendar sob demanda:** injectar agenda só com intent calendário / referência a prova/AT/TP; limitar `max_past_events` por relevância (disciplina/recência), não 27 sempre.
3. **H3 — Institucional sob demanda:** `professors.md` / fatias de `disciplines.md` por menção; não os 5 ficheiros inteiros em FAST.
4. **H4 — RAG adaptativo:** alargar skip além de `time_fact` (cumprimentos, calendar-only puro); filtrar inject quando `confidence=low`.
5. **H5 — Transcript adaptativo:** turns em função de follow-up/deixis; independente → 0–2.
6. **H6 — Context budget + ranking:** caps derivados desta baseline (ex.: overhead fixo alvo ≪ 6,4k; calendar ≪ 27 eventos).
7. **Cache de resposta:** **não** priorizar — risco de transcript inconsistente (lição Orbit); só avaliar cache de *artefactos* (bloco calendar mtime, institutional mtime) se seguro.

## 9. Cobertura da amostra vs pedido (20–50 traces)

| Requisito | Estado |
|-----------|--------|
| 20–50 traces | 70 com tokens; **12** com pipeline de camadas completo |
| Tipos diversos | Temporal, calendário, académico, follow-up curto (`e o AT?`), contextual — presentes; ambíguos/explícitos “explica melhor” **sub-representados** na cohort recente |
| Stages Orbit→Kernel | 14 `MESSAGE_RECEIVED` / `REQUEST_SENT_TO_KERNEL` — amostra Orbit parcial |
| Tokens por componente no provider | LLM não devolve breakdown por bloco; decomposto via medição live + `prompt.context` |

**Lacuna declarada (TBD):** expandir cohort pós-camadas para ≥20 traces cobrindo FAST/NORMAL/DEEP antes do benchmark final (`optimization/benchmark.md`). Os 12 actuais já bastam para **identificar** gargalos sem alterar código.

## 10. Critério de avanço

Baseline **fechada** quando:

- [x] Traces reais inspeccionados
- [x] Latência por etapa medida
- [x] Tokens agregados + overhead fixo medido
- [x] Gargalos ordenados por evidência (não por intuição)
- [ ] Nenhuma alteração de comportamento até plano (Fase 1 MegaBrain / routing) aprovado no ciclo

**Próximo artefacto do ciclo:** plano Capability IR + `optimization/routing.md` (desenho) — implementação só depois.
