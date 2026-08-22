# Arquitetura — Central de Operações (Kernel Ops)

| Campo | Valor |
|-------|-------|
| Data | 2026-07-29 |
| Branch | `feature/kernel-ops-center` |
| Stack | FastAPI + Jinja2 + SQLite + SVG (sem React/SPA) |

## Princípio

Cada ecrã deve ajudar a responder: **o quê → porquê → reproduzir → corrigir**.

## Camadas

```text
Browser (Jinja)
    │  cookie trace_auth (= ACL_INTERNAL_BEARER_TOKEN)
    ▼
api/ops_routes.py  +  api/traces_routes.py
    │
    ├─ kernel/ops/*     (charts, log_ring, runtime)
    ├─ kernel/trace/*   (store SQLite, bus, forensics, replay)
    └─ sample_system_metrics (stdlib resource/shutil)
```

## Rotas P0

| Rota | Função |
|------|--------|
| `GET/POST /ops/login` | Auth cookie |
| `GET /ops/dashboard` | Dashboard executivo + SVG |
| `GET /ops/traces` | Redirect → `/traces` |
| `GET /ops/logs` | Ring buffer + fallback erros |
| `GET /ops/system` | CPU/RAM/disco/uptime/fila (poll 5s) |
| `GET /ops/metrics` | P50/P95/P99, taxa erro, MPM |
| `GET /ops/knowledge/*` … | Placeholders P1–P4 |
| `/traces/*` | Detalhe, timeline, replay, diff, ZIP (existente) |

Estáticos: `/ops-static/*`, `/traces-static/*`.

## Banco (existente + métricas)

Sem schema novo no P0. Reutiliza:

- `traces`, `trace_events`, `trace_snapshots`
- Agregações: `metrics()`, `hourly_series()`
- Logs: ring em memória (`kernel/ops/log_ring.py`), não persistente

## Navegação

Sidebar única em `templates/ops/_sidebar.html` cobre o menu alvo completo.
Itens P1–P4 mostram badge de fase e página placeholder.

## Performance

- Consultas SQLite indexadas + limites
- Gráficos SVG gerados no servidor (0 JS chart libs)
- Polling de sistema só na página Sistema
- Log ring maxlen 2000
- Painel não entra no hot path de `/v1/chat`
