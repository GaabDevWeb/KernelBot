# Kernel — documentação

O produto é uma **API Kernel** (RAG BM25 + LLM). A wiki histórica está em [`docs/wiki/`](docs/wiki/README.md). Contratos actuais: [`docs/API_SPEC.md`](docs/API_SPEC.md), arquitectura: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Início rápido

| Perfil | Onde |
|--------|------|
| **Integrar adapter** | [docs/API_SPEC.md](docs/API_SPEC.md) → [adapters/README.md](adapters/README.md) |
| **Contribuir** | [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) |
| **Subir staging local** | [docs/wiki/13-staging-testes.md](docs/wiki/13-staging-testes.md) → `./bin/staging-setup.sh` + `./bin/staging-serve.sh` |
| **Deploy produção** | [docs/wiki/20-deploy-railway.md](docs/wiki/20-deploy-railway.md) |
| **Wiki técnica** | [docs/wiki/README.md](docs/wiki/README.md) |

## O que é (uma frase)

Núcleo educacional HTTP: BM25 sobre aulas em MySQL + orquestração LLM; qualquer canal (Discord, Moodle, CLI, …) consome o contrato JSON.

## Endpoints mínimos

- `GET /health`
- `POST /chat` (JSON canónico; `stream: true` → SSE)
- `POST /search` (RAG sem LLM)

## Índice da wiki

### Camada pública / integração

- [API Spec](docs/API_SPEC.md)
- [Architecture](docs/ARCHITECTURE.md)
- [PRD True Kernel](docs/prd/2026-07-24-true-kernel.md)
- [ADR-0001](docs/adr/0001-true-kernel-monolith.md)

### Técnica (wiki)

1. [Visão geral](docs/wiki/01-visao-geral.md)
2. [Arquitetura](docs/wiki/02-arquitetura.md) *(actualizada — UI removida)*
3. [Estrutura do código](docs/wiki/03-estrutura-codigo.md) *(parcialmente histórica)*
4. [Dados e MySQL](docs/wiki/04-dados-e-mysql.md)
5. [BM25 e chunking](docs/wiki/05-bm25-chunking.md)
6. [Gates e decisões](docs/wiki/06-gates-e-decisoes.md)
7. [APIs e SSE](docs/wiki/07-apis-e-sse.md) *(contrato JSON + SSE opt-in)*
8. [Frontend](docs/wiki/08-frontend-ui.md) — **removido do produto; página histórica**
9. [Fluxos operacionais](docs/wiki/09-fluxos-operacionais.md)
10. [Integração ISS](docs/wiki/10-integracao-iss-fase5b.md)
11. [Enriquecimento léxico B2](docs/wiki/11-enriquecimento-lexico-b2.md)
12. [Configuração](docs/wiki/12-configuracao.md)
13. [Staging e testes](docs/wiki/13-staging-testes.md)
14. [Segurança e logs](docs/wiki/14-seguranca-observabilidade.md)
15. [Glossário](docs/wiki/15-glossario.md)
16. [Prompts — referência](docs/wiki/17-prompts-referencia.md)
17. [Deploy](docs/wiki/20-deploy-railway.md)

## Repositório ISS

Documentação do pipeline de ingestão: repositório **ISS**.
