# REPORT — Kernel Ops Center (P0)

Data: 2026-07-29  
Branch: `feature/kernel-ops-center`  
Modo frontend-pro: **Build** (sem imagem anexada; anti-slop: paleta slate/cyan operacional, sem cream/terracotta)

## Entregáveis

### 1. Arquitetura
Ver `docs/adr/0004-ops-center-jinja.md` e `docs/prd/2026-07-29-ops-center.md`.

### 2. Estrutura de rotas
- Entrada: `http://127.0.0.1:8001/ops/login`
- Dashboard: `/ops/dashboard`
- Operações: `/ops/traces`, `/ops/logs`, `/ops/system`, `/ops/metrics`
- Menu completo com placeholders P1–P4 sob `/ops/knowledge|users|lab|adapters|settings/*`
- Traces detalhados mantidos em `/traces/{id}` (timeline, RAG, prompt, replay, diff, export)

### 3. Estrutura de banco
Sem migração nova. Extensão de leitura:
- `TraceMetrics`: +`p50_ms`, `timeouts_24h`, `active_users_24h`
- `hourly_series()` → buckets para SVG

### 4. Telas implementadas (P0)
| Ecrã | Estado |
|------|--------|
| Login Ops | OK |
| Dashboard executivo + 3 gráficos SVG | OK |
| Traces (bridge + UI existente) | OK |
| Logs (filtros serviço/nível/texto) | OK |
| Sistema (poll 5s) | OK |
| Métricas | OK |
| Placeholders Conhecimento/Users/Lab/Adapters/Config | Shell OK |

### 5. Fluxos de navegação

```text
/ops/login → /ops/dashboard
                ├─ Operações → Traces/Logs/Sistema/Métricas
                ├─ Conhecimento → (P1)
                ├─ Usuários → (P2)
                ├─ Laboratório → (P3; Replay/Diff já em /traces/{id})
                ├─ Adapters → (P4)
                └─ Configurações → (P4)
```

### 6. Relatório de performance
- Sem React/Next/Chart.js
- SVG inline O(n) horas (n≤168)
- Sistema: 1 GET /5s só nessa página
- Hot path chat/RAG/adapters: inalterado
- Testes: `PYTHONPATH=. .venv/bin/pytest tests/test_ops_center.py tests/test_trace_store.py` → 5 passed

### 7. Recursos futuros (ordem)
1. **P1** RAG Explorer + Documentos + Busca + Reindex (API knowledge existente)
2. **P2** Sessões/Conversas a partir de transcript_store + bloqueios
3. **P3** Playground/Benchmark; unificar Replay/Diff no Lab
4. **P4** Health WhatsApp/Discord via adapter status; edição segura de modelos/prompts
5. Persistência opcional de logs (SQLite ring) e export CSV/JSON por módulo
6. Redact UI audit (já há redact em trace data)

### 8. Critério de sucesso (P0 vs total)

| # | Critério | P0 |
|---|----------|----|
| 1 | Diagnosticar resposta | Parcial (traces existentes) |
| 2 | Gargalos performance | Sim (dashboard/métricas/sistema) |
| 3 | Debug RAG sem terminal | Não (P1) |
| 4 | Inspecionar conversa | Parcial (trace conversation view) |
| 5 | Reproduzir execução | Sim (replay em traces) |
| 6 | Comparar versões | Parcial (diff traces) |
| 7 | Monitorar adapters | Shell (P4) |
| 8 | Exportar dados | Traces ZIP (outros em P1+) |
| 9 | Operar só pelo painel | Parcial (P0 ops) |
| 10 | Multi-canal | Nav preparada |

## Como usar

1. Kernel a correr com `ACL_INTERNAL_BEARER_TOKEN`
2. Abrir `/ops/login`, colar o token
3. Dashboard → Operações

## Nota

Unificação Orbit→Kernel (Q1 A/D) **não** faz parte desta fatia; continua bloqueada à parte.
