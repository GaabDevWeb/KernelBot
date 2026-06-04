# Backlog e débitos técnicos

[← Índice](README.md)

## Prioridade alta

| ID | Item | Impacto | Ficheiro(s) |
|----|------|---------|-------------|
| B1 | `LIMIT` / paginação no `SELECT` MySQL | OOM em catálogo grande | `engine/database.py` |
| B2 | Deploy coordenado ISS → `/reload` | Índice desatualizado em prod | workflow ISS, `api/routes.py` |

## Prioridade média

| ID | Item | Impacto | Ficheiro(s) |
|----|------|---------|-------------|
| B3 | ~~Calibrar `post_generation_flags`~~ | **Onda 1:** advisory em anchored; override só em `strict` | `engine/retrieval.py`, `chat_provider.py`, UI |
| B4 | Meta no prompt (recomendação A opcional) | Queries body-only sem keywords no LLM | `engine/context.py` |
| B5 | Expandir `SecretRedactingFilter` | Traces com mais padrões sensíveis | `core/logging_config.py` |

## Prioridade baixa / melhoria

| ID | Item | Notas |
|----|------|-------|
| B6 | Versionar schema SQL no repo | Hoje DDL só em `bin/staging-apply-schema.sh` |
| B7 | Testes automatizados BM25 B2 | Casos chunk0 vs body-only |
| B8 | Remover ou documentar `engine/watcher.py` | Legado |
| B9 | Ingest staging completo (todas as aulas) | Melhor representatividade nos testes |
| B10 | ~~Injectar `sticky_instruction` no pin~~ | **Onda 1:** merge pin + sticky em `context.py` — ver [09-fluxos-operacionais.md](09-fluxos-operacionais.md) §4 |

## Push / release (bloqueado pelo utilizador)

| Passo | Estado |
|-------|--------|
| Push ISS `b80775d` | Pendente validação utilizador |
| Push KernelBot `2431a00` | Pendente |
| Reload produção pós-ingest | Pendente |

## Histórico de decisões

| Data | Decisão | Riscos aceites |
|------|---------|----------------|
| 2026-05-25 | **Sempre LLM** — remover hard stops de retrieval; `ACL_RETRIEVAL_MODE` deprecado | Tokens, alucinação com chunks fracos |

Registado em `.agent_history.md`. Plano espelho: KernelPlanner `PLAN.md`.
