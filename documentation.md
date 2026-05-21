# ACL (KernelBot) — documentação

O conteúdo técnico completo está na **wiki** em [`docs/wiki/`](docs/wiki/README.md).

## Início rápido

| Ação | Onde |
|------|------|
| Subir staging local | [TESTE-LOCAL.md](TESTE-LOCAL.md) → `./bin/staging-setup.sh` + `./bin/staging-serve.sh` |
| Ler a wiki | [docs/wiki/README.md](docs/wiki/README.md) |
| Pipeline ISS → MySQL | [docs/wiki/10-integracao-iss-fase5b.md](docs/wiki/10-integracao-iss-fase5b.md) |
| Opção B2 (recall léxico) | [docs/wiki/11-enriquecimento-lexico-b2.md](docs/wiki/11-enriquecimento-lexico-b2.md) |
| Testes no chat | [docs/wiki/13-staging-testes.md](docs/wiki/13-staging-testes.md) |

## O que é (uma frase)

Chatbot educacional com **BM25** sobre aulas em MySQL: só chama o LLM quando os **gates** de retrieval passam; caso contrário, **hard stop** sem alucinar.

## Índice da wiki (16 secções)

1. [Visão geral](docs/wiki/01-visao-geral.md)
2. [Arquitetura](docs/wiki/02-arquitetura.md)
3. [Estrutura do código](docs/wiki/03-estrutura-codigo.md)
4. [Dados e MySQL](docs/wiki/04-dados-e-mysql.md)
5. [BM25 e chunking](docs/wiki/05-bm25-chunking.md)
6. [Gates e decisões](docs/wiki/06-gates-e-decisoes.md)
7. [APIs e SSE](docs/wiki/07-apis-e-sse.md)
8. [Frontend](docs/wiki/08-frontend-ui.md)
9. [Fluxos operacionais](docs/wiki/09-fluxos-operacionais.md)
10. [Integração ISS (Fase 5b)](docs/wiki/10-integracao-iss-fase5b.md)
11. [Enriquecimento léxico B2](docs/wiki/11-enriquecimento-lexico-b2.md)
12. [Configuração](docs/wiki/12-configuracao.md)
13. [Staging e testes](docs/wiki/13-staging-testes.md)
14. [Segurança e logs](docs/wiki/14-seguranca-observabilidade.md)
15. [Glossário](docs/wiki/15-glossario.md)
16. [Backlog](docs/wiki/16-backlog.md)

## Repositório ISS

Documentação do pipeline de ingestão: repositório **ISS** (`documentation.md`, workflow `sync-kernelbot-knowledge.yml`).

## Legado

Este ficheiro era um documento monolítico (~450 linhas). O conteúdo foi reorganizado na wiki (maio/2026). Para detalhe histórico de engenharia B1→B→B2, ver secção 11 da wiki.
