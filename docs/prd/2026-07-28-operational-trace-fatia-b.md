# PRD — Operational Trace Panel (Fatia B)

| Campo | Valor |
|-------|-------|
| Data | 2026-07-28 |
| Status | approved (pedido utilizador «fatia B inteira») |
| Branch | `feature/orbit-kernel-tracing` |
| Depende | Fatia A (S2) entregue |

## Escopo (Fases 5–8 do brief original)

| ID | Descrição |
|----|-----------|
| RF-B01 | Dashboard: total traces, erros, tempo médio resposta, traces 24h |
| RF-B02 | Lista com colunas horário/trace_id/origem/utilizador/duração/status |
| RF-B03 | Filtros: trace_id, telefone, grupo, texto, período |
| RF-B04 | Detalhe: timeline com duração por etapa |
| RF-B05 | Vista RAG: query, sources, scores/confidence/reason (dos eventos) |
| RF-B06 | Vista conversa: mensagem, resposta, canal/grupo/user, timestamps ms |
| RF-B07 | Export ZIP: trace específico, período, ou todos |
| RF-B08 | ZIP contém traces.json, events.json, messages.json, orbit.log, kernel.log, metadata.json |
| RF-B09 | Polish visual Jinja (sem React/SPA) |

## Fora de escopo

Multi-tenant, login complexo, ELK/Grafana, observabilidade corporativa.
