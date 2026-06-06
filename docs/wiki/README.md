# Wiki ACL (KernelBot)

Documentação do projecto. Cada página cobre um domínio; o índice abaixo é o ponto de entrada.

**Última revisão:** junho/2026 (camada pública, histórico de conversa, B3.1 advisory, alinhamento provider Cursor SDK default + contrato API/SSE).

---

## Camada pública

Para **alunos**, **curiosos** e **primeiro contacto** — linguagem directa, sem jargão de RAG.

| Página | Conteúdo |
|--------|----------|
| [Início — guia público](00-inicio-publico.md) | O que é, comandos rápidos, mapa da documentação |
| [Como contribuir](18-contribuir.md) | Ambiente, testes, PR, onde mexer no código |
| [FAQ — utilizador](19-faq-usuario.md) | Comandos, pin, memória, fontes, limites |

---

## Navegação técnica

| # | Página | Conteúdo |
|---|--------|----------|
| 1 | [Visão geral](01-visao-geral.md) | O que é o ACL, princípios, limitações |
| 2 | [Arquitetura](02-arquitetura.md) | Stack, componentes, diagramas |
| 3 | [Estrutura do código](03-estrutura-codigo.md) | Pastas, módulos, responsabilidades |
| 4 | [Dados e MySQL](04-dados-e-mysql.md) | Tabela `knowledge`, contrato 1 row = 1 aula |
| 5 | [BM25 e chunking](05-bm25-chunking.md) | Silos, janelas, Opção B2, IDF |
| 6 | [Gates e decisões](06-gates-e-decisoes.md) | Classificação retrieval, pós-geração, advisory |
| 7 | [APIs e SSE](07-apis-e-sse.md) | `/chat`, `history`, `/health/catalog`, `ACL_META` |
| 8 | [Frontend](08-frontend-ui.md) | UI, sessão, histórico, pin, componentes |
| 9 | [Fluxos operacionais](09-fluxos-operacionais.md) | Boot, chat, pin, reload |
| 10 | [Integração ISS (Fase 5b)](10-integracao-iss-fase5b.md) | Pipeline, CI, secrets |
| 11 | [Enriquecimento léxico B2](11-enriquecimento-lexico-b2.md) | Histórico completo de engenharia |
| 12 | [Configuração](12-configuracao.md) | `.env`, variáveis ACL, prompts |
| 13 | [Staging e testes](13-staging-testes.md) | Docker local, scripts `bin/`, chat |
| 14 | [Segurança e logs](14-seguranca-observabilidade.md) | Redacção, OOM, fallbacks |
| 15 | [Glossário](15-glossario.md) | Termos do domínio |
| 16 | [Backlog](16-backlog.md) | Débitos e próximos passos |
| 17 | [Prompts — referência](17-prompts-referencia.md) | Arquitetura ACL, inventário CL4R1T4S, padrões |

---

## Documentos relacionados (fora da wiki)

| Ficheiro | Uso |
|----------|-----|
| [TESTE-LOCAL.md](../../TESTE-LOCAL.md) | Comandos copy-paste para subir staging |
| [documentation.md](../../documentation.md) | Índice curto na raiz do repo |
| [PERGUNTAS-SMOKE-ESCOPO-PIN.md](../../PERGUNTAS-SMOKE-ESCOPO-PIN.md) | Smoke pin / escopo / advisory |
| [PERGUNTAS-SMOKE-HISTORICO-CHAT.md](../../PERGUNTAS-SMOKE-HISTORICO-CHAT.md) | Smoke memória multi-turno |
| [_GITHUB-WIKI-HOME.md](_GITHUB-WIKI-HOME.md) | Pacote copy-paste para a aba Wiki do GitHub (Home + FAQ + Contribuir) |
| Repositório **ISS** — `documentation.md` | Pipeline Jobs 1–5, ingest Job 2 |

---

## Leitura recomendada por perfil

| Perfil | Ordem |
|--------|-------|
| **Aluno / curioso** | [00](00-inicio-publico.md) → [19](19-faq-usuario.md) |
| **Novo contribuidor** | [00](00-inicio-publico.md) → [18](18-contribuir.md) → 1 → 2 → 3 → 9 → 7 |
| **Novo no projeto (técnico)** | 1 → 2 → 3 → 9 → 7 |
| **Operador / deploy** | 10 → 13 → 12 |
| **RAG / retrieval** | 5 → 6 → 17 → 11 |
| **Debug advisory / pin** | 6 → 8 → 13 |
