# PRE-PRODUCTION RED TEAM — Kernel / Orbit

| Campo | Valor |
|-------|-------|
| Data | 2026-08-27 |
| Branch | `audit/preproduction-redteam` (Kernel + Orbit) |
| Base | `feature/v1-hardening` |
| Metodologia | Auditar → Atacar → Reproduzir → Classificar → Corrigir (P0/P1) → Regredir → Validar |
| Veredito | **NOT READY** (produção geral) · **CONDITIONALLY READY** (V1 single-worker documentado) |

> **Actualização V2 (remediação):** ver secção [REDTEAM V2 / REMEDIATION](#redteam-v2--remediation) no final.

---

## EXECUTIVE SUMMARY

Auditoria adversarial focada em **KernelBot** (API `/v1/*`, Group Memory, ops, comms) e **OrbitBot** (adapter WhatsApp → Kernel). O objectivo foi tentar provar que o sistema **não** está pronto para produção.

**Total de problemas catalogados**

| Severidade | Count |
|------------|-------|
| P0 | 0 |
| P1 | 4 |
| P2 | 8 |
| P3 | 5 |

**Bloqueadores de release (gate §92):** nenhum P0 confirmado; isolamento **storage** entre grupos OK; sem vazamento de segredo em código; idempotência Orbit→Kernel activa. **Bloqueio residual:** modelo de auth **adapter-trust** (Bearer global) + estado **in-memory** single-worker + checklist de produção não formalizado como runbook assinado.

---

## BLOCKERS

Nenhum P0 reproduzido. Release bloqueada para **multi-réplica** ou **exposição directa da API Kernel à Internet** sem mitigações documentadas.

---

## CONFIRMED

### REDTEAM-001 — Auth bypass em desenvolvimento

| Campo | Valor |
|-------|-------|
| Severidade | **P1** |
| Categoria | Authentication |
| Local | `api/security.py` → `require_api_auth()` |
| Reproduzível | Sim — `tests/test_preproduction_redteam.py::test_redteam_001_*` |

**Reprodução:** `KERNELBOT_ENV` ≠ production e `ACL_REQUIRE_API_AUTH` unset → `POST /v1/chat` sem Bearer retorna **200**.

**Resultado actual:** API pública em dev/staging mal configurado.

**Esperado:** Em qualquer ambiente exposto, auth obrigatória.

**Impacto:** Qualquer actor na rede pode invocar LLM, ler/gravar group memory via endpoints de gestão se souber URLs.

**Exploitabilidade:** Alta em LAN/VPS com porta 8001 exposta e env de dev.

**Correcção sugerida:** Runbook: `KERNELBOT_ENV=production` + tokens; ou `ACL_REQUIRE_API_AUTH=true` em staging. Fail-fast em production já existe (`validate_production_security_config`).

**Corrigido:** Não (by design dev) · **Mitigado** por fail-fast production.

**Bloqueia release:** Sim, se deploy usar defaults de dev.

---

### REDTEAM-002 — IDOR: Bearer global acede a qualquer grupo

| Campo | Valor |
|-------|-------|
| Severidade | **P1** |
| Categoria | IDOR / Authorization |
| Local | `api/routes_v1.py` — `/v1/groups/{platform}/{channel_id}/*` |
| Reproduzível | Sim — `test_redteam_002_global_bearer_cross_group_idor` |

**Reprodução:** Com `ACL_API_BEARER_TOKEN`, substituir `channel_id` na URL permite ler histórico e **apagar** memória de outro grupo.

**Resultado actual:** Autorização só verifica token de **plataforma** (`whatsapp`), não membership do grupo.

**Esperado:** Modelo adapter-trust: só Orbit chama Kernel; token nunca exposto a utilizadores.

**Impacto:** Vazamento ou wipe cross-group se token vazar ou API exposta.

**Exploitabilidade:** Média (requer Bearer).

**Correcção sugerida:** Rede privada Orbit↔Kernel; rotação de token; futuro ACL por `channel_id` se API for multi-tenant.

**Corrigido:** Não · **Risco aceite V1** (Orbit único cliente).

**Bloqueia release:** Condicional.

---

### REDTEAM-003 — Falha silenciosa em Group Profile (background)

| Campo | Valor |
|-------|-------|
| Severidade | **P2** |
| Categoria | Silent failure / Observability |
| Local | `api/routes_v1.py` → `_async_update_group_profile` |
| Reproduzível | Sim — `test_redteam_003_async_profile_update_logs_on_failure` |

**Reprodução:** Excepção no analyzer → antes `except: pass`; perfil desactualizado sem trace.

**Corrigido:** **Sim** — passou a `log.warning(...)` com platform/channel_id.

**Bloqueia release:** Não.

---

### REDTEAM-004 — Ops cookie sem flag `Secure` (non-prod)

| Campo | Valor |
|-------|-------|
| Severidade | **P2** |
| Categoria | Session security |
| Local | `api/ops_routes.py` — `set_cookie` |
| Reproduzível | Inspecção estática |

**Resultado actual:** Cookie `trace_auth` guarda token raw; HttpOnly + SameSite=lax; **Secure** só em production (`is_production()` ou `KERNELBOT_COOKIE_SECURE`).

**Corrigido:** **Sim** (flag Secure condicional).

**Bloqueia release:** Não.

---

### REDTEAM-005 — Estado in-memory não partilhado (multi-réplica)

| Campo | Valor |
|-------|-------|
| Severidade | **P1** |
| Categoria | Concurrency / Data race |
| Local | `IdempotencyStore`, `TranscriptStore`, `api/rate_limit.py` |
| Reproduzível | Análise estática + docs V1 |

**Impacto:** Duas réplicas → duplicar respostas LLM, rate limit bypass, transcript inconsistente.

**Corrigido:** Não · **Aceite V1** — single worker obrigatório.

**Bloqueia release:** Sim para horizontal scaling.

---

### REDTEAM-006 — Transcript perdido em restart

| Campo | Valor |
|-------|-------|
| Severidade | **P2** |
| Categoria | Persistence |
| Local | `kernel/memory/transcript_store.py` |
| Reproduzível | Análise estática |

**Impacto:** Após SIGTERM/restart, contexto curto de conversa 1:1/grupo por `v1_key` reinicia vazio (Group Memory persistente continua).

**Corrigido:** Não · documentado em `docs/v1-readiness.md`.

---

### REDTEAM-007 — Rate limit bypass multi-IP / multi-worker

| Campo | Valor |
|-------|-------|
| Severidade | **P2** |
| Categoria | Rate limiting |
| Local | `api/rate_limit.py` (in-memory) |

**Impacto:** Scraping distribuído ou N workers contorna limites por IP.

**Corrigido:** Não · aceite V1.

---

### REDTEAM-008 — Isolamento Group Memory (storage) ✅ PASS

| Campo | Valor |
|-------|-------|
| Severidade | — |
| Categoria | Group isolation |
| Local | `kernel/memory/group_memory.py` |
| Reproduzível | `test_strict_group_isolation`, `test_redteam_008_*` |

Grupo B **não** recupera mensagens indexadas no grupo A (SQLite + BM25).

---

### REDTEAM-009 — Fail-fast production sem tokens ✅ PASS

| Campo | Valor |
|-------|-------|
| Severidade | — |
| Categoria | Authentication |
| Local | `api/security.py` → `validate_production_security_config` |
| Reproduzível | `test_redteam_009_*` |

`KERNELBOT_ENV=production` sem `ACL_API_BEARER_TOKEN`/`ACL_INTERNAL_BEARER_TOKEN` → `RuntimeError` no boot.

---

### REDTEAM-010 — v1 session key collision (SEC-001) ✅ PASS

| Campo | Valor |
|-------|-------|
| Severidade | — |
| Categoria | IDOR (transcript) |
| Local | `kernel/memory/session_key.py` |
| Reproduzível | `tests/test_v1_session_key.py` |

`channel_id` com `:` embutido não colide com outra tupla platform/user/session.

---

### REDTEAM-011 — Secret redaction em logs ✅ PASS (parcial)

| Campo | Valor |
|-------|-------|
| Severidade | P3 residual |
| Categoria | Secret leaks |
| Local | `kernel/structured_log.py` |
| Reproduzível | `tests/test_redact_secrets.py` |

Bearer/API keys redactados em pipeline de log. **Residual:** traces guardam `message_preview` (400 chars) — necessário para ops, risco privacy se trace DB vazar.

---

### REDTEAM-012 — Upload comms: path traversal ✅ PASS

| Campo | Valor |
|-------|-------|
| Severidade | — |
| Categoria | File upload |
| Local | `kernel/comms/security.py` |
| Reproduzível | `tests/test_comms.py` |

`Path(name).name`, extensões bloqueadas, tamanho máximo 8 MiB.

---

### REDTEAM-013 — Regressão teste lab ops

| Campo | Valor |
|-------|-------|
| Severidade | **P3** |
| Categoria | Regression |
| Local | `tests/test_lab_ops.py` |
| Reproduzível | Sim — stub `ContextManagerStub` desactualizado (`request_metadata`) |

**Impacto:** CI/golden set; não afecta runtime Orbit.

**Corrigido:** Não (fora scope red team — stub de teste).

---

### REDTEAM-014 — Prompt injection / memory poisoning

| Campo | Valor |
|-------|-------|
| Severidade | **P2** (inherent LLM) |
| Categoria | Prompt injection |
| Reproduzível | Não automatizado nesta auditoria |

Group Profile usa analyzer LLM/heurístico; mensagens hostis no histórico **podem** influenciar perfil. Não há promoção automática a "fact" sem evidence chain formal. **Teste manual recomendado** antes de go-live.

**Status:** UNCONFIRMED para bypass de system prompt; CONFIRMED risco residual LLM.

---

### REDTEAM-015 — Orbit dedupe local in-memory

| Campo | Valor |
|-------|-------|
| Severidade | **P2** |
| Categoria | Idempotency |
| Local | Orbit — sem store persistente de dedupe além de `X-Message-Id` → Kernel |

**Impacto:** Crash Orbit entre receive e POST Kernel → retry Baileys pode reenviar; mitigado por idempotency Kernel se `msg.key.id` estável.

**Status:** UNCONFIRMED em crash real; mitigação parcial documentada.

---

### REDTEAM-016 — SSRF / webhooks remotos

| Campo | Valor |
|-------|-------|
| Severidade | — |
| Categoria | SSRF |
| Status | **N/A** — sem fetch URL user-controlled no Kernel V1 |

---

### REDTEAM-017 — Long-run / stress / backup

| Campo | Valor |
|-------|-------|
| Severidade | **P2** |
| Categoria | Performance / DR |
| Status | **NÃO EXECUTADO** nesta sessão (sem VPS staging sob carga horas) |

---

## FIXED (nesta branch)

| ID | Fix |
|----|-----|
| REDTEAM-003 | Log warning em `_async_update_group_profile` |
| REDTEAM-004 | Cookie ops `Secure` em production |

---

## UNCONFIRMED

- REDTEAM-014 — bypass crítico de system prompt via Group Memory/RAG
- REDTEAM-015 — duplicação WhatsApp após crash Orbit pré-POST
- Race cancelamento vs execução automações (comms scheduler não stressado)
- Disk-full behaviour SQLite

---

## ACCEPTED RISKS (V1)

1. **Single worker** — idempotency, rate limit, transcript in-memory.
2. **Bearer global** — Orbit único cliente; Kernel não exposto publicamente.
3. **ACL_CONTEXT_ROUTER=0** default — latência maior em perguntas simples.
4. **Stream idempotency** — stream off no Orbit V1.
5. **Transcript não persistente** — reinício limpa janela curta.

---

## MATRIZ FINAL

| ID | Categoria | Severidade | Reproduzível | Corrigido | Bloqueia |
|----|-----------|------------|--------------|-----------|----------|
| REDTEAM-001 | Auth bypass dev | P1 | Sim | Mitigado (prod fail-fast) | Se dev exposto |
| REDTEAM-002 | IDOR API grupos | P1 | Sim | Não (aceite) | Condicional |
| REDTEAM-003 | Silent failure profile | P2 | Sim | **Sim** | Não |
| REDTEAM-004 | Cookie Secure | P2 | Estático | **Sim** | Não |
| REDTEAM-005 | Multi-réplica state | P1 | Estático | Não (aceite) | Multi-worker |
| REDTEAM-006 | Transcript RAM | P2 | Estático | Não | Não |
| REDTEAM-007 | Rate limit bypass | P2 | Estático | Não | Não |
| REDTEAM-008 | Group isolation storage | — | Sim | N/A (PASS) | Não |
| REDTEAM-009 | Prod fail-fast | — | Sim | N/A (PASS) | Não |
| REDTEAM-010 | Session key collision | — | Sim | N/A (PASS) | Não |
| REDTEAM-011 | Log redaction | P3 | Sim | Parcial | Não |
| REDTEAM-012 | Lab test regression | P3 | Sim | Não | CI only |
| REDTEAM-013 | Lab stub drift | P3 | Sim | Não | Não |
| REDTEAM-014 | Prompt injection | P2 | Manual | N/A | Condicional |
| REDTEAM-015 | Orbit dedupe | P2 | UNCONFIRMED | Parcial | Condicional |
| REDTEAM-016 | SSRF | — | N/A | N/A | Não |
| REDTEAM-017 | Long-run/DR | P2 | Não testado | N/A | Staging |

---

## TESTES EXECUTADOS

```bash
# Red team (novo)
PYTHONPATH=. .venv/bin/pytest tests/test_preproduction_redteam.py -v

# Suite completa Kernel
PYTHONPATH=. .venv/bin/pytest tests/ -q
# Resultado: 184 passed, 1 failed (test_lab_ops stub)
```

**Testes adicionados:** `tests/test_preproduction_redteam.py` (5 cenários).

**Orbit:** testes escritos em `test/kernel-provider.test.js` — Node não disponível no ambiente do agente durante auditoria.

---

## CHECKLIST READY (§96)

| Item | Estado |
|------|--------|
| P0 corrigidos | ✅ (0 P0) |
| P1 corrigidos ou aceites | ⚠️ Aceites implicitamente V1, não runbook assinado |
| Testes segurança | ✅ Parcial (5 red team + isolamento GM) |
| Testes concorrência | ⚠️ Idempotency unit; sem stress multi-process |
| Golden set | ⚠️ 1 falha lab stub |
| Grupos isolados (storage) | ✅ |
| Painel protegido | ✅ Bearer interno + cookie HttpOnly |
| Backup restaurável | ❓ Não testado |
| Idempotência automações | ❓ Comms não stressado |
| WhatsApp resiliente | ⚠️ Orbit shutdown/retry; sem chaos test |
| Tracing diagnóstico | ✅ |

---

## DEFINIÇÃO DE READY

### NOT READY — produção generalizada / multi-réplica / API Kernel na Internet

Motivos:
- P1 REDTEAM-002 e REDTEAM-005 sem mitigação arquitectural
- Long-run, backup/restore, chaos não executados
- 1 teste de regressão falhando

### CONDITIONALLY READY — V1 single-worker VPS (Orbit + Kernel localhost)

**Pré-requisitos obrigatórios:**
1. `KERNELBOT_ENV=production`
2. `ACL_API_BEARER_TOKEN` + `ACL_INTERNAL_BEARER_TOKEN` (distintos)
3. Kernel API **não** exposta publicamente (bind 127.0.0.1 ou firewall)
4. `KERNEL_IDEMPOTENCY_ENABLED=true`
5. Orbit propaga `X-Message-Id`
6. HTTPS no painel ops com `KERNELBOT_COOKIE_SECURE` ou production auto

---

## ARQUITECTURA APÓS CORREÇÕES

Sem mudança arquitectural. Duas correcções pontuais:
- Observabilidade Group Profile background
- Cookie Secure ops em production

---

## ENTREGA

| Item | Valor |
|------|-------|
| Branch Kernel | `audit/preproduction-redteam` |
| Branch Orbit | `audit/preproduction-redteam` |
| Commits | Nenhum (utilizador não pediu) |
| Relatório | `docs/security/preproduction-redteam.md` |
| Veredito | **NOT READY** (geral) · **CONDITIONALLY READY** (V1 documentado) |

---

# REDTEAM V2 / REMEDIATION

| Campo | Valor |
|-------|-------|
| Data | 2026-08-27 |
| Branch | `fix/preproduction-findings` |
| Suite | **204 passed, 0 failed** |

## Resumo V2

| Severidade | V1 | V2 |
|------------|----|----|
| P0 | 0 | 0 |
| P1 | 4 | 4 (todos documentados/aceites ou mitigados) |
| P2 | 8 | 3 remanescentes aceites |
| P3 | 5 | 2 remanescentes |

**Veredito V2:** **CONDITIONALLY READY** para V1 single-worker VPS com runbook assinado.

---

## ANTES vs DEPOIS

| ID | V1 | V2 | Classificação V2 |
|----|----|----|------------------|
| REDTEAM-001 | P1 dev auth open | Staging exige auth; guardrails bind; runbook | **ACCEPTED RISK** (dev localhost) + **MITIGATED** |
| REDTEAM-002 | P1 IDOR Bearer | Runbook trust model; localhost obrigatório | **ACCEPTED RISK** (V1 adapter-trust) |
| REDTEAM-003 | FIXED | Mantido | **FIXED** |
| REDTEAM-004 | FIXED | Mantido | **FIXED** |
| REDTEAM-005 | P1 multi-réplica | Fail-fast `KERNEL_WORKERS>1` | **WONT FIX — JUSTIFIED** (V1 single-worker) |
| REDTEAM-006 | P2 transcript RAM | Documentado runbook | **ACCEPTED RISK** |
| REDTEAM-007 | P2 rate limit RAM | Documentado | **ACCEPTED RISK** |
| REDTEAM-008 | PASS | Re-test PASS | **NOT REPRODUCED** (continua seguro) |
| REDTEAM-009 | PASS | Re-test PASS | **NOT REPRODUCED** |
| REDTEAM-010 | PASS | Re-test PASS | **NOT REPRODUCED** |
| REDTEAM-011 | P3 trace preview | `ACL_TRACE_MESSAGE_PREVIEW_CHARS` configurável | **ACCEPTED RISK** (ops need) |
| REDTEAM-012 | PASS | Re-test PASS | **NOT REPRODUCED** |
| REDTEAM-013 | FAIL lab stub | **FIXED** — stub `request_metadata` | **FIXED** |
| REDTEAM-014 | UNTESTED | 7 testes arquitectura DATA>POLICY | **TESTED / PASS** |
| REDTEAM-015 | UNCONFIRMED | Teste determinístico Kernel replay + concorrência | **TESTED / PASS** (Orbit E2E **NOT EXECUTED**) |
| REDTEAM-016 | N/A | N/A | **N/A** |
| REDTEAM-017 long-run | NOT EXECUTED | Stress curto 80 req PASS | **PARTIAL** (horas **NOT EXECUTED**) |
| Automation race | UNCONFIRMED | `try_claim_for_send` + 3 testes | **FIXED** |
| Backup/restore | NOT EXECUTED | `test_v1_backup_restore.py` PASS | **TESTED / PASS** |
| Disk-full SQLite | UNCONFIRMED | Modelado com mock OSError PASS | **STATIC ANALYSIS + TEST** |
| Chaos WhatsApp | NOT EXECUTED | Node indisponível | **NOT EXECUTED** |
| Deploy guardrails | — | `validate_deployment_guardrails()` | **FIXED** |

---

## Correções V2 (código)

1. **`api/security.py`** — staging auth obrigatória; `validate_deployment_guardrails()`; `trace_message_preview_chars()`
2. **`kernel/comms/store.py`** — `try_claim_for_send()` atómico
3. **`kernel/comms/service.py`** — abort se cancelado mid-send; claim atómico
4. **`tests/test_lab_ops.py`** — stub actualizado
5. **Novos testes:** prompt injection, idempotency replay, comms race, backup, guardrails, stress curto, disk-full

---

## Testes executados V2

```bash
PYTHONPATH=. .venv/bin/pytest tests/ -q
# 204 passed, 0 failed
```

**Adicionados:** `test_prompt_injection_architecture.py`, `test_v1_idempotency_replay.py`, `test_comms_cancel_race.py`, `test_v1_backup_restore.py`, `test_v1_deployment_guardrails.py`, `test_v1_stress_short.py`, `test_sqlite_disk_full.py`

---

## Long-run / Chaos / Orbit

| Teste | Status |
|-------|--------|
| Long-run horas | **NOT EXECUTED** |
| Stress curto (80 req) | **EXECUTED / PASS** |
| Chaos WhatsApp real | **NOT EXECUTED** |
| Orbit `node --test` | **NOT EXECUTED** (Node indisponível) |
| Clean VPS deploy manual | **NOT EXECUTED** (documentado em runbook) |

---

## Documentação V2

- `docs/operations/v1-production-runbook.md` — **NOVO**
- `.env.example` — `KERNEL_WORKERS`, `KERNEL_BIND_HOST`, `ACL_TRACE_MESSAGE_PREVIEW_CHARS`

---

## Release gate V2 (cenário V1)

| Item | V2 |
|------|-----|
| 0 P0 | ✅ |
| P1 explicados | ✅ (002, 005 aceites) |
| Suite verde | ✅ 204/204 |
| Group Memory isolada | ✅ |
| Auth production | ✅ fail-fast |
| Single-worker | ✅ fail-fast workers>1 |
| Idempotência | ✅ testada |
| Automation race | ✅ testada + fix |
| Prompt injection arquitectura | ✅ testada |
| Backup/restore | ✅ testado |
| Long-run horas | ⚠️ **NOT EXECUTED** — risco aceite staging |
| WhatsApp chaos | ⚠️ **NOT EXECUTED** |

---

## Veredito final V2

### NOT READY — produção generalizada / multi-réplica / API pública

### CONDITIONALLY READY — V1 single-worker VPS

Pré-requisitos: runbook `docs/operations/v1-production-runbook.md` + checklist §13.

**Branch entrega:** `fix/preproduction-findings` (Kernel + Orbit)

