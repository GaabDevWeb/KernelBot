# Configuração

[← Índice](README.md)

**Última revisão:** junho/2026 (alinhado a `core/config.py` + `.env.example`).

Toda a configuração de runtime vem do ambiente (`.env`), carregada por `Settings.load()`. Textos de prompt vêm de ficheiros em `core/systemPrompt/`.

## Ficheiros de ambiente

| Ficheiro | Uso |
|----------|-----|
| `.env` | Produção / desenvolvimento (provider LLM, MySQL, tokens) |
| `.env.example` | Template documentado (copiar para `.env`) |
| `.env.staging.local` | MySQL Docker `:3307` — **gitignore** (modelo em `.env.staging.example`) |

## `KERNELBOT_ENV`

| Valor | Comportamento |
|-------|---------------|
| `staging` | `Settings` carrega `.env.staging.local` com prioridade (`override=True`) |
| (outro / vazio) | `.env` padrão |

Scripts `bin/staging-*.sh` exportam `KERNELBOT_ENV=staging`.

## Provider LLM (boot)

| Variável | Default | Descrição |
|----------|---------|-----------|
| `ACL_LLM_PROVIDER` | `cursor` | `cursor` (Cursor SDK, runtime local) ou `openrouter` |
| `OPENROUTER_API_KEY` | — | **Obrigatória** se `ACL_LLM_PROVIDER=openrouter` |
| `CURSOR_API_KEY` | — | **Obrigatória** se `ACL_LLM_PROVIDER=cursor` |
| `ACL_CURSOR_MODEL` | `composer-2.5` | Modelo do Cursor SDK |

O boot falha (`RuntimeError`) se a chave do provider selecionado estiver ausente. A lista de modelos OpenRouter, URL base e timeout HTTP estão fixados em `core/config.py` (não configuráveis por `.env`).

## MySQL (boot)

Fonte do índice BM25. Variáveis lidas por `Settings.load()`:

| Variável | Default | Exemplo staging |
|----------|---------|-----------------|
| `DB_HOST` | — | `127.0.0.1` (`127.0.0.0` é corrigido com aviso) |
| `DB_PORT` | `3306` | `3307` |
| `DB_NAME` | — | `kernelbot_staging` |
| `DB_USER` | — | `kb_staging` |
| `DB_PASSWORD` | — | (local) |

## Grounding e retrieval

| Variável | Default | Notas |
|----------|---------|-------|
| `ACL_GROUNDING_POLICY` | `anchored` | `strict` \| `anchored` \| `hybrid` — contrato injetado no prompt |
| `ACL_GLOBAL_CONTEXT` | `geral` | `geral` ou `all` — escopo BM25 inicial |
| `ACL_DISAMBIGUATION_ENABLED` | `false` | `true` = `ambiguous_retrieval` pode gerar com `grounding_disambiguation.txt` |
| `ACL_RETRIEVAL_MODE` | *(deprecado)* | Ignorado; gates são só classificação — sempre LLM |

<details>
<summary><strong>Thresholds de retrieval (ver <code>engine/retrieval.py</code>)</strong></summary>

| Variável | Default | Faixa |
|----------|---------|-------|
| `ACL_RETRIEVAL_MIN_SCORE` | 1.5 | 0–50 |
| `ACL_RETRIEVAL_MIN_SCORE_MARGIN` | 0.15 | 0–5 |
| `ACL_RETRIEVAL_MIN_COVERAGE` | 0.34 | 0–1 |
| `ACL_RETRIEVAL_MIN_COVERAGE_WEIGHTED` | 0.34 | 0–1 |
| `ACL_RETRIEVAL_MIN_TERMS` | 2 | 1–10 |
| `ACL_RETRIEVAL_CANDIDATE_K` | 8 | 1–50 |
| `ACL_RETRIEVAL_TOP_K` | 4 | 1–20 |
| `ACL_RETRIEVAL_MAX_CHUNKS_PER_SOURCE` | 2 | 1–10 |

</details>

## Contexto fixado (pin) e histórico

