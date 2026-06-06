    # Enriquecimento léxico (Opção B2)

    [← Índice](README.md) · Ver também [05-bm25-chunking.md](05-bm25-chunking.md)

    ## Objetivo de negócio

    Melhorar **recall BM25** para termos que existem nos JSONs da ISS (`keywords`, `concepts`, `learning_objectives`, `name`) **sem** relaxar gates de hard stop.

    ## Linha do tempo de engenharia

    | Fase | Abordagem | Problema |
    |------|-----------|----------|
    | Inicial (rejeitada) | Chunking na ingestão + meta em cada fragmento | Duplo chunking ISS + KernelBot; meta repetida |
    | **Opção B** | MySQL: doc unificado; RAM: meta em **todos** os chunks | Colapso IDF — keyword em N chunks → score 0 |
    | **Opção B2** (actual) | MySQL igual; RAM: meta **só chunk 0** | Recall OK; body-only queries podem não ver meta no prompt |

    ## Fonte dos metadados (ISS)

    | Campo JSON | Uso no bloco meta |
    |------------|-------------------|
    | `name` | Título da aula |
    | `concepts` | Linha `Conceitos:` |
    | `keywords` | Linha `Keywords:` |
    | `learning_objectives` | Linha `Objetivos:` |

    Ficheiro: `jsons/<discipline>/<discipline>__NN__<slug>.json`  
    SSOT catálogo: `content/lessons.json` (repo ISS).

    ## Implementação ISS (`ingest-knowledge.py`)

    | Função | Papel |
    |--------|-------|
    | `load_lesson_json` | Lê JSON por discipline/slug |
    | `build_meta_header` | Monta bloco entre marcadores |
    | Job 2 | `content = meta_header + "\n\n" + markdown_sem_frontmatter` |
    | `MAX_CONTENT_CHARS` | Trunca/rejeita antes do UPSERT |

    ## Implementação KernelBot (`engine/database.py`)

    ```text
    content (MySQL)
        │
        ▼
    _split_meta_block()  → meta_block | clean_body
        │
        ▼
    _chunk_text()
        ├─ chunk 0: Título + meta + body[0:500 palavras]
        └─ chunk n≥1: Título + body[continuação]
    ```

    ## Evidência de validação (staging)

    | Query | Resultado esperado B2 |
    |-------|----------------------|
    | `transformers` | chunk0 score > 0; chunks 1–3 = 0 |
    | `4 níveis integridade` | Resposta substantiva, fontes corretas |
    | `ML vs DL` | Recall OK |
    | `oi` | `underspecified_query` (gate, não bug B2) |
    | `/python` fora do índice | `index_gap` ou hard stop |

    ## Anti-padrões (não repetir)

    | Anti-padrão | Porquê |
    |-------------|--------|
    | Múltiplos UPSERTs por aula com chunk_id | Overwrite destrói chunks anteriores |
    | Meta em todos os chunks RAM | IDF colapsa |
    | Re-chunking na ingest **e** no bot | Duplicação e drift de fronteiras |
    | Assumir que disclaimer pós-LLM = falha BM25 | São camadas diferentes |

    ## Recomendação A (prompt)

    **Estado:** meta **não** re-injectado em `context.py` quando só chunks ≥1 entram no prompt.

    | Prós | Contras |
    |------|---------|
    | Prompt mais limpo para o aluno | Query sobre meio da aula pode não mostrar keywords ao LLM |

    Backlog opcional: uma linha de meta por `source` no prompt — [16-backlog.md](16-backlog.md).

    ## Deploy coordenado

    ```text
    1. Push ISS → workflow ingest (Job 2)
    2. Job 3 POST /reload no KernelBot (token ACL_RELOAD_TOKEN)
    3. Verificar GET /health/catalog
    4. Smoke: query keyword + query body-only
    ```

    ## Commits de referência (locais, sem push)

    | Repo | Commit | Conteúdo |
    |------|--------|----------|
    | ISS | `b80775d` | Ingest Opção B unificado |
    | KernelBot | `2431a00` | B2 chunk0, OOM guard, logging |

    ## Ver também

    - [10-integracao-iss-fase5b.md](10-integracao-iss-fase5b.md)
    - [06-gates-e-decisoes.md](06-gates-e-decisoes.md)
