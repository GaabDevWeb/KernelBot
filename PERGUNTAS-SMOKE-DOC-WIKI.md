# Smoke test — silo `/doc` (wiki no MySQL)

Perguntas para validar o comando `/doc` após `bin/ingest-wiki-doc.sh` + `/reload` (ou restart).

**Como usar:** envia cada pergunta no chat com o prefixo `/doc` (ex.: `/doc O que é o KernelBot?`). Regista a resposta do bot e compara com a coluna **Referência wiki**. São **30 perguntas** em 4 níveis (1–5 básico, 6–10 intermédio, 11–15 avançado, 16–30 expert).

**Critério mínimo de sucesso:** resposta coerente com a wiki **e** citação `[Fonte: db:doc/…]` quando houver material indexado.

**Pré-requisitos:** `./bin/staging-setup.sh` (ou ingest em produção) + `./bin/staging-serve.sh`.

## Protocolo de execução (obrigatório)

Antes de **cada** pergunta (ou no máximo a cada 3 se estiveres a testar continuidade de sessão):

1. Clica **Nova conversa** no UI (não uses só `/reset` — isso limpa o pin no servidor mas **não** zera o `history` em `localStorage` nem o `session_id` visual).
2. Aguarda o badge do header voltar a **Online** e o stream anterior terminar com `data: [DONE]` (não envies a pergunta seguinte enquanto o composer estiver desactivado).
3. Envia a pergunta com prefixo `/doc`.
4. Não abras múltiplas abas na mesma sessão nem dispares perguntas em paralelo.

O silo `/doc` **não persiste pin** entre turnos (consulta wiki); o protocolo acima evita histórico residual a mascarar fontes no cabeçalho.

---

## Nível 1 — Básico (utilizador / curioso)

### 1. Identidade do bot

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc O que é o KernelBot?` |
| **Páginas esperadas** | `00-inicio-publico`, `19-faq-usuario` |
| **Referência wiki** | Tutor de chat ancorado no **material das aulas indexadas** (não na internet aberta). Sigla ACL = Agente de Contexto Local. Explica com `[Fonte: …]`; não entrega gabarito integral; não substitui professor nem portal oficial. |

### 2. Comandos de disciplina

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc Quais comandos posso usar no início da mensagem para focar numa disciplina?` |
| **Páginas esperadas** | `00-inicio-publico`, `19-faq-usuario` |
| **Referência wiki** | `/python`, `/visualizacao-sql`, `/projeto-bloco`, `/planejamento-curso-carreira`, `/doc` (documentação do bot). Comando no **início** da mensagem, seguido do texto. |

### 3. Tema fixado e `/reset`

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc O que faz o comando /reset?` |
| **Páginas esperadas** | `19-faq-usuario`, `00-inicio-publico` |
| **Referência wiki** | Limpa o **tema fixado (pin)** no servidor. Para apagar também o histórico visual no browser, usar **Nova conversa** (não só `/reset`). |

### 4. Limites do tutor

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc O Kernel pode me dar o gabarito completo do trabalho prático?` |
| **Páginas esperadas** | `00-inicio-publico`, `19-faq-usuario` |
| **Referência wiki** | **Não** — orienta conceitos; não entrega solução integral para colar. Também recusa senhas/API keys e jailbreak. |

### 5. Memória da conversa

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc Onde fica guardado o histórico da minha conversa?` |
| **Páginas esperadas** | `19-faq-usuario`, `01-visao-geral` |
| **Referência wiki** | No **browser** (`localStorage`), não há login/conta. Outro computador ou browser **não** partilha histórico. Truncagem automática dos turnos enviados à API. |

---

## Nível 2 — Intermédio (utilizador atento + contribuidor)

### 6. Formato das fontes

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc O que significa [Fonte: db:python/variaveis-tipos-estilo-python] na resposta?` |
| **Páginas esperadas** | `19-faq-usuario` |
| **Referência wiki** | Trecho indexado de uma aula: `db:` + **disciplina** + **slug** da aula. Se não houver fonte e o tema estiver fora do material, deve admitir lacuna em vez de inventar. |

