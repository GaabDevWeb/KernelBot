# Configuração

[← Índice](README.md)

## Ficheiros de ambiente

| Ficheiro | Uso |
|----------|-----|
| `.env` | Produção / desenvolvimento (OpenRouter, MySQL Aiven, tokens) |
| `.env.example` | Template documentado |
| `.env.staging.local` | MySQL Docker `:3307` — **gitignore** |

## `KERNELBOT_ENV`

| Valor | Comportamento |
|-------|---------------|
| `staging` | `Settings` carrega `.env.staging.local` com prioridade |
| (outro / vazio) | `.env` padrão |

Scripts `bin/staging-*.sh` exportam `KERNELBOT_ENV=staging`.

## Variáveis obrigatórias (boot)

| Variável | Descrição |
|----------|-----------|
| `OPENROUTER_API_KEY` | API OpenRouter |
| Prompts | `core/systemPrompt/system_prompt.txt` e `sticky_instruction.txt` |

## MySQL

| Variável | Exemplo staging |
|----------|-----------------|
| `MYSQL_HOST` | `127.0.0.1` |
| `MYSQL_PORT` | `3307` |
| `MYSQL_USER` | `kernelbot` |
| `MYSQL_PASSWORD` | (local) |
| `MYSQL_DATABASE` | `kernelbot_staging` |

## ACL — retrieval

| Variável | Default |
|----------|---------|
| `ACL_RETRIEVAL_MIN_SCORE` | 1.5 |
| `ACL_RETRIEVAL_MIN_SCORE_MARGIN` | 0.15 |
| `ACL_RETRIEVAL_MIN_COVERAGE` | 0.34 |
| `ACL_RETRIEVAL_MIN_COVERAGE_WEIGHTED` | 0.34 |
| `ACL_RETRIEVAL_MIN_TERMS` | 2 |
| `ACL_RETRIEVAL_CANDIDATE_K` | 8 |
| `ACL_RETRIEVAL_TOP_K` | 4 |
| `ACL_RETRIEVAL_MAX_CHUNKS_PER_SOURCE` | 2 |
| `ACL_RETRIEVAL_MODE` | strict |

## ACL — operação

| Variável | Default | Descrição |
|----------|---------|-----------|
| `ACL_GLOBAL_CONTEXT` | geral | Escopo BM25 inicial |
| `ACL_PIN_TTL_TURNS` | 3 | TTL do pin |
| `ACL_RELOAD_TOKEN` | — | Token `/reload` |
| `ACL_CATALOG_ENABLED` | false | Catálogo ISS + index_gap |
| `ACL_CATALOG_PATH` | — | Path `lessons.json` |

## OpenRouter

| Variável | Notas |
|----------|-------|
| Modelos | Lista em `chat_provider.py` com fallback |
| Timeout | Configurado no provider |

## Logging

| Variável | Efeito |
|----------|--------|
| `ACL_LOG_FORMAT` | `text` ou `json` |
| `ACL_LOG_LEVEL` | INFO, DEBUG, … |

`SecretRedactingFilter` em `core/logging_config.py` — ver [14-seguranca-observabilidade.md](14-seguranca-observabilidade.md).

## Ver também

- [13-staging-testes.md](13-staging-testes.md)
