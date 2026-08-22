# Relatório — Operational Trace Fatia B

| Campo | Valor |
|-------|-------|
| Data | 2026-07-28 |
| Branch | `feature/orbit-kernel-tracing` |
| Testes TRACE | `test_trace_store` + `test_trace_api` + `test_trace_fatia_b` → **6 passed** (suite completa Kernel também verde) |

## Entregue

| Capacidade | Como usar |
|------------|-----------|
| Dashboard | `/traces/dashboard` — totais, erros, 24h, duração média |
| Filtros | `/traces?phone=&group=&text=&since=&until=&errors=1&q=` |
| Detalhe | Conversa + RAG + timeline com Δms |
| ZIP 1 trace | `/traces/{id}/export.zip` |
| ZIP filtrados/todos/período | `/traces/export.zip?scope=filtered\|all\|period` |

ZIP contém: `traces.json`, `events.json`, `messages.json`, `orbit.log`, `kernel.log`, `metadata.json`.

## Como rastrear

1. Login em `/traces/login` com `ACL_INTERNAL_BEARER_TOKEN`
2. Enviar mensagem WhatsApp (`@orbit`)
3. Abrir lista/dashboard → detalhe do `trace_id`
4. Exportar ZIP no detalhe ou na lista

## Limitações

- Previews de mensagem/resposta só em eventos novos (após fatia B)
- Filtros usam `LIKE` em SQLite (adequado a volume operacional local)
- Polish visual Jinja (sem React)

## Próximos passos (opcional)

- Retenção / purge automático
- Scores BM25 por candidato na vista RAG (hoje: sources + reason/confidence)
- Alertas em ERROR
