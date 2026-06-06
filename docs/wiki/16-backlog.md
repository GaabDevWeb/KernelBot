# Backlog e débitos técnicos

[← Índice](README.md)

## Concluído recentemente (junho/2026)

| Item | Notas |
|------|-------|
| Memória de conversa POC | `history` em POST /chat, `localStorage`, Nova conversa, testes |
| Pin + scope hints | `scope_hint`, `suggested_scope_command`, badge Continuando |
| B3 advisory anchored | Override destrutivo só em `strict` |
| B3.1 supressão advisory | `[Fonte:]`, lacuna, extensão pedagógica |
| `sources_note` condicional | Só quando retrieval adiciona fontes além do pin |
| Wiki camada pública | `00`, `18`, `19` + actualização 01/06/08 |

## Prioridade alta

| ID | Item | Impacto | Ficheiro(s) |
|----|------|---------|-------------|
| B1 | `LIMIT` / paginação no `SELECT` MySQL | OOM em catálogo grande | `engine/database.py` |
| B2 | Deploy coordenado ISS → `/reload` | Índice desatualizado em prod | workflow ISS, `api/routes.py` |
| B11 | README raiz do repo | Porta de entrada GitHub fraca | `README.md` |
| B12 | Indexar silo `/doc` no MySQL | Meta do bot só na wiki, não no RAG | ISS `content/doc/`, ingest |

## Prioridade média

| ID | Item | Impacto | Ficheiro(s) |
|----|------|---------|-------------|
| B4 | Meta no prompt (recomendação A opcional) | Queries body-only sem keywords no LLM | `engine/context.py` |
| B5 | Expandir `SecretRedactingFilter` | Traces com mais padrões sensíveis | `core/logging_config.py` |
| B13 | Corpus institucional (docentes, prazos) | Perguntas faculdade fora do RAG | ISS / KernelPlanner `corpus-meta/` |
| B14 | Espelhar wiki → GitHub Wiki | Tab Wiki no GitHub | script ou copy manual Home + links |

## Prioridade baixa / melhoria

| ID | Item | Notas |
|----|------|-------|
| B6 | Versionar schema SQL no repo | Hoje DDL só em `bin/staging-apply-schema.sh` |
| B7 | Testes automatizados BM25 B2 | Casos chunk0 vs body-only |
| B8 | Remover ou documentar `engine/watcher.py` | Legado |
| B9 | Ingest staging completo (todas as aulas) | Melhor representatividade nos testes |
| B10 | ~~Injectar `sticky_instruction` no pin~~ | **Feito** — merge pin + sticky em `context.py` |

## Push / release (bloqueado pelo utilizador)

| Passo | Estado |
|-------|--------|
| Push ISS `b80775d` | Pendente validação utilizador |
| Push KernelBot `2431a00` | Pendente |
| Reload produção pós-ingest | Pendente |
| Publicar wiki no GitHub | Pendente — SSOT em `docs/wiki/` |

## Histórico de decisões

| Data | Decisão | Riscos aceites |
|------|---------|----------------|
| 2026-05-25 | **Sempre LLM** — remover hard stops de retrieval; `ACL_RETRIEVAL_MODE` deprecado | Tokens, alucinação com chunks fracos |
| 2026-06-02 | Histórico POC sem auth | Cliente pode forjar `history` |

Registado em `.agent_history.md`. Plano espelho: KernelPlanner `PLAN.md`.
