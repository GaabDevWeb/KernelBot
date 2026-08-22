# SECURITY_AUDIT — True Kernel

| Campo | Valor |
|-------|-------|
| Data | 2026-07-26 |
| Branch | `security-audit` |
| Skill | `/security` v2.1 (autoridade) |
| Modo | standard/deep |
| Escopo | API Kernel (sem frontend); superfície multi-canal futura |
| Alterações de código | **Nenhuma** (auditoria only) |

---

## 1. Veredito Final

```text
BLOQUEADO - RISCO DETECTADO
```

**Para exposição directa à Internet pública** sem API gateway / WAF / autenticação por canal.

**Release condicional** (rede privada + gateway) pode ser aceite com mitigações P0 listadas em `SECURITY_HARDENING_PLAN.md`.

| Contagem | Qtd |
|----------|-----|
| CRÍTICO | 0* |
| ALTO | 3 |
| MÉDIO | 6 |
| BAIXO | 4 |
| INFORMATIVO | 4 |

\*Session fixation / pin cross-user classificado **ALTO** (não CRÍTICO) porque exige `session_id` conhecido/induzido — sobe a CRÍTICO se adapters usarem IDs previsíveis (`user_id`).

---

## 2. Security Score

**Security Score: 58/100 (D+)**

Base positiva: Bearer timing-safe, Pydantic, headers JSON, Docker non-root, redacção parcial de logs, ops endpoints protegidos.  
Penalização: API LLM aberta + rate-limit frágil + prompts em RAM + session client-controlled.

---

## 3. Verdict Trace

| Gate | Resultado |
|------|-----------|
| Auth-review | Falha parcial — sem AuthN de utilizador (by design); ops Bearer OK |
| API-review | Falha — superfície pública cara (`/chat`) e exfiltrável (`/search`) |
| LLM-review | Falha — geração sempre; Cursor workspace default |
| Judge merge | **≥1 ALTO Confirmado L2** → bloqueio para Internet pública |

Providers activados (registry): threat-modeler, auth-reviewer, api-security-reviewer, llm-security-reviewer (+ scan de superfícies).

---

## 4. Resumo Executivo

O True Kernel é um **núcleo HTTP sem autenticação de utilizador**, pensado para adapters. Isso é válido em **rede confiável**; é **inseguro** como endpoint público.

**Top 3 riscos:**

1. **SEC-001** — Abuso económico / DoS de tokens LLM via `POST /chat`
2. **SEC-002** — Cursor SDK com cwd = `project_root` (default)
3. **SEC-003** — Pin / memória por `session_id` escolhido pelo cliente

---

## 5. Threat Model (resumo)

| Actor | Objectivo | Capacidade |
|-------|----------|------------|
| Internet anon | Custo LLM, scraping RAG | HTTP público |
| Utilizador de canal | Pin poisoning, injection | Controla message/history/session_id |
| Insider / CI leak | Prompts + reload | Bearer reload/internal |
| Adapter mal configurado | Cross-user context | session_id previsível |

**Activos:** chave LLM, corpus MySQL/RAG, system prompts, histórico de conversas, disponibilidade do serviço.

---

## 6. Descobertas (SEC-XXX)

### SEC-001 — Abuso de custo LLM / DoS económico

| Campo | Valor |
|-------|-------|
| Severidade | **ALTO** |
| Probabilidade | Alta (bot / URL vazada) |
| Confiança | Confirmado |
| Evidence Level | L2 |
| OWASP | A04:2021 Insecure Design |
| CWE | CWE-770 |
| Onde | `kernel/rag/retrieval.py` (`allow_generation=True`); `api/routes.py` `POST /chat`; `api/rate_limit.py` |

**Descrição:** Toda mensagem válida em `/chat` dispara o LLM. Gates RAG não bloqueiam geração.

**Impacto:** Esgotamento de quota OpenRouter/Cursor; fatura; saturação de workers.

**Cenário:** Flood ≤30 req/IP/60s (×N réplicas) com `message`/`history` grandes.

**Consequência:** Indisponibilidade económica e operacional.

**Recomendação:** Gateway + quotas por canal; rate limit partilhado; hard-stop opcional por `reason`; caps de tokens.

---

### SEC-002 — Cursor SDK com workspace completo (default)

