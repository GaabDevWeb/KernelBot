# ADR-0003: Trace store SQLite no Kernel + painel /traces

| Campo | Valor |
|-------|-------|
| Data | 2026-07-28 |
| Status | accepted |
| Deciders | MegaBrain + missão tracing |

## Contexto

Precisamos de correlação ponta a ponta Orbit↔Kernel para depurar conversas. Restrições: monólito, sem ELK/Kafka/Redis obrigatório, UI simples (Jinja), sem login multi-user.

## Decisão

1. Hospedar **SQLite de traces** e **painel** no processo FastAPI do Kernel.
2. Orbit emite eventos via `POST /internal/traces/events` (Bearer `ACL_INTERNAL_BEARER_TOKEN`); nunca abre o SQLite.
3. Propagar identidade com header `X-Trace-Id` (não no schema de negócio de `/v1/chat`).
4. Escrita **assíncrona** (`asyncio.Queue` + worker); tracing best-effort.
5. Auth do painel: cookie HttpOnly após `POST /traces/login` validando o mesmo token interno.
6. Path default: `data/traces.sqlite3` (`ACL_TRACE_DB_PATH`).
7. Fatia A (S2): infra + eventos Kernel + Orbit mínimo + lista/detalhe/timeline; ZIP/métricas/filtros avançados adiados.

## Alternativas consideradas

### A — Serviço `trace-panel` separado

Mais isolamento; mais ops. Rejeitado nesta fase.

### B — SQLite partilhado em ficheiro entre Orbit e Kernel

Locks e paths frágeis. Rejeitado.

### C — Só expandir ring buffer `/internal`

Não persiste nem une Orbit. Insuficiente.

## Consequências

### Positivas

- Um processo, um DB, auth reutilizada
- Latência de chat preservada (async)

### Negativas

- Cookie = token interno (risco se Kernel exposto publicamente)
- Melhor-esforço: eventos podem atrasar/perder-se sob carga extrema (ERROR priorizado)

## Referências

- PRD: `docs/prd/2026-07-28-operational-trace.md`
