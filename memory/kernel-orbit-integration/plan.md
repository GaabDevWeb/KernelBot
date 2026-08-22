# Plano — Kernel ↔ Orbit Integration (API v1 + Transcript Store)

| Campo | Valor |
|-------|-------|
| feature_id | kernel-orbit-integration |
| branch | feature/kernel-orbit-integration |
| docs | approved (PRD, ADR-0002, API_SPEC, ARCHITECTURE, DATA-MODEL) |
| Legenda de prefixos | `PO` = contrato · `B` = backend · `T` = testes · `S` = segurança · `D` = docs |

Este plano é o SSOT `[PLANO]` para a Fase 2 do orquestrador até `replanejar`. Implementa **apenas** o que RF-001…RF-011 e G1–G7 (grill-me, `docs/prd/2026-07-28-kernel-orbit-integration.md`) exigem. Nenhum código foi escrito nesta missão — só planeamento.

---

## Objetivo

O Kernel expõe `GET /v1/health` e `POST /v1/chat` (contrato `ChannelContext`), com transcript store in-memory por chave `platform:user_id:channel_id[:session_id]` (janela deslizante, default 16 pares, configurável), `reset_context` limpando transcript+pin, e **zero** mudança funcional em `/chat`, `/health`, `/search` legados.

**Critério de fecho global:** `pytest tests/` 100% verde (suíte legada inalterada + suíte nova v1); `GET /v1/health` → `{"status":"ok"}`; `POST /v1/chat` com `context.platform/user_id/channel_id` + `message` devolve `ChatResponse` no mesmo shape de `/chat`; nenhum endpoint novo além dos dois definidos em RF-004/RF-005.

---

## Verificação de existência

| Artefacto | Método | Estado |
|-----------|--------|--------|
| `docs/prd/2026-07-28-kernel-orbit-integration.md` | Read | confirmado (approved, G1–G7 congeladas) |
| `docs/adr/0002-kernel-v1-channel-api.md` | Read | confirmado (accepted) |
| `docs/API_SPEC.md` (secção "API v1") | Read | confirmado — **campo `reset_context` ausente da tabela de request de `POST /v1/chat`** apesar de RF-011/G3 exigirem o campo (lacuna documental, não contradição) |
| `docs/ARCHITECTURE.md`, `docs/DATA-MODEL.md` | Read | confirmado |
| `kernel/schemas/chat.py` (`ChatRequest`, `ChatResponse`, `HistoryItem`, `confidence_to_float`) | Read | confirmado |
| `kernel/schemas/search.py`, `kernel/schemas/validators.py` | Read | confirmado |
| `kernel/memory/session_key.py` (`memory_session_key`) | Read | confirmado — **não** deriva chave sem `session_id` (retorna `None`); v1 precisa de função nova (G4 diverge do legado) |
| `kernel/memory/pinned_store.py` (`PinnedSessionStore`) | Read | confirmado — API `get/set_pinned/clear/begin_turn` reutilizável tal como está |
| `kernel/orchestrator/context.py` (`ContextManager.build_messages`) | Read | confirmado — aceita `session_id` opaco (qualquer string) e `conversation_history` já truncado por `chat_history_max_turns/max_chars`; **nenhuma alteração necessária** neste ficheiro |
| `kernel/providers/chat_provider.py`, `kernel/providers/aggregate.py` | Read | confirmado — hard stop e `provider_error` sempre produzem `answer` não vazio via `aggregate_sse` |
| `kernel/config.py` (`Settings`) | Read | confirmado — **não existe** `transcript_max_turns` / `ACL_TRANSCRIPT_MAX_TURNS` (a criar) |
| `api/routes.py` (`chat()`, `_services`, `_request_id`) | Read | confirmado — lógica de `/chat` está inline; requer extração para reuso |
| `api/security.py` (`verify_channel_api_bearer`, `allow_public_operation`) | Read | confirmado — reutilizável sem alteração (RF-007) |
| `api/internal_routes.py`, `app/factory.py`, `app/state.py` (`AppServices`) | Read | confirmado — `AppServices` não tem `transcript_store` (a adicionar com default, para não quebrar testes existentes) |
| `main.py` (`build_services`) | Read | confirmado |
| `tests/test_chat_json.py`, `test_chat_schema.py`, `test_health.py`, `test_internal_api.py`, `test_search_endpoint.py`, `test_session_key.py` | Glob + Read | confirmados — usados como base de regressão (T6) e padrão de stub para T5 |
| `adapters/README.md` | Read | confirmado — já referencia `/v1/health`/`/v1/chat`; precisa nota sobre `reset_context` |
| `kernel/schemas/channel.py`, `kernel/memory/transcript_store.py`, `api/routes_v1.py`, `api/chat_pipeline.py` | Glob | **ausentes** (a criar — ver Grafo) |
| `.env.example` | Read | confirmado — sem `ACL_TRANSCRIPT_MAX_TURNS` (a adicionar) |

