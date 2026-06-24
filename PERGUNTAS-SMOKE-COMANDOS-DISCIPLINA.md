# Smoke test — comandos de disciplina

Perguntas espelhadas em [`tests/test_discipline_commands.py`](tests/test_discipline_commands.py) para validar parsing de `/comando` no servidor.

**Como usar:** envia cada mensagem **completa** no chat (comando + pergunta). Verifica badge de escopo, silo BM25 e fontes `db:<disciplina>/...`.

**Protocolo:** nova conversa antes de cada pergunta; aguardar `data: [DONE]`.

---

## Comandos válidos (devem activar o silo)

| # | Mensagem completa | Disciplina esperada | Query extraída |
|---|-------------------|---------------------|----------------|
| 1 | `/python o que são listas?` | `python` | `o que são listas?` |
| 2 | `/visualizacao-sql GROUP BY` | `visualizacao-sql` | `GROUP BY` |
| 3 | `/fluencia-ia diferença ML e DL` | `fluencia-ia` | `diferença ML e DL` |
| 4 | `/python-processamento-dados try except` | `python-processamento-dados` | `try except` |
| 5 | `/sql-modelagem-relacional normalização 3FN` | `sql-modelagem-relacional` | `normalização 3FN` |
| 6 | `/projeto-bloco crud ecommerce` | `projeto-bloco` | `crud ecommerce` |
| 7 | `/planejamento-curso-carreira currículo ATS` | `planejamento-curso-carreira` | `currículo ATS` |

### Critério de sucesso

- O bot reconhece o comando (label de escopo na UI).
- Retrieval restrito ao silo da disciplina.
- Fontes no rodapé começam por `db:<disciplina>/`.

---

## Prefixos inválidos (não devem activar comando)

O servidor exige **espaço ou fim** após o prefixo. Estas mensagens devem ser tratadas como texto livre (sem silo forçado pelo comando).

| # | Mensagem | Comportamento esperado |
|---|----------|------------------------|
| N1 | `/pythonfoo bar` | Comando **não** reconhecido; query = mensagem inteira |
| N2 | `/fluencia-iaextra` | Comando **não** reconhecido |
| N3 | `/sql-modelagem-relacionalfoo` | Comando **não** reconhecido |

---

## Comandos registados (SSOT)

Fonte: [`core/disciplines.json`](core/disciplines.json)

| Comando | Disciplina |
|---------|------------|
| `/planejamento-curso-carreira` | `planejamento-curso-carreira` |
| `/python-processamento-dados` | `python-processamento-dados` |
| `/sql-modelagem-relacional` | `sql-modelagem-relacional` |
| `/visualizacao-sql` | `visualizacao-sql` |
| `/projeto-bloco` | `projeto-bloco` |
| `/fluencia-ia` | `fluencia-ia` |
| `/python` | `python` |

> Ordem no servidor: **comando mais longo primeiro** (ex.: `/python-processamento-dados` antes de `/python`).

---

## Bateria alargada

- **10 perguntas por disciplina (70 total):** [`PERGUNTAS-SMOKE-POR-DISCIPLINA.md`](PERGUNTAS-SMOKE-POR-DISCIPLINA.md)
- Gerais, `/doc`, ambíguas (100 perguntas): [`PERGUNTAS-SMOKE-DISCIPLINAS.md`](PERGUNTAS-SMOKE-DISCIPLINAS.md)
