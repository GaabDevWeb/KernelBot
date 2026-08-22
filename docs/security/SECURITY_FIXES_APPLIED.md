# SECURITY_FIXES_APPLIED — True Kernel

| Campo | Valor |
|-------|-------|
| Data | 2026-07-26 |
| Branch | `security-hardening` |
| Testes | 16 passed |

---

### FIX-001 — Auth de canal em /chat e /search

| Campo | Valor |
|-------|-------|
| Problema | SEC-001 / SEC-007 — superfície anónima cara e exfiltrável |
| Severidade | ALTO / MÉDIO |
| Correção | `api/security.py`: `ACL_API_BEARER_TOKEN` / `ACL_CHANNEL_API_KEYS`; obrigatório em production (`ACL_REQUIRE_API_AUTH=auto`); fail-fast no boot |
| Impacto | Sem Bearer válido → 401; boot production sem tokens → erro |
| Residual | Em development auth continua opcional (CLI local) |

### FIX-002 — Cursor chat-only por default

| Campo | Valor |
|-------|-------|
| Problema | SEC-002 |
| Severidade | ALTO |
| Correção | `ACL_CURSOR_CHAT_ONLY` default **true** se unset; `.env.example=true` |
| Impacto | Workspace Cursor = `.cursor-chat-workspace` vazio |
| Residual | Opt-out explícito `false` ainda possível |

### FIX-003 — Isolamento de pin/memória

| Campo | Valor |
|-------|-------|
| Problema | SEC-003 |
| Severidade | ALTO |
| Correção | `memory_session_key(channel, user_id, session_id)`; rejeita `session_id` só dígitos; docs adapters |
| Impacto | Dois users com mesmo session_id deixam de partilhar pin |
| Residual | Sem `user_id` → `_anon` (adapters devem enviar user_id) |

### FIX-004 — Rate limit multi-chave + trusted proxy + GC

| Campo | Valor |
|-------|-------|
| Problema | SEC-004 / SEC-014 / Novo-B |
| Severidade | MÉDIO / BAIXO |
| Correção | Limites por IP+canal+user; search 20/min; internal 60/min; anti brute-force; `ACL_TRUSTED_PROXY_IPS`; GC de buckets |
| Impacto | Melhor contenção single-process |
| Residual | Sem Redis — limite não partilha entre workers/réplicas |

### FIX-005 — Token interno distinto

| Campo | Valor |
|-------|-------|
| Problema | SEC-005 |
| Severidade | MÉDIO |
| Correção | Production: sem fallback para reload; fail-fast se internal==reload ou ausente |
| Impacto | Least privilege ops vs observabilidade |
| Residual | Development ainda pode fallback para reload |

### FIX-006 — Prompts off por default

| Campo | Valor |
|-------|-------|
| Problema | SEC-006 |
| Severidade | MÉDIO |
| Correção | `ACL_INTERNAL_STORE_PROMPTS` default **false**; redacção ao guardar |
| Impacto | `/internal/prompt/{id}` vazio salvo opt-in |
| Residual | Opt-in ainda guarda conteúdo (com redact) |

### FIX-007 — Snippet /search reduzido

| Campo | Valor |
|-------|-------|
| Problema | SEC-007 |
| Severidade | MÉDIO |
| Correção | Default 200 chars (`ACL_SEARCH_SNIPPET_CHARS`) |
| Impacto | Menos exfiltração por scrape |
| Residual | Com auth válida ainda devolve snippets |

### FIX-008 — Bounds em metadata

| Campo | Valor |
|-------|-------|
| Problema | SEC-008 |
| Severidade | MÉDIO |
| Correção | ≤32 keys, depth≤2, ≤4096 bytes → 422 |
| Impacto | DoS de payload mitigado |
| Residual | Nenhum material |

### FIX-009 — OpenAPI off em production

| Campo | Valor |
|-------|-------|
| Problema | SEC-009 |
| Severidade | BAIXO |
| Correção | `docs/redoc/openapi` None em production; `ACL_ENABLE_DOCS` override |
| Impacto | Menos reconhecimento de `/internal` |
| Residual | Dev mantém docs |

### FIX-010 — Disciplina fail-closed

| Campo | Valor |
|-------|-------|
| Problema | SEC-010 |
| Severidade | BAIXO |
| Correção | `ACL_DISCIPLINE_FAIL_CLOSED` default true em production |
| Impacto | Disciplina inválida → candidatos vazios |
| Residual | Dev default fail-open (compat) |

### FIX-011 — Staging MySQL loopback

| Campo | Valor |
|-------|-------|
| Problema | SEC-011 |
| Severidade | BAIXO |
| Correção | Bind `127.0.0.1:3307` em compose e `staging-docker-up.sh` |
| Impacto | Não escuta em 0.0.0.0 |
| Residual | Passwords staging ainda versionadas (só local) |

### FIX-012 — Redact expandido

| Campo | Valor |
|-------|-------|
| Problema | SEC-013 |
| Severidade | BAIXO |
| Correção | Bearer, sk-, sk-or-, env tokens em `redact_secrets` |
| Impacto | Menos vazamento em logs |
| Residual | Queries longas ainda podem ir para metadata truncada |

### FIX-013 — Request-Id server-only

| Campo | Valor |
|-------|-------|
| Problema | Novo-C |
| Severidade | BAIXO |
| Correção | Ignora `X-Request-Id` do cliente; gera UUID |
| Impacto | Sem colisão/overwrite no recorder |
| Residual | Nenhum |

### FIX-014 — Prompt/history sanitização leve

| Campo | Valor |
|-------|-------|
| Problema | Prompt injection / poisoning |
| Severidade | MÉDIO (parcial) |
| Correção | Strip `\x00`; history só `user|assistant`; docs adapters |
| Impacto | Reduz spoofing grosseiro |
| Residual | Injection semântica no LLM permanece (grounding textual) |

---

## Ficheiros tocados (principais)

- `api/security.py` (novo), `api/rate_limit.py`, `api/routes.py`, `api/internal_routes.py`
- `app/factory.py`
- `kernel/config.py`, `kernel/security_flags.py`, `kernel/schemas/*`, `kernel/memory/session_key.py`
- `kernel/inspect/recorder.py`, `kernel/structured_log.py`, `kernel/rag/search.py`
- `docker-compose.staging.yml`, `bin/staging-docker-up.sh`, `.env.example`
- `adapters/README.md`, `docs/API_SPEC.md`, `tests/*`