**Suposições pendentes:**

1. **SUP-1** — Persistência de transcript aplica-se **só** a `/v1/chat` com `stream=false` (JSON). Com `stream=true`, a resposta é entregue via `StreamingResponse` sem buffer do texto final no processo do handler antes do retorno HTTP; o par não é persistido nesta entrega. Base: ADR-0002 confirma que SSE é "opt-in herdado, não é requisito Orbit fase 1". Dono/verificação: B5 (implementação) + T5-g (teste dedicado).
2. **SUP-2** — O campo `reset_context` (RF-011/G3) está ausente da tabela de `POST /v1/chat` em `docs/API_SPEC.md`; tratado como lacuna a corrigir, não como decisão a rediscutir. Dono/verificação: PO1.
3. **SUP-3** — A resposta de `/v1/chat` ecoa em `metadata.session_id` o valor **fornecido** pelo cliente em `context.session_id` (ou `null` se omitido) — **não** a chave composta interna (G4), que é detalhe de implementação. Dono/verificação: PO1 (contrato) + B5.
4. **SUP-4** — "Sucesso" (G7 — "append só em par completo") = qualquer resposta HTTP 200 de `/v1/chat` com `answer` não vazio devolvido por `aggregate_sse` (inclui hard stop e `provider_error`, que sempre produzem texto coerente ao cliente); falha antes disso (exceção em `build_messages`, 503 de serviços) não persiste o par. Dono/verificação: B5 + T5-a/h.

Nenhuma suposição bloqueia o início da implementação — todas têm dono e teste de verificação já mapeados no grafo abaixo.

---

## Análise de contexto

### Legado e débito técnico

`api/routes.py` tem hoje a lógica de `/chat` (build_messages → provider → aggregate/stream → `PipelineRecord`) inline na função `chat()`. Reutilizá-la para `/v1/chat` **sem duplicar** exige extrair essa lógica para `api/chat_pipeline.py` (B4) — risco de regressão no endpoint legado, mitigado por T6 (suíte de regressão completa, byte-idêntica em asserts) rodando **antes** do gate de segurança (S1). Débito pré-existente e **fora de escopo**: `kernel/tools/watcher.py` com import órfão `engine.search` (já assinalado no PRD).

### Performance

`TranscriptStore` e `PinnedSessionStore` são in-process (sem partilha multi-worker — limitação já aceite no PRD/ADR, fora de escopo resolver aqui). Custo adicional por request: uma leitura + uma escrita O(1) amortizado num `dict[str, deque]`; sem chamadas de rede, sem impacto relevante no hot path BM25+LLM. Trade-off aceite e não mitigado nesta missão: uma entrada de transcript pode reter mensagens de até 16000 caracteres (limite de `message`) sem cap adicional de tamanho — G6 só define limite por **pares**, não por caracteres; ver Riscos.

### Segurança e conformidade

`reset_context` só pode limpar estado **depois** de `verify_channel_api_bearer`/`allow_public_operation` passarem (ordem mandatória em B5) — caso contrário seria um vetor de negação de serviço não autenticado (limpar pin/transcript de terceiros). `ChannelContext` e `ChatRequestV1` usam `extra="forbid"` (RF-001: sem campos vendor tipo `jid`/`guild_id`/`phone`). `session_id` em `ChannelContext` reutiliza o validador opaco existente (rejeita só-dígitos). `/v1/chat` **não** implementa `/reload` nem qualquer operação privilegiada via conteúdo de `message` (diferente do legado) — verificado em S1.

### Fora de escopo

Idêntico ao PRD, mais os itens desta análise: implementar Orbit/Baileys; adapter Discord real; endpoints além de `GET /v1/health`/`POST /v1/chat`; persistência durável de transcript/pin; comandos textuais `/reset`/`/nova` no Kernel; unificar `/chat` legado com transcript; deprecar `/chat`; Redis/filas/service mesh; persistência de transcript quando `stream=true` (SUP-1); cap de caracteres por entrada de transcript (não pedido por G1–G7).

---

## Análise de impacto (resumo executivo)