| Campo | Valor |
|-------|-------|
| Severidade | **ALTO** |
| Probabilidade | Média (se `ACL_LLM_PROVIDER=cursor`) |
| Confiança | Muito provável |
| Evidence Level | L1–L2 |
| OWASP | A01:2021 Broken Access Control / A05 |
| CWE | CWE-668 |
| Onde | `kernel/providers/chat_provider.py` (`_cursor_workspace`); `.env.example` `ACL_CURSOR_CHAT_ONLY=false` |

**Descrição:** Com chat-only desligado, o agente Cursor opera com cwd no project root.

**Impacto:** Leitura potencial de ficheiros do host/repo / tooling além do RAG.

**Cenário:** Prompt injection + provider cursor em produção com secrets no filesystem.

**Consequência:** Exfiltração de código/segredos / acções indesejadas do SDK.

**Recomendação:** `ACL_CURSOR_CHAT_ONLY=true` em produção; preferir OpenRouter HTTP; isolar FS.

---

### SEC-003 — Session fixation / pin cross-user

| Campo | Valor |
|-------|-------|
| Severidade | **ALTO** |
| Probabilidade | Alta se adapter usar IDs previsíveis |
| Confiança | Confirmado |
| Evidence Level | L2 |
| OWASP | A01:2021 |
| CWE | CWE-384 / CWE-639 |
| Onde | `kernel/schemas/chat.py` `session_id`; `kernel/memory/pinned_store.py` |

**Descrição:** `session_id` é client-controlled; pin não está ligado a identidade autenticada; `user_id` é só metadata.

**Impacto:** Contaminação / leitura de contexto RAG entre utilizadores do mesmo bot.

**Cenário:** Discord/Moodle usa `session_id=str(user_id)` → atacante reutiliza o mesmo ID.

**Consequência:** Quebra de isolamento entre utilizadores do canal.

**Recomendação:** UUID opaco server-side ou HMAC; documentar contrato dos adapters; nunca reutilizar user_id cru.

---

### SEC-004 — Rate limit process-local / IP não fiável

| Campo | Valor |
|-------|-------|
| Severidade | **MÉDIO** |
| Probabilidade | Alta em multi-réplica / proxy |
| Confiança | Confirmado |
| Evidence Level | L2 |
| Onde | `api/rate_limit.py`; `api/routes.py` (`request.client.host`) |

**Descrição:** Janela deslizante in-memory; sem Redis; sem Trusted Proxy.

**Impacto:** Limite contornável (N workers) ou partilhado incorrectamente (todos atrás do mesmo IP).

**Recomendação:** Edge rate-limit + Redis; configurar forwarded IP só de proxies confiáveis.

---

### SEC-005 — Token reload = token de observabilidade (fallback)

| Campo | Valor |
|-------|-------|
| Severidade | **MÉDIO** |
| Probabilidade | Média (CI leak) |
| Confiança | Confirmado |
| Evidence Level | L2 |
| Onde | `api/internal_routes.py` `_internal_token` |

**Descrição:** Sem `ACL_INTERNAL_BEARER_TOKEN`, usa `ACL_RELOAD_BEARER_TOKEN` para ler prompts/pipelines.

**Impacto:** Um secret de deploy dá rebuild **e** exfiltração de prompts.

**Recomendação:** Token interno obrigatório e distinto; least privilege.

---

### SEC-006 — Prompts completos em RAM (default on)

| Campo | Valor |
|-------|-------|
| Severidade | **MÉDIO** |
| Probabilidade | Alta se token interno vazado |
| Confiança | Confirmado |
| Evidence Level | L2 |
| Onde | `kernel/inspect/recorder.py` `ACL_INTERNAL_STORE_PROMPTS` default true |

**Descrição:** System+RAG+history guardados no ring buffer; expostos em `/internal/prompt/{id}`.

**Impacto:** PII + prompts de sistema + chunks educacionais.

**Recomendação:** Default `false` em produção; redacção; TTL.

---

### SEC-007 — Exfiltração via `POST /search` sem auth

| Campo | Valor |
|-------|-------|
| Severidade | **MÉDIO** |
| Probabilidade | Alta se URL pública |
| Confiança | Confirmado |
| Evidence Level | L2 |
| Onde | `api/routes.py` `/search`; snippets 500 chars |

**Descrição:** Retrieval público permite scraping do índice.

**Impacto:** Contorna LMS (Moodle) se Kernel estiver na Internet.

**Recomendação:** Auth no search ou rede privada; reduzir snippet.