| Variável | Default | Faixa | Descrição |
|----------|---------|-------|-----------|
| `ACL_PINNED_MAX_TURNS` | 5 | 1–50 | Turnos que o pin sobrevive (TTL via `begin_turn`) |
| `ACL_PINNED_MAX_CHARS` | 24000 | 2000–200000 | Tamanho máximo do texto fixado |
| `ACL_PINNED_WEAK_SCORE` | 0.4 | 0.05–0.95 | Score normalizado «fraco» (heurísticas de pin) |
| `ACL_CHAT_HISTORY_MAX_TURNS` | 12 | 0–40 | Mensagens user/assistant injetadas no prompt |
| `ACL_CHAT_HISTORY_MAX_CHARS` | 12000 | 0–200000 | Chars totais do history no prompt |

> Não existe `ACL_PIN_TTL_TURNS`: o TTL do pin é `ACL_PINNED_MAX_TURNS`.

## Catálogo lexical de aulas (ISS JSON)

| Variável | Default | Descrição |
|----------|---------|-----------|
| `ACL_CATALOG_ENABLED` | `false` | Roteamento por catálogo (rescue, sugestões) |
| `ACL_CATALOG_JSON_DIR` | `../ISS/content` se existir | Diretório com `lessons.json` / `search-index.json` |
| `ACL_CATALOG_MIN_SCORE` | 2.0 | Score mínimo para `is_confident()` |
| `ACL_CATALOG_MIN_MARGIN` | 0.35 | Margem entre 1.º e 2.º match |
| `ACL_CATALOG_STRICT_THRESHOLD` | 4.0 | Limiar de `is_strict_confident()` (fase futura) |
| `ACL_CATALOG_PROMPT_TOP_K` | 5 | Matches retornados em `match()` |

## Reload / health (CI)

| Variável | Notas |
|----------|-------|
| `ACL_RELOAD_BEARER_TOKEN` | Bearer para `/reload` e `GET /health/catalog`; ausente → 503 |
| `KERNELBOT_RELOAD_TOKEN` | Alias legado aceite como token (workflow ISS) |

Ver [07-apis-e-sse.md](07-apis-e-sse.md#reload-comando-administrativo).

## Logging

| Variável | Default | Efeito |
|----------|---------|--------|
| `ACL_LOG_FORMAT` | `text` | `text` (legível) ou `json` (uma linha por evento) |
| `ACL_LOG_LEVEL` | `INFO` | `DEBUG` inclui evento `retrieval_gates_inputs` |

`SecretRedactingFilter` em `core/logging_config.py` — ver [14-seguranca-observabilidade.md](14-seguranca-observabilidade.md).

## Cursor SDK

Com `ACL_LLM_PROVIDER=cursor` (default), o backend usa o pacote `cursor-sdk` (Python) via `AsyncClient.launch_bridge` + `run.iter_text()` em runtime local (`engine/chat_provider.py`). Requer `CURSOR_API_KEY` (Cursor Dashboard → API Keys) e `ACL_CURSOR_MODEL`.

## Ficheiros de prompt (`core/systemPrompt/`)

Todos são **obrigatórios** no boot (ausência → `RuntimeError`):

| Ficheiro | Quando é injetado |
|----------|-------------------|
| `system_prompt.txt` | Sempre |
| `grounding_strict.txt` | `ACL_GROUNDING_POLICY=strict` (ou `hybrid` sem chunks → permissive) |
| `grounding_anchored.txt` | Default (`anchored`) |
| `grounding_permissive.txt` | `hybrid` sem chunks no prompt |
| `grounding_disambiguation.txt` | `ACL_DISAMBIGUATION_ENABLED=true` + `ambiguous_retrieval` |
| `catalog_router.txt` | Sempre (carregado) |
| `sticky_instruction.txt` | Merge no pin (`_assemble_system_content`) — ver [09](09-fluxos-operacionais.md) |

## Ver também

- [17-prompts-referencia.md](17-prompts-referencia.md)
- [13-staging-testes.md](13-staging-testes.md)
- [07-apis-e-sse.md](07-apis-e-sse.md)
