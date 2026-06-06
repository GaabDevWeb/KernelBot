# ACL (KernelBot) — documentação

O conteúdo completo está na **wiki** em [`docs/wiki/`](docs/wiki/README.md).

## Início rápido

| Perfil | Onde |
|--------|------|
| **Aluno / curioso** | [docs/wiki/00-inicio-publico.md](docs/wiki/00-inicio-publico.md) → [FAQ](docs/wiki/19-faq-usuario.md) |
| **Contribuir** | [docs/wiki/18-contribuir.md](docs/wiki/18-contribuir.md) |
| **Subir staging local** | [TESTE-LOCAL.md](TESTE-LOCAL.md) → `./bin/staging-setup.sh` + `./bin/staging-serve.sh` |
| **Wiki técnica** | [docs/wiki/README.md](docs/wiki/README.md) |

## O que é (uma frase)

Chatbot educacional com **BM25** sobre aulas em MySQL: o LLM responde com trechos indexados como evidência; modo **anchored** por defeito, com advisory suave pós-geração.

## Índice da wiki

### Camada pública

- [00 — Início público](docs/wiki/00-inicio-publico.md)
- [18 — Como contribuir](docs/wiki/18-contribuir.md)
- [19 — FAQ utilizador](docs/wiki/19-faq-usuario.md)

### Técnica (01–17)

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
17. [Prompts — referência](docs/wiki/17-prompts-referencia.md)

## Repositório ISS

Documentação do pipeline de ingestão: repositório **ISS** (`documentation.md`, workflow `sync-kernelbot-knowledge.yml`).

## Legado

Este ficheiro era um documento monolítico (~450 linhas). O conteúdo foi reorganizado na wiki (maio/2026). Camada pública adicionada em junho/2026.