---

### SEC-008 — `metadata` sem bound de tamanho

| Campo | Valor |
|-------|-------|
| Severidade | **MÉDIO** |
| Probabilidade | Média |
| Confiança | Muito provável |
| Evidence Level | L1 |
| Onde | `kernel/schemas/chat.py`, `search.py` |

**Descrição:** Dict livre ecoado na resposta.

**Impacto:** Pressão CPU/memória por request.

**Recomendação:** Limitar bytes/profundidade; 413.

---

### SEC-009 — OpenAPI/Swagger expõe mapa `/internal/*`

| Campo | Valor |
|-------|-------|
| Severidade | **BAIXO** |
| Confiança | Confirmado |
| Evidence Level | L2 |
| Onde | `app/factory.py` FastAPI defaults |

**Recomendação:** `docs_url=None` em produção ou proteger docs.

---

### SEC-010 — Disciplina fail-open (busca global)

| Campo | Valor |
|-------|-------|
| Severidade | **BAIXO** (mesmo índice) / sobe se multi-tenant futuro |
| Confiança | Confirmado |
| Evidence Level | L2 |
| Onde | `kernel/rag/search.py` `normalize_discipline` |

**Recomendação:** Fail-closed quando o canal exigir isolamento curricular.

---

### SEC-011 — Staging credentials versionadas + MySQL publicado

| Campo | Valor |
|-------|-------|
| Severidade | **BAIXO** (staging) / **ALTO** se compose usado em host exposto |
| Confiança | Confirmado |
| Evidence Level | L2 |
| Onde | `docker-compose.staging.yml`, `bin/staging-docker-up.sh` |

**Recomendação:** Bind `127.0.0.1`; passwords geradas; nunca reutilizar em cloud.

---

### SEC-012 — Dependências sem pin / sem lockfile

| Campo | Valor |
|-------|-------|
| Severidade | **BAIXO** |
| Confiança | Confirmado |
| Evidence Level | L1 |
| Onde | `requirements.txt`, `requirements-prod.txt`, Dockerfile base tag |

**Recomendação:** Lockfile + `pip-audit` + digest da imagem.

---

### SEC-013 — Logs de query sem redacção de Bearer/API keys no texto

| Campo | Valor |
|-------|-------|
| Severidade | **BAIXO** |
| Confiança | Confirmado |
| Evidence Level | L2 |
| Onde | `kernel/structured_log.py`; logs de query em context/retrieval |

**Recomendação:** Expandir `redact_secrets`; evitar logar query integral em prod.

---

### SEC-014 — `/internal/*` e GETs públicos sem rate limit

| Campo | Valor |
|-------|-------|
| Severidade | **BAIXO** |
| Confiança | Confirmado |
| Evidence Level | L2 |

**Recomendação:** Rate limit rígido em Bearer endpoints (anti brute-force).

---

### INFORMATIVO

| ID | Nota |
|----|------|
| INF-1 | `_hard_stop_result` sem call sites — defesa documentada inexistente no path vivo |
| INF-2 | ACL ≠ RBAC (Agente de Contexto Local) |
| INF-3 | Remoção do frontend elimina XSS de UI do monólito |
| INF-4 | CORS não configurado — OK para adapters server-side |

---

## 7. Prompt / RAG / Memória (síntese)

| Área | Defesas actuais | Lacuna |
|------|-----------------|--------|
| Prompt injection | Grounding textual; history sem role system | LLM sempre chamado; history client-controlled |
| RAG | Whitelist disciplina (regex) | Fail-open; `/search` público |
| Memória | Pin por session | Sem ownership; sem auth |
| Observabilidade | Bearer fail-closed se token ausente | Prompts on by default; token partilhado |

---

## 8. Disponibilidade

Componentes frágeis: provider LLM remoto, rebuild BM25 (`/reload`), workers Uvicorn sob history grande, rate-limit dict sem GC de chaves.

---

## 9. Evidence / Agents

- Security review: [Security](06d952f4-3031-410a-9634-c9b0c0347d93)
- Surface scan: [Explore](b32fb339-4c5f-412a-bf76-5254837feabb)

---

## 10. Documentos irmãos

- [`ATTACK_SURFACE_MAP.md`](ATTACK_SURFACE_MAP.md)
- [`SECURITY_HARDENING_PLAN.md`](SECURITY_HARDENING_PLAN.md)
