# Operational Trace (Fatia A / S2) — Implementation Plan

> **For agentic workers:** Execute task-by-task. Steps use checkbox syntax.

**Goal:** Depurar conversa Orbit → Kernel → WhatsApp via `trace_id` + painel `/traces` funcional.

**Architecture:** Kernel hospeda SQLite (`ACL_TRACE_DB_PATH`) + queue async + Jinja `/traces`. Orbit gera UUID, envia `X-Trace-Id` e emite eventos mínimos via `POST /internal/traces/events`. Best-effort; não bloqueia chat.

**Tech Stack:** FastAPI, aiosqlite/sqlite3+asyncio, Jinja2Templates, axios (Orbit)

## Global Constraints

- Path default: `data/traces.sqlite3`; mkdir parent automático
- Auth ingest: Bearer `ACL_INTERNAL_BEARER_TOKEN`; painel cookie `trace_auth`
- Não poluir body `/v1/chat`; header `X-Trace-Id` only
- Adiar: ZIP, dashboards, filtros complexos, métricas, polish
- Coexiste com `kernel/inspect` (ring buffer)

## File map

### Kernel (create)
- `kernel/trace/__init__.py`
- `kernel/trace/store.py` — SQLite schema + writes
- `kernel/trace/queue.py` — asyncio.Queue + worker (ERROR priority)
- `kernel/trace/emitter.py` — `emit_trace` / redact data
- `kernel/trace/stages.py` — stage constants
- `api/traces_routes.py` — login + list + detail (Jinja)
- `templates/traces/*.html`
- `tests/test_trace_store.py`, `tests/test_trace_api.py`

### Kernel (modify)
- `kernel/config.py` — `trace_db_path`
- `app/factory.py` — start/stop worker; mount traces router; Jinja
- `app/state.py` — optional TraceService on AppServices
- `api/internal_routes.py` — `POST /traces/events`
- `api/routes_v1.py` + `api/chat_pipeline.py` — emit + X-Trace-Id
- `.env.example`, `requirements.txt` (jinja2, aiosqlite if used)

### Orbit (create/modify)
- `src/traceClient.js` — fire-and-forget ingest
- `src/providers/kernelProvider.js` — X-Trace-Id + REQUEST/RESPONSE events
- `src/openai.js`, `messageHandler.js`, `bot.js`, `groupHandler.js` — thread traceId + MESSAGE_* / SENT / ERROR
- `.env.example` — `ACL_INTERNAL_BEARER_TOKEN`
- `test/trace-*.test.js` or extend kernel-provider tests

---

## Task 1: Trace store + queue + config

- [ ] Add `ACL_TRACE_DB_PATH` to Settings (default `data/traces.sqlite3`)
- [ ] Implement SQLite schema `traces` + `trace_events`
- [ ] Async queue worker; ERROR priority; best-effort logging
- [ ] Unit tests with tmp path

## Task 2: Ingest API + Kernel emitters

- [ ] `POST /internal/traces/events`
- [ ] Resolve/generate `X-Trace-Id` in `/v1/chat`; echo `metadata.trace_id`
- [ ] Emit Kernel stages in routes_v1 + chat_pipeline
- [ ] API tests

## Task 3: Painel Jinja

- [ ] `/traces/login` GET/POST cookie
- [ ] `/traces` lista recentes + busca trace_id
- [ ] `/traces/{id}` timeline
- [ ] Mount in factory; start worker on lifespan

## Task 4: Orbit emitters

- [ ] traceClient + UUID at entrypoints
- [ ] Header + stages mínimos
- [ ] Tests + .env.example

## Task 5: Wire docs + smoke

- [ ] `.env.example` Kernel
- [ ] pytest + node tests
- [ ] `.agent_history` update
