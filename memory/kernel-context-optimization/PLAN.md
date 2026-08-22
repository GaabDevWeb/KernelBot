# PLAN — ContextRouter / Perfis FAST|NORMAL|DEEP

| Campo | Valor |
|-------|-------|
| Feature ID | `kernel-context-optimization` |
| Data | 2026-08-09 |
| Baseline SSOT | `optimization/baseline.md` |
| Fase actual | **Planeamento apenas** — zero alteração de código de produto |
| Capability IR | `memory/kernel-context-optimization/plan.ir.yaml` |
| Próximo desenho | `optimization/routing.md` (produzido no ID 1) |

---

## Objetivo

O Kernel passa a montar contexto sob demanda via `ContextRouter` e perfis `FAST|NORMAL|DEEP`, reduzindo tokens de overhead fixo (institucional + calendar always-on) e RAG/transcript desnecessários, **sem remover** providers nem capacidades — apenas quando e quanto injectar.

**Critério de fecho global:** suite de testes de routing/builders verde; cohort pós-mudança com métricas em `optimization/results.md` a cumprir os alvos da secção **Métricas de sucesso**; `optimization/{routing,benchmark,results}.md` publicados; rollback por flag documentado.

---

## Verificação de existência

| Artefacto | Método | Estado |
|-----------|--------|--------|
| `optimization/baseline.md` | Read integral | confirmado |
| `optimization/baseline_raw.json` | Glob | confirmado |
| `kernel/context/intent.py` (`detect_temporal_intent`, `time_fact`/`calendar_fact`) | Read | confirmado |
| `kernel/context/builder.py` (`build_layers`, `assemble_system_content`, ordem canónica) | Read | confirmado |
| `kernel/orchestrator/context.py` (`rag_skipped` em `time_fact` + `build_layers` always-on) | Read §942–1160 | confirmado |
| `kernel/context/institutional.py` (`SECTION_FILES`, `prompt_block` tudo-ou-nada) | Read | confirmado |
| `kernel/context/calendar_provider.py` (`build_prompt_block`, defaults `max_events=15`, `max_past_events=30`) | Read | confirmado |
| `docs/CONTEXT-ARCHITECTURE.md` | Grep + leitura parcial | confirmado |
| `tests/test_context_*.py` (intent, builder, calendar, temporal, trace) | Glob | confirmado |
| `kernel/config.py` (`ACL_CHAT_HISTORY_*`, `ACL_TRANSCRIPT_MAX_TURNS`) | Grep | confirmado |
| `.env.example` (vars transcript/history) | Grep | confirmado |
| `ContextRouter` / perfis FAST\|NORMAL\|DEEP | Grep codebase | **ausente** (a criar) |
| `optimization/routing.md`, `benchmark.md`, `results.md` | Glob | **ausente** (a criar na execução) |
| Cache de respostas LLM | Baseline §8 | **proibido** neste plano |

**Suposições pendentes:**

1. **S1** — Cohort pós-camadas expandirá para ≥20 traces antes do benchmark final (lacuna já declarada no baseline §9). Dono: ID 10 (benchmark).
2. **S2** — Feature flag env (ex.: `ACL_CONTEXT_ROUTER=1`) é o mecanismo de rollback; default off até gate de métricas. Dono: ID 2 (contrato) confirma nome e default.
3. **S3** — “Calendar-only puro” (RAG skip em agenda sem necessidade de docs) é distinguível por heurística determinística + ausência de termos académicos de conteúdo; validar em testes golden. Dono: ID 6.

---

## Decisões (SSOT até replanejar)

