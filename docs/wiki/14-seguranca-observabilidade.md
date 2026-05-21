# Segurança e observabilidade

[← Índice](README.md)

## Logging estruturado

| Módulo | Função |
|--------|--------|
| `core/structured_log.py` | `log_event(name, **fields)` |
| `core/logging_config.py` | Formatters, handlers, filtros |

### Eventos úteis (exemplos)

| Evento | Quando |
|--------|--------|
| `db_chunk_row_skipped` | Row > `MAX_CONTENT_CHARS` |
| `meta_block_malformed` | Marcadores B2 incompletos |
| `meta_block_parse_error` | Erro ao parsear meta |
| `search_rebuild_complete` | Após `rebuild()` |
| `chat_decision` | Decisão retrieval |

## Redacção de segredos

`SecretRedactingFilter` + `redact_secrets()`:

- Mascaram tokens em mensagens de log.
- `exc_info=True` preservado — **não** amputar stack traces por defeito.

**Backlog:** expandir padrões (API keys adicionais, URLs com credenciais) — [16-backlog.md](16-backlog.md).

## Erros de ingest (ISS)

`_sanitize_error()` em `ingest-knowledge.py` — não vazar passwords em logs CI.

## Tokens sensíveis

| Secret | Superfície |
|--------|------------|
| `OPENROUTER_API_KEY` | Env, logs (redact) |
| `ACL_RELOAD_TOKEN` | Header `/reload` |
| MySQL password | Env, GHA secrets |

**Nunca** commitar `.env` ou `.env.staging.local`.

## OOM e memória

| Risco | Mitigação actual | Backlog |
|-------|------------------|---------|
| `fetch_db_chunks` carrega tudo | Skip rows > 4M chars | `LIMIT` paginado (B1) |
| Índice RAM grande | Rebuild explícito | Monitorizar RAM em prod |

## Fallbacks seguros

| Situação | Comportamento |
|----------|---------------|
| MySQL unreachable no `fetch_indexed_lesson_keys` | `frozenset()` vazio (não crash) |
| Meta malformada | Legacy chunking, log ERROR |
| OpenRouter falha | `provider_error`, mensagem ao utilizador |

## Superfície de ataque (resumo)

| Vector | Mitigação |
|--------|-----------|
| `/reload` sem token | 401/403 |
| Prompt injection via conteúdo | Chunks só de MySQL controlado; gates pós-geração |
| Exfiltração via logs | Redactor |

## Ver também

- [16-backlog.md](16-backlog.md)
