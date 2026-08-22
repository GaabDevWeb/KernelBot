# SECURITY_RESIDUAL_RISKS — Pós-Hardening

| Campo | Valor |
|-------|-------|
| Data | 2026-07-26 |
| Branch | `security-hardening` |
| Veredito | `SEGURO PARA RELEASE (CONDICIONAL)` |
| Score | ~78/100 |

## Riscos ALTO/CRÍTICO abertos

**Nenhum**, desde que as condições de production do `SECURITY_REVIEW.md` sejam cumpridas.

| Risco se condições falharem | Nota |
|-----------------------------|------|
| Deploy production sem `ACL_API_BEARER_TOKEN` | Boot **bloqueia** (fail-fast) |
| Adapter usa `session_id` partilhado sem `user_id` | Isolamento degrada para `_anon` |

## Débito de segurança (aceite conscientemente)

| ID | Risco | Severidade | Justificativa | Próximo passo |
|----|-------|------------|---------------|---------------|
| R-001 | Rate limit in-process (sem Redis) | MÉDIO | Evitar infra nova nesta sprint | Edge limit (nginx/Cloudflare) ou Redis |
| R-002 | Prompt injection / jailbreak semântico | MÉDIO | Grounding textual já existe; hard-stop morto (INF-1) | Avaliar hard-stop por `reason` (RF produto) |
| R-003 | LLM sempre chamado (allow_generation=True) | MÉDIO | Auth+RL reduzem abuso; mudar muda produto | Quotas/tokens + flag hard-stop |
| R-004 | Dependências sem lockfile (SEC-012) | BAIXO | Esforço médio; não bloqueante | `pip-compile` + `pip-audit` CI |
| R-005 | Curriculum público (Novo-A) | BAIXO | Metadados LMS; baixo impacto | Auth se catálogo for sensível |
| R-006 | Passwords staging no repo | BAIXO | Só loopback local | Gerar via env local não versionado |
| R-007 | Multi-tenant true isolation | — | Fora de escopo mono-índice | Pin+disciplina já endurecidos |

## O que NÃO foi introduzido (de propósito)

- Redis / filas / microserviços
- RBAC completo de utilizador final no Kernel
- Gateway externo (responsabilidade do deploy/adapters)
- Reescrita do RAG

## Checklist de deploy seguro

- [ ] `KERNELBOT_ENV=production`
- [ ] `ACL_API_BEARER_TOKEN` ou `ACL_CHANNEL_API_KEYS`
- [ ] `ACL_INTERNAL_BEARER_TOKEN` ≠ `ACL_RELOAD_BEARER_TOKEN`
- [ ] `ACL_CURSOR_CHAT_ONLY=true` (ou OpenRouter)
- [ ] `ACL_INTERNAL_STORE_PROMPTS=false`
- [ ] Kernel só acessível por adapters / rede privada
- [ ] Rate limit no edge
- [ ] Adapters: UUID `session_id` + `user_id` + `channel`

## Referências

- [`SECURITY_REVIEW.md`](SECURITY_REVIEW.md)
- [`SECURITY_FIXES_APPLIED.md`](SECURITY_FIXES_APPLIED.md)
- [`SECURITY_AUDIT.md`](SECURITY_AUDIT.md)
- [`SECURITY_HARDENING_PLAN.md`](SECURITY_HARDENING_PLAN.md)
