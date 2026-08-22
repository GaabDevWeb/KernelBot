# REPORT — Ops Center P3 (Laboratório)

Data: 2026-07-29  
Branch: `feature/kernel-ops-center`

## Entrega

| Ecrã | Rota | Função |
|------|------|--------|
| Playground | `GET/POST /ops/lab/playground` | Pergunta + model/temp/top_k/max_tokens → `run_chat_pipeline` |
| Replay | `GET /ops/lab/replay` | Bridge: form POST → `POST /traces/{id}/replay` |
| Diff | `GET /ops/lab/diff` | Side-by-side A/B via `text_diff` (+ link UI traces) |
| Benchmark | `GET/POST /ops/lab/benchmark` | Mesma pergunta em N modelos (CSV env) |

## Rotas / ficheiros

- `api/lab_routes.py` — rotas Lab + helpers
- `templates/ops/lab/{playground,replay,diff,benchmark}.html`
- `app/factory.py` — `include_router(lab_router)`
- `api/ops_routes.py` — removidos placeholders P3 + badges `phase: P3` no nav
- Overrides leves (reuso, sem duplicar pipeline):
  - `kernel/providers/chat_provider.py` — `model` / `temperature` / `max_tokens`
  - `kernel/orchestrator/context.py` — `top_k` opcional em `build_messages`
  - `api/chat_pipeline.py` — propaga overrides

## Como o Benchmark funciona

1. Modelos vêm de `ACL_LAB_BENCHMARK_MODELS` (CSV, até 5). Fallback: `settings.models[:3]` (OpenRouter) ou `cursor_model` (Cursor).
2. Para cada modelo, corre `run_chat_pipeline(..., stream=False, model=…)` sequencialmente.
3. Tabela: status, latência (`trace_performance.total_ms` ou wall clock), `tokens_used` (fragmentos de stream), link do trace.
4. Abaixo: resposta completa por modelo.

## Auth

Todas as páginas usam `require_ops_cookie` (mesmo cookie do Ops Center).

## Testes

```bash
PYTHONPATH=. .venv/bin/pytest tests/test_lab_ops.py -q
```

Cobre: redirect sem cookie; GET 200 autenticado; playground/benchmark com `ChatProviderStub`.

## Gaps / limitações honestas

- **Cursor SDK**: `temperature` / `max_tokens` não aplicam (só `model`); OpenRouter sim.
- **Tokens**: `tokens_used` continua a ser contagem de fragmentos SSE, não tokens do provider.
- **Replay**: Lab não re-implementa lógica — faz POST no endpoint traces existente (UI traces).
- **Diff de prompt**: mostra meta do snapshot (`prompt` forensics), não o texto completo do system prompt salvo (depende de `ACL_TRACE_STORE_PROMPTS` / snapshot).
- **Benchmark sequencial**: N modelos = N latências acumuladas no request HTTP (pode timeout em modelos lentos).
- **Sem serviços**: se `app.state.services` for `None`, páginas GET degradam (models vazios); POST devolve 503.

## Env

```env
# ACL_LAB_BENCHMARK_MODELS=modelA,modelB,modelC
```

Documentado em `.env.example`.
