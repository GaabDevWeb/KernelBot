# KERNEL_EVOLUTION_PLAN

| Campo | Valor |
|-------|-------|
| Data | 2026-07-26 |
| Base | AUDIT_REVIEW + código |

## Críticas

### CR-1 — Referência `_search_kernel` (chat quebrado)

| | |
|--|--|
| Problema | `ContextManager` chamava atributo inexistente |
| Impacto | `/chat` → AttributeError; adapters inutilizáveis |
| Risco | Alto se não corrigido |
| Esforço | Baixo |
| Benefício | Restaura pipeline pretendido |
| Estado | **Corrigido** nesta branch (`_search_engine.search_candidates`) |

### CR-2 — Sem `request_id` / recorder

| | |
|--|--|
| Problema | Impossível correlacionar logs ↔ turno |
| Impacto | Bloqueia API interna útil |
| Risco | Médio (ops cego) |
| Esforço | Médio |
| Benefício | Observabilidade real |
| Estado | **Implementado** (middleware + PipelineRecorder) |

### CR-3 — Fail-open de disciplina inválida

| | |
|--|--|
| Problema | Filtro inválido vira busca global |
| Impacto | Pode violar isolamento esperado por canal/LMS |
| Risco | Alto em multi-tenant futuro |
| Esforço | Baixo–médio |
| Benefício | Contrato de escopo previsível |
| Estado | Documentado — **não alterado** (mudaria comportamento) |

## Importantes

### IM-1 — Rate limit process-local / proxy IP

| | |
|--|--|
| Problema | Janela deslizante in-memory; IP do socket |
| Impacto | Limite frágil em réplicas e atrás de Nginx |
| Risco | Médio |
| Esforço | Médio (TrustedProxy / Redis opcional) |
| Benefício | Proteção real em produção |

### IM-2 — Tokens/custo reais do provider

| | |
|--|--|
| Problema | `tokens_used` ≠ tokens OpenRouter/Cursor |
| Impacto | Métricas e billing errados |
| Risco | Médio |
| Esforço | Médio |
| Benefício | FinOps + SLO |

### IM-3 — Readiness (`/health` estático)

| | |
|--|--|
| Problema | Liveness ≠ ready |
| Impacto | Deploy verde com índice vazio |
| Risco | Médio |
| Esforço | Baixo |
| Benefício | Orquestração correcta |
| Estado | Parcial — `GET /internal/health/deep` (Bearer) |

### IM-4 — Acoplamento routes ↔ domínio

| | |
|--|--|
| Problema | `api/routes.py` orquestra demasiado |
| Impacto | Difícil testar e evoluir adapters |
| Risco | Médio |
| Esforço | Médio (application service) |
| Benefício | Desacoplamento |

## Desejáveis

### DE-1 — Remover/arquivar `watcher.py` morto

| | |
|--|--|
| Problema | Import legado `engine.search` |
| Impacto | Confusão de onboarding |
| Risco | Baixo |
| Esforço | Baixo |
| Benefício | Clareza |

### DE-2 — Strip modelos OpenRouter + config via env

| | |
|--|--|
| Problema | Lista hardcoded + espaço trailing |
| Impacto | Falhas silenciosas de modelo |
| Risco | Baixo–médio |
| Esforço | Baixo |
| Benefício | Operabilidade |

### DE-3 — Persistência de pin / histórico server-side

| | |
|--|--|
| Problema | Memória some com restart/multi-worker |
| Impacto | WhatsApp/Telegram precisam sticky frágil |
| Risco | Médio se feito cedo demais |
| Esforço | Alto |
| Benefício | Canais stateful |

### DE-4 — OpenTelemetry / Prometheus

| | |
|--|--|
| Problema | Sem export padrão |
| Impacto | Sem dashboards/alertas |
| Risco | Baixo |
| Esforço | Médio |
| Benefício | Ops enterprise |

## Limitações para adapters futuros

| Canal | Bloqueio actual |
|-------|-----------------|
| WhatsApp / Telegram | Precisam mapear `user_id`↔`session_id`; pin não sobrevive multi-instância |
| Discord | Rate limit por IP do gateway pode ser partilhado |
| Moodle / LMS | Fail-open de disciplina perigoso; falta auth por turma |
| Mobile | SSE opt-in OK; falta request_id era um gap (agora header) |

## Acoplamentos / complexidade

- `ContextManager` concentra escopo+RAG+prompt+pin (God object relativo).
- Sem ciclos de import graves detectados.
- Duplicação leve: validação history Pydantic vs `_normalize_conversation_history` órfão.
- Código morto: `watcher`, `_hard_stop_result` sem call sites no path vivo.
