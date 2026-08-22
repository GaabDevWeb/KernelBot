# Relatório Final — Kernel↔Orbit API v1

| Campo | Valor |
|-------|-------|
| feature_id | kernel-orbit-integration |
| branch | `feature/kernel-orbit-integration` |
| Data | 2026-07-28 |
| Plano | `memory/kernel-orbit-integration/plan.md` (17 IDs, lotes P1–P5) |
| Testes | `pytest tests/` → **42 passed** (0 falhas) |
| Segurança | `CONDICIONAL` — achado SEC-001 corrigido; SEC-002/SEC-003 residuais (ver abaixo) |
| PO Review | `OK` (critério técnico do plano cumprido — ver secção dedicada) |

---

## O que foi alterado

| Ficheiro | Mudança |
|----------|---------|
| `kernel/schemas/channel.py` | Novo — `ChannelContext` (`platform`, `user_id`, `channel_id`, `session_id?`), `extra="forbid"` |
| `kernel/schemas/chat.py` | `ChatRequestV1` adicionado (reusa `HistoryItem`, `validate_metadata`); `ChatRequest` legado sem alteração de comportamento |
| `kernel/schemas/validators.py` | `strip_and_require()` extraído para reuso DRY entre `ChatRequest`/`ChatRequestV1`/`SearchRequest` |
| `kernel/memory/session_key.py` | Nova `v1_memory_key()` (G4) — chave `platform:user_id:channel_id[:session_id]`, percent-encoded por segmento; `memory_session_key` legado intacto |
| `kernel/memory/transcript_store.py` | Novo — `TranscriptStore` (thread-safe, janela deslizante) |
| `kernel/config.py` | `Settings.transcript_max_turns` via `ACL_TRANSCRIPT_MAX_TURNS` (default 16, clamp 1–100) |
| `api/chat_pipeline.py` | Novo — `run_chat_pipeline()` extraído de `api/routes.py::chat()`; `/chat` passou a delegar a este helper |
| `api/routes_v1.py` | Novo — `GET /v1/health` (sem auth), `POST /v1/chat` (auth → `reset_context` → transcript → pipeline → persistência) |
| `app/state.py`, `main.py` | `AppServices.transcript_store` (default factory) + injeção em `build_services()` |
| `app/factory.py` | `include_router(routes_v1.router)` |
| `.env.example` | `ACL_TRANSCRIPT_MAX_TURNS` documentado |
| `docs/API_SPEC.md` | Secção "API v1" com `ChannelContext`, `GET /v1/health`, `POST /v1/chat` (incl. `reset_context`), exemplo de consumo Orbit |
| `adapters/README.md` | Contrato de segurança + secção "Transcript de conversa" (in-memory, `reset_context`, não durável) |
| `docs/DATA-MODEL.md` | Entidade `TranscriptStore` + nota de chave v1 (percent-encoding, SEC-001) — **esta missão** |
| `docs/ARCHITECTURE.md` | Fluxo 1 (Chat v1) detalhado com leitura/escrita de transcript e `reset_context` — **esta missão** |
| `tests/test_channel_context_schema.py`, `test_v1_session_key.py`, `test_transcript_store.py`, `test_v1_health.py`, `test_v1_chat.py` | Novos — cobrem contrato, isolamento de chave (incl. SEC-001), janela deslizante, e os 8 casos (a–h) de `/v1/chat` |

## O que permaneceu igual

- **`POST /chat` (legado):** comportamento byte-idêntico — sem transcript store, sem `reset_context`, sem mapeamento `ChannelContext`. Verificado por regressão completa (`test_chat_json.py`, `test_chat_schema.py`, `test_health.py`, `test_internal_api.py`, `test_search_endpoint.py`, `test_session_key.py`) sem diffs de asserts.
- **`GET /health`, `POST /search`:** sem alteração de contrato ou comportamento.
- **`api/security.py` (auth/rate-limit), `kernel/orchestrator/context.py` (`ContextManager.build_messages`):** reutilizados sem modificação — `/v1/chat` aplica a mesma auth de canal e o mesmo rate limit de `/chat`.
- **RAG, grounding, providers LLM, `PinnedSessionStore`:** lógica interna intacta; `/v1/chat` só passa a alimentar `conversation_history` a partir do `TranscriptStore` em vez do corpo da requisição.
- **Nenhum endpoint novo** além de `GET /v1/health` e `POST /v1/chat` (critério de fecho do plano).

## Como o Orbit consome a API

Fluxo feliz (`stream=false`):

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token-canal-whatsapp>" \
  -d '{
    "context": {
      "platform": "whatsapp",
      "user_id": "5511999999999",
      "channel_id": "5511888888888"
    },
    "message": "O que é normalização SQL?"
  }'
