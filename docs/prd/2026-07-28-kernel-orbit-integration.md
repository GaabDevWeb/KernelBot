# PRD — Kernel ↔ Orbit Integration (API v1 canal-agnóstica)

| Campo | Valor |
|-------|-------|
| Data | 2026-07-28 |
| Autor | MegaBrain / missão utilizador |
| Status | approved |
| Versão | 1.0 |

## Contexto

**Proveniência:** missão explícita `/MegaBrain` (documento Kernel↔Orbit, Jul 2026), complementar ao PRD True Kernel (`docs/prd/2026-07-24-true-kernel.md`, status `approved`).

O ecossistema tem dois projectos:

| Projecto | Papel desejado |
|----------|----------------|
| **Kernel** (`KernelBot`) | Cérebro central: chat, RAG, memória, políticas, providers |
| **Orbit** (`OrbitBot`) | Adapter WhatsApp (Baileys): transporte, sessão, formatação, comandos locais |

Estado verificado do Kernel (auditoria 2026-07-28, branch de trabalho `feature/kernel-orbit-integration` a partir de `security-hardening`):

- Pipeline de chat funcional: `POST /chat` → `ContextManager` → RAG → `ChatProvider` → JSON (`stream=false`) ou SSE customizado
- Schemas existentes: `ChatRequest` / `ChatResponse` em `kernel/schemas/chat.py` (campos flat: `channel`, `user_id`, `session_id`, `message`, …)
- **Não existe** prefixo `/v1`, nem schema `ChannelContext`
- `adapters/` é apenas README normativo — sem código Orbit
- Memória pin: in-process (`PinnedSessionStore`); chave `channel:user_id:session_id`
- Sem agentes multi-tool no Kernel; “agente” no código = Cursor SDK LLM provider
- Auth de canal já endurecida (`ACL_CHANNEL_API_KEYS` / Bearer)

O Orbit hoje (fora deste repo) tipicamente fala com um LLM provider directo (ex.: OpenRouter). O objectivo é permitir substituir esse provider por um **KernelProvider** HTTP com mudança mínima no Orbit.

## Objectivos

Quando a feature estiver pronta:

1. O Kernel expõe **apenas** dois endpoints versionados novos: `GET /v1/health` e `POST /v1/chat`.
2. Contratos `ChannelContext`, `ChatRequest` (v1), `ChatResponse` (v1) são canal-agnósticos (WhatsApp, Discord, futuros).
3. `POST /v1/chat` **reutiliza** o pipeline existente (sem reimplementar RAG/LLM).
4. Endpoints legados (`/health`, `/chat`, …) **permanecem** (compatibilidade; sem breaking change nesta missão).
5. Documentação clara de como o Orbit deve consumir a API (contrato KernelProvider).

**Métricas de sucesso:**

- `GET /v1/health` → `{"status":"ok"}`
- `POST /v1/chat` com `platform` + `user` + `channel` + `message` devolve `ChatResponse` JSON
- Testes pytest cobrem os dois endpoints v1
- Zero introdução de filas, Redis obrigatório, microserviços ou event bus

## Personas / Utilizadores

| Persona | Necessidade |
|---------|-------------|
| Engenheiro Orbit | Trocar OpenRouterProvider → KernelProvider com HTTP + JSON mínimo |
| Engenheiro Discord (futuro) | Mesmo contrato `/v1/chat` sem campos WhatsApp |
| Maintainer Kernel | Evoluir RAG/LLM sem conhecer Baileys/Discord |
| Operador | Health versionado para probes do adapter |

## Decisões grill-me (2026-07-28) — congeladas

| ID | Decisão |
|----|---------|
| G1 | Adapters finos: só mensagem + metadados de canal; Kernel dono do contexto |
| G2 | Transcript store in-memory (sem Redis/MySQL); janela deslizante |
| G3 | `reset_context: true` limpa transcript **e** pin; adapters traduzem `/reset`; sem endpoint/comandos no Kernel |
| G4 | Chave: sem `session_id` → `platform:userId:channelId`; com → `…:sessionId`; transcript≡pin |
| G5 | Transcript + reset **só** em `/v1/chat`; legado `/chat` intacto |
| G6 | Default 16 pares; `ACL_TRANSCRIPT_MAX_TURNS` no bootstrap |
| G7 | Persistência transcript só em sucesso (par completo); `history` no body v1 = no-op |

## Requisitos funcionais