### 7. Pin e badge «Continuando»

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc O que é o tema fixado ou o badge Continuando no chat?` |
| **Páginas esperadas** | `19-faq-usuario` |
| **Referência wiki** | O Kernel **fixa um tema** (ex.: SQL) para follow-ups curtos. Se mudar de disciplina, usar `/python …` ou `/reset`. Rodapé pode avisar quando fontes misturam contextos. |

### 8. O que o ACL não é

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc O KernelBot usa busca semântica ou embeddings como o ChatGPT?` |
| **Páginas esperadas** | `01-visao-geral` |
| **Referência wiki** | **Não** — apenas **BM25 léxico** sobre MySQL. Não lê `KernelBot/content/` no fluxo actual; fonte é MySQL. Não faz auto-reload periódico (`watcher.py` é legado). |

### 9. `/reset` vs Nova conversa

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc Qual a diferença entre /reset e o botão Nova conversa?` |
| **Páginas esperadas** | `19-faq-usuario` |
| **Referência wiki** | `/reset` → limpa **pin** no servidor. **Nova conversa** → apaga histórico local, novo `session_id`, limpa pin. Para esquecer a conversa visualmente, precisa de Nova conversa. |

### 10. Grounding `anchored` e badges

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc O que é a política de grounding anchored e o que significa Modo didático na interface?` |
| **Páginas esperadas** | `01-visao-geral`, `19-faq-usuario`, `06-gates-e-decisoes` |
| **Referência wiki** | Default `ACL_GROUNDING_POLICY=anchored`: trechos RAG são **evidência primária**; pode haver **extensão pedagógica rotulada**. Badge «Modo didático» = política anchored. Em `strict`, override destrutivo é mais conservador. |

---

## Nível 3 — Avançado (dev / operador / RAG)

### 11. Chunking BM25

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc Quantas palavras tem cada chunk BM25 e qual o overlap entre janelas?` |
| **Páginas esperadas** | `05-bm25-chunking`, `15-glossario` |
| **Referência wiki** | **500 palavras** por janela (`DB_CHUNK_WORDS`), **overlap 50** (`DB_CHUNK_OVERLAP`). Chunking só em **RAM**; MySQL guarda 1 documento por aula/row. |

### 12. Opção B2 e IDF

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc Por que os metadados léxicos B2 vão só no chunk 0 e não em todos os chunks?` |
| **Páginas esperadas** | `05-bm25-chunking`, `11-enriquecimento-lexico-b2` |
| **Referência wiki** | Meta em **todos** os chunks faria a mesma keyword aparecer em N docs do mini-índice → **IDF → 0** → scores nulos → `insufficient_context`. Opção B2: meta só em `chunk_index == 0`. |

### 13. API `/reload`

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc Existe uma rota POST /reload separada? Como reconstruo o índice BM25?` |
| **Páginas esperadas** | `07-apis-e-sse`, `09-fluxos-operacionais` |
| **Referência wiki** | **Não** existe `POST /reload` dedicado. `/reload` é **mensagem** no corpo de `POST /chat` (`message: "/reload"`) com **Bearer** `ACL_RELOAD_BEARER_TOKEN`. Reinício do processo também reconstrói o índice. **Smoke:** validar o Bearer numa **Nova conversa** isolada (curl/Postman ou DevTools), não misturar com perguntas de conteúdo na mesma sessão. |

### 14. `index_gap` e catálogo

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc O que é index_gap no retrieval e quando acontece?` |
| **Páginas esperadas** | `06-gates-e-decisoes`, `15-glossario` |
| **Referência wiki** | Aula **confiante no catálogo ISS** mas **ausente do índice** MySQL/RAM. LLM é chamado na mesma; advisory em `context.py`; não é hard stop de retrieval. |

