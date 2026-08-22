# Auditoria — Unificação OrbitBot → Adapter Interno do Kernel

| Campo | Valor |
|-------|-------|
| Data | 2026-07-29 |
| Fase | 1 (auditoria — **sem alterações de código de migração**) |
| Status | aguarda decisão arquitectural bloqueante (Q1) |
| Branch Kernel | `feature/orbit-kernel-tracing` (trabalho tracing) |
| Branch Orbit | `feature/orbit-kernel-tracing` |

## Resumo executivo

O Orbit **já não tem IA própria**. O fluxo principal é:

```text
WhatsApp → Baileys (Node) → HTTP POST /v1/chat → Kernel (Python) → resposta → WhatsApp
```

Migrar “para dentro do Kernel” **não é só mover pastas**: Baileys é ecossistema **Node.js**; o Kernel é monólito **Python/FastAPI**. Não existe port maduro de Baileys em Python.

## Inventário (síntese)

### ADAPTER — migrar (transporte)

| Área | Paths Orbit | Notas |
|------|-------------|-------|
| Bootstrap Baileys | `app.js`, `src/bot.js` | QR, reconnect, `auth/` |
| Parsing / JIDs | `src/whatsappUtils.js` | puro, testado |
| Formatter MD→WA | `src/utils/whatsappFormatter.js` | puro, bem testado |
| Dedupe / locks | `src/messageDedupe.js`, `src/concurrency.js` | in-memory |
| Grupos | `src/groups/groupHandler.js`, `groupBuffer.js` | buffer só observabilidade |
| Reset mapping | `src/kernelContext.js` | `/reset`→`reset_context` |
| Comandos admin | `src/commands/**` | `/ai` hoje engana (stats locais) |
| Trigger teste | `src/testTrigger.js` | `@orbit` modo teste |

### CORE — não migrar / descartar

| Área | Paths | Decisão |
|------|-------|--------|
| KernelProvider HTTP | `src/providers/kernelProvider.js` | **eliminar** pós in-process/IPC |
| TraceClient HTTP | `src/traceClient.js` | **eliminar** → `emit_kernel` |
| OpenRouter / cache / retry | `openrouterProvider.js`, `core/cache.js`, `core/retry.js` | **DESCARTAR** (código morto) |
| Persona local | `aiConfig.js`, `prompts/SYSTEM.md` | legado; não é SSOT |
| openai.js | casca sobre KernelProvider | desaparece na unificação |

### OPS

| Item | Nota |
|------|------|
| Sem Dockerfile no Orbit | Kernel já tem Docker |
| `auth/` Baileys | segredo; migrar = novo QR recomendado |
| SQLite local Orbit | **não** é SSOT (Kernel transcript); útil como auditoria local opcional |

## Estado do Kernel (pronto para ChatService)

| Capacidade | Path | In-process? |
|------------|------|-------------|
| Pipeline chat | `api/chat_pipeline.run_chat_pipeline` | Sim (precisa extrair orquestração de `routes_v1`) |
| Transcript / pin | `kernel/memory/*` | Sim |
| Trace emit | `kernel.trace.emit_kernel` | Sim **no mesmo processo Python** |
| Adapters hoje | `adapters/README.md` só | Contrato actual = **HTTP externo** (ADR-0002) |

## Conflito bloqueante: 1 processo vs Baileys Node

A missão pede:

- um único serviço executável
- sem HTTP interno
- adapter WhatsApp (Baileys)

Opções reais:

| ID | Modelo | 1 binário? | Sem HTTP? | Baileys? | Risco |
|----|--------|------------|-----------|----------|-------|
| **A** | Kernel Python + **subprocess/sidecar Node** WhatsApp no mesmo deploy (compose/PM2) | Deploy unitário | IPC local (não HTTP público) | Sim | Médio |
| **B** | Manter 2 processos, colocalizados, HTTP localhost | Não | Não | Sim | Baixo (já funciona) |
| **C** | Reescrever WhatsApp em Python | Sim | Sim | Não (sem Baileys) | **Inviável** a curto prazo |
| **D** | Monorepo: Kernel Python + pacote `adapters/whatsapp` Node, orquestração única | Quase A | Bridge in-process via stdio/socket | Sim | Médio |

**Recomendação do arquitecto:** **A/D** — um *deploy unit* com Kernel Python + adapter WhatsApp Node gerido pelo bootstrap do Kernel (sem `/v1/chat` HTTP público entre eles; bridge local). Documentar como “monólito modular multi-runtime”, não microserviço.

## Ordem de migração (pós-aprovação Q1)

0. Decidir A/B/C/D  
1. Higiene Orbit (apagar mortos, corrigir `/ai stats`)  
2. Extrair `ChatService` Python (orquestração de `routes_v1` sem HTTP)  
3. Bridge adapter→ChatService (IPC ou import path definido por Q1)  
4. Portar módulos puros (formatter, JIDs, dedupe, kernelContext)  
5. Portar `bot.js` / grupos / Baileys session  
6. Trace in-process (eliminar `traceClient` HTTP)  
7. Testes paridade 1:1/grupo/reset/tracing  
8. Arquivar Orbit (read-only), não apagar

## Riscos

| Risco | Mitigação |
|-------|-----------|
| Sessão Baileys `auth/` | Novo QR no ambiente Kernel |
| `/reset` vs `/reset confirmar` | Testes de regressão explícitos |
| Transcript Kernel in-memory | Manter SQLite Orbit como log opcional ou aceitar volatilidade |
| ADR-0002 “HTTP only” | Novo ADR-0004 superseding parcial |

## Entregável desta fase

Este documento. **Nenhuma migração de código até Q1.**
