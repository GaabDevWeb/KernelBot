# PRD — Flight Recorder (Fatia C)

| Campo | Valor |
|-------|-------|
| Data | 2026-07-28 |
| Status | approved (missão utilizador inline) |
| Branch | `feature/orbit-kernel-tracing` |
| Depende | Fatias A+B |

## Objectivo

Painel auditável/reproduzível: timeline, RAG, prompt, tokens, performance, ZIP, replay+diff, retenção.

## Env

```env
ACL_TRACE_ENABLED=true
ACL_TRACE_DB_PATH=data/traces.sqlite3
ACL_TRACE_RETENTION_DAYS=30
ACL_TRACE_STORE_PROMPTS=true
```

## Novidades vs A+B

PROMPT_BUILT, snapshots forensics, P95/P99, system health, retention, replay, diff, ZIP v2.