| # | Decisão | Justificação (evidência baseline) |
|---|---------|-----------------------------------|
| D1 | **Não remover** Temporal, Calendar, Institucional, RAG, Transcript, Tracing | Baseline §7 — problema é *quando/quanto*, não existência |
| D2 | Prioridade de implementação: **institucional+calendar on-demand → RAG adaptativo → transcript adaptativo → budgets** | Briefing + gargalos #1–#4 ordenados por evidência |
| D3 | Perfis canónicos: `FAST` \| `NORMAL` \| `DEEP` | H1; único roteamento actual é `rag_skipped` em `time_fact` |
| D4 | Router **determinístico** (regex/heurística + intents existentes); sem LLM de classificação nesta fase | Latência LLM já é 97,8% do total; não adicionar round-trip |
| D5 | Ordem canónica de `assemble_system_content` **preservada**; blocos omitidos quando vazios | `builder.py` já omite vazios — router decide o que preencher |
| D6 | **Proibido** cache de respostas que bypass transcript | Baseline H7 / lição Orbit |
| D7 | Cache de *artefactos* (mtime institutional/calendar) só após métricas e se não alterar semântica por turno | Fora do caminho crítico; opcional ID docs-dívida |
| D8 | `calendar_fact` deixa de implicar “sempre RAG + 27 eventos”; passa por perfil + budgets | Baseline §4.4 |
| D9 | Observabilidade obrigatória: `context_profile`, flags de camadas, eventos calendar usados, `rag_skipped` reason, transcript turns | Extende stages já existentes (`TEMPORAL_CONTEXT`, `CALENDAR_LOOKUP`, `prompt.context`) |
| D10 | Esta entrega de planeamento **não** altera código de produto | REGRA Nº1 do utilizador |

---

## Análise de contexto

### Legado e débito técnico

- `ContextBuilder.build_layers()` resolve institutional + temporal + calendar **sempre**, sem parâmetros de selecção.
- `ContextManager` só aplica `rag_skipped` para `time_fact` sem `/doc` / force RAG / disciplina.
- `InstitutionalContextProvider.prompt_block()` injecta os 5 ficheiros preenchidos de uma vez (~3580 tok).
- `CalendarProvider.build_prompt_block()` aceita caps mas o caller usa defaults → 27 eventos observados.
- Transcript: janela fixa `ACL_CHAT_HISTORY_MAX_TURNS` / `ACL_TRANSCRIPT_MAX_TURNS` — sem perfil.
- **Decisão do plano:** introduzir contrato `ContextRoute` *antes* de mutar `build_layers` / `ContextManager`; fatias por provider evitam big-bang.

### Performance

- Hot path: tokens → LLM (p50 total_ms cohort 13566; prompt_tokens p50 13360).
- Overhead fixo medido ~6403 tok sem RAG/transcript.
- Alvo primário: cortar institutional+calendar em FAST; secundário: RAG skip + transcript curto.
- Não priorizar otimização de BM25 ms (p50 ~71).

### Segurança e conformidade

- Institucional/rules omitidos em FAST não podem criar respostas que contradigam regras oficiais em perguntas que as exijam → NORMAL/DEEP devem repor `rules.md` quando a query tocar política/turma.
- Calendar filtrado: risco de omitir evento relevante → DEEP e queries com disciplina/menção explícita alargam janela; conflito agenda > transcript permanece (CONTEXT-ARCHITECTURE).
- Sem exposição nova de PII; traces já guardam prompt (truncado 20k no snapshot forense).

### Fora de escopo

- Cache de respostas LLM / bypass de transcript
- Reescrita do BM25 / troca de retrieval engine
- Classificador LLM de intent
- UI do painel de traces (apenas campos novos nos stages/snapshots)
- Alteração de `system_prompt.txt` / persona (salvo omissão de camadas)
- Expansão de dados institucionais em disco

---

## Análise de impacto (resumo executivo)

| Área | Risco | Mitigação (ID) |
|------|-------|----------------|
| Legado (`context.py` monolítico) | médio | Contrato ID 2 + fatias 4–8; flag rollback |
| Performance (regressão se DEEP inflar) | baixo–médio | Budgets ID 8 + benchmark ID 10 |
| Segurança (omitir rules/agenda) | médio | Matriz routing ID 1; testes golden ID 9 |
| Qualidade resposta calendar-only | médio | S3 + testes ID 6/9; DEEP escape hatch |
| Observabilidade / comparabilidade baseline | baixo | ID 7 campos estáveis vs `baseline_raw.json` |

