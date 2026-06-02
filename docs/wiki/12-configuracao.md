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
| `ACL_LLM_PROVIDER` | `cursor` (default) ou `openrouter` |
| `OPENROUTER_API_KEY` | Obrigatória se `ACL_LLM_PROVIDER=openrouter` |
| `CURSOR_API_KEY` | Obrigatória se `ACL_LLM_PROVIDER=cursor` |
| `ACL_CURSOR_MODEL` | Modelo Cursor SDK (default `composer-2.5`) |
| Prompts | `core/systemPrompt/` — ver [17-prompts-referencia.md](17-prompts-referencia.md) |

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
| `ACL_RETRIEVAL_MODE` | *(deprecado)* | Ignorado; gates são só classificação — sempre LLM + `grounding_strict` |
| `ACL_DISAMBIGUATION_ENABLED` | false | `true` = `ambiguous_retrieval` pode gerar com `grounding_disambiguation.txt` |

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

## Cursor SDK

Quando `ACL_LLM_PROVIDER=cursor`, o backend usa o pacote `cursor-sdk` (Python) em runtime local.

| Variável | Notas |
|----------|-------|
| `CURSOR_API_KEY` | Chave no Cursor Dashboard → API Keys |
| `ACL_CURSOR_MODEL` | Ex.: `composer-2.5` |

## Logging

| Variável | Efeito |
|----------|--------|
| `ACL_LOG_FORMAT` | `text` ou `json` |
| `ACL_LOG_LEVEL` | INFO, DEBUG, … |

`SecretRedactingFilter` em `core/logging_config.py` — ver [14-seguranca-observabilidade.md](14-seguranca-observabilidade.md).

## Ficheiros de prompt (`core/systemPrompt/`)

| Ficheiro | Boot obrigatório |
|----------|------------------|
| `system_prompt.txt` | Sim |
| `grounding_strict.txt` | Sim |
| `grounding_permissive.txt` | Legado | Não injectado em runtime (histórico) |
| `grounding_disambiguation.txt` | Sim | `ACL_DISAMBIGUATION_ENABLED=true` + `ambiguous_retrieval` |
| `catalog_router.txt` | Sim |
| `sticky_instruction.txt` | Sim (carregado; inject no chat pendente — ver wiki §17) |

## Ver também

- [17-prompts-referencia.md](17-prompts-referencia.md)
- [13-staging-testes.md](13-staging-testes.md)
