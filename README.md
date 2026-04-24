# KernelBots (ACL)

Agente de contexto local com RAG (BM25) sobre **MySQL**, interface em `templates/` e respostas em streaming via OpenRouter.

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
- `/content …` — força uso da base local (com fallback para os primeiros chunks se não houver hit BM25).
- `/doc …` — injeta o conteúdo da documentação quando disponível no índice.
- `/python …`, `/visualizacao-sql …`, `/projeto-bloco …`, `/planejamento-curso-carreira …` — filtra por disciplina.

## Fluxo de dados

```
content/*.md → scripts/ingest_content.py → MySQL (knowledge) → engine/database.py → BM25 index → /chat
```