| Área | Risco | Mitigação (ID) |
|------|-------|-----------------|
| Regressão em `/chat` legado durante extração do pipeline partilhado | médio | B4 preserva assinatura externa; T6 roda suíte completa sem alterar asserts |
| Contrato Orbit divergente do documentado (`reset_context` ausente) | médio | PO1 corrige `docs/API_SPEC.md` antes de B5 consumir o contrato |
| Vazamento de contexto entre utilizadores/canais via chave v1 mal derivada | alto (dados educacionais por utilizador) | B2 implementa G4 literalmente; T2 testa isolamento; S1 audita |
| `reset_context` como vetor de bypass/DoS não autenticado | alto | B5 aplica auth **antes** do reset; S1 checklist dedicado |
| Crescimento de memória do transcript store | baixo (janela fixa por config) | B1 define `ACL_TRANSCRIPT_MAX_TURNS`; B3 aplica janela deslizante |
| Quebra de testes existentes por novo campo obrigatório em `AppServices` | médio | B6 usa `default_factory`, sem quebrar construções existentes |

---

## Grafo de execução

| ID | Descrição | Tipo | Complexidade | Depende de | CP | Lote | Critério de aceite técnico |
|----|-----------|------|--------------|------------|----|------|----------------------------|
| PO1 | `ChannelContext` (novo `kernel/schemas/channel.py`) + `ChatRequestV1` (em `kernel/schemas/chat.py`) + extração de `strip_and_require()` para `kernel/schemas/validators.py` (reuso DRY, `ChatRequest` legado sem mudança de comportamento) + correção de `docs/API_SPEC.md` (campo `reset_context` na tabela de `POST /v1/chat`) | contrato | M | — | sim | P1 | `extra="forbid"` rejeita campo vendor; `session_id` só-dígitos rejeitado; `ChatRequest` legado 100% compatível (T6 verde); API_SPEC lista `reset_context: bool, default false` |
| B1 | `kernel/config.py`: `Settings.transcript_max_turns` via `ACL_TRANSCRIPT_MAX_TURNS` (default 16, bounds 1–100, `_env_int`); documentar em `.env.example` | backend | S | — | não | P1 | `Settings.load()` sem env usa 16; valor fora de [1,100] é clampado |
| B2 | `kernel/memory/session_key.py`: nova `v1_memory_key(platform, user_id, channel_id, session_id) -> str` (G4, nunca `None`); `memory_session_key` legado inalterado | backend | S | — | não | P1 | sem `session_id` → `platform:user:channel`; com → `+ ":" + session_id`; `memory_session_key` byte-idêntico |
| B3 | `kernel/memory/transcript_store.py`: `TranscriptStore` (thread-safe, `RLock`) — `get(key)`, `append_pair(key, user_msg, assistant_msg, max_turns)`, `clear(key)` | backend | M | — | sim | P1 | janela deslizante mantém só os últimos `max_turns` pares; `get()` em chave ausente devolve `[]`; chamadas com `key=None` são no-op |
| B4 | `api/chat_pipeline.py` (novo): extrai de `api/routes.py` a lógica comum `build_messages → stream_response → (aggregate_sse \| StreamingResponse) → PipelineRecord` em `ChatPipelineOutcome`/`run_chat_pipeline(...)`; `api/routes.py`'s `chat()` passa a delegar a este helper | backend | L | — | sim | P1 | comportamento de `/chat` idêntico (T6 100% verde, mesmos asserts); `/chat` continua a tratar `/reload` fora do helper |
| D1 | `adapters/README.md`: documentar `reset_context` e natureza in-memory/não-durável do transcript store | docs | S | PO1 | não | P2 | secção "Contrato de segurança" ou nova nota menciona `reset_context` e limitação in-memory |
| T1 | `tests/test_channel_context_schema.py`: valida `ChannelContext`/`ChatRequestV1` (campo vendor rejeitado, `session_id` só-dígitos rejeitado, `session_id` opcional aceite) | testes | M | PO1 | não | P2 | 100% dos casos acima cobertos e verdes |
| T2 | `tests/test_v1_session_key.py`: cobre as 2 ramificações de G4 e isolamento entre plataformas/utilizadores distintos | testes | S | B2 | não | P2 | ≥4 casos (com/sem session_id × 2 combinações de isolamento) verdes |
| T3 | `tests/test_transcript_store.py`: janela deslizante, `clear()`, `get()` em chave ausente | testes | M | B3 | não | P2 | trunca corretamente ao exceder `max_turns`; `clear()` remove por completo |
| B5 | `api/routes_v1.py` (novo): `APIRouter(prefix="/v1")` — `GET /v1/health` sem auth; `POST /v1/chat` mapeia `context→channel/user_id`, aplica auth/rate-limit de `/chat`, trata `reset_context` (limpa pin+transcript **após** auth), ignora `payload.history`, injeta `transcript_store.get(v1_key)` como `conversation_history`, chama `run_chat_pipeline` (B4), grava par em sucesso `stream=false` | backend | L | PO1, B1, B2, B3, B4 | sim | P2 | `GET /v1/health` → 200; `POST /v1/chat` feliz → `ChatResponse` igual ao shape de `/chat`; `reset_context` limpa antes de processar; `history` do body nunca chega a `build_messages` |
| B6 | `app/state.py`: `AppServices.transcript_store: TranscriptStore = field(default_factory=TranscriptStore)` | backend | S | B3 | sim | P2 | testes existentes que constroem `AppServices(...)` sem `transcript_store` continuam a passar |
| B7 | `main.py`: `build_services()` instancia `TranscriptStore()` e injeta em `AppServices` | backend | S | B3, B6 | sim | P3 | app real (fora de testes) sobe com `transcript_store` funcional |
| B8 | `app/factory.py`: `app.include_router(api.routes_v1.router)` | backend | S | B5 | sim | P3 | `TestClient(create_app(...))` responde em `/v1/health` e `/v1/chat` |
| T4 | `tests/test_v1_health.py`: `GET /v1/health` → 200 mesmo sem `services` configurado (paridade com `/health`) | testes | S | B8 | não | P4 | verde |
| T5 | `tests/test_v1_chat.py`: fluxo feliz; `reset_context` limpa pin+transcript; transcript persiste entre 2 chamadas e é injetado na 2.ª; `history` do body é no-op; auth/rate-limit paridade com `/chat`; `session_id` só-dígitos → 422; `stream=true` não persiste transcript (SUP-1); `message="/reload"` em `/v1/chat` não dispara rebuild | testes | L | B5, B8, T1, T2, T3 | sim | P4 | todos os 8 casos (a–h, ver Estratégia de teste) verdes |
| T6 | Regressão: `tests/test_chat_json.py`, `test_chat_schema.py`, `test_health.py`, `test_internal_api.py`, `test_search_endpoint.py`, `test_session_key.py` sem alteração de asserts | testes | M | B4, B6, B7, B8 | sim | P4 | `pytest tests/ -k "not v1"` 100% verde, zero diffs nos ficheiros de teste legados |
| S1 | Checklist de segurança: 401 sem Bearer válido em `/v1/chat`; extra=forbid em `ChannelContext`/`ChatRequestV1`; `reset_context` não contorna auth; `TranscriptStore` isola por chave sem vazamento; `/v1/chat` não expõe `/reload` | seguranca | M | T5, T6 | sim | P5 | checklist sem achados críticos/altos abertos |

