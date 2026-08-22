# Context Architecture — contexto em camadas do Kernel

| Campo | Valor |
|-------|-------|
| Data | 2026-08-08 |
| Estado | implementado |
| Módulos | `kernel/context/`, `kernel/orchestrator/context.py`, `api/chat_pipeline.py` |

O Kernel deixa de ser "um chatbot com mais prompt" e passa a montar um
**contexto estruturado em camadas**: o LLM interpreta, raciocina e comunica;
o Kernel é responsável por tempo, datas, eventos, estado, memória, fontes,
políticas e observabilidade.

## Fluxo

Com `ACL_CONTEXT_ROUTER=1` (default **off** = legado always-on), o
`ContextRouter` escolhe o perfil `FAST|NORMAL|DEEP` e só então as camadas
necessárias são montadas. Desenho: `optimization/routing.md`.

```text
                    ┌────────────────────┐
                    │   Request atual    │  POST /v1/chat (ChannelContext)
                    └─────────┬──────────┘
                              │
                    ┌─────────▼──────────┐
                    │  ContextRouter *   │  * se ACL_CONTEXT_ROUTER=1
                    │  FAST|NORMAL|DEEP  │  (senão: camadas always-on)
                    └─────────┬──────────┘
                              │
            ┌─────────────────┼─────────────────┐
            ↓                 ↓                 ↓
      Identity Context   Temporal Context   Channel Context
      (identity.txt +    (relógio do        (platform/user_id/
       context/*.md †)    servidor + TZ)     channel_id → memória)
            │                 │                 │
            └─────────────────┼─────────────────┘
                              ↓
                    ┌─────────────────┐
                    │ Calendar Context│  † Calendar / institucional / RAG /
                    │ (deltas prontos)│    transcript sob demanda por perfil
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │   Transcript    │  turns adaptativos por perfil
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │      RAG        │  BM25 skip: FAST, calendar-only, …
                    └────────┬────────┘
                             ↓
                    ┌─────────────────┐
                    │ ContextBuilder  │  system prompt em ordem canônica
                    └────────┬────────┘
                             ↓
                           LLM (ChatProvider)
```

## Componentes

| Componente | Ficheiro | Papel |
|------------|----------|-------|
| `TemporalContextProvider` | `kernel/context/temporal.py` | "Agora" do servidor no timezone configurado; nunca confia no relógio do cliente |
| `CalendarProvider` | `kernel/context/calendar_provider.py` | Eventos acadêmicos estruturados; consultas (próxima avaliação, semana, ontem) e **deltas de dias calculados no backend** |
| `InstitutionalContextProvider` | `kernel/context/institutional.py` | Lê `context/*.md` preenchidos pelo operador; ignora placeholders |
| `detect_temporal_intent` | `kernel/context/intent.py` | Classifica `time_fact` / `calendar_fact` sem LLM |
| `ContextBuilder` | `kernel/context/builder.py` | Resolve camadas e monta o system prompt numa ordem única |
| Identidade | `kernel/policies/systemPrompt/identity.txt` | Contrato comportamental: assistente acadêmico contextual, política de fontes, ausência e conflito |
| Template humano | `context/context.md` | Documentação operacional (NÃO é carregado no prompt) |

## Ordem canônica do system prompt

1. `system_prompt.txt` (base — identidade Kernel, tom)
2. `identity.txt` (assistente acadêmico da turma, prioridade de fontes)
3. Contexto institucional (`context/identity.md`, `faculty.md`, `professors.md`, `disciplines.md`, `rules.md`)
4. Contexto temporal (data, hora, dia da semana, timezone, timestamp)
5. Agenda acadêmica (eventos com deltas calculados + regras anti-invenção)
6. Catálogo de aulas (existente)
7. Sticky/pin (existente)
8. Contrato de grounding (existente, com exceção para blocos estruturados)
9. Trechos RAG `[Fonte: …]` (existente)

Depois: histórico truncado (transcript) → mensagem atual do utilizador.

## Prioridade de fontes

Declarada em `identity.txt` e reforçada nos blocos:

1. **Dados estruturados do sistema** (temporal + agenda oficial)
2. **Contexto institucional oficial** (`context/*.md`)
3. **RAG / documentos oficiais** (`[Fonte: …]`)
4. **Transcript da conversa**
5. **Conhecimento geral do modelo** (rotulado, quando o grounding permitir)