---

## Esboço de regras de routing (input de `optimization/routing.md`)

> Norma de desenho — **congelar** no ID 1. Implementação só depois do contrato ID 2.

### Sinais de entrada (determinísticos)

| Sinal | Fonte |
|-------|-------|
| `temporal_intent` | `detect_temporal_intent` → `time_fact` \| `calendar_fact` \| `None` |
| `force_doc` / `force_rag` / disciplina `/…` | ContextManager (já existente) → **força ≥ NORMAL**, RAG on |
| Cumprimento / ack curto | Heurística nova (lista fechada PT-BR) |
| Deixis / follow-up | Pronomes/anáforas (`e o AT?`, `isso`, `aquele`) ou turns>0 com query curta |
| Menção institucional | Tokens vs `professors.md` / nomes de disciplina |
| Pedido profundo | Marcadores (`explica`, `detalha`, `compara`, `por que`, multi-pergunta) |
| RAG confidence | `decision.confidence` / `reason=context_misaligned` (pós-retrieval) |

### Matriz perfil → camadas

| Camada | FAST | NORMAL | DEEP |
|--------|------|--------|------|
| base + identity | on | on | on |
| temporal | on | on | on |
| institutional | **off** (excepto fatia mínima se menção explícita nome próprio já classificado) | selectivo: `rules.md` se política; `professors`/`disciplines` por menção; `faculty`/`identity.md` opcional | ranking completo até budget |
| calendar | **off** | on com caps baixos + filtro relevância | on com caps altos / disciplina |
| RAG | **skip** | on; skip se calendar-only puro (S3) | on; inject filtrado se `confidence=low` |
| transcript turns | 0–2 | 2–8 (deixis↑) | até config max |
| catalog/sticky/grounding | grounding mínimo | como hoje | como hoje |

### Mapeamento sinal → perfil (prioridade top-down)

1. `force_doc` \| `force_rag` \| disciplina explícita → **DEEP** (ou NORMAL+RAG obrigatório; contrato fixa)
2. Marcadores profundos / query longa multi-hop → **DEEP**
3. `time_fact` → **FAST**
4. Cumprimento/ack sem conteúdo → **FAST**
5. `calendar_fact` → **NORMAL** (calendar on, RAG condicional)
6. Deixis/follow-up curto → **NORMAL** (transcript↑, institutional/calendar só se sinais)
7. Default académico → **NORMAL**; upgrade DEEP se retrieval fraco + pedido de detalhe

### Caps iniciais (derivados do baseline; afinar no ID 8)

| Budget | FAST | NORMAL | DEEP |
|--------|------|--------|------|
| `max_calendar_events` (futuro+passado usados) | 0 | 6 | 15 |
| `max_past_events` | 0 | 4 | 12 |
| Institutional chars (aprox) | 0 | ≤4000 | ≤14323 (hoje) |
| Transcript turns (prompt) | 0–2 | 2–8 | ≤ `chat_history_max_turns` |
| RAG top sources inject | 0 | ≤5; 0 se low-conf filter | ≤7 (actual) |
| Overhead fixo alvo (sem RAG/transcript) | **≪ 2,0k tok** | ≪ 4,5k | ≤ 6,4k (baseline) |

### Exemplos golden (aceitação comportamental)

| Query | Perfil | institutional | calendar | rag_skipped | turns |
|-------|--------|---------------|----------|-------------|-------|
| `que horas são chefe?` | FAST | off | off | true | 0 |
| `Que dia é hoje?` | FAST | off | off | true | 0 |
| `oi` / `obrigado` | FAST | off | off | true | 0–1 |
| `Quando é a próxima prova?` | NORMAL | selectivo | on (caps) | true se calendar-only | 0–4 |
| `e o AT?` (follow-up) | NORMAL | off/select | on filtrado | condicional | ≥2 |
| `explica o TP de projeto de bloco com base nos materiais` | DEEP | on/rank | on | false | até max |

