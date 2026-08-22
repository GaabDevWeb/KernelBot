# AUDIT_REVIEW — Revisão Independente da Auditoria

| Campo | Valor |
|-------|-------|
| Data | 2026-07-26 |
| Branch | `kernel-observability-implementation` |
| Fontes | `docs/audit/{SYSTEM_MAP,API_MAP,KERNEL_FLOW}.md` vs código |
| Revisor | MegaBrain (validação adversarial) |

## Método

Cada claim material dos três mapas foi confrontado com `kernel/`, `api/`, `app/`, `main.py`.  
Classificação: **Confirmado** · **Parcialmente Correto** · **Incorreto** · **Omissão**.

---

## Confirmado

| # | Claim | Evidência |
|---|-------|-----------|
| C1 | Sete endpoints públicos no router único | `api/routes.py` |
| C2 | Boot de serviços no lifespan, não no import | `main.py`, `app/factory.py` |
| C3 | Bug `_search_kernel` vs `_search_engine` bloqueava `/chat` | `context.py:755` vs `:1037` (corrigido nesta branch) |
| C4 | `allow_generation=True` em todo `build_decision` | `retrieval.py` |
| C5 | Pin só por `session_id` em RAM; `user_id` não armazena | `pinned_store.py`, routes |
| C6 | Disciplina inválida → fail-open (busca global) | `search.py` normalize + search_candidates |
| C7 | Rate limit 30/IP/60s em `/chat` e `/search` | `routes.py` + `rate_limit.py` |
| C8 | Frontend ausente do runtime | `factory.py` sem mounts/templates |
| C9 | SSE opt-in; JSON default | `ChatRequest.stream` |

## Parcialmente Correto

| # | Claim | Realidade |
|---|-------|-----------|
| P1 | “Hard stop raro” | `_hard_stop_result` sem chamadores; hard-stop efectivo só provider_error / override pós-geração `strict` |
| P2 | Catalog rescue também usa `_search_kernel` | Sim, mas era inalcançável após falha anterior |
| P3 | `tokens_used` = “fragmentos SSE” | Conta deltas de conteúdo **antes** da serialização SSE (OpenRouter/Cursor); semântica “não são tokens do provider” está correcta |
| P4 | `aggregate_sse` caminho JSON | Correcto, mas pode concatenar texto original + hard-stop pós-geração |

## Incorreto

| # | Claim | Correcção |
|---|-------|-----------|
| I1 | Rate limit é “token-bucket” (`SYSTEM_MAP`) | É **janela deslizante** de timestamps (`api/rate_limit.py`) |
| I2 | Modelos OpenRouter hardcoded no **provider** | Hardcoded em `kernel/config.py` (`Settings.models`); provider consome `settings.models` |
| I3 | Branch da auditoria em SYSTEM_MAP header | Documento escrito em `kernel-observability-audit`; working tree de implementação é outra branch |

## Omissão

| # | Lacuna na auditoria | Impacto |
|---|---------------------|---------|
| O1 | `/health` nunca verifica MySQL/índice/provider | Readiness falsa |
| O2 | Rate limit process-local, sem lock, IP via `request.client.host` | Multi-worker / proxy |
| O3 | Modelo OpenRouter com espaço trailing no 1º id | Risco de 404 no provider |
| O4 | `ACL_META` inicial frequentemente `tokens_used=0` sem meta final | Observabilidade de tokens inútil |
| O5 | `watcher.py` morto + importa `engine.search` + fora do Docker | Código morto enganador |
| O6 | `_normalize_conversation_history` existe mas rota HTTP não a chama (Pydantic cobre o essencial) | Documentar path real |

## Veredito sobre a auditoria

A auditoria é **majoritariamente fiável** nos fluxos centrais e no bloqueio do `/chat`.  
Não deve ser usada como SSOT sem cruzar: natureza do rate-limit, localização dos modelos, e semântica de tokens.

Agente de validação: [review](d6888df3-cb0c-4c63-8872-84057cca92be)
