<p align="center">
  <img src="frontend/assets/images/KernelBanner.webp" alt="KernelBot" width="100%" />
</p>

# KernelBots (ACL)

Agente de contexto local com RAG (BM25) sobre Markdown em `content/`, interface em `templates/` e respostas em streaming via OpenRouter.

## Requisitos

- Python 3.10+
- Chave `OPENROUTER_API_KEY` no arquivo `.env` na raiz do repositório

## Instalação

```bash
pip install -r requirements.txt
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
| `main.py` | Orquestração: logging, `SearchEngine`, watchdog, `create_app` |
| `core/` | Config (`Settings`), logging centralizado |
| `engine/` | BM25 (`SearchEngine`), `ContentWatcher`, `ContextManager`, `ChatProvider` |
| `api/` | Rotas FastAPI (`GET /`, `POST /chat`) |
| `app/` | `create_app()`, estado injetado em `app.state` |
| `content/` | Arquivos `.md` indexados |
| `templates/` | UI (Jinja2) |

## Testes

```bash
python -m pytest tests/ -v
```

## Logging

O projeto usa `logging` da biblioteca padrão com loggers prefixados `kernelbots.*` (ex.: `kernelbots.engine.search`, `kernelbots.api.chat`). Para logs estruturados em JSON no stdout, é possível estender `core/logging_config.py` com algo como `structlog` no mesmo ponto de configuração.

## Comandos no chat

- `/content …` — força uso da base local (com fallback para os primeiros chunks se não houver hit BM25).
- `/doc …` — injeta o conteúdo de `documentation.md` quando disponível no índice.
