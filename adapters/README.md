# Adapters

Adapters são consumidores externos do Kernel. Eles **não** importam módulos Python internos: comunicam somente pelo contrato HTTP.

## Contrato recomendado (v1)

| Método | Path | Uso |
|--------|------|-----|
| GET | `/v1/health` | Liveness do Kernel |
| POST | `/v1/chat` | Chat com `ChannelContext` |

Schemas: [`../docs/API_SPEC.md`](../docs/API_SPEC.md) · PRD: [`../docs/prd/2026-07-28-kernel-orbit-integration.md`](../docs/prd/2026-07-28-kernel-orbit-integration.md).

## Contrato de segurança (obrigatório)

1. **Auth de canal** — Em `KERNELBOT_ENV=production`, o Kernel exige `Authorization: Bearer <token>` em `POST /v1/chat`, `POST /chat` e `POST /search` (`ACL_API_BEARER_TOKEN` ou chave do canal em `ACL_CHANNEL_API_KEYS`).
2. **`session_id` opaco** — UUID/`secrets.token_urlsafe` (≥8 chars) **ou** omitir e deixar o Kernel derivar de `platform`+`user_id`+`channel_id`. **Proibido** reutilizar IDs só-numéricos como `session_id`.
3. **Isolamento de memória** — O pin RAG é chaveado como `platform:user_id:session_id` (após mapeamento). Envie sempre `platform` estável e `user_id` do utilizador do canal.
4. **Não exponha o Kernel na Internet** sem gateway — o adapter (WhatsApp/Telegram/Discord/…) é a fronteira AuthN/AuthZ do utilizador final.
5. **Sem campos vendor no schema** — Baileys JIDs, Discord snowflakes crus, etc. mapeiam-se para `user_id` / `channel_id` strings; extras vão em `metadata` dentro dos limites.

## Transcript de conversa (`POST /v1/chat`)

- O Kernel mantém, por chave `platform:user_id:channel_id[:session_id]`, uma janela deslizante do histórico de turnos (`ACL_TRANSCRIPT_MAX_TURNS`, default 16 pares). O adapter **não** precisa (e não deve) reenviar `history` no body — o campo é aceite por compatibilidade de schema mas é **sempre ignorado**; o histórico usado no prompt vem exclusivamente do transcript store do Kernel.
- **`reset_context: bool`** (default `false`) — quando `true`, limpa o transcript **e** o contexto RAG fixado (pin) da chave antes de processar o turno atual. Use para comandos do tipo "nova conversa"/"esquecer contexto" no adapter. A limpeza só ocorre **depois** da autenticação de canal ser validada (nunca antes) — não é um atalho para bypass de auth.
- **Não durável / não compartilhado entre processos** — o transcript store é `in-memory`, por processo do Kernel. Reinícios do serviço, deploys ou múltiplos workers/réplicas **perdem ou fragmentam** o histórico (cada worker tem seu próprio estado). Se o adapter precisar de continuidade garantida entre reinícios, deve manter seu próprio histórico e reenviá-lo via mensagens individuais — não existe endpoint de importação de histórico em `/v1/chat`.
- Com `stream=true`, o par (pergunta/resposta) da chamada corrente **não** é persistido no transcript (a resposta é entregue via SSE sem passar pelo agregador que produziria o texto final no handler); use `stream=false` quando a continuidade de contexto entre chamadas for necessária.

## Orbit (WhatsApp)

Responsabilidades do Orbit:

- Transporte e sessão Baileys
- Formatação de mensagens
- Comandos administrativos **locais**
- Cliente **KernelProvider**: `POST /v1/chat` → usar `answer`
- **Outbound proactivo** (Comunicações): `POST /internal/outbound/send` em `ORBIT_INTERNAL_HOST:ORBIT_INTERNAL_PORT` (default `127.0.0.1:8010`), auth `ACL_INTERNAL_BEARER_TOKEN`

O Kernel **não** fala com Baileys directamente. O cliente fica em `adapters/whatsapp/outbound.py`.

**Ops Center:** `/ops/adapters/whatsapp` mostra o status outbound (`outbound_status` → Orbit `/internal/outbound/status`) e métricas best-effort de traces. Discord: `/ops/adapters/discord` (stub).

Responsabilidades que **não** ficam no Orbit:

- RAG, grounding, disciplinas, providers LLM, memória pin do Kernel

## Endpoints legados (compat)

- `POST /chat` — schema flat (ainda suportado)
- `POST /search` — candidatos BM25 sem LLM
- `GET /health` — liveness sem prefixo

Hardening: [`../docs/security/SECURITY_HARDENING_PLAN.md`](../docs/security/SECURITY_HARDENING_PLAN.md).