**Legenda:** **CP** = no caminho crítico. **Lote** = `P1`…`P5` para execução paralela por sub-agentes após dependências satisfeitas (dentro de um lote, nenhuma tarefa depende de outra do mesmo lote).

### Caminho crítico (cadeia bloqueante)

`PO1 ∥ B4 ∥ B3 → B5 → B8 → T5 ∥ T6 → S1`

(B3→B6→B7 é uma cadeia paralela de igual profundidade que também converge em T6, logo participa do caminho crítico.)

### Lotes paralelos

- **P1** (sem dependências prévias): PO1, B1, B2, B3, B4
- **P2** (pré-requisito: P1): B5, B6, D1, T1, T2, T3
- **P3** (pré-requisito: P1∪P2): B7, B8
- **P4** (pré-requisito: P1∪P2∪P3): T4, T5, T6
- **P5** (pré-requisito: P4): S1

### Dependências (grafo em texto)

- PO1 → bloqueia → B5, D1, T1
- B1 → bloqueia → B5
- B2 → bloqueia → B5, T2
- B3 → bloqueia → B5, B6, T3
- B4 → bloqueia → B5, T6
- B5 → bloqueia → B8, T5
- B6 → bloqueia → B7, T6
- B7 → bloqueia → T6
- B8 → bloqueia → T4, T5, T6
- T1, T2, T3 → bloqueiam → T5
- T5, T6 → bloqueiam → S1

---

## Definição de interfaces (contratos)

| Contrato | Consumidores (IDs) | Artefacto | Versionamento |
|----------|--------------------|-----------|-----------------|
| API v1 Kernel↔Orbit (`ChannelContext` + `ChatRequestV1` + `ChatResponse`) | PO1, B5, T1, T5, D1 (externo: Orbit) | `docs/API_SPEC.md` (secção "API v1") + `kernel/schemas/channel.py` + `kernel/schemas/chat.py::ChatRequestV1` | breaking → novo ADR + novo ID `contrato` |
| `run_chat_pipeline` (helper interno BE↔BE, `/chat` e `/v1/chat`) | B4, B5, T5, T6 | `api/chat_pipeline.py` | mudança de assinatura → nova revisão de B4/B5 no mesmo ciclo |

