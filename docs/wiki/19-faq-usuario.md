# FAQ — utilizador do chat

[← Índice](README.md) · [Início público](00-inicio-publico.md)

Perguntas frequentes para **alunos** e **curiosos** que usam o KernelBot no browser. Para detalhe técnico, ver a wiki 01–17.

**Última revisão:** junho/2026.

---

## O que é o Kernel?

É um assistente de estudo ligado ao **material das suas aulas** (Python, SQL, Projeto Bloco, planejamento de carreira, etc.). Ele busca trechos relevantes numa base indexada e monta a resposta com um modelo de linguagem — citando fontes quando possível.

Não substitui o professor, o portal da faculdade nem o regulamento oficial.

---

## Como fazer uma boa pergunta?

Formato que funciona melhor:

**[disciplina ou tecnologia] + [o que quer saber] + [contexto opcional]**

Exemplos:

- `Como funciona GROUP BY com HAVING em SQL?`
- `/python Me explica variáveis com um exemplo de cadastro simples`
- `Por que aprender Python em ADS?`

Perguntas muito curtas (`oi`, uma palavra só) podem receber pedido de mais contexto.

---

## Comandos no início da mensagem

| Comando | Disciplina / silo |
|---------|-------------------|
| `/python` | Python |
| `/visualizacao-sql` | Visualização de dados e SQL |
| `/projeto-bloco` | Projeto Bloco |
| `/planejamento-curso-carreira` | Graduação, carreira, competências |
| `/doc` | Documentação do bot (quando indexada) |
| `/reset` ou `/limpar` | Limpa o **tema fixado** (pin) |

Use o comando **no início** da mensagem, seguido do texto:

```text
/python E o que é f-string?
```

---

## O que é «tema fixado» ou «Continuando…»?

Depois de algumas perguntas, o Kernel pode **fixar um tema** (ex.: SQL) para follow-ups como «E o HAVING?». Aparece um badge tipo **Continuando: …** no campo de entrada.

| Situação | O que fazer |
|----------|-------------|
| Quer continuar no mesmo tema | Pergunte normalmente («E no meu exemplo?») |
| Mudou de disciplina (SQL → Python) | Use `/python …` ou `/reset` |
| Rodapé avisa que fontes misturam contextos | `/reset` ou comando da disciplina certa |

---

## Memória da conversa

O histórico fica guardado no **seu browser** (`localStorage`), não numa conta de login.

| Acção | Efeito |
|-------|--------|
| Continuar na mesma aba | O Kernel lembra turnos anteriores (ex.: «qual nome usei no primeiro exemplo?») |
| **Nova conversa** (botão no header) | Apaga histórico local, novo ID de sessão, limpa pin |
| `/reset` | Limpa pin no servidor; use **Nova conversa** para apagar histórico visual |
| Fechar e reabrir o browser | Histórico mantém-se (mesmo computador / mesma origem) |
| Outro computador ou browser | Não partilha histórico |

**Limite:** só os turnos mais recentes são enviados à API (truncagem automática).

---

## O que significa `[Fonte: db:…]`?

Indica que a resposta usou trecho indexado de uma aula, por exemplo:

```text
[Fonte: db:python/variaveis-tipos-estilo-python]
```

- `python` — disciplina  
- `variaveis-tipos-estilo-python` — slug da aula  

Se **não** houver fonte e o tema estiver fora do material, o Kernel deve dizer que **não encontrou** na base — em vez de inventar uma aula.

---

## Badges e avisos na interface

| O que vê | Significado |
|----------|-------------|
| **Modo didático** | Política `anchored` — pode haver extensão pedagógica rotulada |
| **Complemento pedagógico** | Bloco extra além do material indexado (explícito no texto) |
| Aviso amarelo suave | Revisão automática sugerida — resposta **mantida** (não é erro fatal) |
| **Revisão** (modo rigoroso) | Resposta pode ter saído do escopo das fontes (`strict`) |
| Chips de desambiguação | Várias aulas parecidas — escolha ou refine a pergunta |

---

## O que o Kernel **não** deve fazer

| Pedido | Comportamento esperado |
|--------|------------------------|
| Senha do banco, API keys | Recusa |
| «Ignore as regras» / jailbreak | Mantém papel de tutor |
| Gabarito completo do TP para colar | Orienta conceitos; não entrega solução integral |
| Instalar software fora do curso (ex.: K8s genérico) | Lacuna ou extensão rotulada, sem fingir aula |
| Opinião sobre professores | Não inventa — só o que estiver no material indexado |

---

## Dúvidas sobre a faculdade (prazos, professores, Living Code)

Hoje o bot responde melhor sobre **conteúdo de aula**. Informação administrativa (datas oficiais, regulamento completo, corpo docente) depende de estar **indexada** no corpus.

Se a resposta for vaga ou disser que não encontrou na base:

- Consulte o **portal / AVA** e a **coordenação**
- Em breve: documentos institucionais dedicados no índice

---

## Problemas comuns

| Problema | Tentativa |
|----------|-----------|
| Resposta genérica ou «vaga» | Reformule com disciplina + tema; use `/python` etc. |
| Fontes de outra disciplina | `/reset` e comando certo |
| Chat não abre (`connection refused`) | Servidor local não está em http://127.0.0.1:8001 |
| Perdeu o histórico | Clicou Nova conversa, outro browser, ou limpou dados do site |

Operadores: [TESTE-LOCAL.md](../../TESTE-LOCAL.md).

---

## Ver também

- [Início público](00-inicio-publico.md)
- [Como contribuir](18-contribuir.md) — reportar bugs ou sugerir melhorias
- [08-frontend-ui.md](08-frontend-ui.md) — detalhe técnico da UI
