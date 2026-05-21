# Dados e MySQL

[← Índice](README.md)

## Contrato de dados

| Regra | Detalhe |
|-------|---------|
| **1 row = 1 aula** | `discipline` + `slug` identificam unicamente |
| **UPSERT** | Job 2 ISS sobrescreve `content` inteiro — não há append de chunks no SQL |
| **Fonte de verdade do texto** | Coluna `content` (meta + body unificado na Opção B) |
| **Chunking** | Apenas em RAM no KernelBot (`engine/database.py`) |

## Schema (referência)

O DDL não está versionado neste repo. Forma esperada:

```sql
CREATE TABLE knowledge (
  id INT AUTO_INCREMENT PRIMARY KEY,
  discipline VARCHAR(255) NOT NULL,
  slug VARCHAR(255) NOT NULL,
  title VARCHAR(512),
  content LONGTEXT NOT NULL,
  active TINYINT(1) DEFAULT 1,
  updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  UNIQUE KEY uq_discipline_slug (discipline, slug)
);
```

Staging: `bin/staging-apply-schema.sh` aplica DDL idempotente.

## Colunas usadas pelo KernelBot

| Coluna | Uso |
|--------|-----|
| `discipline` | Silo BM25 + filtro de escopo |
| `slug` | Parte do `source` (`db:{discipline}/{slug}`) |
| `title` | Prefixo `Título:` em cada chunk |
| `content` | Documento completo (meta + markdown) |
| `active` | `WHERE active = 1` no fetch |

## Query de fetch (conceitual)

```sql
SELECT discipline, slug, title, content
FROM knowledge
WHERE active = 1;
```

**Backlog:** `LIMIT` por batch para evitar OOM em catálogos grandes — ver [16-backlog.md](16-backlog.md).

## Guard de tamanho

| Limite | Comportamento |
|--------|---------------|
| `MAX_CONTENT_CHARS` (4M) | Row ignorada no fetch; log `db_chunk_row_skipped` |
| ISS `MAX_CONTENT_CHARS` pré-UPSERT | Evita gravar row gigante |

## `source` no índice RAM

Formato: `db:{discipline}/{slug}`

Exemplos staging:

- `db:_staging/legacy-modelagem`
- `db:_staging/fluencia-b2`

Prefixo `_staging/` quando ingest usa disciplina de teste.

## Chaves indexadas vs catálogo

`fetch_indexed_lesson_keys()` → `frozenset` de `"discipline:slug"`.

Usado por:

- `GET /health/catalog` — drift report
- `engine/context.py` — `index_gap` quando catálogo confiante mas chave ausente no índice

## Staging vs produção

| Ambiente | MySQL | Env |
|----------|-------|-----|
| Staging local | Docker `:3307`, DB `kernelbot_staging` | `.env.staging.local` + `KERNELBOT_ENV=staging` |
| Produção | Aiven / managed | `.env` (não usar `python main.py` sem staging se apontar para prod) |

## Ver também

- [10-integracao-iss-fase5b.md](10-integracao-iss-fase5b.md)
- [13-staging-testes.md](13-staging-testes.md)
