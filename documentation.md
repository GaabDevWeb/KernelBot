## Propósito do sistema

O **ACL (KernelBot)** é um chatbot com **RAG lexical (BM25)** que responde via **LLM (OpenRouter)**, mas com uma regra explícita de segurança: **se o retrieval não tiver confiança suficiente, ele não chama o modelo** (hard stop).

Na prática, o sistema transforma o conteúdo de uma tabela MySQL chamada **`knowledge`** (aulas por disciplina) em um índice BM25 **em memória**, particionado por **silos** (disciplinas). A cada pergunta, ele escolhe um escopo (global, disciplina, `/doc`) e só gera resposta quando os gates de retrieval (score, coverage, ambiguidade) permitem.

Fora de escopo (neste repo, no estado atual): pipeline de ingestão, schema SQL versionado e suíte de testes automatizados. Este `documentation.md` documenta **o que está implementado no código hoje**, sem inferir arquivos/pastas inexistentes.

## Arquitetura

### Stack

| Camada | Tecnologia |
|---|---|
| Servidor HTTP | FastAPI + Uvicorn |
| Retrieval | BM25Okapi (`rank-bm25`) — in-memory |
| Dados | MySQL (lido via `PyMySQL`) |
| Gateway LLM | OpenRouter (streaming via `httpx`) |
| Frontend | HTML estático (`templates/index.html`) + JS modular em `frontend/src/` |
| Streaming | SSE (`text/event-stream`) |
| Logs | `logging` stdlib + payload estruturado (texto/JSON) |

### Visão de componentes

```mermaid
flowchart TD
    UI["Browser UI\n(templates/index.html + frontend/src)"] -->|POST /chat (JSON)| API["FastAPI /chat (SSE)"]
    API --> CM["ContextManager.build_messages()"]
    CM --> SE["SearchEngine.search_candidates()\nBM25 por silo"]
    SE --> DB["MySQL\nknowledge WHERE active=1"]
    CM -->|messages + decision + trace| CP["ChatProvider.stream_response()\nOpenRouter streaming"]
    CP -->|SSE tokens + ACL_META| UI
```

### Estrutura do repositório (real no workspace)

```
KernelBot/
├── main.py                 # Entry point: carrega Settings, monta serviços e roda Uvicorn (127.0.0.1:8001)
├── app/
│   ├── factory.py          # create_app(): templates, static mounts, lifespan, routers
│   └── state.py            # AppServices (injeção de dependências via app.state)
├── api/
│   └── routes.py           # GET / (UI) e POST /chat (SSE)
├── core/
│   ├── config.py           # Settings.load() a partir do .env + prompts + thresholds
│   ├── logging_config.py   # configure_logging() (text/json)
│   ├── structured_log.py   # log_event() + formatter com payload ACL
│   └── systemPrompt/       # system_prompt.txt + sticky_instruction.txt (obrigatórios)
├── engine/
│   ├── search.py           # SearchEngine: rebuild, silos BM25, candidatos (raw_score) + whitelist de discipline
│   ├── database.py         # SELECT no MySQL e chunking por janela de palavras
│   ├── retrieval.py        # gates/decisão (hard stop vs allow_generation) + sanity pós-geração
│   ├── context.py          # roteamento (/doc, /content, /python...) + pin por sessão + hard stop
│   ├── chat_provider.py    # streaming OpenRouter com fallback + ACL_META + override pós-geração
│   ├── pinned_store.py     # PinnedSessionStore em memória (session_id → chunks)
│   └── watcher.py          # legado (não integrado ao fluxo atual)
├── templates/
│   └── index.html          # Shell da UI (carrega /src/main.js)
├── frontend/
│   ├── src/                # UI JS (ChatService, render markdown, histórico, sessão)
│   └── assets/             # CSS e imagens
├── content/                # existe, mas o engine atual não lê arquivos daqui
├── SQL/                    # existe no workspace, mas sem artefatos versionados (neste estado)
├── requirements.txt
├── .env / .env.example
└── documentation.md
```

### Decisões de design (trade-offs)

- **BM25 (lexical) em vez de embeddings**: simples, barato e rápido; trade-off é recall semântico menor e dependência de termos na query.
- **Hard stop no modo strict**: reduz alucinação e custo de tokens; trade-off é mais “recusa” quando a pergunta é vaga/ambígua.
- **Pin por sessão (server-side em memória)**: melhora follow-ups sem re-busca constante; trade-off é que o pin expira por turnos e some ao reiniciar o processo.

## APIs

### Base URL

Por padrão, o servidor sobe em:

```bash
http://127.0.0.1:8001
```

Sem autenticação.

### Endpoints

| Método | Caminho | Descrição |
|---|---|---|
| `GET` | `/` | Serve a UI (`templates/index.html`) |
| `POST` | `/chat` | Recebe mensagem e retorna SSE (`text/event-stream`) |

### `POST /chat`

**Request body (JSON):**

```json
{
  "message": "string (obrigatório)",
  "discipline": "string (opcional)",
  "session_id": "string (opcional; 8–128 [A-Za-z0-9_-])"
}
```

Notas:

- **`discipline` (JSON)**: se fornecido, passa por whitelist em `SearchEngine.normalize_discipline()` (só aceita valores presentes no DB em `SELECT DISTINCT discipline ...`).
- **`session_id`**: habilita **contexto fixado (pin)**; o frontend gera e persiste em `sessionStorage`.
- **Comando `/reload`**: se `message == "/reload"` (case-insensitive após trim), o backend reconstrói o índice BM25 e retorna um stream curtinho com status.

