# V1 Production Runbook — Kernel / Orbit

| Campo | Valor |
|-------|-------|
| Escopo | Single-worker VPS · Orbit → Kernel localhost · adapter-trust |
| Não suportado V1 | Multi-réplica · API Kernel pública · multi-tenant |

---

## 1. Pré-requisitos

- Python 3.11+ (Kernel) · Node 18+ (Orbit)
- SQLite writable em `data/`
- Reverse proxy HTTPS (painel ops)
- Firewall: **porta Kernel (8001) só localhost**

---

## 2. Variáveis obrigatórias (production)

```bash
KERNELBOT_ENV=production
ACL_REQUIRE_API_AUTH=auto          # true em production
ACL_API_BEARER_TOKEN=<segredo>     # Orbit → Kernel
ACL_INTERNAL_BEARER_TOKEN=<segredo-distinto>
KERNEL_IDEMPOTENCY_ENABLED=true
KERNEL_WORKERS=1                   # ou UVICORN_WORKERS=1
KERNEL_BIND_HOST=127.0.0.1
OPENROUTER_API_KEY=<key>           # se provider=openrouter
```

**Staging:** `KERNELBOT_ENV=staging` — auth de canal **obrigatória** (mesmo sem `ACL_REQUIRE_API_AUTH`).

**Development localhost:** auth opcional; nunca expor bind `0.0.0.0` sem `ACL_REQUIRE_API_AUTH=true`.

---

## 3. Boot fail-fast

O Kernel recusa arrancar em `production` se:

- faltar `ACL_API_BEARER_TOKEN` ou `ACL_CHANNEL_API_KEYS`
- faltar `ACL_INTERNAL_BEARER_TOKEN`
- `ACL_INTERNAL_BEARER_TOKEN` == token de reload
- `KERNEL_WORKERS` > 1

---

## 4. Deploy limpo (VPS)

```bash
# Kernel
cd KernelBot
python -m venv .venv && .venv/bin/pip install -r requirements.txt
cp .env.example .env   # preencher tokens
PYTHONPATH=. .venv/bin/python main.py

# Orbit (mesma máquina)
cd OrbitBot
npm ci
cp .env.example .env   # KERNEL_API_URL=http://127.0.0.1:8001
node app.js
```

Health:

- Kernel: `GET http://127.0.0.1:8001/v1/health`
- Orbit: `GET http://127.0.0.1:8010/internal/health`

---

## 5. Trust model (REDTEAM-002)

- Um Bearer global acede a **todos** os `channel_id` — **by design V1**
- Mitigação: Kernel **nunca** exposto à Internet; só Orbit chama
- Token nunca no cliente WhatsApp / browser

---

## 6. Idempotência Orbit → Kernel

Orbit envia `X-Message-Id: msg.key.id` em todo `POST /v1/chat`.

Retry Baileys / crash Orbit → Kernel devolve resposta cacheada (mesmo `X-Message-Id`).

Kill switch: `KERNEL_IDEMPOTENCY_ENABLED=false` (não recomendado em prod).

---

## 7. Backup / restore

Ficheiros críticos (parar processos ou `PRAGMA wal_checkpoint` antes de copiar):

| Ficheiro | Conteúdo |
|----------|----------|
| `data/group_memory.sqlite3` | Group Memory + BM25 index |
| `data/comms.sqlite3` | Campanhas / automações |
| `data/users.sqlite3` | Sessões ops / bloqueios |
| `data/traces.sqlite3` | Traces operacionais |

Teste automatizado: `tests/test_v1_backup_restore.py`

Restore: copiar ficheiros de volta + reiniciar Kernel.

---

## 8. Restart gracioso

**Kernel:** SIGTERM → lifespan encerra trace bus + comms scheduler.

**Orbit:** SIGTERM/SIGINT → `shutdown.js` drena fila (`userLock.pendingCount()`).

**Transcript in-memory:** perdido em restart (aceite V1). Group Memory persiste.

---

## 9. Provider failure

Orbit: retry 502/503/504/timeout (`KERNEL_API_MAX_RETRIES`, default 2).

Kernel: erro controlado ao utilizador; detalhe em trace (sem secrets).

---

## 10. Observabilidade

- Painel: `/ops/login` → token interno
- Traces: `message_preview` truncado (`ACL_TRACE_MESSAGE_PREVIEW_CHARS`, default 400)
- Logs: redacção automática de Bearer/API keys

---

## 11. Kill switches

| Variável | Efeito |
|----------|--------|
| `KERNEL_IDEMPOTENCY_ENABLED=false` | Desliga dedupe Kernel |
| `ACL_CONTEXT_ROUTER=0` | Router off (default) |
| `group_memory_enabled` (settings) | Desliga GM |

---

## 12. Troubleshooting

| Sintoma | Acção |
|---------|-------|
| 401 em `/v1/chat` | Verificar Bearer Orbit == `ACL_API_BEARER_TOKEN` |
| 409 idempotency | Normal em retry; aguardar ou mesmo `X-Message-Id` |
| 429 rate limit | Ajustar `ACL_*_RATE_LIMIT` ou reduzir carga |
| Duplicar resposta | Verificar `X-Message-Id`; confirmar single worker |
| Group memory vazia | Verificar ingest Orbit + `group_memory_enabled` |

---

## 13. Checklist go-live

- [ ] `KERNELBOT_ENV=production`
- [ ] Tokens distintos configurados
- [ ] Bind 127.0.0.1 + firewall
- [ ] `KERNEL_WORKERS=1`
- [ ] Backup testado
- [ ] HTTPS ops + cookie Secure
- [ ] Suite testes verde local
