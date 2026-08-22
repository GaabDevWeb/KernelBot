# REPORT — Ops Center P1 (Conhecimento)

Data: 2026-07-29  
Branch: `feature/kernel-ops-center`

## Entrega

| Ecrã | Rota | Função |
|------|------|--------|
| Documentos | `GET /ops/knowledge/docs` | Lista disciplina, título/slug, source, chunks RAM, `updated_at` MySQL; filtro q/disciplina |
| Busca | `GET /ops/knowledge/search` | Modos BM25 / híbrida / completa + scores e chunks |
| RAG Explorer | `GET /ops/knowledge/rag` | Debug retrieval do chat (sem LLM): query processada, top docs, confidence, reason, chunks |
| Reindexação | `GET/POST /ops/knowledge/reindex` | Rebuild BM25 (+ refresh keys); scope all/disciplina/documento best-effort |

Auth: cookie Ops (`require_ops_cookie`), mesmo token que `/ops/login`.

## Arquitectura

```text
/ops/knowledge/*
    → api/knowledge_routes.py
        → kernel/knowledge/ops.py
            → SearchEngine / build_decision / ContextManager.build_messages
            → fetch_db_document_meta (MySQL, sem content)
            → rebuild() + refresh_indexed_lesson_keys_state (como /reload)
    → templates/ops/knowledge/*.html (shell Ops existente)
```

NAV: badges `phase: P1` removidos dos itens Conhecimento. Placeholders knowledge retirados de `api/ops_routes.py`.

## Como funciona o RAG Explorer

1. Operador submete pergunta (+ disciplina opcional).
2. Chama `context_manager.build_messages(..., session_id=None)` — **mesma rota** do chat (comandos `/doc`, catálogo, narrowing, `build_decision`, rescue), **sem** pin e **sem** LLM.
3. UI mostra:
   - query original vs `normalized_query`
   - reason / confidence / top_score / coverage / margem
   - chunks seleccionados + candidatos pré-decisão (accordion)
4. Config actual do índice vem de `kernel.inspect.sdk.rag`.

## Modos da Busca

| Modo | Comportamento |
|------|----------------|
| `bm25` | `search_candidates` bruto (sem política ACL) |
| `hybrid` | candidatos + `build_decision` (como `POST /search`) |
| `full` | pipeline `build_messages` (catálogo/disciplina efectiva) |

## Reindexação (honestidade)

- Rebuild BM25 é **sempre completo** (API existente não tem rebuild parcial).
- Scope disciplina/documento só filtra **estatísticas** pós-rebuild.
- Checkbox opcional: reingerir do disco (`jsons` / wiki se `doc`) antes do rebuild — best-effort staging.
- Passos reportados com ms: `ingest_*` (opcional) → `rebuild_bm25` → `refresh_indexed_keys`.

## Ficheiros

- `api/knowledge_routes.py` (novo)
- `kernel/knowledge/ops.py` (novo)
- `kernel/knowledge/database.py` — `fetch_db_document_meta`
- `templates/ops/knowledge/{docs,search,rag,reindex}.html`
- `app/factory.py` — `knowledge_router`
- `api/ops_routes.py` — NAV + remoção placeholders P1 knowledge
- `tests/test_knowledge_ops.py`
- `memory/kernel-ops-center/REPORT-p1.md`

## Testes

`PYTHONPATH=. .venv/bin/pytest tests/test_knowledge_ops.py -q` → 2 passed

## Gaps / limitações

1. Sem rebuild parcial por silo/documento (só full + stats filtradas).
2. Data de ingestão depende de MySQL `updated_at`; só RAM → "—".
3. Ingest disco no painel faz UPSERT **global** de jsons (não filtra por um único documento).
4. RAG Explorer não grava pin nem chama provider (intencional).
5. Sem streaming de progresso HTMX durante rebuild (progresso pós-facto por steps).