**Campos críticos (anti-desalinhamento):**

| Campo | Tipo | Produtor | Consumidor |
|-------|------|----------|------------|
| `context.platform` | `str` (1–64) | Cliente (Orbit) | B5 → mapeado para `channel` interno |
| `context.user_id` | `str` (1–256) | Cliente | B5 → mapeado para `user_id` interno |
| `context.channel_id` | `str` (1–256) | Cliente | B5 → entra na derivação da chave (G4/B2) |
| `context.session_id` | `str \| null`, opaco `[A-Za-z0-9_-]{8,128}` | Cliente (opcional) | B5 → derivação G4 (B2); ecoado em `metadata.session_id` (SUP-3) |
| `reset_context` | `bool`, default `false` | Cliente | B5 → limpa pin+transcript na chave v1 antes do turno |
| `history` (body v1) | `array` (aceite, ignorado) | Cliente | B5 → nunca repassado a `build_messages` (G7 no-op) |
| `ChatPipelineOutcome.answer` | `str \| None` | B4 | B5 → grava em `transcript_store.append_pair` só quando não-`None` (JSON, sucesso) |

---

## Estratégia de teste

| ID(s) | Tipo | Comando / ferramenta | Prova de conclusão |
|-------|------|-----------------------|----------------------|
| PO1, T1 | Unitário | `pytest tests/test_channel_context_schema.py` | `ValidationError` nos casos inválidos; aceite nos válidos |
| B2, T2 | Unitário | `pytest tests/test_v1_session_key.py` | chaves G4 corretas e isoladas por tupla (platform,user,channel) |
| B3, T3 | Unitário | `pytest tests/test_transcript_store.py` | janela deslizante e `clear()` corretos |
| B8, T4 | Integração (TestClient) | `pytest tests/test_v1_health.py` | 200 `{"status":"ok"}` |
| B5, T5 | Integração (TestClient + stubs, padrão de `test_chat_json.py`/`test_internal_api.py`) | `pytest tests/test_v1_chat.py` | 8 casos (a–h) verdes |
| B4, B6, B7, B8, T6 | Regressão (integração) | `pytest tests/test_chat_json.py tests/test_chat_schema.py tests/test_health.py tests/test_internal_api.py tests/test_search_endpoint.py tests/test_session_key.py` | 100% verde, zero diffs nos ficheiros de teste |
| S1 | Checklist manual + reexecução de T5/T6 | `pytest tests/` completo + inspeção de código (auth antes de reset; `extra=forbid`) | checklist assinado sem achados críticos |

**Ordem de execução de testes:** T1/T2/T3 (unitário) → T4 (integração simples) → T5 (integração completa v1) → T6 (regressão legado) → S1 (gate final, exige T5 e T6 verdes).

Casos T5 detalhados (a–h):
- **(a)** fluxo feliz com `context` completo → `ChatResponse` no shape de `/chat` (mesmos campos de `metadata`).
- **(b)** `reset_context=true` → pin e transcript da chave v1 limpos antes do `build_messages` (stub captura `conversation_history=[]` mesmo com transcript pré-existente).
- **(c)** duas chamadas com o mesmo `context` (sem `session_id`) → 2.ª chamada recebe o par da 1.ª em `conversation_history`.
- **(d)** `history` não-vazio no body → stub recebe `conversation_history` vindo **só** do transcript store, nunca do body.
- **(e)** com `ACL_REQUIRE_API_AUTH=true`: sem Bearer → 401; com Bearer de canal correto (`platform` como chave em `ACL_CHANNEL_API_KEYS`) → 200; acima do rate limit → 429.
- **(f)** `context.session_id` só-dígitos → 422.
- **(g)** `stream=true` seguido de nova chamada `stream=false` → 2.ª chamada não reflete a 1.ª (transcript vazio).
- **(h)** `message="/reload"` em `/v1/chat` → resposta normal do pipeline (sem chamar `search_engine.rebuild()`, verificável por stub/mock não invocado).

---

## Estratégia de validação (por ID)

