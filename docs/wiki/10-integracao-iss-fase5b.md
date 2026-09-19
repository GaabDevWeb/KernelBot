# Integração ISS (Fase 5b)

[← Índice](README.md)

## Papéis dos repositórios

| Repo | SSOT | Entrega |
|------|------|---------|
| **ISS** | `content/lessons.json`, `content/**/*.md`, `jsons/**` | UPSERT MySQL via ingest |
| **KernelBot** | BM25, gates, API, UI | Lê MySQL, expõe chat |

## Workflow GitHub Actions (ISS)

Ficheiro: `.github/workflows/sync-kernelbot-knowledge.yml`

| Job | Script | Função |
|-----|--------|--------|
| 1 | `validate-catalog.mjs` | Consistência catálogo |
| 2 | `ingest-knowledge.py` | UPSERT `knowledge.content` |
| 3 | `verify-kernelbot-sync.mjs` + `reload-kernelbot.mjs` | Drift + `/reload` |

## Job 2 — Ingest (Opção B)

| Passo | Detalhe |
|-------|---------|
| Lê markdown | Remove frontmatter YAML |
| Lê JSON | `keywords`, `concepts`, `learning_objectives`, `name` |
| Monta | `build_meta_header()` + body |
| UPSERT | 1 row por `(discipline, slug)` |
| Limite | `MAX_CONTENT_CHARS=4_000_000` |

### Bloco meta (contrato partilhado)

```text
[CONCEITOS E KEYWORDS DA AULA PARA INDEXAÇÃO LÉXICA]
Disciplina: {discipline}
Título: {title}
Conceitos: {csv}
Keywords: {csv}
Objetivos: {csv separado por ;}
====== FIM DOS METADADOS ======
```

## Secrets GHA (ISS)

| Secret | Uso |
|--------|-----|
| MySQL host/user/pass | Job 2 UPSERT |
| `KERNELBOT_RELOAD_URL` | Job 3 |
| `KERNELBOT_RELOAD_TOKEN` | Header reload |

## Job 3 — Verificação

- `GET /health/catalog` no KernelBot
- Compara chaves catálogo vs `indexed_lesson_keys`
- Falha CI se drift crítico
- `POST /reload` após ingest bem-sucedido

## Rows extra: transcrições e calendário

Além das lições, o ingest do ISS (`knowledge_extras.py`) grava na mesma tabela:

| Tipo | `discipline` | `slug` | Conteúdo |
|------|--------------|--------|----------|
| Transcrição bruta | a da aula | `transcricao__NN__DDMMYYYY` | Texto integral do `.vtt` com `[mm:ss]` a cada ~60 s; sem nomes de quem fala |
| Calendário | `calendario` | `calendario-YYYY-trim-N` | Resumo de entregas TP/AT/PB + grelha semanal (planilha pública Infnet) |

No KernelBot nada muda estruturalmente: são rows normais, chunkadas a 500 palavras. O `__NN__` do slug vira «Aula NN» na UI; o título vem da 1.ª linha do chunk quando a row não está no catálogo. Essas chaves aparecem como `index_only` no `/health/catalog` — o `verify-kernelbot-sync.mjs` exclui-as da contagem de lições e só falha por `catalog_only`.

## O que o KernelBot **não** faz na ingest

| Não faz | Quem faz |
|---------|----------|
| Chunking SQL | ISS grava documento unificado |
| Ler `jsons/` directamente | ISS no Job 2 |
| Auto-sync no boot | CI + `/reload` |

## Catálogo lexical (`ACL_CATALOG_ENABLED`)

| Componente | Função |
|------------|--------|
| `engine/lesson_catalog.py` | Carrega manifest ISS |
| `engine/catalog_sync.py` | Drift + bootstrap |
| `index_gap` | Pergunta sobre aula que existe no catálogo mas não no índice |

## Ver também

- [11-enriquecimento-lexico-b2.md](11-enriquecimento-lexico-b2.md)
- [04-dados-e-mysql.md](04-dados-e-mysql.md)