---

## Grafo de execução

| ID | Descrição | Tipo | Complexidade | Depende de | CP | Lote | Critério de aceite técnico |
|----|-----------|------|--------------|------------|----|------|----------------------------|
| 1 | Publicar `optimization/routing.md` com matriz sinal→perfil→camadas + golden + caps (congelar D1–D9) | docs | M | — | sim | — | Ficheiro existe; cobre FAST/NORMAL/DEEP; exemplos da tabela golden; proíbe cache de respostas |
| 2 | Contrato `ContextRoute` / `ContextProfile` (campos, defaults, flag env, razões `rag_skipped`) em `docs/contracts/context-route-v1.md` + esqueleto tipos | contrato | M | 1 | sim | — | Documento + tipos referenciam os mesmos nomes (`profile`, `include_*`, `budgets`, `rag_skip_reason`); default flag off |
| 3 | Implementar `ContextRouter` puro (query+sinais → `ContextRoute`) sem I/O | backend | M | 2 | sim | — | Unitários: golden da matriz; `time_fact`⇒FAST; force_rag⇒≠FAST |
| 4 | Institutional on-demand: API selectiva no provider + `build_layers` respeita route | backend | M | 2, 3 | sim | — | FAST `time_fact`: `institutional_files==()`; NORMAL com menção professor inclui `professors.md` |
| 5 | Calendar on-demand: caps/filtro por route; 0 eventos em FAST | backend | M | 2, 3 | sim | P1 | FAST: `calendar_events_used==0` e bloco vazio; NORMAL respeita caps do contrato |
| 6 | RAG adaptativo: skip alargado + filtro inject `confidence=low` | backend | M | 2, 3 | sim | P1 | Skip em FAST cumprimentos + time_fact; calendar-only puro skip (S3); low-conf não injeta chunks (teste) |
| 7 | Observabilidade: profile + layer flags + skip reason nos stages/snapshot | backend | M | 3 | não | P2 | Trace contém `context_profile` e contagens comparáveis ao baseline |
| 8 | Transcript adaptativo por perfil (turns efectivos) | backend | M | 2, 3 | não | P2 | FAST independente: ≤2 turns no prompt; deixis NORMAL ≥2 quando history existe |
| 9 | Budgets + ranking (caps duros + trim institutional/calendar) | backend | M | 4, 5, 6, 8 | sim | — | Nenhum assemble excede caps do perfil; teste de trim |
| 10 | Suite testes + regressão builders/intent/router/integration | testes | L | 3–9 | sim | — | `pytest tests/test_context_*.py tests/test_context_router*.py` verde |
| 11 | Benchmark cohort ≥20 + `optimization/benchmark.md` + `results.md` vs baseline | pesquisa | M | 7, 10 | sim | — | Métricas alvo § abaixo cumpridas ou gap documentado com decisão go/no-go |
| 12 | Actualizar `docs/CONTEXT-ARCHITECTURE.md` + `.env.example` da flag | docs | S | 11 | não | — | Docs descrevem router/perfis; env documentado |

**Legenda:** **CP** = caminho crítico. **Lote** = paralelo seguro após dependências.

### Caminho crítico (cadeia bloqueante)

`1 → 2 → 3 → (4 ∥ 5 ∥ 6) → 9 → 10 → 11 → 12`  
(Observabilidade 7 e transcript 8 em paralelo após 3; 8 alimenta 9.)

### Lotes paralelos

- **P1:** IDs 4, 5, 6 (pré-requisito: 3; ficheiros distintos: `institutional.py` / `calendar_provider.py`+builder / `context.py` RAG — coordenar `builder.py` via contrato de kwargs já definido no ID 2 para evitar conflito; se conflito de ficheiro, serializar 4→5→6)
- **P2:** IDs 7, 8 (após 3; 8 antes de 9)

### Dependências (grafo em texto)