| ID | Como provar "concluído" | Evidência exigida no [RESULTADO] |
|----|--------------------------|--------------------------------|
| PO1 | Schemas importáveis + `docs/API_SPEC.md` atualizado + T6 continua verde | diff de `kernel/schemas/channel.py`, `kernel/schemas/chat.py`, `docs/API_SPEC.md` |
| B1 | `Settings.load()` com/sem env produz valor esperado | trecho de teste ou execução manual (`python -c`) |
| B2 | T2 verde | output do pytest |
| B3 | T3 verde | output do pytest |
| B4 | T6 verde (regressão) | output do pytest + diff de `api/routes.py` reduzido a delegação |
| B5 | T5 verde | output do pytest |
| B6 | AppServices existentes instanciam sem erro | output do pytest (T6) |
| B7 | `python -c "import main"` sem exceção (sem infra real, só import) | log de execução |
| B8 | T4/T5 verdes | output do pytest |
| D1 | Revisão de texto (Markdown) | diff de `adapters/README.md` |
| T1–T6 | pytest verde | comando + resumo de output |
| S1 | Checklist preenchido, 0 itens críticos abertos | checklist assinado no [RESULTADO] |

---

## Briefings PDA (tarefas delegáveis)

### Briefing — ID PO1 (contrato)

**Estrutura do projeto:** monólito FastAPI. Schemas em `kernel/schemas/` (`chat.py`, `search.py`, `validators.py`). `ChatRequest`/`ChatResponse`/`HistoryItem`/`confidence_to_float` já existem em `kernel/schemas/chat.py`. Validadores partilhados (`validate_metadata`, `validate_session_id`) em `kernel/schemas/validators.py`.

**Objetivo imediato:** Criar `kernel/schemas/channel.py` com `ChannelContext` (`platform: str[1..64]`, `user_id: str[1..256]`, `channel_id: str[1..256]`, `session_id: str|None` com o mesmo padrão `^[A-Za-z0-9_-]{8,128}$` + `validate_session_id`), `extra="forbid"`. Adicionar `ChatRequestV1` em `kernel/schemas/chat.py` (`context: ChannelContext`, `message` idêntico ao legado, `discipline`, `history: list[HistoryItem]` aceite-mas-ignorado, `metadata`, `stream: bool = False`, `reset_context: bool = False`), `extra="forbid"`. Extrair a lógica de `strip_strings`/`opaque_session` repetida em `ChatRequest`/`SearchRequest` para `kernel/schemas/validators.py::strip_and_require()` e reutilizá-la nos 3 schemas (legado incluído) **sem** alterar o comportamento observável (mesmas mensagens de erro/422). Corrigir `docs/API_SPEC.md` (tabela de `POST /v1/chat`) para incluir `reset_context: boolean, opcional, default false — limpa transcript+pin da chave antes de processar (G3)`.

**Impedimentos:** Não alterar `ChatRequest`/`SearchRequest` de forma que mude o corpo das mensagens de erro 422 existentes (`tests/test_chat_schema.py`, `test_internal_api.py::test_session_id_digits_rejected/test_metadata_too_large_rejected` são SSOT do comportamento aceite). `docs/API_SPEC.md` é documento aprovado — só adicionar o campo em falta, não redesenhar a secção.

### Briefing — ID B3 (backend)

**Estrutura do projeto:** `kernel/memory/pinned_store.py` é o padrão de referência (dataclass + `threading.RLock`, sem dependências externas).

**Objetivo imediato:** Criar `kernel/memory/transcript_store.py` com `TranscriptStore`: `get(key: str | None) -> list[dict[str,str]]` (lista plana `{"role","content"}`, oldest-first, `[]` se chave ausente/`None`); `append_pair(key, user_message: str, assistant_message: str, max_turns: int) -> None` (ignora se `key`/mensagens vazias; mantém só os últimos `max_turns` pares = `2*max_turns` mensagens, descartando do início); `clear(key: str | None) -> None`. Thread-safe com `RLock`, mesmo estilo de `PinnedSessionStore`.

**Impedimentos:** Não introduzir dependência de `Settings` dentro da classe — `max_turns` é sempre passado pelo chamador (mesma filosofia de `PinnedSessionStore.set_pinned(..., max_turns)`), para manter a store agnóstica de configuração e testável isoladamente.

### Briefing — ID B4 (backend, caminho crítico)

**Estrutura do projeto:** `api/routes.py::chat()` (linhas ~160–339) contém hoje toda a lógica de `/chat`: `build_messages` → `PipelineRecord` (erro e sucesso) → `chat_provider.stream_response` → branch `stream`/JSON (`aggregate_sse`) → `ChatResponse`. `api/security.py` cuida de auth/rate-limit (não mexer). `kernel/inspect/recorder.py::PipelineRecord/get_recorder` já importado em `routes.py`.

