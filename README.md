<p align="center">
  <img src="frontend/assets/images/KernelBanner.webp" alt="KernelBot" width="100%" />
</p>

# KernelBot

**Chatbot RAG local-first que transforma Markdown em base de conhecimento consultável via chat.**

---

## O que é

O KernelBot — internamente chamado **ACL (Agente de Contexto Local)** — é um sistema que indexa arquivos Markdown de um diretório local (`content/`) usando BM25, recupera trechos relevantes e os injeta como contexto para um LLM via OpenRouter. A resposta chega em streaming (SSE) com rastreabilidade: você sabe de onde veio cada trecho usado.

Sem banco de dados, sem fila, sem infra pesada. Índice e estado ficam na memória do processo.

---

## Problema que resolve

Alunos precisam revisar gravações de aulas de ~2h para tirar dúvidas simples. Sem o KernelBot, a alternativa é reassistir o material bruto ou esperar resposta da secretaria/professores.

O sistema usa resumos estruturados das aulas como corpus RAG, permitindo perguntas diretas com respostas ancoradas no conteúdo real — não em "achismo" do modelo.

---

## Como funciona

```
content/*.md ──► SearchEngine (BM25 por silo) ──► ContextManager ──► ChatProvider ──► SSE
     ▲                                                                      │
     │                                                                      ▼
  Watchdog                                                            OpenRouter API
(rebuild automático)                                                 (LLM com fallback)
```

**Três etapas:**

1. **Indexação** — `SearchEngine` lê `content/**/*.md`, divide por headers em chunks e cria um índice BM25 separado por silo (subpasta). O Watchdog monitora alterações e reconstrói o índice automaticamente (~1.5s de debounce).

2. **Decisão de contexto** — `ContextManager.build_messages()` interpreta comandos (`/python`, `/doc`, `/content`), campo `discipline` do JSON e pinned context por sessão para decidir quais chunks injetar no system prompt.

3. **Geração** — `ChatProvider` chama o LLM via OpenRouter em streaming SSE. Suporta fallback automático entre modelos. Antes dos tokens, emite metadados (`[ACL_META]`) com rótulo do silo e fontes usadas.

---

## Diferenciais

| Recurso | O que faz |
|---------|-----------|
| **Silos BM25** | Cada subpasta de `content/` é um domínio isolado com índice próprio — evita mistura de contextos entre disciplinas |
| **Comandos de escopo** | `/python`, `/doc`, `/content` etc. forçam onde a busca acontece |
| **Pinned context** | Mantém contexto entre mensagens da mesma sessão para follow-ups curtos não "perderem o fio" |
| **File watching** | Editou um `.md` em `content/`? Em ~1.5s o índice já reflete a mudança |
| **Rastreabilidade** | Respostas incluem breadcrumbs com os arquivos fonte usados (via `[ACL_META]` no SSE) |
| **Zero infra** | Sem banco, sem Redis, sem Docker obrigatório — `python main.py` e pronto |

---

## Estrutura de pastas

```
KernelBot/
├── main.py              # Orquestração: serviços, watchdog, app FastAPI
├── core/                # Settings (.env), logging centralizado
├── engine/              # SearchEngine, ContentWatcher, ContextManager, ChatProvider, PinnedSessionStore
├── api/                 # Rotas FastAPI (GET /, POST /chat)
├── app/                 # create_app(), estado injetado (AppServices)
├── content/             # Base de conhecimento — silos por subpasta
│   ├── python/          # 16 aulas
│   ├── visualizacao-sql/# 17 aulas
│   ├── projeto-bloco/   # 9 aulas
│   ├── planejamento-curso-carreira/  # 7 aulas
│   └── doc/             # Documentação interna (silo /doc)
├── frontend/            # Assets CSS e módulos JS da UI
├── templates/           # index.html (Jinja2)
├── tests/               # Smoke tests (pytest)
└── requirements.txt
```

---

## Como rodar

### Pré-requisitos

- Python 3.10+
- Chave de API do [OpenRouter](https://openrouter.ai/)

### Instalação

```bash
git clone https://github.com/seu-usuario/KernelBot.git
cd KernelBot
pip install -r requirements.txt
```

### Configuração

Crie um arquivo `.env` na raiz:

```
OPENROUTER_API_KEY=sua-chave-aqui
```

Variáveis opcionais:

| Variável | Default | Descrição |
|----------|---------|-----------|
| `ACL_GLOBAL_CONTEXT` | `geral` | Escopo BM25 sem filtro: `geral` (só silo geral) ou `all` (todos os silos) |
| `ACL_PINNED_MAX_TURNS` | `5` | Turnos antes do pinned context expirar |
| `ACL_PINNED_MAX_CHARS` | `24000` | Limite de caracteres no pinned context |
| `ACL_PINNED_WEAK_SCORE` | `0.4` | Score BM25 abaixo do qual se reutiliza o pin |

### Executar

```bash
python main.py
```

Ou com reload para desenvolvimento:

```bash
uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Acesse `http://127.0.0.1:8000`.

---

## Comandos do chat

| Comando | Efeito |
|---------|--------|
| `/python <pergunta>` | Busca RAG restrita ao silo `python` |
| `/visualizacao-sql <pergunta>` | Busca RAG restrita ao silo `visualizacao-sql` |
| `/projeto-bloco <pergunta>` | Busca RAG restrita ao silo `projeto-bloco` |
| `/planejamento-curso-carreira <pergunta>` | Busca RAG restrita ao silo `planejamento-curso-carreira` |
| `/doc <pergunta>` | Injeta todo o conteúdo de `content/doc/` no prompt |
| `/content <pergunta>` | Força RAG no escopo global (com fallback para os primeiros chunks se não houver hit) |
| `/reset` ou `/limpar` | Limpa o pinned context da sessão |

Sem comando, o sistema usa o campo `discipline` do JSON (se enviado) ou o escopo global configurado.

---

## Testes

```bash
python -m pytest tests/ -v
```

---

## Limitações

- **BM25 é lexical, não semântico** — se o vocabulário da pergunta divergir do corpus, o retrieval pode falhar. Use `/content` para forçar contexto.
- **Sem autenticação** — adequado para uso local (`127.0.0.1`). Não expor em rede sem proteção adicional.
- **Pinned context em RAM** — reiniciar o servidor perde o estado de sessão.
- **Comandos de silo não são automáticos** — novas subpastas em `content/` indexam automaticamente, mas o atalho `/nome` precisa ser adicionado manualmente em `_DISCIPLINE_COMMAND_PREFIXES` (`engine/context.py`).
- **Versões não fixadas** — `requirements.txt` sem pins exatos; risco de drift em novas instalações.

---

## Por que existe

Criado para resolver uma dor real: alunos do INFNET gastavam horas revisando gravações de aula para tirar dúvidas pontuais. O KernelBot transforma resumos estruturados dessas aulas em uma base pesquisável via chat — com controle de escopo, rastreabilidade e zero dependência de infra complexa.

---

## Stack

| Camada | Tecnologia |
|--------|------------|
| Servidor HTTP | FastAPI + Uvicorn |
| Índice de busca | BM25Okapi (`rank-bm25`) |
| File watching | Watchdog |
| LLM gateway | OpenRouter API (`httpx` async) |
| Frontend | HTML/CSS/JS puro (Jinja2) |
| Streaming | Server-Sent Events (SSE) |

---

## Licença

Veja o arquivo [LICENSE](LICENSE).