- ID 1 → bloqueia → ID 2
- ID 2 → bloqueia → ID 3, e define kwargs de `build_layers`
- ID 3 → bloqueia → IDs 4, 5, 6, 7, 8
- IDs 4, 5, 6, 8 → bloqueiam → ID 9
- IDs 3–9 → bloqueiam → ID 10
- IDs 7, 10 → bloqueiam → ID 11
- ID 11 → bloqueia → ID 12

**Nota anti-conflito:** se P1 contender em `builder.py`/`context.py`, o orquestrador **serializa** 4→5→6 no mesmo ficheiro; o lote P1 aplica-se a providers isolados.

---

## Definição de interfaces (contratos)

| Contrato | Consumidores (IDs) | Artefacto | Versionamento |
|----------|-------------------|-----------|---------------|
| ContextRoute v1 | 3–9 | `docs/contracts/context-route-v1.md` | breaking → novo ID contrato |
| Routing design | 2–12 | `optimization/routing.md` | alteração de golden → re-benchmark |

**Campos críticos (anti-desalinhamento):**

| Campo | Tipo | Produtor | Consumidor |
|-------|------|----------|------------|
| `profile` | enum `FAST\|NORMAL\|DEEP` | Router (3) | Builder/Manager (4–9), traces (7) |
| `include_institutional` | bool | Router | Institutional provider (4) |
| `institutional_files` | `list[str]` allowlist | Router | Institutional (4) |
| `include_calendar` | bool | Router | Calendar (5) |
| `calendar_budgets.max_events` | int | Router/Budgets | Calendar (5, 9) |
| `calendar_budgets.max_past_events` | int | Router/Budgets | Calendar (5, 9) |
| `rag_skipped` | bool | Router+Manager (6) | Retrieval (6), traces (7) |
| `rag_skip_reason` | str enum | Manager (6) | traces (7), results (11) |
| `transcript_max_turns` | int | Router (8) | truncate history (8) |
| `router_enabled` | bool (env) | Settings | ContextManager entry |

---

## Estratégia de teste

| ID(s) | Tipo | Comando / ferramenta | Prova de conclusão |
|-------|------|---------------------|-------------------|
| 3 | Unitário | `pytest tests/test_context_router.py -q` | Golden perfil |
| 4–5 | Unitário | `pytest tests/test_context_builder.py tests/test_context_calendar.py -q` | Camadas omitidas/caps |
| 6 | Unitário + integração leve | `pytest tests/test_context_intent.py tests/test_context_router.py -q` | Skip reasons |
| 7 | Unitário trace | `pytest tests/test_context_trace.py -q` | Campos novos presentes |
| 8–9 | Unitário | testes de truncate + budget | Caps respeitados |
| 10 | Gate | `pytest tests/test_context_*.py tests/test_context_router*.py -q` | Suite verde |
| 11 | Medição | script/notas sobre `data/traces.sqlite3` + live builders | `results.md` com deltas |

**Ordem:** unit router → unit providers/builder → trace → suite gate → benchmark live.

---

## Estratégia de validação (por ID)

| ID | Como provar "concluído" | Evidência exigida no [RESULTADO] |
|----|-------------------------|----------------------------------|
| 1 | Review de `optimization/routing.md` | path + secções matriz/golden/caps |
| 2 | Diff contrato + nomes iguais ao código stub | path contrato |
| 3 | pytest router verde | comando + N testes |
| 4 | FAST sem institutional_files | teste + eventual trace fixture |
| 5 | FAST calendar_events_used=0 | teste |
| 6 | skip reasons cobertos | teste parametrizado |
| 7 | snapshot/stage com `context_profile` | teste trace |
| 8 | turns por perfil | teste |
| 9 | trim não excede cap | teste |
| 10 | suite verde | log pytest |
| 11 | tabela antes/depois vs baseline | `optimization/results.md` |
| 12 | docs + env.example | paths |

---

## Métricas de sucesso (antes / depois vs baseline)