**Objetivo imediato:** Criar `api/chat_pipeline.py` com uma função `run_chat_pipeline(request, services, *, request_id, message, channel, user_id, discipline, session_key, conversation_history, stream, request_metadata, response_session_id, pipeline_kind="chat") -> ChatPipelineOutcome` (dataclass com `built`, `answer: str|None`, `metadata: dict|None`, `streaming_response: StreamingResponse|None`, `chat_response: ChatResponse|None`) que encapsula exatamente a lógica hoje inline em `chat()` (exceto o branch `/reload`, que **fica** em `api/routes.py`, exclusivo do legado). Refatorar `api/routes.py::chat()` para: (1) manter auth/rate-limit/`/reload` como estão; (2) computar `pin_key = memory_session_key(...)` como hoje; (3) chamar `run_chat_pipeline(..., session_key=pin_key, conversation_history=[item.model_dump() for item in payload.history], response_session_id=payload.session_id)`; (4) `return outcome.streaming_response or outcome.chat_response`.

**Impedimentos:** Comportamento de `/chat` deve ser **byte-idêntico** ao atual — nenhum assert de `tests/test_chat_json.py`, `test_chat_schema.py`, `test_health.py`, `test_internal_api.py`, `test_search_endpoint.py`, `test_session_key.py` pode mudar. Esta é a tarefa de maior risco de regressão do plano; rodar a suíte completa antes de considerar concluída.

### Briefing — ID B5 (backend, caminho crítico)

**Estrutura do projeto:** Depende de PO1 (schemas), B1 (`Settings.transcript_max_turns`), B2 (`v1_memory_key`), B3 (`TranscriptStore`), B4 (`run_chat_pipeline`). `api/internal_routes.py` é o padrão de `APIRouter(prefix=...)` isolado num ficheiro próprio.

**Objetivo imediato:** Criar `api/routes_v1.py` com `router = APIRouter(prefix="/v1")`. `GET /v1/health` sem auth → `{"status":"ok"}`. `POST /v1/chat` (payload `ChatRequestV1`): (1) mapear `channel = payload.context.platform`, `user_id = payload.context.user_id`; (2) `allow_public_operation(request, "chat", channel=channel, user_id=user_id)` + `verify_channel_api_bearer(request, channel=channel)` — **nesta ordem, antes de qualquer leitura/limpeza de estado**; (3) `v1_key = v1_memory_key(payload.context.platform, payload.context.user_id, payload.context.channel_id, payload.context.session_id)`; (4) se `payload.reset_context`: `services.pinned_store.clear(v1_key)` e `services.transcript_store.clear(v1_key)`; (5) `history_in = services.transcript_store.get(v1_key)` (ignorar **sempre** `payload.history`); (6) `outcome = await run_chat_pipeline(request, services, request_id=_request_id(request), message=payload.message, channel=channel, user_id=user_id, discipline=payload.discipline, session_key=v1_key, conversation_history=history_in, stream=payload.stream, request_metadata=payload.metadata, response_session_id=payload.context.session_id)`; (7) se `outcome.chat_response is not None` (i.e., `stream=false`, sucesso): `services.transcript_store.append_pair(v1_key, payload.message, outcome.answer, services.context_manager.settings.transcript_max_turns)`; (8) `return outcome.streaming_response or outcome.chat_response`.

**Impedimentos:** Não implementar `/reload` nem qualquer atalho de `message` em `/v1/chat` (fora de escopo, API_SPEC explícito). Não repassar `payload.history` para `run_chat_pipeline` em nenhuma circunstância (G7). Ordem auth→reset é inegociável (S1 valida).

### Briefing — ID T1 (testes)

**Objetivo imediato:** `tests/test_channel_context_schema.py` — instanciar `ChannelContext`/`ChatRequestV1` com campo vendor (`jid`, `guild_id`) → `ValidationError`; `session_id="12345678"` → `ValidationError`; `session_id=None` → aceite; payload mínimo válido → aceite. Seguir o estilo de asserts de `tests/test_chat_schema.py` (checar `status_code`/mensagem quando via HTTP, ou `pydantic.ValidationError` quando unitário puro).

### Briefing — ID T3 (testes)

**Objetivo imediato:** `tests/test_transcript_store.py` — `append_pair` sucessivo além de `max_turns` mantém só os últimos N pares (ordem preservada, mais antigos descartados); `get()` em chave nunca usada devolve `[]`; `clear()` remove por completo (get subsequente devolve `[]`).

### Briefing — ID T5 (testes, caminho crítico)

**Estrutura do projeto:** Seguir o padrão de stubs de `tests/test_chat_json.py` (`ContextManagerStub.build_messages` capturando kwargs) e `tests/test_internal_api.py` (`AppServices` completo com stubs, `monkeypatch` de env para auth).

**Objetivo imediato:** `tests/test_v1_chat.py` cobrindo os 8 casos (a–h) descritos na Estratégia de teste deste plano. Usar um `ContextManagerStub.build_messages` que **grava** os kwargs recebidos (especialmente `conversation_history`) num atributo inspecionável pelo teste, para provar (b)/(c)/(d) sem depender de LLM real.

