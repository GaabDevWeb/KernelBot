# SECURITY_HARDENING_PLAN — True Kernel

| Campo | Valor |
|-------|-------|
| Data | 2026-07-26 |
| Branch | `security-audit` |
| Nota | **Plano apenas** — nenhuma correção aplicada nesta auditoria |

## Princípio

Priorizar mitigações que permitam **exposição controlada via adapters**, sem reescrever o Kernel.

---

## P0 — Antes de Internet pública / canais reais

| # | Acção | Mitiga | Esforço | Impacto esperado |
|---|-------|--------|---------|------------------|
| P0.1 | API gateway / reverse proxy com auth por canal (API key ou mTLS) à frente de `/chat` e `/search` | SEC-001, SEC-007 | Médio | Elimina abuso anónimo directo |
| P0.2 | Rate limit no edge (e/ou Redis partilhado); IP real só de proxy confiável | SEC-001, SEC-004 | Médio | Limite efectivo multi-réplica |
| P0.3 | Produção: `ACL_CURSOR_CHAT_ONLY=true` **ou** só OpenRouter HTTP | SEC-002 | Baixo | Reduz superfície agente FS |
| P0.4 | Exigir `ACL_INTERNAL_BEARER_TOKEN` ≠ reload; falhar boot se iguais/ausente em prod | SEC-005 | Baixo | Least privilege ops vs observabilidade |
| P0.5 | `ACL_INTERNAL_STORE_PROMPTS=false` default em produção | SEC-006 | Baixo | Reduz blast radius de prompts |
| P0.6 | Contrato adapters: `session_id` = UUID opaco (nunca user_id cru) | SEC-003 | Baixo (docs+SDK) | Isolamento entre utilizadores do canal |

**Risco residual após P0:** prompt injection dentro do canal autenticado (aceitável com grounding + monitorização).

---

## P1 — Fortalecer Kernel (próximo sprint de hardening)

| # | Acção | Mitiga | Esforço | Notas |
|---|-------|--------|---------|-------|
| P1.1 | Bound em `metadata` (bytes/profundidade) | SEC-008 | Baixo | Sem mudar RAG |
| P1.2 | Rate limit em `/internal/*` e `/health/catalog` (anti brute-force) | SEC-014 | Baixo | |
| P1.3 | Desactivar `/docs`/`/redoc` em `KERNELBOT_ENV=production` | SEC-009 | Baixo | |
| P1.4 | Expandir `redact_secrets` (Bearer, sk-, OpenRouter) | SEC-013 | Baixo | |
| P1.5 | Quotas/caps de tokens no provider + métrica de custo | SEC-001 | Médio | |
| P1.6 | Hard-stop configurável por `reason` (feature flag; muda comportamento) | SEC-001 | Médio | RF produto |
| P1.7 | Fail-closed de disciplina inválida (flag por canal) | SEC-010 | Baixo | RF produto |
| P1.8 | Pin keyed por `(channel, user_id, session_id)` quando auth existir | SEC-003 | Médio | Requer auth |

---

## P2 — Supply chain & staging

| # | Acção | Mitiga | Esforço |
|---|-------|--------|---------|
| P2.1 | Lockfile + pin versões + `pip-audit` no CI | SEC-012 | Médio |
| P2.2 | Image digest pin no Dockerfile | SEC-012 | Baixo |
| P2.3 | MySQL staging bind `127.0.0.1`; passwords não versionadas | SEC-011 | Baixo |
| P2.4 | Readiness pública mínima sem vazar internals (`/health` vs deep) | disponibilidade | Baixo |

---

## Ordem sugerida de implementação (quando autorizada)

```text
1. Gateway + edge rate limit          (P0.1, P0.2)
2. Env hardening Cursor/prompts/token (P0.3–P0.5)
3. Docs/SDK session_id opaco          (P0.6)
4. Bounds metadata + docs off + redact(P1.1–P1.4)
5. Quotas LLM / hard-stop flags       (P1.5–P1.6)
6. Lockfile + staging hygiene         (P2.*)
```

---

## O que NÃO fazer agora (evitar overengineering)

- Microserviços de auth
- Kafka/filas
- RBAC completo dentro do Kernel antes dos adapters
- Reescrever RAG por “segurança”

---

## Critérios de desbloqueio (Internet pública)

| Critério | Estado actual |
|----------|---------------|
| Auth no perímetro de `/chat` e `/search` | ❌ |
| Rate limit partilhado/edge | ❌ |
| Cursor chat-only ou sem Cursor | ⚠️ config |
| Token interno distinto | ⚠️ opcional |
| Prompts off por default prod | ❌ (default on) |
| Contrato session_id documentado nos adapters | ⚠️ parcial |

Quando P0.1–P0.6 estiverem evidenciados → reavaliar veredito para **SEGURO PARA RELEASE (condicional)**.

---

## Referências

- [`SECURITY_AUDIT.md`](SECURITY_AUDIT.md)
- [`ATTACK_SURFACE_MAP.md`](ATTACK_SURFACE_MAP.md)
- Skill `/security` v2.1 — bloqueio por ALTO Confirmado L≥2 em exposição pública
