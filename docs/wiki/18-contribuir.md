# Como contribuir

[← Índice](README.md) · [Início público](00-inicio-publico.md)

Guia para quem quer **corrigir bugs**, **melhorar o RAG/UI** ou **actualizar documentação**. Não é necessário conhecer todo o stack — escolha uma área abaixo.

**Última revisão:** junho/2026.

---

## Repositórios

| Repo | Papel | Contribuições típicas |
|------|-------|------------------------|
| **KernelBot** | API, BM25, gates, frontend, wiki | Código Python/JS, testes, `docs/wiki/` |
| **ISS** | Aulas Markdown, JSONs, pipeline ingest | Conteúdo pedagógico, keywords B2, workflow CI |

Links: substituir pelos URLs GitHub reais do projecto quando publicar.

---

## Antes de abrir um PR

1. **Issue ou alinhamento** — para mudanças grandes, abra issue ou comente no PR o «porquê».
2. **Branch** — crie a partir de `main` (ou branch acordada): `fix/…`, `feat/…`, `docs/…`.
3. **Staging local** — valide que o chat sobe e responde (ver abaixo).
4. **Testes** — `pytest -q` verde antes do PR.
5. **Diff focado** — uma preocupação por PR quando possível (ex.: docs separado de refactor grande).

---

## Ambiente local (KernelBot)

### Pré-requisitos

- Python 3.11+ (ou versão do projecto)
- Docker (MySQL staging na porta **3307**)
- Chave do provider LLM no `.env`: `CURSOR_API_KEY` (default `ACL_LLM_PROVIDER=cursor`) **ou** `OPENROUTER_API_KEY` (se `ACL_LLM_PROVIDER=openrouter`)
- Repositório **ISS** em `../ISS` (ingest completo opcional)

### Subir staging

```bash
cd KernelBot
chmod +x bin/*.sh
./bin/staging-setup.sh      # uma vez — E2E deve terminar com SIM
./bin/staging-serve.sh      # deixar aberto — http://127.0.0.1:8001
```

**Não uses** `python main.py` directo se o `.env` apontar para produção — usa sempre `./bin/staging-serve.sh`.

Guia completo: [TESTE-LOCAL.md](../../TESTE-LOCAL.md) · wiki [13-staging-testes.md](13-staging-testes.md).

### Testes automatizados

```bash
cd KernelBot
source .venv/bin/activate   # se aplicável
pytest -q
```

Suites relevantes por área:

| Área | Ficheiros (exemplos) |
|------|----------------------|
| Histórico de conversa | `tests/test_conversation_history.py` |
| Pin / scope hints | `tests/test_scope_hint.py`, `tests/test_pin_context.py` |
| Grounding anchored | `tests/test_post_generation_anchored.py` |
| Chat provider | `tests/test_chat_provider_post_gen.py` |

---

## Smoke manual (browser)

Depois de mudanças em retrieval, UI ou contexto:

| Bateria | Ficheiro | Foco |
|---------|----------|------|
| Escopo, pin, advisory | [PERGUNTAS-SMOKE-ESCOPO-PIN.md](../../PERGUNTAS-SMOKE-ESCOPO-PIN.md) | 10 turnos rápidos |
| Memória multi-turno | [PERGUNTAS-SMOKE-HISTORICO-CHAT.md](../../PERGUNTAS-SMOKE-HISTORICO-CHAT.md) | 3 turnos H1–H3 |

URL: http://127.0.0.1:8001 · hard refresh após deploy local.

---

## Onde mexer (mapa rápido)

| Quer alterar… | Comece em |
|---------------|-----------|
| Gates / advisory pós-LLM | `engine/retrieval.py`, `engine/chat_provider.py` |
| Prompt / mensagens / pin | `engine/context.py` |
| API `/chat`, SSE | `api/routes.py`, `docs/wiki/07-apis-e-sse.md` |
| UI, histórico, Nova conversa | `frontend/src/ui.js`, `frontend/src/utils/history.js` |
| BM25 / chunking | `engine/database.py`, `docs/wiki/05-bm25-chunking.md` |
| Variáveis de ambiente | `.env.staging.example`, `docs/wiki/12-configuracao.md` |
| Wiki | `docs/wiki/*.md` (SSOT — espelhar para GitHub Wiki depois) |

Estrutura completa: [03-estrutura-codigo.md](03-estrutura-codigo.md).

---

## Contribuir com conteúdo (aulas)

1. Editar Markdown em **ISS** (`content/<disciplina>/…`).
2. Exportar JSON (`lesson-json-export.mjs`).
3. Ingerir para MySQL (`ingest-knowledge.py` / `./bin/staging-ingest-iss.sh`).
4. `/reload` no KernelBot (`POST /chat` com `message: "/reload"` + `Authorization: Bearer $ACL_RELOAD_BEARER_TOKEN`).

Pipeline: [10-integracao-iss-fase5b.md](10-integracao-iss-fase5b.md).

Documentos **meta** (sobre o bot, faculdade) — rascunhos em KernelPlanner `corpus-meta/`; mesma pipeline quando prontos.

---

## Documentação

| Acção | Onde |
|-------|------|
| Wiki técnica | `docs/wiki/` — actualizar índice em [README.md](README.md) |
| Camada pública | `00-inicio-publico.md`, `18-contribuir.md`, `19-faq-usuario.md` |
| Entrada curta na raiz | `documentation.md` (aponta para a wiki) |
| Prompt agente doc (Fase 6) | [PROMPT-AGENTE-DOCUMENTACAO.md](../PROMPT-AGENTE-DOCUMENTACAO.md) |

Ao adicionar página nova: incluir no índice da wiki e, se for pública, linkar a partir de [00-inicio-publico.md](00-inicio-publico.md).

---

## Estilo de código e PR

- Seguir padrões existentes no ficheiro que editas (naming, imports, testes).
- Commits: mensagem clara no imperativo («fix advisory when [Fonte:] present»).
- Não commitar `.env`, credenciais ou dumps MySQL.
- Documentar variáveis novas em [12-configuracao.md](12-configuracao.md).

---

## Ver também

- [FAQ — utilizador](19-faq-usuario.md) — linguagem para alunos (útil ao escrever UX)
- [Segurança e logs](14-seguranca-observabilidade.md) — redacção de segredos
- [Backlog](16-backlog.md) — débitos conhecidos
