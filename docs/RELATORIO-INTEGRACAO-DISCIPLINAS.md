# Relatório: integração das 3 novas disciplinas

Data: 2026-06-22

## 1. Hipóteses preliminares — veredito do gate

| Hipótese | Veredito | Evidência |
|----------|--------|-----------|
| Pipeline ISS → MySQL → BM25 | **Confirmada** | `engine/database.py`, `engine/search.py`, wiki 10-integracao-iss-fase5b |
| `jsons/` não lido em runtime | **Confirmada** | Sem referências a `jsons/` no motor RAG |
| Registo de disciplinas disperso | **Confirmada** | 5+ ficheiros antes do refactor; agora SSOT |
| Ingest ISS local indisponível | **Confirmada** | `ISS/.github/scripts/ingest-knowledge.py` ausente no checkout local |
| UI desalinhada (`/sql`, `/carreira`) | **Confirmada** | `entrance.js` corrigido; menu expandido |
| Heurística de pin só 4 disciplinas | **Confirmada e corrigida** | Markers agora vêm da SSOT (7 disciplinas) |
| Poucos testes de comando | **Confirmada e corrigida** | `tests/test_discipline_commands.py` |

**Critério de abandono:** não aplicável — integração viável sem violar regressões.

## 2. Gate arquitetural — decisões

| Decisão | Alternativas consideradas | Escolha | Justificativa |
|---------|---------------------------|---------|---------------|
| Pipeline de dados | Mover ingest para KernelBot; vector store | **Manter ISS→MySQL→BM25** | Desacoplamento existente; BM25 escala para ~111 aulas |
| Ingest em dev | Só ISS script; só CI | **`bin/ingest-jsons.sh`** | Paridade com meta B2; espelha `wiki_doc.py`; produção continua ISS |
| SSOT disciplinas | Python-only; derivar de `lessons.json`; listas manuais | **`core/disciplines.json`** + espelho frontend | Um ficheiro JSON; import Python + JS; teste de sync |
| BM25 OOM | Paginação; índice persistente | **Monitorar** | ~529 chunks estimados; aceitável em RAM |

## 3. Alterações realizadas

| Ficheiro | Impacto |
|----------|---------|
| [`core/disciplines.json`](../core/disciplines.json) | SSOT: 7 disciplinas, comandos, labels, markers |
| [`core/disciplines.py`](../core/disciplines.py) | Loader Python |
| [`engine/context.py`](../engine/context.py) | Prefixos, labels e pin markers dinâmicos |
| [`engine/jsons_ingest.py`](../engine/jsons_ingest.py) | Ingest UPSERT `jsons/` → MySQL |
| [`bin/ingest-jsons.sh`](../bin/ingest-jsons.sh) | Wrapper staging/prod |
| [`frontend/src/config/disciplines.json`](../frontend/src/config/disciplines.json) | Espelho SSOT (teste de paridade) |
| [`frontend/src/config/disciplines.js`](../frontend/src/config/disciplines.js) | API JS |
| [`frontend/src/utils/contextLabel.js`](../frontend/src/utils/contextLabel.js) | Labels via SSOT |
| [`frontend/src/acl/parseAclMeta.js`](../frontend/src/acl/parseAclMeta.js) | Comandos via SSOT |
| [`frontend/src/entrance.js`](../frontend/src/entrance.js) | Sugestões com comandos reais |
| [`templates/index.html`](../templates/index.html) | Menu: 7 disciplinas + `/doc` |
| [`tests/test_discipline_commands.py`](../tests/test_discipline_commands.py) | Regressão + novas disciplinas |

## 4. Resultado da indexação

### Contagens de documentos (`jsons/` → ingest)

