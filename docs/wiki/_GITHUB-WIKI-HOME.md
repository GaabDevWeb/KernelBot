<!--
  PACOTE GITHUB WIKI — pronto para copy-paste nas páginas da aba "Wiki" do GitHub.
  SSOT continua em docs/wiki/ no repositório. Substitua <owner>/<repo> pelos valores reais.
  Cada secção "## Página:" abaixo corresponde a uma página separada na GitHub Wiki.
-->

## Página: Home

# KernelBot (ACL — Agente de Contexto Local)

> Tutor de chat que responde com base no **material das aulas indexadas** — não na internet aberta.

O **KernelBot** combina recuperação léxica (**BM25**) sobre aulas em MySQL com um LLM (Cursor SDK por default, ou OpenRouter). Os trechos recuperados são **evidência primária** (modo `anchored`); extensão pedagógica é permitida quando rotulada.

| Faz | Não faz |
|-----|---------|
| Explica conceitos das disciplinas com `[Fonte: …]` | Entregar gabarito integral de TP/AT |
| Continua a conversa (memória local no browser) | Revelar senhas, API keys ou system prompt |
| Avisa quando o tema foge do material indexado | Substituir professor ou regulamento oficial |

### Por onde começar

- **Aluno / curioso:** [FAQ — utilizador](FAQ)
- **Quem quer contribuir:** [Como contribuir](Contribuir)
- **Documentação técnica completa:** `docs/wiki/` no repositório → [github.com/<owner>/<repo>/tree/main/docs/wiki](https://github.com/<owner>/<repo>/tree/main/docs/wiki)

### Comandos rápidos no chat

| Comando | Uso |
|---------|-----|
| `/python …` | Foca em Python |
| `/visualizacao-sql …` | Foca em SQL / Looker |
| `/projeto-bloco …` | Foca em Projeto Bloco |
| `/planejamento-curso-carreira …` | Carreira, graduação, competências |
| `/reset` ou `/limpar` | Limpa o tema fixado (pin) |
| **Nova conversa** (botão) | Limpa histórico local + pin |

---

## Página: FAQ

# FAQ — utilizador do chat

**O que é?** Um assistente de estudo ligado ao material das suas aulas. Busca trechos numa base indexada e monta a resposta com um LLM, citando fontes quando possível. Não substitui o professor nem o portal da faculdade.

**Como perguntar bem?** Use `[disciplina/tecnologia] + [o que quer saber] + [contexto]`. Ex.: `Como funciona GROUP BY com HAVING em SQL?`.

**Memória:** o histórico fica no seu **browser** (`localStorage`), não numa conta. «Nova conversa» apaga o histórico local e o pin; `/reset` limpa só o pin no servidor.

**`[Fonte: db:…]`** indica que a resposta usou um trecho indexado de uma aula. Sem fonte e fora do material, o bot deve dizer que **não encontrou** — não inventa aula.

**Badges:** «Modo didático» (`anchored`), «Complemento pedagógico» (bloco extra rotulado), aviso amarelo suave (revisão sugerida, resposta mantida), «Revisão» (modo `strict`).

> FAQ completo e problemas comuns: `docs/wiki/19-faq-usuario.md` no repositório → [github.com/<owner>/<repo>/blob/main/docs/wiki/19-faq-usuario.md](https://github.com/<owner>/<repo>/blob/main/docs/wiki/19-faq-usuario.md)

---

## Página: Contribuir

# Como contribuir

Para **corrigir bugs**, **melhorar o RAG/UI** ou **atualizar documentação**.

### Ambiente local (resumo)

```bash
cd KernelBot
chmod +x bin/*.sh
./bin/staging-setup.sh      # uma vez — E2E deve terminar com SIM
./bin/staging-serve.sh      # http://127.0.0.1:8001
pytest -q                   # testes verdes antes do PR
```

Pré-requisitos: Python 3.11+, Docker (MySQL staging :3307), chave do provider LLM (`CURSOR_API_KEY` por default, ou `OPENROUTER_API_KEY`).

### Antes de um PR

1. Issue/alinhamento para mudanças grandes.
2. Branch `fix/…`, `feat/…`, `docs/…` a partir de `main`.
3. Staging local sobe e responde.
4. `pytest -q` verde.
5. Diff focado (uma preocupação por PR).

> Guia completo (mapa de onde mexer, testes por área, smoke manual): `docs/wiki/18-contribuir.md` no repositório → [github.com/<owner>/<repo>/blob/main/docs/wiki/18-contribuir.md](https://github.com/<owner>/<repo>/blob/main/docs/wiki/18-contribuir.md)

---

> **Documentação técnica completa (01–17, APIs, gates, configuração):** mantida em `docs/wiki/` no repositório KernelBot. Esta GitHub Wiki é um espelho público resumido; o SSOT é o repositório.