Fontes *antes*: `optimization/baseline.md` cohort pós-camadas n=12 (e medição live overhead).

| Métrica | Antes (baseline) | Alvo depois | Gate |
|---------|------------------|-------------|------|
| `time_fact` prompt_tokens | 6895 / 6908 | **≤ 2500** | hard |
| `time_fact` `calendar_events_used` | 27 | **0** | hard |
| `time_fact` `institutional_files` length | 5 | **0** | hard |
| `time_fact` `rag_skipped` | true | true + reason estável | hard |
| Overhead fixo camadas (live, sem RAG/transcript) FAST | ~6403 tok | **≤ 2000 tok** | hard |
| `calendar_fact` eventos usados | 27 | **≤ 6** (NORMAL) | hard |
| Taxa RAG skip (cohort mista FAST-eligível) | 2/12 | **≥ 25%** da cohort de benchmark (≥20) | soft→hard no go-live |
| prompt_tokens p50 cohort pós-camadas | 13360 | **≤ 9350** (−30%) | soft (documentar se N insuficiente) |
| total_ms p50 | 13566 | monitorar; esperado ↓ com tokens | informativo |
| Regressão qualidade golden | n/a | 0 falhas nos golden routing | hard |
| Capacidades removidas | n/a | **0** (providers intactos) | hard |

**Go-live:** flag `ACL_CONTEXT_ROUTER=1` só após hard gates verdes na cohort de benchmark.

---

## Briefings PDA (tarefas delegáveis)

### Briefing — ID 1

**Estrutura do projeto:** Baseline em `optimization/baseline.md`; arquitectura em `docs/CONTEXT-ARCHITECTURE.md`; intents em `kernel/context/intent.py`.

**Objetivo imediato:** Publicar `optimization/routing.md` congelando matriz e golden deste PLAN.

**Impedimentos:** Não implementar código; não contradizer D1/D6; H1–H6 são ponto de partida priorizado por evidência.

### Briefing — ID 2

**Estrutura do projeto:** Novo contrato sob `docs/contracts/`; tipos a viver junto de `kernel/context/` na implementação.

**Objetivo imediato:** `ContextRoute` v1 com campos da tabela de contrato + flag env default off.

**Impedimentos:** Nomes estáveis para IDs 3–9; breaking change exige novo contrato.

### Briefing — ID 3

**Estrutura do projeto:** Módulo novo (ex. `kernel/context/router.py`); puro, sem providers.

**Objetivo imediato:** `route(query, signals) -> ContextRoute` alinhado a `routing.md`.

**Impedimentos:** Depende ID 2; não chamar LLM; preservar `detect_temporal_intent` como sinal.

### Briefing — ID 4

**Estrutura do projeto:** `kernel/context/institutional.py` + `builder.py`.

**Objetivo imediato:** Allowlist de ficheiros por route; FAST sem bloco institucional.

**Impedimentos:** Não apagar ficheiros em disco; `context.md` continua fora do prompt.

### Briefing — ID 5

**Estrutura do projeto:** `calendar_provider.py` já expõe caps — wiring em `build_layers`/caller.

**Objetivo imediato:** FAST sem agenda; NORMAL/DEEP com caps do contrato.

**Impedimentos:** Conflito agenda > transcript permanece documentado.

### Briefing — ID 6

**Estrutura do projeto:** `rag_skipped` hoje só `time_fact` em `context.py` §954–960.

**Objetivo imediato:** Alargar skip + filtro low-confidence; reasons observáveis.

**Impedimentos:** `force_*` e disciplina anulam skip; não remover BM25.

### Briefing — ID 7

**Estrutura do projeto:** stages em `kernel/trace/`; testes `test_context_trace.py`.

**Objetivo imediato:** Persistir `context_profile` e flags para diff vs baseline.

**Impedimentos:** Snapshot forense trunca system_prompt a 20k — métricas usam `prompt_tokens` completos.

### Briefing — ID 8