**Response (`text/event-stream`)**:

- `data: [ACL_META]{...}\n\n` — metadados (sempre no começo do stream; e pode reaparecer no override pós-geração)
- `data: <chunk>\n\n` — tokens/trechos (com `\n` escapado como `\\n`)
- `data: [DONE]\n\n` — fim
- `data: [ERROR] ...\n\n` — erro amigável de provider (quando todos os modelos falham)

**Campos relevantes em `ACL_META` (v=2)** (emitidos por `engine/chat_provider.py`):

- `label`: rótulo de escopo (ex.: “Python”, “Base geral”, “Documentação (doc)”)
- `sources`: lista de fontes (ex.: `db:python/slug-da-aula`)
- `pinned_active` / `pinned_display`: status do pin da sessão
- `mode`: `strict` (no estado atual)
- `decision`: `answer` ou `hard_stop`
- `reason`: motivo (ex.: `ok`, `insufficient_context`, `context_misaligned`, `provider_error`, `post_generation_misalignment`)
- `confidence`: `high|medium|low`
- `llm_called`: boolean
- `tokens_used`: contador aproximado (incrementa por delta recebido)

## Fluxos

### Fluxo 1 — Inicialização do servidor

1. `main.py` chama `configure_logging()`.
2. `Settings.load()` lê `.env` e valida pré-requisitos:
   - `OPENROUTER_API_KEY` é obrigatório.
   - `core/systemPrompt/system_prompt.txt` e `core/systemPrompt/sticky_instruction.txt` são obrigatórios.
3. `SearchEngine(...).rebuild()` tenta carregar chunks do MySQL (`engine/database.py`). Se DB não estiver configurado ou estiver inacessível, o índice fica vazio e logs avisam.
4. `create_app()` registra templates, monta estáticos (`/assets`, `/src`) e inclui rotas.
5. Uvicorn sobe em `127.0.0.1:8001`.

### Fluxo 2 — Chat (ponta a ponta)

```text
UI (frontend/src/ui.js) → POST /chat { message, session_id } → SSE stream
```

1. O usuário envia uma mensagem.
2. A UI (`frontend/src/api.js`) faz `fetch("/chat")` e lê `res.body.getReader()` processando linhas `data: ...`.
3. O backend (`api/routes.py`) valida JSON, `message`, `discipline` e `session_id`.
4. `ContextManager.build_messages()` decide o escopo e tenta retrieval:
   - Comandos de escopo no texto (prefixos): `/doc`, `/content`, `/python`, `/visualizacao-sql`, `/projeto-bloco`, `/planejamento-curso-carreira`.
   - Sem comando, ele pode usar o **pin** da sessão para sugerir escopo efetivo (se existir e não conflitar).
5. `SearchEngine.search_candidates()` retorna candidatos BM25 (com `raw_score` e `matched_terms`).
6. `engine/retrieval.build_decision()` aplica gates (score absoluto, margem, coverage, termos mínimos, “vague but high risk”).
7. Se **`allow_generation=False`**: o backend envia **hard stop** via SSE (sem chamar LLM).
8. Se **`allow_generation=True`**: o backend chama OpenRouter em streaming e re-emite tokens via SSE.
9. No final, o provider roda um **sanity check pós-geração** (`post_generation_flags`). Se detectar desalinhamento em modo `strict`, ele emite um `ACL_META` atualizado e anexa uma mensagem de hard stop (`post_generation_misalignment`).
10. A UI renderiza Markdown incremental (via `marked@12` + `highlight.js`) e mostra breadcrumbs a partir de `meta.sources`.

### Fluxo 3 — Contexto fixado (pin) por sessão

- O frontend gera um `session_id` (UUID sem hífens) e salva em `sessionStorage` (`frontend/src/utils/sessionId.js`).
- O backend salva os chunks selecionados no `PinnedSessionStore` (em memória), com:
  - `turns_left` (expira a cada turno via `begin_turn()`),
  - `scope_key` (ex.: `discipline:python`, `doc`, `content`).
- Se o usuário enviar `/reset` ou `/limpar` no começo da mensagem, o backend limpa o pin daquela sessão.

### Fluxo 4 — Rebuild manual do índice (`/reload`)

1. Usuário envia `/reload`.
2. `api/routes.py` chama `services.search_engine.rebuild()`.
3. O endpoint retorna um stream curto com:
   - `data: Índice reconstruído: ...\n\n`
   - `data: [DONE]\n\n`

## Glossário e referências (opcional)

- **Silo**: partição lógica do índice por `discipline` (ex.: `python`).
- **Chunk**: janela de ~500 palavras com overlap de 50 (ver `engine/database.py`).
- **Retrieval candidate**: item retornado por `SearchEngine.search_candidates()` com `raw_score` (BM25 cru).
- **Hard stop**: decisão de não chamar o LLM e responder com uma mensagem de reformulação (modo `strict`).
- **Pin**: contexto fixado por sessão em memória (`PinnedSessionStore`).

Referências no código:

- Backend: `main.py`, `api/routes.py`, `app/factory.py`, `engine/context.py`, `engine/retrieval.py`, `engine/chat_provider.py`
- Frontend: `templates/index.html`, `frontend/src/api.js`, `frontend/src/ui.js`