| Disciplina | Documentos | Chunks estimados (B2, 500w/50 overlap) |
|------------|------------|----------------------------------------|
| fluencia-ia | 9 | 51 |
| python-processamento-dados | 22 | 92 |
| sql-modelagem-relacional | 16 | 84 |
| python | 16 | 77 |
| visualizacao-sql | 21 | 96 |
| projeto-bloco | 17 | 81 |
| planejamento-curso-carreira | 10 | 48 |
| **Total aulas** | **111** | **~529** |

### Execução MySQL neste ambiente

Staging MySQL (`127.0.0.1:3307`) **indisponível** (Docker não acessível). Ingest validado por:

- `iter_lesson_rows()` — contagens acima
- `tests/test_discipline_commands.py::test_iter_lesson_rows_counts`

**Produção / staging com MySQL:**

```bash
KERNELBOT_ENV=staging ./bin/ingest-jsons.sh
# ou ./bin/staging-ingest-iss.sh quando ISS script existir
# depois: POST /chat com /reload + Bearer
```

## 5. Validação de regressão

| Verificação | Resultado |
|-------------|-----------|
| `pytest tests/` | **24 passed** |
| `node frontend/src/acl/ambiguityStreamBuffer.test.mjs` | **OK** |
| Ordem/comandos 4 disciplinas legadas | **Preservados** (testes parametrizados) |
| Labels legados | **Preservados** |
| Prefixos ambíguos (`/pythonfoo`) | **Rejeitados** |

## 6. Plano de rollback

| Dimensão | Procedimento |
|----------|--------------|
| **Código** | `git revert` do commit de integração; ficheiros críticos: `context.py`, `core/disciplines.*`, frontend `config/` |
| **Índice** | `POST /reload` ou restart após revert |
| **Dados** | Rows novas: `UPDATE knowledge SET active=0 WHERE discipline IN (...)` **ou** restore snapshot MySQL; **nunca** truncate sem decisão explícita |
| **Activar rollback se** | Smoke regressão falha; `index_gap` em disciplina antiga; pin quebrado; fontes de silo errado em D3 |
| **RTO estimado** | ~15 min (revert + reload + smoke) |

## 7. Testes realizados

- Comandos slash: 7 disciplinas + casos negativos
- Sync JSON core ↔ frontend
- Contagem de aulas por disciplina no ingest
- Meta header B2 no ingest
- Suite legada (doc, disambiguation, ambiguity buffer)

### Smokes manuais recomendados (pós-ingest + reload)

| Comando | Query | Critério |
|---------|-------|----------|
| `/fluencia-ia` | diferença ML e DL | Fontes só `db:fluencia-ia/...` |
| `/python-processamento-dados` | try except finally | Fontes só `db:python-processamento-dados/...` |
| `/sql-modelagem-relacional` | normalização 3FN | Fontes só `db:sql-modelagem-relacional/...` |
| `/visualizacao-sql` | GROUP BY looker | Sem `db:sql-modelagem-relacional/...` |
| `/python` | listas e for | Sem `db:python-processamento-dados/...` |

## 8. Critérios de sucesso

| # | Critério | Estado |
|---|----------|--------|
| 1 | Disponibilidade (comandos + menu) | **OK** (código) |
| 2 | Indexação integral | **Pendente MySQL** — ingest pronto; executar em ambiente com DB |
| 3 | Isolamento de domínio | **OK** (BM25 por silo + testes de comando); smoke manual pós-ingest |
| 4 | Zero regressões | **OK** (pytest 24/24) |
| 5 | Expansão mais barata | **OK** — antes: 6+ ficheiros; depois: `core/disciplines.json` + espelho frontend + ingest |

## 9. Próximos pontos de melhoria

- Sincronizar `frontend/src/config/disciplines.json` via script único (evitar cópia manual)
- Menu de escopo gerado a partir da SSOT (eliminar HTML duplicado)
- Pull ISS com `ingest-knowledge.py` e validar paridade com `ingest-jsons.sh`
- Smoke E2E automatizado com MySQL em CI
- Monitorar memória do `rebuild()` com corpus completo
