# ADR-0002: API v1 canal-agnóstica (`/v1/health`, `/v1/chat`) sem partir legado

| Campo | Valor |
|-------|-------|
| Data | 2026-07-28 |
| Status | accepted |
| Deciders | MegaBrain + missão Kernel↔Orbit |

## Contexto

O Kernel já expõe `POST /chat` e `GET /health` com schemas flat (`channel`, `user_id`, `session_id`). O Orbit (WhatsApp) e futuros canais (Discord) precisam de um contrato estável e versionado, com contexto de conversa explícito, sem acoplar o Kernel a Baileys ou a IDs nativos de um vendor.

Restrições: monólito; sem filas/Redis obrigatório; reutilizar pipeline; não fazer breaking change no contrato legado nesta entrega.

## Decisão

1. Introduzir router versionado **`/v1`** com **apenas** `GET /health` e `POST /chat` montados sob o prefixo (`GET /v1/health`, `POST /v1/chat`).
2. Adoptar `ChannelContext` + `ChatRequest` v1 + `ChatResponse` (canónico já existente) como contrato de integração multi-canal.
3. Mapear v1 → pipeline interno existente (`ContextManager` / `ChatProvider`); **não** duplicar RAG/LLM.
4. Manter `/chat` e `/health` legados intactos.
5. Default de `/v1/chat`: JSON (`stream=false`). Streaming SSE permanece opt-in herdado, não é requisito Orbit fase 1.
6. Trabalho exclusivo na branch `feature/kernel-orbit-integration`.

## Alternativas consideradas

### Alternativa A — Só documentar o `/chat` actual como contrato Orbit

- Prós: zero código.
- Contras: sem versionamento; `channel` ambíguo (plataforma vs thread); dificulta evoluir sem partir Orbit.

### Alternativa B — Substituir `/chat` por `/v1/chat` (breaking)

- Prós: um único contrato.
- Contras: parte clientes/CLI/testes actuais; fora da restrição “menor mudança”.

### Alternativa C — Gateway/BFF dedicado + event bus

- Prós: desacoplamento teórico.
- Contras: proibido pela missão (complexidade injustificada).

## Consequências

### Positivas

- Orbit pode implementar KernelProvider contra `/v1/chat` sem conhecer internals.
- Discord e outros reutilizam o mesmo contrato.
- Legado continua a funcionar durante a migração.

### Negativas / trade-offs

- Dois contratos públicos coexistindo (legado + v1) até depreciação futura.
- Derivação de `session_id` quando omitido adiciona lógica de mapeamento a testar.
- Memória pin continua in-process (limitação conhecida, fora de escopo).

## Referências

- PRD: `docs/prd/2026-07-28-kernel-orbit-integration.md`
- Relacionado: ADR-0001 (`docs/adr/0001-true-kernel-monolith.md`)
