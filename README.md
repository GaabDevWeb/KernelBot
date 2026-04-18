# KernelBot

Agente de contexto local com RAG (BM25) sobre Markdown, interface Jinja2 e respostas em streaming via OpenRouter.

![Python](https://img.shields.io/badge/python-3.10+-111111?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-111111?style=flat-square&logo=fastapi&logoColor=white)
![License](https://img.shields.io/github/license/GaabDevWeb/KernelBot?style=flat-square&color=111111&labelColor=111111&logoColor=white)
![Last Commit](https://img.shields.io/github/last-commit/GaabDevWeb/KernelBot?style=flat-square&color=111111&labelColor=111111)
![Open Issues](https://img.shields.io/github/issues/GaabDevWeb/KernelBot?style=flat-square&color=111111&labelColor=111111)

---

## Requisitos

- Python 3.10+
- `OPENROUTER_API_KEY` no `.env` na raiz

---

## Instalação

```bash
pip install -r requirements.txt
```

---

## Executar

```bash
python main.py
```

Com Uvicorn:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000
```

`http://127.0.0.1:8000`

---

## Estrutura

| Caminho | Função |
|---|---|
| `main.py` | Orquestração: logging, `SearchEngine`, watchdog, `create_app` |
| `core/` | Config (`Settings`), logging centralizado |
| `engine/` | BM25 (`SearchEngine`), `ContentWatcher`, `ContextManager`, `ChatProvider` |
| `api/` | Rotas FastAPI (`GET /`, `POST /chat`) |
| `app/` | `create_app()`, estado injetado em `app.state` |
| `content/` | Arquivos `.md` indexados |
| `templates/` | UI (Jinja2) |

---

## Testes

```bash
python -m pytest tests/ -v
```

---

## Logging

Loggers prefixados `kernelbots.*` (ex.: `kernelbots.engine.search`, `kernelbots.api.chat`). Para JSON estruturado no stdout, estender `core/logging_config.py` com `structlog`.

---

## Comandos

`/content …` — força uso da base local (BM25, fallback para os primeiros chunks).  
`/doc …` — injeta `documentation.md` no contexto quando disponível no índice.

---

![KernelBot Metrics](https://raw.githubusercontent.com/GaabDevWeb/KernelBot/main/kernel-status.svg)
