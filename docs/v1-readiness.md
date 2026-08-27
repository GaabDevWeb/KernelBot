# V1 Readiness Report — Kernel / Orbit

| Campo | Valor |
|-------|-------|
| Data | 2026-08-27 |
| Branch | `feature/v1-hardening` (Kernel + Orbit) |
| Metodologia | Auditar → Medir → Corrigir → Testar |

## 1. Arquitectura auditada

```text
WhatsApp → Orbit (Baileys, buffer, userLock, dedupe local)
         → POST /v1/chat (+ X-Message-Id, X-Trace-Id, metadata)
         → Kernel (idempotency → rate limit → transcript → Context Router
                    → RAG/GM/Profile/Calendar → LLM → trace)
         → resposta → Orbit → WhatsApp
```

**Componentes verificados:** idempotência, concorrência por grupo, contextual `@orbit`, apresentação, rate limit, provider retry, health composto, shutdown gracioso, SQLite WAL, context budget (router), privacidade Git.

## 2. Riscos encontrados e status

| Área | Antes | Depois | Notas |
|------|-------|--------|-------|
| Idempotência Orbit→Kernel | **GAP** — sem `X-Message-Id` | **OK** | Header propagado de `msg.key.id` |
| Kill switch idempotência | **GAP** — flag ignorada | **OK** | `main.py` condicional |
| Apresentação concorrente | **GAP** — race TOCTOU | **OK** | `try_claim_introduction()` atómico |
| Rate limit `/v1/groups/*` | **GAP** | **OK** | `ACL_GROUPS_RATE_LIMIT` |
| Provider retry Orbit | **GAP** | **OK** | 502/503/504/timeout, backoff |
| Health Orbit | **PARTIAL** | **OK** | WA + Kernel probe |
| Graceful shutdown Orbit | **GAP** | **OK** | SIGTERM/SIGINT + drain |
| Multi-réplica | **GAP** | **ACEITO V1** | Documentado single-worker |
| Stream idempotência | **GAP** | **ACEITO V1** | Stream off no Orbit |
| Context budget global | **PARTIAL** | **ACEITO V1** | Router off por default; caps parciais |

## 3. Correções aplicadas (esta branch)

### KernelBot
- `KERNEL_IDEMPOTENCY_ENABLED` respeitado em `main.py`
- `GroupMemoryStore.try_claim_introduction()` — claim atómico
- Rate limit em todos endpoints `/v1/groups/*`
- Rate limits configuráveis via env (`ACL_*_RATE_LIMIT`)
- `.env.example` — idempotência + rate limits documentados
- Teste `test_try_claim_introduction_atomic`

### OrbitBot
- `X-Message-Id` em `kernelProvider.chat()`
- Retry com backoff (`KERNEL_API_MAX_RETRIES`, default 2)
- Tratamento 409/429 com códigos dedicados
- Graceful shutdown (`src/shutdown.js`, `app.js`)
- Health composto `/internal/health` (WhatsApp + Kernel)
- `userLock.pendingCount()` para drain

## 4. Testes executados

```bash
# Kernel
PYTHONPATH=. .venv/bin/pytest \
  tests/test_contextual_invocation.py \
  tests/test_idempotency.py \
  tests/test_group_memory.py \
  tests/test_v1_chat.py \
  tests/test_group_endpoints.py \
  -q
```

**Resultado:** suite hardening — ver output local (última execução nesta sessão).

### Golden regression set (consolidado)

| Categoria | Ficheiro(s) |
|-----------|-------------|
| Contrato v1 chat | `tests/test_v1_chat.py` |
| Idempotência | `tests/test_idempotency.py` |
| Contextual @orbit | `tests/test_contextual_invocation.py` |
| Group Memory | `tests/test_group_memory.py`, `test_group_endpoints.py` |
| Context Router | `tests/test_context_router.py` |
| WhatsApp import | `tests/test_whatsapp_import.py` |

> Não utiliza mensagens reais de grupos — apenas fixtures sintéticas.

### Orbit (requer Node)

```bash
node --test test/group-invocation.test.js test/kernel-provider.test.js test/concurrency.test.js
```

## 5. Benchmark / latência

**Baseline:** não executado stress 10–100 msg/min nesta sessão (sem ambiente WA+LLM live).

**Expectativa V1 single-worker:**
- Idempotência hit: ~0ms (replay memória)
- Contextual @orbit: +0 leituras extra (buffer Orbit já em RAM)
- Retry provider: +800ms–2.4s apenas em falha transitória

**Regressão conhecida:** nenhuma medida em produção nesta passagem.

## 6. Tokens

Métricas existentes no trace: `trace_tokens`, `prompt_tokens_est`, `KERNEL_PROMPT_BUILT`.

Separação fina system/recent/rag/memory — **parcial** (snapshot em `chat_pipeline._context_snapshot_from_trace`).

## 7. Falhas corrigidas vs aceites

| Falha | Acção |
|-------|-------|
| Dupla resposta sem Message-Id | Corrigido (Orbit) |
| Dupla apresentação concorrente | Corrigido (SQLite claim) |
| Groups API sem rate limit | Corrigido |
| Shutdown abrupto Orbit | Corrigido |
| Idempotency flag morta | Corrigido |

| Limitação aceite V1 | Razão |
|---------------------|-------|
| Idempotency in-memory | Single worker |
| Transcript in-memory | By design SSOT session |
| Router off default | Compat legado; ligar em prod |
| Sem stress test formal | Requer staging |

## 8. Critérios de aprovação V1 (checklist)

- [x] `@orbit` vazio não gera erro técnico
- [x] Idempotência Kernel com `X-Message-Id` (Orbit integrado)
- [x] Ordenação por grupo (`userLock`)
- [x] Isolamento Group Memory por canal
- [x] Recent context ≠ RAG query
- [x] Provider retry + timeout
- [x] Rate limit groups + chat
- [x] Trace `CONTEXTUAL_INVOCATION`
- [x] `introduction_sent` atómico; `/reset` não repõe (by design)
- [x] SQLite runtime fora do Git (`.gitignore`)
- [ ] Stress P95 formal — **pendente staging**
- [ ] Backup/restore testado — **verificar ops runbook**

## 9. Próximos passos (pós-V1, não nesta branch)

- Readiness público `/v1/health/ready` (MySQL ping)
- Stream idempotency complete
- `ACL_CONTEXT_ROUTER=1` em produção
- Golden set expandido (50–100 casos) com runner dedicado

## 10. Referências

- `docs/V1_SCOPE.md`
- `docs/ARCHITECTURE.md` (secção V1)
- `docs/CONTEXT-ARCHITECTURE.md`
- Orbit: `docs/KERNEL-INTEGRATION.md`
