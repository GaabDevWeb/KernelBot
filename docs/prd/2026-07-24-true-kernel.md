# PRD — True Kernel (KernelBot → Kernel reutilizável)

| Campo | Valor |
|-------|-------|
| Data | 2026-07-24 |
| Autor | MegaBrain / missão utilizador |
| Status | approved |
| Versão | 1.0 |

## Contexto

**Proveniência:** missão explícita do utilizador (`/MegaBrain` — KernelBot → True Kernel), complementada por análise do código em `main` (`e436295`).

O KernelBot é hoje um monólito FastAPI que **acopla** o núcleo educacional (RAG BM25 + orquestração LLM) a uma **interface web** Vanilla JS servida pelo mesmo processo (`templates/`, `frontend/`, `GET /`, mounts `/src` e `/assets`).

O produto principal deve deixar de ser a UI e passar a ser um **Kernel de IA backend**, consumível por WhatsApp, Telegram, Discord, Moodle, LMS, web, mobile, CLI e integrações futuras — via **contrato HTTP universal**.

Estado actual verificado:

- Kernel funcional: `engine/` (search, retrieval, context, chat_provider) + `core/` (config, disciplines, prompts)
- UI acoplada: `frontend/`, `templates/index.html`, Jinja2, CSP orientada a browser
- `POST /chat` entrega SSE (`[ACL_META]` + tokens + `[DONE]`), validação JSON manual, sem Pydantic
- Directório `tests/` **ausente** no checkout (CI declara `pytest tests/`)
- Sem microserviços; MySQL `knowledge` + BM25 in-process

## Objectivos

Quando a feature estiver pronta:

1. O repositório **não** serve HTML/CSS/JS de interface.
2. O domínio Kernel vive sob estrutura clara (`kernel/` ou equivalente mapeado) **sem** dependências de UI.
3. Qualquer canal consome **apenas** o contrato universal de entrada/saída.
4. Endpoints mínimos públicos: `POST /chat`, `POST /search`, `GET /health`.
5. RAG, disciplinas, pin de sessão, providers LLM e grounding **preservam** comportamento já validado (refactor, não rewrite).

**Métricas de sucesso:**

- Zero rotas/static mounts de UI no composition root
- Suite de testes do kernel a verde (criar/recuperar cobertura mínima)
- `POST /chat` e `POST /search` documentados e exercitáveis sem browser
- Imagem Docker / requirements sem Jinja2, frontend, Tailwind/Playwright de UI

## Personas / Utilizadores

| Persona | Necessidade |
|---------|-------------|
| Adapter engineer | Integrar Discord/WhatsApp/etc. só com HTTP + JSON |
| Operador / DevOps | Health, reload de índice, deploy sem assets UI |
| Maintainer Kernel | Evoluir RAG/LLM sem tocar em HTML |
| Produto educacional | Respostas com disciplina, sources, confidence |

## Requisitos funcionais

| ID | Descrição | Prioridade | Critério de aceite |
|----|-----------|------------|-------------------|
| RF-001 | Remover frontend, templates, assets visuais e pipelines exclusivos de UI | Must | Pastas `frontend/`, `templates/` e deps UI ausentes; `GET /` não devolve HTML |
| RF-002 | Extrair lógica de negócio residual da UI (se houver) para kernel/API ou adapter de exemplo | Must | Nenhuma regra RAG/disciplina só em JS |
| RF-003 | Reorganizar código em Kernel + API (+ `adapters/` placeholder) | Must | Estrutura documentada em ARCHITECTURE; imports estáveis ou shims temporários |
| RF-004 | Contrato universal de entrada (`user_id`, `message`, `channel`, `metadata` + campos compatíveis) | Must | Schema Pydantic validado; OpenAPI reflecte |
| RF-005 | Contrato universal de saída (`answer`, `discipline`, `sources`, `confidence`, `metadata`) | Must | Resposta JSON canónica em `POST /chat` (modo não-stream) |
| RF-006 | `POST /chat` orquestra mensagem → escopo → RAG → LLM → resposta estruturada | Must | Fluxo equivalente ao actual `ContextManager` + `ChatProvider` |
| RF-007 | `POST /search` executa retrieval sem LLM | Must | Devolve candidatos/decisão/sources sem chamar provider |
| RF-008 | `GET /health` liveness | Must | `{"status":"ok"}` (ou equivalente estável) |
| RF-009 | Preservar disciplinas, BM25, grounding, pin, catálogo ISS opcional | Must | Comportamento documentado; testes/smoke API cobrem happy path |
| RF-010 | Manter endpoints operacionais necessários (`/reload` protegido, curriculum/catalog se ainda úteis a adapters) | Should | Não quebram contrato mínimo; auth Bearer onde já existe |
| RF-011 | Modo stream opcional (SSE) para adapters que precisem de tokens incrementais | Could | Opt-in (`stream: true` ou Accept); default = JSON |

## Requisitos não-funcionais

| ID | Descrição | Critério |
|----|-----------|----------|
| RNF-001 | Sem microserviços, Kafka, RabbitMQ ou filas novas | Arquitectura monólito FastAPI |
| RNF-002 | Simplicidade: preferir move/rename a rewrite | Diff focado; lógica RAG/LLM reconhecível |
| RNF-003 | Rate limit em `/chat` preservado (30/IP/60s) | Comportamento 429 mantido |
| RNF-004 | Segredos e Bearer de reload inalterados em espírito | Mesmas env vars; docs actualizados |
| RNF-005 | Branch exclusiva `trueKernel` a partir de `main` actualizada | Nunca commit directo em `main` nesta missão |

## Fora de escopo

- Implementar adapters reais WhatsApp/Discord/Telegram/Moodle (apenas pasta/placeholder e docs)
- Persistência partilhada multi-worker para pin/rate-limit
- Reescrever algoritmo BM25 ou prompts de grounding “do zero”
- Nova UI web ou design system
- Mudança de SGBD (permanece MySQL `knowledge`)

## Dependências e riscos

| Item | Tipo | Mitigação |
|------|------|-----------|
| Ausência de `tests/` no checkout | risco | Criar testes mínimos de API/kernel na mesma branch |
| SSE `[ACL_META]` usado por clientes legacy | risco | JSON canónico + stream opt-in; documentar migração |
| `allow_generation` é telemetria (LLM quase sempre chamado) | dependência | Não “corrigir” política sem RF; preservar |
| Assets UI já em falta (`output.css`, logos) | risco | Remoção completa elimina 404s de UI |
| CI espera `pytest tests/` | dependência | Restaurar suite na branch |

## Glossário

| Termo | Definição |
|-------|-----------|
| Kernel | Núcleo de domínio: orquestração, RAG, memória, políticas, providers |
| Adapter | Camada externa que traduz canal → contrato universal |
| ACL_META | Envelope SSE legado de metadados de turno |
| Silo | Índice BM25 por disciplina |
| Channel | Identificador do canal consumidor (`discord`, `whatsapp`, `cli`, …) |

## Referências

- ADR: `docs/adr/0001-true-kernel-monolith.md`
- API: `docs/API_SPEC.md`
- Arquitectura: `docs/ARCHITECTURE.md`
- Data model: `docs/DATA-MODEL.md`
- Missão utilizador: KernelBot → True Kernel (2026-07-24)
- Análise código: branch `main` @ `e436295`
