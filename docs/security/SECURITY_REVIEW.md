# SECURITY_REVIEW — Validação da Auditoria + Hardening

| Campo | Valor |
|-------|-------|
| Data | 2026-07-26 |
| Branch | `security-hardening` |
| Skill | `/security` v2.1 |
| Fonte | `docs/security/SECURITY_AUDIT.md` + código actual |

## 1. Matriz de validação da auditoria

| ID | Auditoria | Validação código | Severidade pós-review |
|----|-----------|------------------|------------------------|
| SEC-001 | ALTO — abuso LLM | **Confirmado** | ALTO → mitigado (auth canal + RL) |
| SEC-002 | ALTO — Cursor workspace | **Confirmado** | ALTO → mitigado (default chat-only) |
| SEC-003 | ALTO — pin cross-user | **Confirmado** | ALTO → mitigado (chave composta + rejeita dígitos) |
| SEC-004 | MÉDIO — RL process-local | **Confirmado** | MÉDIO (parcial: trusted proxy + multi-chave; sem Redis) |
| SEC-005 | MÉDIO — token partilhado | **Confirmado** | MÉDIO → mitigado em production |
| SEC-006 | MÉDIO — prompts default on | **Confirmado** | MÉDIO → mitigado (default off) |
| SEC-007 | MÉDIO — /search público | **Confirmado** | MÉDIO → mitigado (auth + snippet 200) |
| SEC-008 | MÉDIO — metadata unbounded | **Confirmado** | MÉDIO → mitigado |
| SEC-009 | BAIXO — OpenAPI | **Confirmado** | BAIXO → mitigado em production |
| SEC-010 | BAIXO — fail-open disciplina | **Confirmado** | BAIXO → mitigado (flag; default prod) |
| SEC-011 | BAIXO — staging ports | **Confirmado** | BAIXO → mitigado (bind 127.0.0.1) |
| SEC-012 | BAIXO — deps sem pin | **Confirmado** | BAIXO — **documentado** (sem lockfile nesta sprint) |
| SEC-013 | BAIXO — redact incompleto | **Confirmado** | BAIXO → mitigado |
| SEC-014 | BAIXO — /internal sem RL | **Confirmado** | BAIXO → mitigado |

### Novos achados (auditoria → confirmados no review)

| ID | Achado | Severidade | Acção |
|----|--------|------------|-------|
| Novo-A | Curriculum público | BAIXO | Documentado (metadados) |
| Novo-B | Buckets RL sem GC | BAIXO | Mitigado (GC) |
| Novo-C | X-Request-Id client-controlled | BAIXO | Mitigado (UUID server-only) |

Nenhum item classificado **Incorreto**.

## 2. Priorização (impacto × probabilidade × facilidade × alcance)

| Prioridade | IDs | Decisão |
|------------|-----|---------|
| ALTO | SEC-001, 002, 003 | Corrigir nesta sprint |
| MÉDIO baixo custo | SEC-005, 006, 007, 008, 013, 014, 009, 010, 011 | Corrigir |
| MÉDIO residual | SEC-004 (Redis) | Documentar residual |
| BAIXO | SEC-012, Novo-A | Documentar |

## 3. Veredito pós-hardening (Judge)

```text
SEGURO PARA RELEASE (CONDICIONAL)
```

**Condições:**

1. `KERNELBOT_ENV=production` com `ACL_API_BEARER_TOKEN` (ou channel keys) + `ACL_INTERNAL_BEARER_TOKEN` ≠ reload
2. Kernel **não** exposto anonimamente na Internet (adapters/gateway à frente)
3. `ACL_CURSOR_CHAT_ONLY=true` (default) ou provider OpenRouter
4. Adapters usam `session_id` opaco + `user_id`/`channel` correctos

**Security Score (estimado):** 58 → **78/100 (C+)**

## 4. Threat coverage residual

| Ameaça | Estado |
|--------|--------|
| Abuso anónimo /chat | Mitigado em production (401 sem Bearer) |
| Scraping /search | Mitigado em production + snippet menor |
| Pin cross-user | Mitigado se adapters enviarem user_id |
| Cursor FS | Mitigado por default |
| Prompt injection | Residual (LLM + history client) — debt |
| Multi-réplica RL | Residual sem Redis — edge recommended |
| Supply chain pins | Residual |

## 5. Evidence

- Testes: `16 passed` (`pytest tests/`)
- Providers: validação estática + hardening implementado nesta branch
