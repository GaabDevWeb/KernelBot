# Relatório — Flight Recorder (Fatia C)

| Campo | Valor |
|-------|-------|
| Data | 2026-07-28 |
| Branch | `feature/orbit-kernel-tracing` |
| Testes | **51 passed** (`pytest tests/`) |

## Objectivo

Tornar cada mensagem WhatsApp auditável e reproduzível (Flight Recorder), sem stack corporativa.

## O que já existia (A+B)

X-Trace-Id, eventos Orbit/Kernel mínimos, SQLite async, login cookie, lista/filtros, dashboard básico, ZIP legado, RAG/conversa parciais.

## Novidades Fatia C

| Capacidade | Detalhe |
|------------|---------|
| Config | `ACL_TRACE_ENABLED`, `ACL_TRACE_RETENTION_DAYS`, `ACL_TRACE_STORE_PROMPTS` |
| `PROMPT_BUILT` | Evento + snapshot de system/transcript/pin/messages |
| Forensics | `trace_snapshots`: conversation, rag, prompt, tokens, performance, system |
| Performance | rag/bm25, prompt_build, llm, total (ms) |
| Tokens | estimativa chars/4 (+ provider se existir) |
| Dashboard | P95, P99, hoje, última hora, erros/hora |
| Replay | `POST /traces/{id}/replay` → novo trace + diff |
| Diff | `GET /traces/{id}/diff?vs=` |
| ZIP v2 | `trace.json`, `conversation.json`, `events.json`, `performance.json`, `rag.json`, `prompt.json`, `tokens.json`, `system_metrics.json`, logs, metadata |
| Retenção | purge no boot (`ACL_TRACE_RETENTION_DAYS`, default 30) |
| Health | sample RSS/CPU/disco no snapshot |

## Como usar

1. Login: `http://127.0.0.1:8001/traces/login`
2. Dashboard / lista / detalhe
3. No detalhe: **Exportar ZIP** ou **Replay**
4. Diff visual na página de replay

## Critérios de sucesso (mapa)

1–6,9–10: painel + forensics + ZIP  
7–8: Replay + Diff  

## Limitações

- BM25 ms ≈ rag_total (não instrumentado à parte no SearchEngine)
- Tokens frequentemente estimados
- System health sem psutil (stdlib)
- Capturas de ecrã automáticas: browser MCP indisponível neste ambiente
- Orbit latency stages (parse/WA send) vêm dos eventos Orbit; não há agregador dedicado além da timeline

## Próximos passos (opcional)

- Instrumentar BM25 vs assemble no ContextManager
- Tokens reais OpenRouter quando o stream os expor
- Capturas frontend-pro quando Puppeteer estiver OK

## Fecho

- Retenção: boot + loop horário no TraceBus (`ACL_TRACE_RETENTION_DAYS`)
- Testes Kernel **51** / Orbit **63** verdes