| ID | Descrição | Prioridade | Critério de aceite |
|----|-----------|------------|-------------------|
| RF-001 | Introduzir schema `ChannelContext` (`platform`, `user_id`, `channel_id`, `session_id` opcional) | Must | Pydantic; sem campos vendor (`jid`, `guild_id`, `phone`, …) |
| RF-002 | `ChatRequest` v1: `context` + `message` + opcionais (`discipline`, `metadata`, `stream`, `reset_context`, `history` no-op) | Must | OpenAPI; `extra=forbid`; `history` aceite mas ignorado |
| RF-003 | `ChatResponse` canónico (`answer`, `discipline`, `sources`, `confidence`, `metadata`) | Must | Compatível com `/chat` JSON |
| RF-004 | `GET /v1/health` | Must | `{"status":"ok"}`; sem auth |
| RF-005 | `POST /v1/chat` → pipeline existente (`ContextManager` + provider) | Must | Reutiliza RAG/LLM; default `stream=false` |
| RF-006 | Resolver chave de sessão v1 (G4); pin e transcript usam a mesma chave; mapear `platform`→`channel` interno | Must | Testes unitários da resolução |
| RF-007 | Auth/rate-limit iguais a `/chat` | Must | Mesmo Bearer + RL |
| RF-008 | Documentar consumo Orbit (KernelProvider) | Must | API_SPEC + adapters/README |
| RF-009 | Preservar `/health` e `/chat` legados sem mudança funcional | Must | Testes legados continuam a passar |
| RF-010 | Transcript store in-process: últimos N pares; default 16; env `ACL_TRANSCRIPT_MAX_TURNS` | Must | Só `/v1/chat`; append só em sucesso |
| RF-011 | `reset_context` opcional limpa transcript + pin da chave antes de processar a mensagem | Must | Sem endpoint extra |

## Requisitos não-funcionais

| ID | Descrição | Critério |
|----|-----------|----------|
| RNF-001 | Sem microserviços, Kafka, RabbitMQ, Redis obrigatório, CQRS, event bus | Diff só monólito FastAPI |
| RNF-002 | Menor mudança possível; reutilizar código | Handler v1 chama helpers partilhados com `/chat` ou delega |
| RNF-003 | Branch exclusiva `feature/kernel-orbit-integration` | Nenhuma alteração de código na branch base |
| RNF-004 | Sem renomeações cosméticas em massa | `engine→kernel` já feito; não reabrir |
| RNF-005 | Segurança: não enfraquecer auth de produção | Reutilizar `api/security.py` |

## Fora de escopo

- Implementar código do OrbitBot / Baileys neste repositório
- Adapter Discord real
- Novos endpoints além de `GET /v1/health` e `POST /v1/chat`
- Persistência durável / multi-worker do transcript ou pin
- Unificar legado `/chat` com transcript store
- Comandos textuais `/reset`/`/nova` no Kernel
- Reescrever protocolo SSE (v1 default = JSON)
- Agentes multi-tool / function-calling
- Remover ou deprecar formalmente `/chat` (fase futura pós-validação Orbit)
- Redis, filas, service mesh

## Dependências e riscos

| Item | Tipo | Mitigação |
|------|------|-----------|
| Pipeline `/chat` já seguro e testado | dependência | Extrair helper partilhado; testes de paridade v1↔legado |
| `session_id` rejeita só-dígitos | risco | Derivação opaca obrigatória no mapeamento v1 |
| Orbit espera streaming token-a-token | risco | v1 documenta JSON; SSE via `stream:true` opcional herdado — Orbit pode usar JSON primeiro |
| Working tree WIP (True Kernel + security) na branch base | risco | Branch feature a partir do estado actual; não resetar histórico |
| `kernel/tools/watcher.py` import órfão `engine.search` | dívida | Fora de escopo; não activar watcher nesta missão |

## Glossário

| Termo | Definição |
|-------|-----------|
| Platform | Identificador estável do canal lógico (`whatsapp`, `discord`, `cli`, …) — equivale ao `channel` interno legado |
| Channel (v1 `channel_id`) | Identificador da conversa/thread **dentro** da plataforma (ex.: chat id), **não** o nome da plataforma |
| KernelProvider | Cliente HTTP no Orbit que substitui o provider LLM directo |
| ChannelContext | Objeto de contexto multi-canal sem campos específicos de um vendor |

## Referências

- ADR: `docs/adr/0002-kernel-v1-channel-api.md`
- API: `docs/API_SPEC.md`
- Arquitectura: `docs/ARCHITECTURE.md`
- Data model: `docs/DATA-MODEL.md`
- PRD anterior: `docs/prd/2026-07-24-true-kernel.md`
- Auditoria: `docs/audit/` (contexto; não substitui este PRD)