```

Resposta (mesmo shape de `/chat`):

```json
{
  "answer": "…",
  "discipline": "sql-modelagem-relacional",
  "sources": ["db:sql-modelagem-relacional/…"],
  "confidence": 0.95,
  "metadata": { "channel": "whatsapp", "user_id": "5511999999999", "session_id": null, "request_id": "…" }
}
```

Comando "nova conversa" no adapter (limpa transcript + pin da mesma chave, **após** validar o Bearer):

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token-canal-whatsapp>" \
  -d '{
    "context": { "platform": "whatsapp", "user_id": "5511999999999", "channel_id": "5511888888888" },
    "message": "olá de novo",
    "reset_context": true
  }'
```

O Orbit **não** reenvia `history` (campo aceite mas sempre ignorado — SSOT do histórico é o `TranscriptStore` do Kernel) e **não** implementa RAG/LLM localmente. Ver `docs/API_SPEC.md` (secção "API v1") e `adapters/README.md` para o contrato de segurança completo.

## Riscos conhecidos

| Risco | Estado | Detalhe |
|-------|--------|---------|
| **In-memory, não durável, não partilhado entre workers** | Aceite (trade-off de design, G2/ADR-0002) | `TranscriptStore` e `PinnedSessionStore` vivem no processo do Kernel. Reinícios/deploys/múltiplas réplicas perdem ou fragmentam histórico e contexto fixado. Fora de escopo desta missão (persistência durável = Redis/DB, não implementado de propósito). |
| **SEC-002 — `tests/` fora do controlo de versão** | **Residual, ação necessária** | `.gitignore` foi editado nesta branch para deixar de ignorar `tests/` (comentário "Não ignorar `tests/` — SEC-002"), **mas essa edição ainda não foi commitada** (`git diff HEAD -- .gitignore` mostra a remoção do padrão `tests/` como mudança não staged) **e o directório `tests/` continua totalmente não rastreado** (`git ls-files tests/` → 0 ficheiros). Numa branch/CI que só veja o histórico commitado, `pytest tests/ -q` não encontraria nenhum dos 42 testes (incluindo toda a suíte de regressão legada) — risco de falso-verde silencioso no CI. **Ação:** `git add tests/ .gitignore && git commit` antes de abrir PR/mergear (orquestrador pode corrigir em paralelo). |
| **SEC-003 — Bearer partilhado entre canais** | Residual, mitigável por configuração | `api/security.py::verify_channel_api_bearer` aceita **tanto** `ACL_API_BEARER_TOKEN` (global, válido para qualquer canal) **quanto** `ACL_CHANNEL_API_KEYS` (token por canal). Em deploys mínimos que só configuram o token global, todos os canais (WhatsApp/Discord/Telegram) partilham o mesmo segredo — o comprometimento de um adapter (ex.: leak no Orbit) permite personificar qualquer outro canal perante o Kernel. **Mitigação recomendada (não implementada nesta missão):** em produção, usar exclusivamente `ACL_CHANNEL_API_KEYS` com um token por canal, sem `ACL_API_BEARER_TOKEN` global; permite rotação/revogação independente por adapter. |
| Colisão de chave v1 por delimitador embutido | **Corrigido** (SEC-001) | `v1_memory_key` agora faz percent-encoding por segmento; coberto por `tests/test_v1_session_key.py::test_v1_memory_key_rejects_delimiter_injection_collision`. Documentado em `docs/DATA-MODEL.md`. |
| Riscos herdados (rate limit sem Redis, prompt injection, dependências sem lockfile, …) | Não re-abertos nesta missão | Ver `docs/security/SECURITY_RESIDUAL_RISKS.md` (R-001…R-007) — inalterados por esta feature. |

## Próximos passos

1. **Resolver SEC-002:** commitar `.gitignore` + `git add tests/` para que a suíte (legada e v1) exista no histórico versionado antes de qualquer merge/CI real.
2. **Avaliar SEC-003:** decidir se produção exige `ACL_CHANNEL_API_KEYS` exclusivo (sem token global) — decisão de deploy, não de código; atualizar `docs/security/SECURITY_RESIDUAL_RISKS.md` se adotado.
3. **Rodar S1 formalmente contra este REPORT** (checklist do plano, secção "Briefing — ID S1") caso ainda não tenha sido assinado como artefacto — as evidências de código/teste já suportam os 5 itens, mas não há ficheiro de checklist assinado dedicado a esta feature.
4. Persistência durável de transcript/pin (Redis) — fora de escopo, mencionada no PRD/ADR-0002 como possível evolução futura.
5. Depreciação do `/chat` legado em favor de `/v1/chat` — só após validação do Orbit em produção (decisão G5/grill-me Q5), fora desta missão.

## Referências

- Plano: `memory/kernel-orbit-integration/plan.md`
- PRD: `docs/prd/2026-07-28-kernel-orbit-integration.md`
- ADR: `docs/adr/0002-kernel-v1-channel-api.md`
- API: `docs/API_SPEC.md` · Dados: `docs/DATA-MODEL.md` · Arquitetura: `docs/ARCHITECTURE.md`
- Segurança pré-existente: `docs/security/SECURITY_RESIDUAL_RISKS.md`