### 15. Ingest da wiki no silo doc

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc Como a documentação da wiki entra no MySQL para o comando /doc funcionar?` |
| **Páginas esperadas** | `18-contribuir`, `00-inicio-publico`, `13-staging-testes` |
| **Referência wiki** | SSOT: `docs/wiki/*.md`. Script `bin/ingest-wiki-doc.sh` faz UPSERT em `knowledge` com `discipline=doc`. Staging: `KERNELBOT_ENV=staging ./bin/ingest-wiki-doc.sh`. Depois: restart ou `/reload`. Fontes no chat: `db:doc/{slug}`. |

---

## Nível 4 — Expert (arquitetura, SSE, gates, CI)

> **Dica:** neste nível segue o [protocolo](#protocolo-de-execução-obrigatório) — **Nova conversa** antes de cada pergunta (máx. 3 na mesma sessão só para teste de continuidade). O silo `/doc` não persiste pin; o histórico residual no browser ainda pode afectar `history` enviado à API.

### 16. Política `hybrid` vs `anchored`

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc Com ACL_GROUNDING_POLICY=hybrid, em que condições o Kernel injeta grounding_permissive.txt em vez de grounding_anchored.txt, e o LLM é chamado na mesma?` |
| **Páginas esperadas** | `06-gates-e-decisoes`, `17-prompts-referencia`, `12-configuracao` |
| **Referência wiki** | `hybrid` usa `anchored` quando há chunks ou `reason=ok`; usa `grounding_permissive.txt` **sem chunks** em retrieval fraco. Gates de retrieval **não** bloqueiam o LLM — classificam `reason`/`confidence` apenas. `ACL_RETRIEVAL_MODE` está deprecado. |

### 17. Sanity pós-geração e supressão B3.1

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc Quais flags dispara post_generation_flags após o LLM responder, qual o limiar de termos não suportados em strict vs anchored, e quando anchored_post_generation_advisory_flags suprime o advisory amarelo?` |
| **Páginas esperadas** | `06-gates-e-decisoes`, `08-frontend-ui` |
| **Referência wiki** | Flags: `missing_informative_terms`, `missing_source_entities`, `introduced_unsupported_terms`. Limiares: **>25** termos longos (strict), **>50** (anchored/hybrid) — `unsupported_limit` em `engine/retrieval.py`. Em `anchored`, advisory suprimido se há `[Fonte:`, declaração de lacuna/recusa, ou bloco *Extensão pedagógica*. `strict` → override destrutivo `post_generation_misalignment`; `anchored` → `post_generation_advisory` suave, resposta mantida. |

### 18. Dois eventos `[ACL_META]` no SSE

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc O stream SSE pode emitir dois [ACL_META] no mesmo turno? Em que ordem e com que campos extra no segundo evento?` |
| **Páginas esperadas** | `07-apis-e-sse`, `08-frontend-ui`, `06-gates-e-decisoes` |
| **Referência wiki** | Sim: meta **inicial** antes de qualquer texto; **segundo** opcional pós-geração. Segundo meta pode trazer `post_generation_advisory`, `post_generation_override`, `post_generation_flags`, `disambiguation_options`. Contrato v=3; linhas `data: [ACL_META]{json}` + fragmentos + `data: [DONE]`. UI reage: override → badge «Revisão»; advisory → hint amarelo sem apagar resposta. |

### 19. Desambiguação com geração (`ambiguous_retrieval`)

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc Com ACL_DISAMBIGUATION_ENABLED=true e reason ambiguous_retrieval, como o modelo deve formatar as opções, que ficheiro de grounding entra no prompt e como o frontend evita mostrar XML cru na bolha?` |
| **Páginas esperadas** | `17-prompts-referencia`, `08-frontend-ui`, `06-gates-e-decisoes` |
| **Referência wiki** | Injecta `grounding_disambiguation.txt`; fontes numeradas `[Fonte 1]`, `[Fonte 2]`, … Saída XML `<ambiguity_options><option discipline=… slug=… label=…/></ambiguity_options>`. `parseAmbiguityOptions.js` remove XML do markdown e monta `DisambiguationChips`. Com `allow_generation=true`, stream continua; chips incrementais no slot sem esperar fim do stream. Margem BM25 < `ACL_RETRIEVAL_MIN_SCORE_MARGIN` (0.15) dispara `ambiguous_retrieval`. |

### 20. Pin, merge e `sources_note`

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc Como funciona o merge entre chunks fixados (pin) e a busca BM25 do turno actual, e quando aparece sources_note na UI?` |
| **Páginas esperadas** | `06-gates-e-decisoes`, `08-frontend-ui`, `12-configuracao` |
| **Referência wiki** | `PinnedSessionStore` por `session_id`; TTL `ACL_PINNED_MAX_TURNS` (default 5), limite `ACL_PINNED_MAX_CHARS`. Turno combina pin + retrieval; meta `pin_chunks_used: true` → badge «Continuando». `sources_note` quando fontes do turno **≠** só pin — nota informativa no rodapé (`.message-sources-note`), não é advisory amarelo. Copy orienta `/reset` ou comando de disciplina. **Nota smoke:** com `ACL_DISAMBIGUATION_ENABLED=false` (default), `ambiguous_retrieval` **não** deve mostrar chips — só texto + breadcrumb; chips só com a flag `true` ou XML explícito do modelo. |

### 21. Campo `history` na API (POC)

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc Quais validações o servidor aplica ao campo history do POST /chat, que roles são rejeitados, e como isso difere do que fica no localStorage do browser?` |
| **Páginas esperadas** | `07-apis-e-sse`, `08-frontend-ui`, `12-configuracao` |
| **Referência wiki** | `history`: lista `{ role, content }`; roles `user`/`assistant` apenas — `system` do cliente → **400**. Máx. **40** itens na entrada; **8192** chars/item (truncado server-side). Prompt: `ACL_CHAT_HISTORY_MAX_TURNS` (12), `ACL_CHAT_HISTORY_MAX_CHARS` (12000). UI: `localStorage` `acl_conversation_v1`, até 30 turnos / 200k chars; POC sem auth — history pode ser forjado. Ordem prompt: system RAG → history → user actual. |

### 22. Opção B — MySQL vs chunking RAM

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc Na Opção B, o que fica gravado no MySQL por aula, onde ocorre o chunking 500/50, e o que acontece a uma row com content acima de MAX_CONTENT_CHARS?` |
| **Páginas esperadas** | `04-dados-e-mysql`, `05-bm25-chunking`, `10-integracao-iss-fase5b` |
| **Referência wiki** | **1 row** = `(discipline, slug)` com `content` unificado (meta B2 + body); UPSERT sobrescreve documento inteiro — sem `chunk_id` no SQL. Chunking só em RAM (`engine/database.py::_chunk_text`). Limite **4M** chars: row ignorada no fetch, log `db_chunk_row_skipped`. ISS também valida antes do UPSERT. `source` no índice: `db:{discipline}/{slug}`. |

### 23. Drift catálogo e `GET /health/catalog`

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc O que devolve GET /health/catalog, que autenticação exige, e como o Job 3 do workflow ISS usa essa rota para detectar drift?` |
| **Páginas esperadas** | `07-apis-e-sse`, `10-integracao-iss-fase5b`, `04-dados-e-mysql` |
| **Referência wiki** | Bearer `ACL_RELOAD_BEARER_TOKEN` (alias `KERNELBOT_RELOAD_TOKEN`); sem token configurado → 503. JSON: `catalog_enabled`, `indexed_lesson_keys_count`, `catalog_lesson_keys_count`, `catalog_only_count`, `catalog_only_sample` (até 10 chaves). Job 3 compara catálogo ISS vs `indexed_lesson_keys`; falha CI se drift crítico; depois `POST /chat` com `message=/reload`. |

### 24. Ordem dos gates em `build_decision`

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc Qual a ordem de avaliação dos gates em build_decision e que reason resulta de top_score abaixo de ACL_RETRIEVAL_MIN_SCORE versus margem entre 1º e 2º candidato abaixo de ACL_RETRIEVAL_MIN_SCORE_MARGIN?` |
| **Páginas esperadas** | `06-gates-e-decisoes`, `12-configuracao`, `15-glossario` |
| **Referência wiki** | Ordem: (1) sem hits / score baixo → `insufficient_context`; (2) `MIN_TERMS` → `underspecified_query`; (3) margem top2 < **0.15** → `ambiguous_retrieval`; (4) coverage → `context_misaligned`; (5) vague high risk; (6) senão `ok`. Defaults: `MIN_SCORE=1.5`, `MIN_SCORE_MARGIN=0.15`, `MIN_COVERAGE=0.34`, `MIN_TERMS=2`. **Todas** as reasons chamam LLM (excepto `provider_error`). |

### 25. `index_gap` com catálogo activo

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc Com ACL_CATALOG_ENABLED=true, o que é index_gap, bloqueia a geração do LLM, e que componentes carregam o catálogo lexical ISS?` |
| **Páginas esperadas** | `10-integracao-iss-fase5b`, `06-gates-e-decisoes`, `03-estrutura-codigo` |
| **Referência wiki** | `index_gap`: aula **confiante no catálogo** (`lessons.json` / `search-index.json`) mas **ausente** do índice MySQL/RAM. **Não** é hard stop de retrieval — LLM chamado; advisory em `context.py`. Componentes: `lesson_catalog.py`, `catalog_sync.py` (`bootstrap_catalog_state`, `refresh_indexed_lesson_keys_state`). UI: `IndexGapAlert` só em hard stop estruturado (`allow_generation=false`). |

### 26. Camadas de decisão no runtime

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc Enumera as camadas de decisão do KernelBot desde a validação em api/routes.py até o override pós-geração, e esclarece se allow_generation=false nos gates de retrieval bloqueia o LLM.` |
| **Páginas esperadas** | `02-arquitetura`, `17-prompts-referencia`, `06-gates-e-decisoes` |
| **Referência wiki** | Ordem: (1) entrada validada; (2) escopo `/doc`, pin, disciplina; (3) BM25 `search_candidates`; (4) `build_decision`; (5) montagem prompt + LLM; (6) `post_generation_flags`; (7) SSE ACL_META + tokens + DONE. `allow_generation` em ACL_META é **telemetria/UI** — gates **não** bloqueiam LLM por defeito. Hard stop real: `provider_error`, override `strict` pós-geração, alguns fluxos `trace.decision=hard_stop`. |

### 27. `sticky_instruction.txt` (backlog)

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc O ficheiro sticky_instruction.txt é injectado no prompt quando há pin activo? Onde está definido e qual o estado actual segundo a wiki?` |
| **Páginas esperadas** | `17-prompts-referencia`, `03-estrutura-codigo`, `12-configuracao` |
| **Referência wiki** | Carregado em `Settings.load()` (boot falha se faltar). Injectado via `_sticky_block_for_pin()` em `context.py` quando há pin activo (template `{name}` ← display do pin), entre catálogo e grounding. Silo `/doc` não persiste pin — sticky só em tutoria com pin ISS. |

### 28. Segurança: tokens, logs e `provider_error`

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc Como o KernelBot protege segredos nos logs, o que acontece quando OpenRouter ou Cursor falham, e que superfícies exigem Bearer token?` |
| **Páginas esperadas** | `14-seguranca-observabilidade`, `07-apis-e-sse`, `06-gates-e-decisoes` |
| **Referência wiki** | `SecretRedactingFilter` + `redact_secrets()` mascaram API keys; `exc_info` preservado. Falha LLM → `provider_error`, `allow_generation=false`, texto fixo streamed (sem LLM). Bearer: `/reload` via `POST /chat` e `GET /health/catalog`. `/reload` sem token válido → 401; token não configurado → 503. Nunca commitar `.env` / `.env.staging.local`. |

### 29. Staging: precedência de `.env`

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc Com KERNELBOT_ENV=staging, qual ficheiro de ambiente tem prioridade sobre o .env principal para DB_HOST e DB_PORT, e por que não devo correr python main.py directamente contra Aiven por engano?` |
| **Páginas esperadas** | `12-configuracao`, `13-staging-testes`, `04-dados-e-mysql` |
| **Referência wiki** | `Settings.load()` carrega `.env.staging.local` com `override=True` quando `KERNELBOT_ENV=staging`. Staging: MySQL Docker **:3307**, DB `kernelbot_staging`. `bin/staging-serve.sh` exporta staging + **não** faz `source .env` no bash (evita linhas inválidas); LLM keys vêm do `.env` via Python dotenv. Produção Aiven no `.env` + `python main.py` sem staging → risco de apontar para prod ou falha de ligação. |

### 30. Montagem do system message

| Campo | Conteúdo |
|-------|----------|
| **Pergunta** | `/doc Qual a ordem exacta de _assemble_system_content no system prompt, e qual a precedência semântica entre grounding_strict, catálogo e trechos RAG segundo a wiki de prompts?` |
| **Páginas esperadas** | `17-prompts-referencia`, `03-estrutura-codigo`, `06-gates-e-decisoes` |
| **Referência wiki** | Ordem: (1) `system_prompt.txt`; (2) `catalog_router.txt` se há secção catálogo; (3) `catalog_section` dinâmico; (4) `sticky_instruction.txt` se pin activo; (5) grounding condicional (`_select_grounding`); (6) trechos RAG `[Fonte: …]`. Precedência: grounding factual > catálogo > evidência RAG > identidade/tom > dados do utilizador. Função em `engine/context.py`. |

---

## Checklist rápido pós-rodada

**Passo 0 (cada pergunta):** Nova conversa → badge **Online** → enviar pergunta → aguardar `[DONE]`.

| # | Passou? | Citou `db:doc/…`? | Notas |
|---|---------|-------------------|-------|
| 1 | | | |
| 2 | | | |
| 3 | | | |
| 4 | | | |
| 5 | | | |
| 6 | | | |
| 7 | | | |
| 8 | | | |
| 9 | | | |
| 10 | | | |
| 11 | | | |
| 12 | | | |
| 13 | | | |
| 14 | | | |
| 15 | | | |
| 16 | | | |
| 17 | | | |
| 18 | | | |
| 19 | | | |
| 20 | | | |
| 21 | | | |
| 22 | | | |
| 23 | | | |
| 24 | | | |
| 25 | | | |
| 26 | | | |
| 27 | | | |
| 28 | | | |
| 29 | | | |
| 30 | | | |

## Regressões a vigiar

- Pergunta **fora** do silo doc com `/doc` activo não deve misturar fontes de aulas (`db:python/…`) sem aviso.
- Pergunta **sem** `/doc` sobre «o que é o Kernel» pode cair no RAG global — comportamento esperado, não falha do silo doc.
- Pergunta de **uma palavra** (`/doc KernelBot`) pode gerar `underspecified_query` (`MIN_TERMS=2`) — preferir as perguntas completas desta lista.
- Nível **expert** (16–30): **Nova conversa** antes de cada pergunta (ver protocolo).
- Perguntas **19** e **17** assumem leitura da wiki — não exigem `ACL_DISAMBIGUATION_ENABLED=true` no teu `.env` para passar no conteúdo; validam conhecimento documentado.
- Pergunta **20** com `ACL_DISAMBIGUATION_ENABLED=false`: sem chips de desambiguação (só texto); margem BM25 baixa entre páginas doc é esperada.
- Aguardar **`[DONE]`** antes da pergunta seguinte; pedidos paralelos distorcem latência e meta SSE.
