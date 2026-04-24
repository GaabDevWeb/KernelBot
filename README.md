# KernelBots (ACL)

Agente de contexto local com RAG (BM25) sobre **MySQL**, interface em `templates/` e respostas em streaming via OpenRouter.

**Modo local estrito (padrão):** desde a mitigação descrita em `.cursor/plans/rag_acl_incremental_6951b55f.plan.md`, o ACL opera por padrão em modo `strict`. A geração só acontece quando a decisão de retrieval permitir; pergunta sem base não chama LLM, `/content` não injeta mais `scope_chunks[:5]` e respostas que passam pelos gates mas falham no sanity check pós-geração são substituídas por hard stop `post_generation_misalignment`. A regra central é: na dúvida, não responder.

## Requisitos

- Python 3.10+
- MySQL 8.0+
- Chave `OPENROUTER_API_KEY` no arquivo `.env` na raiz do repositório

## Instalação

```bash
pip install -r requirements.txt
```

## Configuração do banco

1. Crie o banco e a tabela:

```bash
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS pybot CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -u root -p pybot < SQL/schema.sql
```

2. Ingira o conteúdo das aulas (pasta `content/`) no MySQL:

```bash
python scripts/ingest_content.py
```

Flags úteis: `--dry-run` (só valida, sem escrita), `--only-discipline python`, `--verbose`.

3. Configure o `.env`:

```env
OPENROUTER_API_KEY=sua_chave

DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=pybot
DB_USER=root
DB_PASSWORD=sua_senha
```

## Executar

```bash
python main.py
```

Ou com Uvicorn:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

Abra `http://127.0.0.1:8000`.

## Estrutura

| Caminho | Função |
|--------|--------|
| `main.py` | Orquestração: logging, `SearchEngine`, `create_app` |
| `core/` | Config (`Settings`), logging centralizado |
| `engine/` | BM25 (`SearchEngine`), `ContextManager`, `ChatProvider`, `database` (MySQL) |
| `api/` | Rotas FastAPI (`GET /`, `POST /chat`) |
| `app/` | `create_app()`, estado injetado em `app.state` |
| `SQL/` | Schema, JSON Schema do payload, migrações, scripts de criação |
| `scripts/` | `ingest_content.py` — parse Markdown → MySQL |
| `content/` | Arquivos `.md` originais (legado — fonte de dados para o script de ingestão) |
| `templates/` | UI (Jinja2) |
| `evaluation/` | Pipeline de avaliação do RAG — [documentação](evaluation/README.md) |

## Testes

```bash
python -m pytest tests/ -v
```

## Logging

O projeto usa `logging` da biblioteca padrão com loggers prefixados `kernelbots.*` (ex.: `kernelbots.engine.search`, `kernelbots.api.chat`).

## Comandos no chat

- `/reload` — reconstrói o índice BM25 a partir do MySQL.
- `/content …` — busca global explícita; **sem fallback** de primeiros chunks. Se não houver hit forte o bastante, retorna hard stop com reformulação guiada.
- `/doc …` — injeta o conteúdo da documentação quando disponível no índice; fluxo determinístico (não passa pela política de decisão).
- `/python …`, `/visualizacao-sql …`, `/projeto-bloco …`, `/planejamento-curso-carreira …` — filtra por disciplina.

## Política de retrieval e hard stop

A camada `engine/retrieval.py` separa recuperação lexical bruta (`SearchEngine.search_candidates`) da decisão de suficiência (`build_decision`). A decisão devolve `RetrievalDecision` com `allow_generation`, `reason`, `confidence` e `trace` estruturado, exposto no SSE como `[ACL_META]`.

Hard stops possíveis:

| `reason` | Quando dispara |
|---|---|
| `insufficient_context` | Sem hits ou `top_score < MIN_SCORE` |
| `underspecified_query` | Menos que `MIN_TERMS` termos informativos (strict) |
| `vague_but_high_risk` | Termo vago (`performance`, `erro`, `timeout`) sem domínio específico |
| `ambiguous_retrieval` | `top_score - second_score < MIN_SCORE_MARGIN` |
| `context_misaligned` | `coverage < MIN_COVERAGE` no melhor chunk |
| `low_confidence` | Coverage ponderada baixa ou termo central ausente no modo strict |
| `post_generation_misalignment` | Sanity check pós-geração detectou resposta fora dos chunks |
| `provider_error` | Todos os modelos OpenRouter falharam |

Thresholds configuráveis via `.env` (ver `core/config.py`):

| Variável | Default | Efeito |
|---|---|---|
| `ACL_RETRIEVAL_MIN_SCORE` | 1.5 | Hard stop se `top_score` bruto for menor |
| `ACL_RETRIEVAL_MIN_SCORE_MARGIN` | 0.15 | Margem mínima entre top1 e top2 |
| `ACL_RETRIEVAL_MIN_COVERAGE` | 0.34 | Overlap mínimo de termos informativos |
| `ACL_RETRIEVAL_MIN_COVERAGE_WEIGHTED` | 0.34 | Idem, com centrais valendo 2x |
| `ACL_RETRIEVAL_MIN_TERMS` | 2 | Termos informativos mínimos em `strict` |
| `ACL_RETRIEVAL_CANDIDATE_K` | 8 | Quantos candidatos o retrieval devolve |
| `ACL_RETRIEVAL_TOP_K` | 4 | Quantos vão para o prompt |
| `ACL_RETRIEVAL_MAX_CHUNKS_PER_SOURCE` | 2 | Diversidade de fonte |

## Calibração e avaliação

A pasta `evaluation/` contém a ferramenta que gera o artefato exigido pelo plano incremental:

```bash
python -m evaluation.calibration_runner --questions evaluation/all.md --out evaluation/calibration_traces.jsonl --limit 20
python -m evaluation.calibration_summary --traces evaluation/calibration_traces.jsonl
```

O runner produz um JSONL com trace completo por query (scores, coverage, termos, fontes, decisão) e um placeholder `manual_label` para revisão humana. O summary imprime percentis de scores e as taxas `Stop vs Answer`, `Ambiguous Retrieval`, `Underspecified Query`, `Vague But High Risk`.

## Limitações conhecidas

- **BM25-only é mitigação temporária.** O módulo `engine/retrieval.py` deixa explícito (`retrieval_mode = "bm25_lexical_temporary"`). A evolução correta é busca híbrida (BM25 + embeddings + reranking), fora do escopo inicial.
- **Coverage lexical** aproxima alinhamento semântico, não resolve. Por isso a Fase 3 adiciona sanity check pós-geração como último firewall.
- **Calibração manual de 20 casos é bootstrap**, não prova final. A evolução prevista é 100–200 casos semi-automatizados.
- **Modo `assistive`** existe como flag, mas não é ativado por padrão. A mitigação estabiliza o modo `strict` primeiro.

## Fluxo de dados

```
content/*.md → scripts/ingest_content.py → MySQL (knowledge) → engine/database.py → BM25 index → /chat
```
