# Wiki ACL (KernelBot)

Documentação técnica em formato wiki. Cada página cobre um domínio do sistema; o índice abaixo é o ponto de entrada.

**Última revisão:** maio/2026 (Opção B2, Fase 5b, staging local).

---

## Navegação

| # | Página | Conteúdo |
|---|--------|----------|
| 1 | [Visão geral](01-visao-geral.md) | O que é o ACL, princípios, limitações |
| 2 | [Arquitetura](02-arquitetura.md) | Stack, componentes, diagramas |
| 3 | [Estrutura do código](03-estrutura-codigo.md) | Pastas, módulos, responsabilidades |
| 4 | [Dados e MySQL](04-dados-e-mysql.md) | Tabela `knowledge`, contrato 1 row = 1 aula |
| 5 | [BM25 e chunking](05-bm25-chunking.md) | Silos, janelas, Opção B2, IDF |
| 6 | [Gates e decisões](06-gates-e-decisoes.md) | Hard stop, thresholds, pós-geração |
| 7 | [APIs e SSE](07-apis-e-sse.md) | `/chat`, `/health/catalog`, `ACL_META` |
| 8 | [Frontend](08-frontend-ui.md) | UI, sessão, componentes de hard stop |
| 9 | [Fluxos operacionais](09-fluxos-operacionais.md) | Boot, chat, pin, reload |
| 10 | [Integração ISS (Fase 5b)](10-integracao-iss-fase5b.md) | Pipeline, CI, secrets |
| 11 | [Enriquecimento léxico B2](11-enriquecimento-lexico-b2.md) | Histórico completo de engenharia |
| 12 | [Configuração](12-configuracao.md) | `.env`, variáveis ACL, prompts |
| 13 | [Staging e testes](13-staging-testes.md) | Docker local, scripts `bin/`, chat |
| 14 | [Segurança e logs](14-seguranca-observabilidade.md) | Redacção, OOM, fallbacks |
| 15 | [Glossário](15-glossario.md) | Termos do domínio |
| 16 | [Backlog](16-backlog.md) | Débitos e próximos passos |

---

## Documentos relacionados (fora da wiki)

| Ficheiro | Uso |
|----------|-----|
| [TESTE-LOCAL.md](../../TESTE-LOCAL.md) | Comandos copy-paste para subir staging |
| [documentation.md](../../documentation.md) | Índice curto na raiz do repo (aponta para esta wiki) |
| Repositório **ISS** — `documentation.md` | Pipeline Jobs 1–5, ingest Job 2 |

---

## Leitura recomendada por perfil

| Perfil | Ordem |
|--------|-------|
| **Novo no projeto** | 1 → 2 → 3 → 9 → 7 |
| **Operador / deploy** | 10 → 15 → 13 → 12 |
| **RAG / retrieval** | 5 → 6 → 11 |
| **Debug hard stop** | 6 → 13 → 11 (testes chat) |
