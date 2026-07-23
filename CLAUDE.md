# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Kernel (KernelBot / ACL) — educational assistant chatbot with BM25-based contextual retrieval over indexed lessons stored in MySQL, a real-time SSE web UI, and multi-discipline support. Backend is FastAPI/Python; frontend is vanilla JS (ES modules) with Tailwind CSS v4. Primary docs (Portuguese) live in `docs/wiki/` — `documentation.md` is the index. `README.md` has full setup/deploy/test instructions.

## Commands

```bash
# Run the app (MySQL + LLM key required in .env)
python main.py                      # http://127.0.0.1:8001

# Backend tests
PYTHONPATH=. pytest tests/ -q
PYTHONPATH=. pytest tests/test_foo.py::test_name -q   # single test

# Frontend smoke test (server must be running on :8001, needs Chromium via Playwright)
python3 bin/validate-frontend.py
SMOKE_BROWSERS=chromium,firefox python3 bin/validate-frontend.py   # cross-browser

# Local staging (MySQL in Docker on :3307)
./bin/staging-setup.sh      # first time: DB schema + seed + ingest wiki
./bin/staging-serve.sh      # run server with KERNELBOT_ENV=staging

# Content ingestion (UPSERT into MySQL `knowledge` table)
KERNELBOT_ENV=staging ./bin/ingest-wiki-doc.sh    # docs/wiki/*.md -> discipline=doc
KERNELBOT_ENV=staging ./bin/ingest-jsons.sh       # jsons/<discipline>/*.json
./bin/staging-ingest-iss.sh                       # full ISS ingest (needs ISS repo checked out)

# Docker
docker build -t kernelbot:latest .
docker compose up -d --build
```

CI (`.github/workflows/ci.yml`) runs `pytest tests/ -q` with `PYTHONPATH=.` on Python 3.12. There is currently no `tests/` directory in the repo — check before assuming test coverage exists.

After changing retrieval/gating logic or `.env` defaults, re-read `docs/wiki/06-gates-e-decisoes.md` and `docs/wiki/12-configuracao.md` — they document exact threshold values and must stay in sync with `engine/retrieval.py` / `core/config.py`.

## Architecture

```
main.py → app/factory.py → api/routes.py
                         → frontend/ (static /assets, /src)
                         → engine/
templates/index.html
```

`main.py` boots `Settings.load()` (fails fast if the LLM provider key or prompt files are missing), builds the BM25 index via `SearchEngine.rebuild()`, loads the optional lesson catalog, and wires everything into an `AppServices` dataclass (`app/state.py`) that's injected into the FastAPI app created by `app/factory.py`.

### Request flow (retrieval → generation → gating)

1. `api/routes.py` validates input (`POST /chat`, rate-limited to 30 req/IP/60s).
2. `engine/context.py` (`ContextManager`) parses scope commands (`/doc`, `/python`, discipline slugs), integrates the pinned-session state, and orchestrates retrieval.
3. `engine/search.py` (`SearchEngine`) runs BM25Okapi per-discipline "silo" over chunks loaded from MySQL (`engine/database.py`) — the index lives entirely in RAM and is rebuilt on boot or via `/reload`.
4. `engine/retrieval.py` `build_decision()` classifies the query into a `DecisionReason` (`ok`, `insufficient_context`, `underspecified_query`, `ambiguous_retrieval`, `context_misaligned`, `vague_but_high_risk`, `index_gap`, etc.) using score/margin/coverage/term-count thresholds. **Every message reaches the LLM** — gates only classify and select which grounding prompt + chunks to inject; they no longer hard-block generation (except `provider_error`).
5. `engine/chat_provider.py` (`ChatProvider`) streams the response from the configured LLM provider (`ACL_LLM_PROVIDER`: `cursor` via Cursor SDK, default, or `openrouter`), emitting `ACL_META` over SSE.
6. `post_generation_flags()` in `engine/retrieval.py` sanity-checks the LLM output against the injected chunks. Under `ACL_GROUNDING_POLICY=strict` a flag triggers a destructive override + disclaimer; under `anchored`/`hybrid` (default `anchored`) it's advisory-only and the answer is kept.

Full decision-gate table, thresholds, and grounding-file selection logic: `docs/wiki/06-gates-e-decisoes.md`.

### Key modules

| Module | Responsibility |
|--------|----------------|
| `core/config.py` | `Settings.load()` — all runtime config from `.env` (`ACL_*` vars); fails on missing LLM key or missing `core/systemPrompt/*` files |
| `core/systemPrompt/` | Prompt text files injected per policy: `system_prompt.txt`, `grounding_strict.txt`, `grounding_anchored.txt`, `grounding_permissive.txt`, `grounding_disambiguation.txt`, `catalog_router.txt`, `sticky_instruction.txt` — all required at boot |
| `core/logging_config.py`, `core/structured_log.py` | Logging setup + `SecretRedactingFilter` (redacts secrets from logs) |
| `engine/database.py` | `fetch_db_chunks` (SELECT `active=1` from `knowledge`), chunking (500/50 windows), B2 meta-block parsing |
| `engine/search.py` | `SearchEngine` — per-silo BM25 index, `search_candidates()` |
| `engine/retrieval.py` | `build_decision()`, `post_generation_flags()`, `normalize_and_tokenize()` — the gating logic described above |
| `engine/context.py` | `ContextManager` — scope command parsing, catalog integration, prompt assembly, pin save/load |
| `engine/chat_provider.py` | LLM streaming (Cursor SDK or OpenRouter), `ACL_META` emission, misalignment override |
| `engine/catalog_sync.py`, `engine/lesson_catalog.py` | Optional ISS lexical lesson catalog (`ACL_CATALOG_ENABLED`), used for `index_gap` detection and drift reporting |
| `engine/pinned_store.py` | `PinnedSessionStore` — in-memory `session_id` → fixed context chunks, TTL by turn count |
| `app/factory.py` | FastAPI app assembly: `SecurityHeadersMiddleware` (CSP, HSTS, etc.), dev-only `/src/` no-cache middleware, static mounts |
| `api/routes.py` | `GET /`, `POST /chat` (rate-limited), `GET /health`, `GET /health/catalog`, admin `/reload` |
| `frontend/src/` | `main.js` (entry), `api.js` (fetch + SSE parsing), `ui.js` (chat loop, markdown, disambiguation chips, index-gap alerts) — vanilla ES modules, no bundler in production |

`engine/watcher.py` and `content/` are legacy/unused — they don't drive the current BM25 index.

### Config and environments

Config is entirely env-driven via `Settings.load()` (`python-dotenv`); see `docs/wiki/12-configuracao.md` for the full variable reference. `KERNELBOT_ENV` selects behavior: `production` disables the dev no-store cache middleware on `/src/` and requires `ACL_RELOAD_BEARER_TOKEN` for `/reload` and `/health/catalog`; `staging` loads `.env.staging.local` with override priority (used by `bin/staging-*.sh`); anything else is treated as development.

`ACL_LLM_PROVIDER` selects the LLM backend at boot (`cursor` default, needs `CURSOR_API_KEY`; or `openrouter`, needs `OPENROUTER_API_KEY`) — missing the required key raises `RuntimeError` on startup.

### Security notes

CSP in `app/factory.py` currently allows `unsafe-inline` for `script-src`/`style-src` because templates/ES modules still use inline handlers — the documented preferred fix is per-request nonces rather than loosening `script-src` further. `POST /chat` rate limiting (30/IP/60s) is hardcoded in `api/routes.py`, not `.env`-configurable.