**Impedimentos:** Não usar rede/MySQL/LLM real — só stubs, como todos os testes existentes.

### Briefing — ID T6 (testes)

**Objetivo imediato:** Rodar `pytest tests/test_chat_json.py tests/test_chat_schema.py tests/test_health.py tests/test_internal_api.py tests/test_search_endpoint.py tests/test_session_key.py` após B4/B6/B7/B8 e confirmar zero regressões. Se algum assert precisar mudar, é **sinal de regressão real** — reportar como bloqueio (`replanejar`), não editar o teste para "passar".

### Briefing — ID S1 (segurança)

**Objetivo imediato:** Checklist manual + reexecução de testes: (i) `/v1/chat` sem Bearer válido quando `ACL_REQUIRE_API_AUTH=true` → 401; (ii) `ChannelContext`/`ChatRequestV1` com campo extra → 422 (`extra=forbid`); (iii) ler o código de B5 e confirmar que `reset_context` só executa após as chamadas de auth; (iv) rodar/gerar um teste ad-hoc que confirma que duas chaves distintas (`platform`/`user_id`/`channel_id` diferentes) nunca leem o transcript uma da outra; (v) confirmar por leitura de código que `api/routes_v1.py` não contém nenhum branch equivalente a `/reload`.

---

## Riscos, bloqueios e replaneamento

| Risco | Probabilidade | Impacto | Resposta (ID ou DECISÃO) |
|-------|----------------|---------|----------------------------|
| Extração do pipeline (B4) introduz diferença sutil em `/chat` (ex.: ordem de campos em `metadata`, contagem de `recorder.incr`) | média | alto (regressão em produção) | T6 obrigatório antes de B5 ser considerado "pronto para merge"; `replanejar` se T6 falhar após 1 correção |
| `reset_context` mal posicionado (antes da auth) vira vetor de DoS | baixa | alto | S1 bloqueia release; critério de aceite de B5 já exige ordem auth→reset |
| Ambiguidade de "sucesso" (G7) leva a inconsistência entre implementações futuras | baixa | médio | SUP-4 documentada e testada (T5-a/h); qualquer divergência futura exige nova decisão grill-me, não interpretação ad-hoc |
| Transcript store cresce sem cap de caracteres por entrada | baixa (uso interno, não pedido) | baixo | aceite como trade-off nesta missão (ver Análise de contexto → Performance); se virar problema real, novo ID futuro `B-transcript-char-cap` |
| `docs/API_SPEC.md` fica dessincronizado se PO1 não for a primeira tarefa concluída | baixa | médio | PO1 é pré-requisito explícito de B5 e D1 no grafo |

**Gatilhos de `replanejar` para o orquestrador:**

- T6 falhar mais de uma vez após correção (regressão real em `/chat`, não falha de execução do agente).
- S1 encontrar achado crítico/alto não coberto pelas mitigações já mapeadas (ex.: `reset_context` acessível sem auth em algum caminho não previsto).
- Orbit (fora deste repo) reportar incompatibilidade de contrato não coberta por PO1/API_SPEC — exige novo ADR, não ajuste silencioso.

---

## Ordem de execução mandatória

1. **Lote P1** (paralelo): PO1, B1, B2, B3, B4 — nenhuma depende de outra do lote.
2. **Lote P2** (paralelo, após P1): B5, B6, D1, T1, T2, T3.
3. **Lote P3** (paralelo, após P1∪P2): B7, B8.
4. **Lote P4** (paralelo, após P1∪P2∪P3): T4, T5, T6.
5. **Lote P5**: S1 (gate final — exige T5 **e** T6 verdes).

---

## Handoff ao Orquestrador Raiz

- **Próximo comando lógico:** Fase 2 do MegaBrain inicia pelo Lote P1 (PO1, B1, B2, B3, B4 em paralelo por sub-agentes distintos, sem conflito de ficheiro).
- **Persistência:** registrar em `.agent_history.md` o delta deste plano (feature `kernel-orbit-integration`, branch `feature/kernel-orbit-integration`) e manter os IDs em aberto até P5 concluir.
- **Não iniciar implementação** sem aceitar este documento como `[PLANO]` SSOT. Nenhum código foi escrito nesta missão (Planner não implementa).
- **Nota de formato:** este plano não inclui `plan.ir.yaml` — o skill Planner carregado nesta sessão define formato de saída **Markdown puro** (sem Capability IR/YAML); o precedente do repositório (`memory/true-kernel/plan.md`) segue o mesmo padrão.