Em conflito (ex.: transcript diz uma data, agenda diz outra), o bloco da
agenda instrui o LLM a usar a fonte oficial e a **mencionar a divergência**.

## Consciência temporal

- O tempo vem **sempre do servidor**, convertido para `KERNEL_TIMEZONE`
  (IANA; default `America/Sao_Paulo`; validado no boot).
- Cálculos críticos ("quantos dias faltam") são feitos pelo backend: o
  `CalendarProvider` injeta linhas como `faltam 38 dias`, `é AMANHÃ`,
  `foi ONTEM`. O prompt instrui o LLM a **não recalcular**.
- Intents:
  - `time_fact` ("que dia é hoje?", "que horas são?") → respondível só com o
    contexto temporal → **BM25 é dispensado** (`rag_skipped=true`,
    `reason=temporal_fact`). Comandos de escopo (`/doc`, `/python`…) nunca
    são ignorados: com escopo explícito o RAG roda normalmente.
  - `calendar_fact` ("quando é a próxima prova?", "quantos dias faltam?") →
    agenda + temporal; com router on, RAG pode ser skipado em calendar-only
    puro; pedidos híbridos (material + agenda) mantêm RAG.

## Integração com RAG e transcript

Nada do pipeline existente foi removido: pin, catálogo, grounding, BM25 e
transcript funcionam como antes. As camadas novas são **aditivas** e opt-in
(`ContextManager(context_builder=None)` reproduz o comportamento anterior —
coberto por teste). Com `ACL_CONTEXT_ROUTER=1`, institutional/calendar/RAG/
transcript passam a ser sob demanda por perfil (ver `optimization/routing.md`).
Os contratos de grounding ganharam uma exceção explícita: blocos estruturados
do sistema são fonte oficial e não exigem trechos `[Fonte: …]` nem aviso de lacuna.

## Configuração

| Env | Default | Descrição |
|-----|---------|-----------|
| `KERNEL_TIMEZONE` | `America/Sao_Paulo` | Timezone IANA do servidor |
| `KERNEL_CONTEXT_DIR` | `<repo>/context` | Diretório dos `.md` institucionais |
| `KERNEL_CALENDAR_PATH` | `<KERNEL_CONTEXT_DIR>/calendar.json` | Agenda acadêmica |
| `ACL_CONTEXT_ROUTER` | off | `1` activa ContextRouter FAST\|NORMAL\|DEEP |

`calendar.json` é recarregado automaticamente quando o mtime muda.

## Observabilidade (traces + painel)

Novos stages no Flight Recorder, correlacionados por `X-Trace-Id`:

```text
Trace
 ├── REQUEST_RECEIVED
 ├── TRANSCRIPT_LOADED        (transcript usado)
 ├── PIN_LOADED
 ├── TEMPORAL_CONTEXT         (date, time, weekday, timezone, intent, rag_skipped)
 ├── CALENDAR_LOOKUP          (events_used com days_delta calculado)
 ├── RAG_STARTED / RAG_FINISHED  (sources; vazio quando dispensado)
 ├── PROMPT_BUILT
 ├── LLM_STARTED / LLM_FINISHED
 ├── RESPONSE_GENERATED
 └── RESPONSE_RETURNED
```

O snapshot do trace ganha a secção `prompt.context` (identity ativa, ficheiros
institucionais carregados, temporal, intent, eventos usados, fontes RAG,
turnos de transcript). O painel `/traces/{id}` mostra o painel
**"Contexto (camadas)"** com Current Time, Timezone, Calendar Events Used,
Transcript Used e RAG Sources Used — apenas observabilidade, sem alterar o
comportamento do Kernel. Não são registados segredos.

## Testes

`tests/test_context_temporal.py`, `test_context_calendar.py`,
`test_context_intent.py`, `test_context_builder.py`, `test_context_trace.py`
cobrem: tempo ("que dia é hoje?", "que horas são?"), datas ("quantos dias
faltam?" com delta calculado), eventos ("qual é a próxima prova?"),
transcript+tempo, RAG+tempo (híbrido), ausência (não inventar) e conflito
(agenda oficial > transcript), além da compatibilidade sem builder.