**Estrutura do projeto:** truncate em `context.py` + settings `ACL_CHAT_HISTORY_*`.

**Objetivo imediato:** Turns efectivos por perfil; sem bypass de transcript store.

**Impedimentos:** Proibido cache de respostas; store pode manter N alto — o corte é no prompt.

### Briefing — ID 9

**Estrutura do projeto:** pós-selecção de camadas; trim determinístico.

**Objetivo imediato:** Caps duros por perfil; falha segura = omitir cauda, não rebentar.

**Impedimentos:** Depende 4/5/6/8.

### Briefing — ID 10

**Estrutura do projeto:** `tests/test_context_*.py` existentes como âncora de não-regressão.

**Objetivo imediato:** Cobrir router + integrações; suite verde.

**Impedimentos:** Flag off = comportamento legacy nos testes de compat.

### Briefing — ID 11

**Estrutura do projeto:** `data/traces.sqlite3` + medição live estilo baseline.

**Objetivo imediato:** `benchmark.md` + `results.md` com tabela antes/depois.

**Impedimentos:** S1 cohort ≥20; se falhar hard gate → `replanejar` caps, não forçar go-live.

---

## Riscos, bloqueios e replaneamento

| Risco | Probabilidade | Impacto | Resposta |
|-------|---------------|---------|----------|
| Omitir institutional em pergunta de regras/turma | média | alto | rules.md em NORMAL quando sinais de política; golden negativos |
| Calendar-only skip esconde data só em PDF | média | alto | S3 conservador; hybrid → RAG on; DEEP escape |
| Conflito de merge em `context.py` no P1 | alta | médio | Serializar 4→5→6 se necessário |
| Cohort <20 no benchmark | média | médio | Documentar gap; hard gates em golden sintéticos + traces disponíveis |
| Regressão latência por lógica router | baixa | baixo | Router sync <1ms; medir no ID 11 |
| Pressão para cache de respostas | baixa | alto | Recusar (D6); só artefactos mtime pós-resultados |

**Gatilhos de `replanejar`:**

- Hard metrics de `time_fact` não atingidas após ID 9+11 sem bug óbvio de wiring
- Necessidade de classificador LLM para atingir qualidade
- Conflito irreconcilável entre omitir `rules.md` e compliance da turma
- Alteração de ordem canónica do prompt (proibida sem novo contrato)

---

## Ordem de execução mandatória

1. **ID 1** — congela routing (desbloqueia contrato)
2. **ID 2** — contrato ContextRoute v1
3. **ID 3** — ContextRouter puro + testes
4. **P1:** IDs 4, 5, 6 (ou serializados se conflito de ficheiro)
5. **P2:** IDs 7, 8
6. **ID 9** — budgets
7. **ID 10** — gate testes
8. **ID 11** — benchmark/results vs baseline
9. **ID 12** — docs arquitectura + env

---

## Handoff ao Orquestrador Raiz

- **Próximo comando lógico:** aceitar este `[PLANO]` → Fase 2 com **ID 1** (`optimization/routing.md`)
- **Persistência:** registar em `.agent_history.md` o feature id `kernel-context-optimization` e IDs 1–12 abertos
- **Não iniciar implementação de produto** sem aceitar este documento + `plan.ir.yaml` como SSOT
- **IR:** `memory/kernel-context-optimization/plan.ir.yaml`
- **Fase actual cumprida quando:** `PLAN.md` + `plan.ir.yaml` existem com DoD mensurável (esta entrega)

---

## Definition of Done — artefacto de planeamento (esta fase)

- [x] Baseline lido e hipóteses H1–H6 priorizadas por evidência
- [x] Contratos de `intent` / `build_layers` / `rag_skipped` inspeccionados
- [x] `PLAN.md` com objectivo, decisões, DAG, riscos, métricas antes/depois
- [x] Esboço de routing incluído (predecessora de `routing.md`)
- [x] `plan.ir.yaml` Capability IR v2
- [x] Zero diff de código de produto nesta fase
