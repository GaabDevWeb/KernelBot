# Orbit — Contexto Institucional (template operacional)

> **Este ficheiro é documentação para o responsável pelo bot — NÃO é lido pelo
> Kernel.** Os dados reais vivem nos ficheiros ao lado (`identity.md`,
> `faculty.md`, `professors.md`, `disciplines.md`, `rules.md`, `calendar.json`).
> Preencha-os seguindo as secções abaixo. Ficheiros vazios ou contendo apenas
> comentários `<!-- -->` são ignorados pelo Kernel — nada de fictício entra no
> prompt por engano.

## Como funciona

| Ficheiro | Injetado no prompt como | Quando preencher |
|----------|------------------------|------------------|
| `identity.md` | Secção "Identidade do assistente" | Nome público do bot, descrição, finalidade |
| `faculty.md` | Secção "Instituição" | Nome da faculdade, curso, turma, campus, cidade |
| `professors.md` | Secção "Professores" | Um bloco por professor |
| `disciplines.md` | Secção "Disciplinas" | Um bloco por disciplina |
| `rules.md` | Secção "Regras da instituição/turma" | Regras de avaliação, presença, etc. |
| `calendar.json` | Agenda acadêmica (com contagem de dias calculada pelo servidor) | Avaliações, entregas, eventos |

O diretório é configurável via `KERNEL_CONTEXT_DIR`; o calendário via
`KERNEL_CALENDAR_PATH`. Timezone do servidor: `KERNEL_TIMEZONE`
(default `America/Sao_Paulo`).

**Regra de ouro: não invente. Se não souber uma informação, deixe o campo por
preencher — o bot declara ausência de registo em vez de chutar.**

---

## Identidade (→ `identity.md`)

```markdown
Nome do bot: <Kernel>
Descrição: <Assistente acadêmico da turma, integrado ao grupo de WhatsApp da faculdade, responsável por auxiliar os alunos com dúvidas, informações acadêmicas e contexto das conversas. — ex.: assistente acadêmico da turma X>
Finalidade: <Ajudar os alunos da turma a encontrar, compreender e relacionar informações acadêmicas, utilizando o contexto da conversa, materiais oficiais, calendário, avaliações e demais informações fornecidas pela faculdade. O Orbit deve responder quando solicitado/mencionado e priorizar informações confiáveis e oficiais. Não deve inventar informações, datas, conteúdos, professores ou respostas quando não houver dados suficientes. Quando houver conflito entre informações, deve sinalizar a inconsistência e priorizar a fonte oficial.>
```

## Instituição (→ `faculty.md`)

```markdown
Nome: <instituto infnet>
Curso: <Análise e desenvolvimento de sistemas (ADS)>
Turma: <26E3-26E4>
Campus: <Rio de Janeiro - RJ>
Cidade: <Rio de Janeiro - RJ>
```

## Disciplinas (→ `disciplines.md`)

Repita o bloco para cada disciplina:

```markdown
### <Planejamento de curso e carreira>
Professor: <Marina Alejandra Vergili>
Descrição: <Planejamento de carreira, currículo e posicionamento profissional em tecnologia.>
Conteúdos: <Como funciona sua graduação: blocos, estágio e atividades complementares; Planejamento de carreira com SWOT: das estrelas ao caminho concreto; Currículo para tecnologia: função, estrutura, ATS e experiências que contam; LinkedIn para carreira em tecnologia: visibilidade, networking e busca de vagas; Hábitos, mudança e trabalho em equipe: proatividade na carreira em tecnologia; Privilégios, ética, diversidade e gatilhos emocionais na carreira em tecnologia; Trabalho final (AT), apresentações e oratória: medo, preparo e voz; Competências, rubricas e seleção por comportamento: do AT ao caso Heineken; Rodadas de apresentação entre pares: dinâmica da aula prática; Encerramento das apresentações: última rodada e organização em salas>
Observações: <1º trimestre. Foco em carreira em tecnologia: estrutura da graduação (blocos, estágio, atividades complementares), SWOT, currículo ATS, LinkedIn, hábitos/equipes, ética e diversidade, oratória e AT com apresentações entre pares.>
```
```markdown
### <Fluência em IA>
Professor: <Alan alonso>
Descrição: <Fundamentos e prática para usar IA de forma eficaz, crítica e aplicada.>
Conteúdos: <Introdução à Fluência em IA: termos, limites e como pensar; IA, ML, deep learning e IA generativa na prática; Tokens, embeddings, prompt e temperatura em LLMs; Ética, automação e direitos autorais na era da IA generativa; Ética, verificação crítica e ecossistema de IAs generativas; Engenharia de Prompt: Fundamentos, Persona e Estrutura; Técnicas Avançadas de Prompt: Raciocínio, Decomposição e Auditoria; Prompts estruturados para resumos de aula e NotebookLM com RAG; Agentes de IA, ferramentas e RAG: da decisão à busca semântica>
Observações: <2º trimestre. Ênfase em uso crítico de IA generativa: termos e limites, LLMs (tokens, embeddings, temperatura), ética/direitos autorais, engenharia de prompt, NotebookLM/RAG e agentes.>
```
```markdown
### <Introdução a visualização de dados e SQL>
Professor: <Carlos eduardo (Caduzão)>
Descrição: <Consultas SQL e criação de dashboards com Looker Studio.>
Conteúdos: <Visualizar dados de um CSV no Looker Studio; Conta bancária no Looker Studio com Google Planilhas; Entendendo arquivos CSV e dados de produtos; Dashboard da cafeteria Herman: objetivos de negócio, métricas e layout; Implementando o dashboard da cafeteria Herman no Looker Studio; Refinando o relatório de conta bancária no Looker Studio; Dashboard de comparação de anos no Looker Studio; Dashboard de pizza e barras para tipos e categorias de transações no Looker Studio; Introdução a bancos de dados, tipos de dados e SQL; Operadores lógicos, filtros e expressões em SQL com SELECT; Criando tabelas no SQLiteStudio e DML básica; Ordenando resultados em SQL com ORDER BY; Consultas SQL na tabela de clientes: prática com filtros e ordenação; Agregação em SQL: GROUP BY, HAVING e funções SUM e COUNT; Agrupamento por múltiplas dimensões: rankings e duplicidades; Avaliação Final (AT): Visualização de Dados e Consultas Analíticas; Agregações em dados reais (SQLite): DISTINCT, GROUP BY, ORDER BY e HAVING com weather_stations; Monitoria: AT academia, fontes no Looker, datas e visão OLAP; Monitoria: páginas no Looker, dúvidas do AT e índices em SQL; Monitoria: revisão visual do AT e boas práticas de dashboard; Monitoria: correção do AT e transição para o segundo trimestre>
Observações: <1º trimestre. Primeira metade em Looker Studio (CSV, Planilhas, dashboards); segunda em SQL/SQLite (SELECT, filtros, ORDER BY, GROUP BY/HAVING). AT com projeto de academia e monitorias de revisão.>
```
```markdown
### <Introdução a programação com python>
Professor: <Gesiel Lopes>
Descrição: <Fundamentos de programação com Python e manipulação de dados.>
Conteúdos: <Por que programar e por que Python?; Algoritmos, pensamento computacional e seu primeiro notebook Python; Variáveis, tipos de dados e estilo de código em Python; Conversão de tipos e operadores aritméticos em Python; Strings em Python: aspas, literais e textos multilinha; Strings em Python: escapes, concatenação e repetição; Strings em Python: índices, slices e métodos úteis; Strings em Python: interpolação, f-strings e input; Desvios condicionais em Python: if, elif e else; Operadores lógicos, tabela-verdade e match/case em Python; Laços de repetição em Python: for, range e listas; Range avançado, acumuladores, enumerate e loops aninhados em Python; Prática: teste de mesa, tabuada, enumerate e matriz (loops em Python); Funções em Python: definição, parâmetros, docstrings e builtins; Parâmetros avançados e retorno de funções em Python; Algoritmos na prática: ordenação, módulo random e composição de funções>
Observações: <1º trimestre. Base de programação: algoritmos, notebooks, tipos, strings, condicionais, loops, funções e prática com composição de algoritmos. Conteúdo alinhado ao material ISS (pasta python/).>
```
```markdown
### <SQL e modelagem relacional>
Professor: <Carlos Eduardo (Kadu)>
Descrição: <Modelagem relacional e consultas SQL com foco em consistência e prática.>
Conteúdos: <Modelagem de Dados Relacional: fundamentos, evolução e terminologia; MER, DER, cardinalidade e terminologia: do diagrama ao processo de design; Modelagem conceitual: listas preliminares, DER com PK/FK e BRModelo; TP1 Livraria: normalização, chaves e tipos de dados; Modelo lógico: primeira, segunda e terceira formas normais; TP2: planilha desnormalizada, normalização e modelo entidade-relacionamento; Caso cinemas: do MER ao SQLite e consultas com JOIN; Inspecionar e modificar dados no SQLite: dados sujos, perfilamento e preparação para correção; Qualidade de dados em SQL no SQLiteStudio: diagnóstico, UPDATE seguro e normalização pontual; Manipulação de Dados e Evolução de Estruturas em SQL; Exclusão de Dados, Backup e Alteração de Estrutura; Modelagem relacional: sistema de hotel (reservas, ocupação e serviços); JOINs e ligação entre tabelas; Assessment (AT): ambiente, Parte A e modelagem da Parte B; Agregações SQL: GROUP BY, HAVING e análise temporal com JOIN; Implementação SQL do modelo Hotel: DDL, DML e JOINs na prática>
Observações: <2º trimestre. MER/DER, normalização (1FN–3FN), SQLite, qualidade de dados, DDL/DML, JOINs e casos (livraria, cinemas, hotel). Inclui TPs e Assessment (AT).>
```
```markdown
### <Python para processamento de dados>
Professor: <Gesiel Lopes e Marcelo Tomio Hama>
Descrição: <Processamento de dados com Python: parsing, limpeza e transformações.>
Conteúdos: <Primeiros passos em Python para processamento de dados: strings e plano da disciplina; Indexação, fatiamento e tokenização inicial de textos; Funções de pré-processamento, list comprehension e contagem de ocorrências; Busca, alinhamento e validação de strings em pré-processamento; Limpeza robusta de tokens, formatação de strings e introdução a coleções; Listas mutáveis: inserção, remoção, ordenação e busca sequencial; Matrizes com listas aninhadas e tuplas imutáveis; Dicionários em Python: chave-valor, mutabilidade e contagem de tokens; Conjuntos (set) em Python para dados; Conjuntos para comparar listas, importações e gestão de pacotes com pip; Manipulação de arquivos em disco com Python (texto, binário e fluxos); JSON em Python: serialização, leitura/escrita em arquivo e uso em dados; Tratamento de exceções e pipelines resilientes de processamento de dados; Try, Except, Else e Finally em Python; Pass, supressão de exceções e debugging com pdb; Cliente HTTP com Requests: GET, POST e interpretação de respostas; Requisições HTTP com Python: GET, POST e tratamento de respostas; Integração com LLMs e servidor Flask multi-IA; Monitoria do AT: Flask, funções e introdução à orientação a objetos; Resolução do AT Parte B: Flask no Deepnote, deduplicação e escopo de funções>
Observações: <2º trimestre. Aprofunda Python para dados: strings/tokenização, coleções, arquivos, JSON, exceções, HTTP/Requests, Flask e integração com LLMs. Há monitorias e resolução de AT.>
```
```markdown
### <Projeto de Bloco: Fundamentos do processamento de dadoss>
Professor: <Gesiel Lopes e Marcelo Tomio Hama>
Descrição: <Projeto prático integrando Python, SQL e visualização de dados.>
Conteúdos: <Introdução ao Projeto de Bloco — Formação em Dados; Metodologias de Projeto para Dados — Tradicional vs Ágil; Pipeline de Dados, Ferramentas e Escolha de Bancos — do ETL ao Dashboard; Montando seu Laboratório de Dados com Python e SQL; Variáveis em Python dentro de Projetos de Dados; Consultas SQL na Prática e Integração Python–Excel–SQL Server; Perfis Profissionais em Dados e Desenvolvimento — e um Case Real de Classificação de Consumidores; Python, Jupyter e CRUD em PostgreSQL, MySQL e SQL Server; Etapas do ciclo de projeto, estruturas Python e mercado de trabalho; Ingestão de dados: CSV, Excel, pandas e SQLite em Python; Requisitos, persistência, POC e SQLite no projeto (revisão e e-commerce); Modelagem conceitual, lógica e física do e-commerce em SQLite; Views SQL e camada de visualização: estoque, pedidos e carga de dados; Modelagem relacional transacional versus analítica, views de negócio e fluxos em listas com Python; JOINs, VIEWs, Ambientes e Estrutura Modular em Python; Integração Python e SQL no E-commerce: CRUD, Views e Regras de Negócio; Debug em Python e normalização de dados no e-commerce>
Observações: <Disciplina integradora (1º e 2º trimestres). Une Python, SQL e visualização num pipeline prático (laboratório, ingestão CSV/Excel/pandas/SQLite, modelagem e-commerce, views, CRUD e Live Codings/apresentação final).>
```


## Professores (→ `professors.md`)

Repita o bloco para cada professor:

```markdown
### <Marina Alejandra Vergili>a
Disciplina: <Planejamento de curso e carreira>
Informações relevantes: <preencher — ex.: forma de contacto preferida>
```
```markdown
### <Alan alonso>
Disciplina: <Fluência em IA>
Informações relevantes: <preencher — ex.: forma de contacto preferida>
```
```markdown
### <Carlos eduardo (Caduzão)>
Disciplina: <Introdução a visualização de dados e SQL>
Informações relevantes: <Quando for se referir a ele, chamar de kadu ou kaduzão  e em vez de falar arquivo, falar arquivinho, ni diminutivo mesmo>
```
```markdown
### <Gesiel Lopes>
Disciplina: <Introdução a programação com python; Python para processamento de dados; Projeto de Bloco: Fundamentos do processamento de dadoss>
Informações relevantes: <Ele saiu porque ninguém gostava das aulas dele, no geral ele não tirava as dúvidas, não passava exercicios para praticar, além de ser rude as vezes com os alunos>
```
```markdown
### <Carlos Eduardo (Kadu)>
Disciplina: <SQL e modelagem relacional>
Informações relevantes: <Quando for se referir a ele, chamar de kadu ou kaduzão  e em vez de falar arquivo, falar arquivinho, ni diminutivo mesmo>
```
```markdown
### <Marcelo Tomio Hama>
Disciplina: <Python para processamento de dados; Projeto de Bloco: Fundamentos do processamento de dadoss>
Informações relevantes: <Ele veio depois do gesiel>
```
```markdown
### <Rafael Cruz>
Disciplina: <Fundamentos de Desenvolvimento com C#>
Informações relevantes: <Professor inicial (3º trimestre); transição documentada na aula de revisão>
```
```markdown
### <Luiz Paulo Maia (LP)>
Disciplina: <Fundamentos de Desenvolvimento com C#>
Informações relevantes: <Assumiu após Rafael Cruz (aula de transição)>
```
```markdown
### <Elberth Moraes>
Disciplina: <Fundamentos de Desenvolvimento com Java>
Informações relevantes: <3º trimestre>
```
```markdown
### <Orlando Fonseca Guilarte>
Disciplina: <Projeto de Bloco — Desenvolvimento Back-End>
Informações relevantes: <3º trimestre; GitHub referido no material: github.com/ofonsek0702>
```

## 3º trimestre — novas disciplinas (→ `disciplines.md` / `calendar.json`)

Fonte académica: `ISS/jsons` + `ISS/content/disciplines.json`. Não inventar datas.

```markdown
### <Fundamentos de Desenvolvimento com C#>
Professor: <Rafael Cruz / Luiz Paulo Maia>
Descrição: <Fundamentos de C# e .NET para backend>
Conteúdos: <6 aulas — intro .NET; primeiro projeto; strings/variáveis; prática console; revisão/transição; DateTime>
Observações: <3º trimestre. Rafael Cruz → Luiz Paulo Maia (LP). Moodle: TP1 10/08; TP2 24/08; TP3 07/09; Assessment 22/09/2026 (23:59).>
```
```markdown
### <Fundamentos de Desenvolvimento com Java>
Professor: <Elberth Moraes>
Descrição: <Fundamentos de Java para backend>
Conteúdos: <6 aulas — intro/carreira; raciocínio/JDK; variáveis/Scanner; classes/projetos; if; condicionais/ternário>
Observações: <3º trimestre. Elberth Moraes. Moodle: TP1 10/08; TP2 24/08; TP3 07/09; Assessment 22/09/2026 (23:59).>
```
```markdown
### <Projeto de Bloco — Desenvolvimento Back-End>
Professor: <Orlando Fonseca Guilarte>
Descrição: <Projeto integrador backend — ciclo de vida, requisitos, modelos>
Conteúdos: <3 aulas — combinado/entregas; ciclo de vida/requisitos; cascata/RUP/ágil>
Observações: <3º trimestre. Orlando Fonseca Guilarte. Moodle: TP1 24/08; TP2 21/09; TP3 19/10; TP4 16/11; TP5 23/11; Entrega de Projeto 04/12/2026 (23:59).>
```

Eventos calendário Java (ano 2026 alinhado ao restante `calendar.json`):
- `event-028` TP1 Java `2026-08-10`
- `event-029` TP2 Java `2026-08-24`

## Regras (→ `rules.md`)

a

## Calendário e avaliações (→ `calendar.json`)

Todos os eventos (avaliações Moodle + calendário acadêmico institucional Graduação 2026)
vão no `calendar.json`. Em conflito de datas de entrega, prevalece o Moodle.

```json
{
  "events": [
    {
      "title": "FÉRIAS",
      "type": "holiday",
      "discipline": null,
      "date": "2025-12-29",
      "time": null,
      "description": "Período 2025-12-29 a 2026-01-03. INSTITUIÇÃO FECHADA.\nNÃO É POSSÍVEL FAZER REQUERIMENTOS. Fonte: Calendário Acadêmico Discente Graduação 2026.",
      "source": "official",
      "id": "event-001"
    },
    {
      "title": "RECESSO/RECESSO",
      "type": "holiday",
      "discipline": null,
      "date": "2026-01-05",
      "time": null,
      "description": "Período 2026-01-05 a 2026-01-10. INSTITUIÇÃO FECHADA ATÉ 6/01.\nNÃO É POSSÍVEL FAZER REQUERIMENTOS. Fonte: Calendário Acadêmico Discente Graduação 2026.",
      "source": "official",
      "id": "event-002"
    },
    {
      "title": "RECESSO",
      "type": "holiday",
      "discipline": null,
      "date": "2026-01-12",
      "time": null,
      "description": "Período 2026-01-12 a 2026-01-17. INSTITUIÇÃO ABERTA, MAS SEM AULAS DE GRADUAÇÃO Fonte: Calendário Acadêmico Discente Graduação 2026.",
      "source": "official",
      "id": "event-003"
    },
    {
      "title": "RECESSO",
      "type": "holiday",
      "discipline": null,
      "date": "2026-01-19",
      "time": null,
      "description": "Período 2026-01-19 a 2026-01-24. INSTITUIÇÃO ABERTA, SEM AULAS DE GRADUAÇÃO.\n20: FERIADO DE SÃO SEBASTIÃO Fonte: Calendário Acadêmico Discente Graduação 2026.",
      "source": "official",
      "id": "event-004"
    },
    {
      "title": "FERIADO DE SÃO SEBASTIÃO",
      "type": "holiday",
      "discipline": null,
      "date": "2026-01-20",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: RECESSO. Obs: INSTITUIÇÃO ABERTA, SEM AULAS DE GRADUAÇÃO. 20: FERIADO DE SÃO SEBASTIÃO",
      "source": "official",
      "id": "event-005"
    },
    {
      "title": "2026 Trimestre 1 — Semana 1",
      "type": "event",
      "discipline": null,
      "date": "2026-01-26",
      "time": null,
      "description": "PERÍODO PARA REQUISITAR A REAVALIAÇÃO DE DISCIPLINAS EM 2026.1S. Atividades típicas: ESTUDO DA ETAPA 1 / ESTUDO DA ETAPA 1 / ESTUDO DA ETAPA 6 | LEITURA EM AULA DO TP3 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-006"
    },
    {
      "title": "2026 Trimestre 1 — Semana 2",
      "type": "event",
      "discipline": null,
      "date": "2026-02-02",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 2 | LEITURA EM AULA DO TP1 / ESTUDO DA ETAPA 1 / ESTUDO DA ETAPA 7 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-007"
    },
    {
      "title": "2026 Trimestre 1 — Semana 3",
      "type": "event",
      "discipline": null,
      "date": "2026-02-09",
      "time": null,
      "description": "14: SÁBADO DE CARNAVAL Atividades típicas: ESTUDO DA ETAPA 3 / ESTUDO DA ETAPA 2 / ESTUDO DA ETAPA 7 | ENTREGA DO TP3 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-008"
    },
    {
      "title": "SÁBADO DE CARNAVAL",
      "type": "holiday",
      "discipline": null,
      "date": "2026-02-14",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 1 | Semana 3. Obs: 14: SÁBADO DE CARNAVAL",
      "source": "official",
      "id": "event-009"
    },
    {
      "title": "2026 Trimestre 1 — Semana 4",
      "type": "event",
      "discipline": null,
      "date": "2026-02-16",
      "time": null,
      "description": "16, 17, 18: CARNAVAL Atividades típicas: ESTUDO DA ETAPA 4, ENTREGA DO TP1. | LEITURA EM AULA DO TP2 / ESTUDO DA ETAPA 2 | LEITURA EM AULA DO TP1 / ESTUDO DA ETAPA 8 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-010"
    },
    {
      "title": "CARNAVAL",
      "type": "holiday",
      "discipline": null,
      "date": "2026-02-16",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 1 | Semana 4. Obs: 16, 17, 18: CARNAVAL",
      "source": "official",
      "id": "event-011"
    },
    {
      "id": "event-012",
      "title": "Teste de Performance - TP1 [Obrigatório]",
      "type": "assignment",
      "discipline": "Introdução a programação com python",
      "date": "2026-02-16",
      "time": "23:59",
      "description": "Data de entrega segunda, 16 fev 2026, 23:59",
      "source": "official"
    },
    {
      "id": "event-013",
      "title": "Teste de Performance - TP1 [Obrigatório]",
      "type": "assignment",
      "discipline": "Introdução a visualização de dados e SQL",
      "date": "2026-02-16",
      "time": "23:59",
      "description": "Data de entrega segunda, 16 fev 2026, 23:59",
      "source": "official"
    },
    {
      "id": "event-014",
      "title": "Teste de Performance - TP1 [Obrigatório]",
      "type": "assignment",
      "discipline": "Planejamento de curso e carreira",
      "date": "2026-02-16",
      "time": "23:59",
      "description": "Data de entrega segunda, 16 fev 2026, 23:59",
      "source": "official"
    },
    {
      "title": "CARNAVAL",
      "type": "holiday",
      "discipline": null,
      "date": "2026-02-17",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 1 | Semana 4. Obs: 16, 17, 18: CARNAVAL",
      "source": "official",
      "id": "event-015"
    },
    {
      "title": "CARNAVAL",
      "type": "holiday",
      "discipline": null,
      "date": "2026-02-18",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 1 | Semana 4. Obs: 16, 17, 18: CARNAVAL",
      "source": "official",
      "id": "event-016"
    },
    {
      "title": "2026 Trimestre 1 — Semana 5",
      "type": "event",
      "discipline": null,
      "date": "2026-02-23",
      "time": null,
      "description": "23: INÍCIO DAS AULAS PARA NOVOS ALUNOS PRESENCIAIS DA FACULDADE INFNET Atividades típicas: ESTUDO DA ETAPA 5 / ESTUDO DA ETAPA 3 / ESTUDO DA ETAPA 8 | LEITURA EM AULA DO TP4 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-017"
    },
    {
      "title": "INÍCIO DAS AULAS PARA NOVOS ALUNOS PRESENCIAIS DA FACULDADE INFNET",
      "type": "event",
      "discipline": null,
      "date": "2026-02-23",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 1 | Semana 5. Obs: 23: INÍCIO DAS AULAS PARA NOVOS ALUNOS PRESENCIAIS DA FACULDADE INFNET",
      "source": "official",
      "id": "event-018"
    },
    {
      "title": "2026 Trimestre 1 — Semana 6",
      "type": "event",
      "discipline": null,
      "date": "2026-03-02",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 6, ENTREGA DO TP2. | LEITURA EM AULA DO TP3 / ESTUDO DA ETAPA 3 | ENTREGA DO TP1 / ESTUDO DA ETAPA 9 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-019"
    },
    {
      "id": "event-020",
      "title": "Teste de Performance - TP2 [OBRIGATÓRIO]",
      "type": "assignment",
      "discipline": "Introdução a programação com python",
      "date": "2026-03-02",
      "time": "23:59",
      "description": "Data de entrega segunda, 2 mar 2026, 23:59",
      "source": "official"
    },
    {
      "id": "event-021",
      "title": "Teste de Performance - TP2 [OBRIGATÓRIO]",
      "type": "assignment",
      "discipline": "Introdução a visualização de dados e SQL",
      "date": "2026-03-02",
      "time": "23:59",
      "description": "Data de entrega segunda, 2 mar 2026, 23:59",
      "source": "official"
    },
    {
      "id": "event-022",
      "title": "Teste de Performance - TP2 [Obrigatório]",
      "type": "assignment",
      "discipline": "Planejamento de curso e carreira",
      "date": "2026-03-02",
      "time": "23:59",
      "description": "Data de entrega segunda, 2 mar 2026, 23:59",
      "source": "official"
    },
    {
      "id": "event-023",
      "title": "Live Coding 1 [Obrigatório]",
      "type": "assignment",
      "discipline": "Projeto de Bloco: Fundamentos do processamento de dados",
      "date": "2026-03-06",
      "time": "23:59",
      "description": "Data de entrega sexta, 6 mar 2026, 23:59",
      "source": "official"
    },
    {
      "title": "2026 Trimestre 1 — Semana 7",
      "type": "event",
      "discipline": null,
      "date": "2026-03-09",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 7 / ESTUDO DA ETAPA 4 / ESTUDO DA ETAPA 9 | ENTREGA DO TP4 | LEITURA EM AULA DO TP5 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-024"
    },
    {
      "title": "2026 Trimestre 1 — Semana 8",
      "type": "event",
      "discipline": null,
      "date": "2026-03-16",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 8, ENTREGA DO TP3 / ESTUDO DA ETAPA 4 | LEITURA EM AULA DO TP2 / ESTUDO DA ETAPA 10 | ENTREGA DO TP5 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-025"
    },
    {
      "id": "event-026",
      "title": "Teste de Performance - TP3 [Obrigatório]",
      "type": "assignment",
      "discipline": "Introdução a programação com python",
      "date": "2026-03-16",
      "time": "23:59",
      "description": "Data de entrega segunda, 16 mar 2026, 23:59",
      "source": "official"
    },
    {
      "id": "event-027",
      "title": "Teste de Performance - TP3 [Obrigatório]",
      "type": "assignment",
      "discipline": "Introdução a visualização de dados e SQL",
      "date": "2026-03-16",
      "time": "23:59",
      "description": "Data de entrega segunda, 16 mar 2026, 23:59",
      "source": "official"
    },
    {
      "id": "event-028",
      "title": "Teste de Performance - TP3 [Obrigatório]",
      "type": "assignment",
      "discipline": "Planejamento de curso e carreira",
      "date": "2026-03-16",
      "time": "23:59",
      "description": "Data de entrega segunda, 16 mar 2026, 23:59",
      "source": "official"
    },
    {
      "title": "2026 Trimestre 1 — Semana 9",
      "type": "assessment",
      "discipline": null,
      "date": "2026-03-23",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 9 | LEITURA EM AULA DO ASSESSMENT / ESTUDO DA ETAPA 5 / ESTUDO DA ETAPA 10 | ENTREGA DO PROJETO DE BLOCO Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-029"
    },
    {
      "title": "2026 Trimestre 1 — Semana 10",
      "type": "assessment",
      "discipline": null,
      "date": "2026-03-30",
      "time": null,
      "description": "3, 4, 5: PÁSCOA 30: INÍCIO DAS AULAS PARA NOVOS ALUNOS PRESENCIAIS DA ECDD Atividades típicas: ENTREGA/ARGUIÇÃO DO ASSESSMENT / ESTUDO DA ETAPA 5 | ENTREGA DO TP2 / APRESENTAÇÕES DE PROJETOS DE BLOCO Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-030"
    },
    {
      "title": "INÍCIO DAS AULAS PARA NOVOS ALUNOS PRESENCIAIS DA ECDD",
      "type": "event",
      "discipline": null,
      "date": "2026-03-30",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 1 | Semana 10. Obs: 3, 4, 5: PÁSCOA 30: INÍCIO DAS AULAS PARA NOVOS ALUNOS PRESENCIAIS DA ECDD",
      "source": "official",
      "id": "event-031"
    },
    {
      "id": "event-032",
      "title": "Live Coding 2 [Obrigatório]",
      "type": "assignment",
      "discipline": "Projeto de Bloco: Fundamentos do processamento de dados",
      "date": "2026-03-30",
      "time": "23:59",
      "description": "Data de entrega segunda, 30 mar 2026, 23:59",
      "source": "official"
    },
    {
      "id": "event-033",
      "title": "Assessment [Obrigatório]",
      "type": "assessment",
      "discipline": "Planejamento de curso e carreira",
      "date": "2026-03-31",
      "time": "23:59",
      "description": "Data de entrega terça, 31 mar 2026, 23:59",
      "source": "official"
    },
    {
      "title": "PÁSCOA",
      "type": "holiday",
      "discipline": null,
      "date": "2026-04-03",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 1 | Semana 10. Obs: 3, 4, 5: PÁSCOA 30: INÍCIO DAS AULAS PARA NOVOS ALUNOS PRESENCIAIS DA ECDD",
      "source": "official",
      "id": "event-034"
    },
    {
      "title": "PÁSCOA",
      "type": "holiday",
      "discipline": null,
      "date": "2026-04-04",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 1 | Semana 10. Obs: 3, 4, 5: PÁSCOA 30: INÍCIO DAS AULAS PARA NOVOS ALUNOS PRESENCIAIS DA ECDD",
      "source": "official",
      "id": "event-035"
    },
    {
      "title": "PÁSCOA",
      "type": "holiday",
      "discipline": null,
      "date": "2026-04-05",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 1 | Semana 10. Obs: 3, 4, 5: PÁSCOA 30: INÍCIO DAS AULAS PARA NOVOS ALUNOS PRESENCIAIS DA ECDD",
      "source": "official",
      "id": "event-036"
    },
    {
      "title": "2026 Trimestre 1 — Semana 11",
      "type": "event",
      "discipline": null,
      "date": "2026-04-06",
      "time": null,
      "description": "Atividades típicas: VISTA DO AT, REENTREGA DO AT / ESTUDO DA ETAPA 6 / APRESENTAÇÕES DE PROJETOS DE BLOCO Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-037"
    },
    {
      "id": "event-038",
      "title": "Assessment [Obrigatório]",
      "type": "assessment",
      "discipline": "Introdução a programação com python",
      "date": "2026-04-06",
      "time": "23:59",
      "description": "Data de entrega segunda, 6 abr 2026, 23:59",
      "source": "official"
    },
    {
      "id": "event-039",
      "title": "Assessment [Obrigatório]",
      "type": "assessment",
      "discipline": "Introdução a visualização de dados e SQL",
      "date": "2026-04-06",
      "time": "23:59",
      "description": "Data de entrega segunda, 6 abr 2026, 23:59",
      "source": "official"
    },
    {
      "title": "2026 Trimestre 2 — Semana 1",
      "type": "event",
      "discipline": null,
      "date": "2026-04-13",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 1 / ESTUDO DA ETAPA 6 | LEITURA EM AULA DO TP3 / ESTUDO DA ETAPA 1 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-040"
    },
    {
      "title": "2026 Trimestre 2 — Semana 2",
      "type": "event",
      "discipline": null,
      "date": "2026-04-20",
      "time": null,
      "description": "21: TIRADENTES | 23: SÃO JORGE 20, 22 e 24: AULAS DA MODALIDADE PRESENCIAL PELO ZOOM Atividades típicas: ESTUDO DA ETAPA 2 | LEITURA EM AULA DO TP1 / ESTUDO DA ETAPA 7 / ESTUDO DA ETAPA 1 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-041"
    },
    {
      "title": "AULAS DA MODALIDADE PRESENCIAL PELO ZOOM",
      "type": "event",
      "discipline": null,
      "date": "2026-04-20",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 2 | Semana 2. Obs: 21: TIRADENTES | 23: SÃO JORGE 20, 22 e 24: AULAS DA MODALIDADE PRESENCIAL PELO ZOOM",
      "source": "official",
      "id": "event-042"
    },
    {
      "title": "TIRADENTES",
      "type": "holiday",
      "discipline": null,
      "date": "2026-04-21",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 2 | Semana 2. Obs: 21: TIRADENTES | 23: SÃO JORGE 20, 22 e 24: AULAS DA MODALIDADE PRESENCIAL PELO ZOOM",
      "source": "official",
      "id": "event-043"
    },
    {
      "title": "AULAS DA MODALIDADE PRESENCIAL PELO ZOOM",
      "type": "event",
      "discipline": null,
      "date": "2026-04-22",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 2 | Semana 2. Obs: 21: TIRADENTES | 23: SÃO JORGE 20, 22 e 24: AULAS DA MODALIDADE PRESENCIAL PELO ZOOM",
      "source": "official",
      "id": "event-044"
    },
    {
      "title": "SÃO JORGE",
      "type": "holiday",
      "discipline": null,
      "date": "2026-04-23",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 2 | Semana 2. Obs: 21: TIRADENTES | 23: SÃO JORGE 20, 22 e 24: AULAS DA MODALIDADE PRESENCIAL PELO ZOOM",
      "source": "official",
      "id": "event-045"
    },
    {
      "title": "AULAS DA MODALIDADE PRESENCIAL PELO ZOOM",
      "type": "event",
      "discipline": null,
      "date": "2026-04-24",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 2 | Semana 2. Obs: 21: TIRADENTES | 23: SÃO JORGE 20, 22 e 24: AULAS DA MODALIDADE PRESENCIAL PELO ZOOM",
      "source": "official",
      "id": "event-046"
    },
    {
      "title": "2026 Trimestre 2 — Semana 3",
      "type": "event",
      "discipline": null,
      "date": "2026-04-27",
      "time": null,
      "description": "1: TRABALHO Atividades típicas: ESTUDO DA ETAPA 3 / ESTUDO DA ETAPA 7 | ENTREGA DO TP3 / ESTUDO DA ETAPA 2 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-047"
    },
    {
      "id": "event-048",
      "title": "Live Coding 3 [Obrigatório]",
      "type": "assignment",
      "discipline": "Projeto de Bloco: Fundamentos do processamento de dados",
      "date": "2026-04-27",
      "time": "23:59",
      "description": "Data de entrega segunda, 27 abr 2026, 23:59",
      "source": "official"
    },
    {
      "title": "TRABALHO",
      "type": "holiday",
      "discipline": null,
      "date": "2026-05-01",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 2 | Semana 3. Obs: 1: TRABALHO",
      "source": "official",
      "id": "event-049"
    },
    {
      "title": "2026 Trimestre 2 — Semana 4",
      "type": "event",
      "discipline": null,
      "date": "2026-05-04",
      "time": null,
      "description": "8: EVENTO \"APRESENTAÇÃO DE PORTFÓLIO DE PROJETOS\" Atividades típicas: ESTUDO DA ETAPA 4, ENTREGA DO TP1. | LEITURA EM AULA DO TP2 / ESTUDO DA ETAPA 8 / ESTUDO DA ETAPA 2 | LEITURA EM AULA DO TP1 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-050"
    },
    {
      "id": "event-051",
      "title": "Teste de Performance - TP1 [Obrigatório]",
      "type": "assignment",
      "discipline": "Python para processamento de dados",
      "date": "2026-05-04",
      "time": "23:59",
      "description": "Data de entrega segunda, 4 mai 2026, 23:59",
      "source": "official"
    },
    {
      "id": "event-052",
      "title": "Teste de Performance - TP1 [Obrigatório]",
      "type": "assignment",
      "discipline": "SQL e modelagem relacional",
      "date": "2026-05-04",
      "time": "23:59",
      "description": "Data de entrega segunda, 4 mai 2026, 23:59",
      "source": "official"
    },
    {
      "title": "EVENTO \"APRESENTAÇÃO DE PORTFÓLIO DE PROJETOS\"",
      "type": "event",
      "discipline": null,
      "date": "2026-05-08",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 2 | Semana 4. Obs: 8: EVENTO \"APRESENTAÇÃO DE PORTFÓLIO DE PROJETOS\"",
      "source": "official",
      "id": "event-053"
    },
    {
      "title": "2026 Trimestre 2 — Semana 5",
      "type": "event",
      "discipline": null,
      "date": "2026-05-11",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 5 / ESTUDO DA ETAPA 8 | LEITURA EM AULA DO TP4 / ESTUDO DA ETAPA 3 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-054"
    },
    {
      "title": "2026 Trimestre 2 — Semana 6",
      "type": "event",
      "discipline": null,
      "date": "2026-05-18",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 6, ENTREGA DO TP2. | LEITURA EM AULA DO TP3 / ESTUDO DA ETAPA 9 / ESTUDO DA ETAPA 3 | ENTREGA DO TP1 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-055"
    },
    {
      "id": "event-056",
      "title": "Teste de Performance - TP2 [OBRIGATÓRIO]",
      "type": "assignment",
      "discipline": "Python para processamento de dados",
      "date": "2026-05-18",
      "time": "23:59",
      "description": "Data de entrega segunda, 18 mai 2026, 23:59",
      "source": "official"
    },
    {
      "id": "event-057",
      "title": "Teste de Performance - TP2 [OBRIGATÓRIO]",
      "type": "assignment",
      "discipline": "SQL e modelagem relacional",
      "date": "2026-05-18",
      "time": "23:59",
      "description": "Data de entrega segunda, 18 mai 2026, 23:59",
      "source": "official"
    },
    {
      "title": "2026 Trimestre 2 — Semana 7",
      "type": "event",
      "discipline": null,
      "date": "2026-05-25",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 7 / ESTUDO DA ETAPA 9 | ENTREGA DO TP4 | LEITURA EM AULA DO TP5 / ESTUDO DA ETAPA 4 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-058"
    },
    {
      "id": "event-059",
      "title": "Live Coding 4 [Obrigatório]",
      "type": "assignment",
      "discipline": "Projeto de Bloco: Fundamentos do processamento de dados",
      "date": "2026-05-29",
      "time": "23:59",
      "description": "Data de entrega sexta, 29 mai 2026, 23:59",
      "source": "official"
    },
    {
      "title": "2026 Trimestre 2 — Semana 8",
      "type": "event",
      "discipline": null,
      "date": "2026-06-01",
      "time": null,
      "description": "4: CORPUS CHRISTI 5: AULAS DA MODALIDADE PRESENCIAL PELO ZOOM Atividades típicas: ESTUDO DA ETAPA 8, ENTREGA DO TP3 / ESTUDO DA ETAPA 10 | ENTREGA DO TP5 / ESTUDO DA ETAPA 4 | LEITURA EM AULA DO TP2 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-060"
    },
    {
      "id": "event-061",
      "title": "Teste de Performance - TP3 [Obrigatório]",
      "type": "assignment",
      "discipline": "Python para processamento de dados",
      "date": "2026-06-01",
      "time": "23:59",
      "description": "Data de entrega segunda, 1 jun 2026, 23:59",
      "source": "official"
    },
    {
      "id": "event-062",
      "title": "Teste de Performance - TP3 [Obrigatório]",
      "type": "assignment",
      "discipline": "SQL e modelagem relacional",
      "date": "2026-06-01",
      "time": "23:59",
      "description": "Data de entrega segunda, 1 jun 2026, 23:59",
      "source": "official"
    },
    {
      "title": "CORPUS CHRISTI",
      "type": "holiday",
      "discipline": null,
      "date": "2026-06-04",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 2 | Semana 8. Obs: 4: CORPUS CHRISTI 5: AULAS DA MODALIDADE PRESENCIAL PELO ZOOM",
      "source": "official",
      "id": "event-063"
    },
    {
      "title": "AULAS DA MODALIDADE PRESENCIAL PELO ZOOM",
      "type": "event",
      "discipline": null,
      "date": "2026-06-05",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 2 | Semana 8. Obs: 4: CORPUS CHRISTI 5: AULAS DA MODALIDADE PRESENCIAL PELO ZOOM",
      "source": "official",
      "id": "event-064"
    },
    {
      "title": "2026 Trimestre 2 — Semana 9",
      "type": "assessment",
      "discipline": null,
      "date": "2026-06-08",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 9 | LEITURA EM AULA DO ASSESSMENT / ESTUDO DA ETAPA 10 | ENTREGA DO PROJETO DE BLOCO / ESTUDO DA ETAPA 5 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-065"
    },
    {
      "id": "event-066",
      "title": "Live Coding 5 [Obrigatório]",
      "type": "assignment",
      "discipline": "Projeto de Bloco: Fundamentos do processamento de dados",
      "date": "2026-06-09",
      "time": "23:59",
      "description": "Data de entrega terça, 9 jun 2026, 23:59",
      "source": "official"
    },
    {
      "title": "2026 Trimestre 2 — Semana 10",
      "type": "assessment",
      "discipline": null,
      "date": "2026-06-15",
      "time": null,
      "description": "Atividades típicas: ENTREGA/ARGUIÇÃO DO ASSESSMENT / APRESENTAÇÕES DE PROJETOS DE BLOCO / ESTUDO DA ETAPA 5 | ENTREGA DO TP2 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-067"
    },
    {
      "id": "event-068",
      "title": "Assessment [Obrigatório]",
      "type": "assessment",
      "discipline": "Python para processamento de dados",
      "date": "2026-06-16",
      "time": "23:59",
      "description": "Data de entrega terça, 16 jun 2026, 23:59",
      "source": "official"
    },
    {
      "id": "event-069",
      "title": "Apresentação Final dos Conceitos [Obrigatório]",
      "type": "seminar",
      "discipline": "Projeto de Bloco: Fundamentos do processamento de dados",
      "date": "2026-06-17",
      "time": "23:59",
      "description": "Data de entrega quarta, 17 jun 2026, 23:59",
      "source": "official"
    },
    {
      "title": "2026 Trimestre 2 — Semana 11",
      "type": "event",
      "discipline": null,
      "date": "2026-06-22",
      "time": null,
      "description": "SISTEMA DE REQUERIMENTOS FECHADO PARA AS FÉRIAS Atividades típicas: VISTA DO AT, REENTREGA DO AT / APRESENTAÇÕES DE PROJETOS DE BLOCO / ESTUDO DA ETAPA 6 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-070"
    },
    {
      "id": "event-071",
      "title": "Assessment [Obrigatório]",
      "type": "assessment",
      "discipline": "SQL e modelagem relacional",
      "date": "2026-06-23",
      "time": "23:59",
      "description": "Data de entrega terça, 23 jun 2026, 23:59",
      "source": "official"
    },
    {
      "title": "FÉRIAS",
      "type": "holiday",
      "discipline": null,
      "date": "2026-06-29",
      "time": null,
      "description": "Período 2026-06-29 a 2026-07-04. INSTITUIÇÃO FECHADA, SEM ATENDIMENTO.\nNÃO É POSSÍVEL FAZER REQUERIMENTOS. Fonte: Calendário Acadêmico Discente Graduação 2026.",
      "source": "official",
      "id": "event-072"
    },
    {
      "title": "FÉRIAS",
      "type": "holiday",
      "discipline": null,
      "date": "2026-07-06",
      "time": null,
      "description": "Período 2026-07-06 a 2026-07-11. INSTITUIÇÃO FECHADA, SEM ATENDIMENTO.\nNÃO É POSSÍVEL FAZER REQUERIMENTOS. Fonte: Calendário Acadêmico Discente Graduação 2026.",
      "source": "official",
      "id": "event-073"
    },
    {
      "title": "RECESSO",
      "type": "holiday",
      "discipline": null,
      "date": "2026-07-13",
      "time": null,
      "description": "Período 2026-07-13 a 2026-07-18. INSTITUIÇÃO ABERTA, MAS SEM AULAS. Fonte: Calendário Acadêmico Discente Graduação 2026.",
      "source": "official",
      "id": "event-074"
    },
    {
      "title": "2026 Trimestre 3 — Semana 1",
      "type": "event",
      "discipline": null,
      "date": "2026-07-20",
      "time": null,
      "description": "PERÍODO PARA REQUISITAR A REAVALIAÇÃO DE DISCIPLINAS EM 2026.2S. Atividades típicas: ESTUDO DA ETAPA 1 / ESTUDO DA ETAPA 1 / ESTUDO DA ETAPA 6 | LEITURA EM AULA DO TP3 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-075"
    },
    {
      "id": "event-076",
      "title": "Assessment [Obrigatório]",
      "type": "assessment",
      "discipline": "Fluência em IA",
      "date": "2026-07-21",
      "time": "23:59",
      "description": "Data de entrega terça, 21 jul 2026, 23:59",
      "source": "official"
    },
    {
      "title": "2026 Trimestre 3 — Semana 2",
      "type": "event",
      "discipline": null,
      "date": "2026-07-27",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 2 | LEITURA EM AULA DO TP1 / ESTUDO DA ETAPA 1 / ESTUDO DA ETAPA 7 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-077"
    },
    {
      "title": "2026 Trimestre 3 — Semana 3",
      "type": "event",
      "discipline": null,
      "date": "2026-08-03",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 3 / ESTUDO DA ETAPA 2 / ESTUDO DA ETAPA 7 | ENTREGA DO TP3 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-078"
    },
    {
      "title": "2026 Trimestre 3 — Semana 4",
      "type": "event",
      "discipline": null,
      "date": "2026-08-10",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 4, ENTREGA DO TP1. | LEITURA EM AULA DO TP2 / ESTUDO DA ETAPA 2 | LEITURA EM AULA DO TP1 / ESTUDO DA ETAPA 8 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-079"
    },
    {
      "id": "event-080",
      "title": "Teste de Performance - TP1 [Obrigatório]",
      "type": "assignment",
      "discipline": "Fundamentos de Desenvolvimento com C#",
      "date": "2026-08-10",
      "time": "23:59",
      "description": "Data de entrega segunda, 10 ago 2026, 23:59",
      "source": "official"
    },
    {
      "id": "event-081",
      "title": "Teste de Performance - TP1 [Obrigatório]",
      "type": "assignment",
      "discipline": "Fundamentos de Desenvolvimento com Java",
      "date": "2026-08-10",
      "time": "23:59",
      "description": "Data de entrega segunda, 10 ago 2026, 23:59",
      "source": "official"
    },
    {
      "title": "2026 Trimestre 3 — Semana 5",
      "type": "event",
      "discipline": null,
      "date": "2026-08-17",
      "time": null,
      "description": "17: INÍCIO DAS AULAS PARA NOVOS ALUNOS PRESENCIAIS DA FACULDADE INFNET Atividades típicas: ESTUDO DA ETAPA 5 / ESTUDO DA ETAPA 3 / ESTUDO DA ETAPA 8 | LEITURA EM AULA DO TP4 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-082"
    },
    {
      "title": "INÍCIO DAS AULAS PARA NOVOS ALUNOS PRESENCIAIS DA FACULDADE INFNET",
      "type": "event",
      "discipline": null,
      "date": "2026-08-17",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 3 | Semana 5. Obs: 17: INÍCIO DAS AULAS PARA NOVOS ALUNOS PRESENCIAIS DA FACULDADE INFNET",
      "source": "official",
      "id": "event-083"
    },
    {
      "title": "2026 Trimestre 3 — Semana 6",
      "type": "event",
      "discipline": null,
      "date": "2026-08-24",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 6, ENTREGA DO TP2. | LEITURA EM AULA DO TP3 / ESTUDO DA ETAPA 3 | ENTREGA DO TP1 / ESTUDO DA ETAPA 9 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-084"
    },
    {
      "id": "event-085",
      "title": "Teste de Performance - TP2 [OBRIGATÓRIO]",
      "type": "assignment",
      "discipline": "Fundamentos de Desenvolvimento com C#",
      "date": "2026-08-24",
      "time": "23:59",
      "description": "Data de entrega segunda, 24 ago 2026, 23:59",
      "source": "official"
    },
    {
      "id": "event-086",
      "title": "Teste de Performance - TP2 [OBRIGATÓRIO]",
      "type": "assignment",
      "discipline": "Fundamentos de Desenvolvimento com Java",
      "date": "2026-08-24",
      "time": "23:59",
      "description": "Data de entrega segunda, 24 ago 2026, 23:59",
      "source": "official"
    },
    {
      "id": "event-087",
      "title": "Teste de Performance - TP1 [Obrigatório]",
      "type": "assignment",
      "discipline": "Projeto de Bloco — Desenvolvimento Back-End",
      "date": "2026-08-24",
      "time": "23:59",
      "description": "Data de entrega segunda, 24 ago 2026, 23:59",
      "source": "official"
    },
    {
      "title": "2026 Trimestre 3 — Semana 7",
      "type": "event",
      "discipline": null,
      "date": "2026-08-31",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 7 / ESTUDO DA ETAPA 4 / ESTUDO DA ETAPA 9 | ENTREGA DO TP4 | LEITURA EM AULA DO TP5 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-088"
    },
    {
      "title": "2026 Trimestre 3 — Semana 8",
      "type": "event",
      "discipline": null,
      "date": "2026-09-07",
      "time": null,
      "description": "7: INDEPENDÊNCIA Atividades típicas: ESTUDO DA ETAPA 8, ENTREGA DO TP3 / ESTUDO DA ETAPA 4 | LEITURA EM AULA DO TP2 / ESTUDO DA ETAPA 10 | ENTREGA DO TP5 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-089"
    },
    {
      "title": "INDEPENDÊNCIA",
      "type": "holiday",
      "discipline": null,
      "date": "2026-09-07",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 3 | Semana 8. Obs: 7: INDEPENDÊNCIA",
      "source": "official",
      "id": "event-090"
    },
    {
      "id": "event-091",
      "title": "Teste de Performance - TP3 [Obrigatório]",
      "type": "assignment",
      "discipline": "Fundamentos de Desenvolvimento com C#",
      "date": "2026-09-07",
      "time": "23:59",
      "description": "Data de entrega segunda, 7 set 2026, 23:59",
      "source": "official"
    },
    {
      "id": "event-092",
      "title": "Teste de Performance - TP3 [Obrigatório]",
      "type": "assignment",
      "discipline": "Fundamentos de Desenvolvimento com Java",
      "date": "2026-09-07",
      "time": "23:59",
      "description": "Data de entrega segunda, 7 set 2026, 23:59",
      "source": "official"
    },
    {
      "title": "2026 Trimestre 3 — Semana 9",
      "type": "assessment",
      "discipline": null,
      "date": "2026-09-14",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 9 | LEITURA EM AULA DO ASSESSMENT / ESTUDO DA ETAPA 5 / ESTUDO DA ETAPA 10 | ENTREGA DO PROJETO DE BLOCO Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-093"
    },
    {
      "title": "2026 Trimestre 3 — Semana 10",
      "type": "assessment",
      "discipline": null,
      "date": "2026-09-21",
      "time": null,
      "description": "21: INÍCIO DAS AULAS PARA NOVOS ALUNOS PRESENCIAIS DA ECDD Atividades típicas: ENTREGA/ARGUIÇÃO DO ASSESSMENT / ESTUDO DA ETAPA 5 | ENTREGA DO TP2 / APRESENTAÇÕES DE PROJETOS DE BLOCO Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-094"
    },
    {
      "title": "INÍCIO DAS AULAS PARA NOVOS ALUNOS PRESENCIAIS DA ECDD",
      "type": "event",
      "discipline": null,
      "date": "2026-09-21",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 3 | Semana 10. Obs: 21: INÍCIO DAS AULAS PARA NOVOS ALUNOS PRESENCIAIS DA ECDD",
      "source": "official",
      "id": "event-095"
    },
    {
      "id": "event-096",
      "title": "Teste de Performance - TP2 [OBRIGATÓRIO]",
      "type": "assignment",
      "discipline": "Projeto de Bloco — Desenvolvimento Back-End",
      "date": "2026-09-21",
      "time": "23:59",
      "description": "Data de entrega segunda, 21 set 2026, 23:59",
      "source": "official"
    },
    {
      "id": "event-097",
      "title": "Assessment [Obrigatório]",
      "type": "assessment",
      "discipline": "Fundamentos de Desenvolvimento com C#",
      "date": "2026-09-22",
      "time": "23:59",
      "description": "Data de entrega terça, 22 set 2026, 23:59",
      "source": "official"
    },
    {
      "id": "event-098",
      "title": "Assessment [Obrigatório]",
      "type": "assessment",
      "discipline": "Fundamentos de Desenvolvimento com Java",
      "date": "2026-09-22",
      "time": "23:59",
      "description": "Data de entrega terça, 22 set 2026, 23:59",
      "source": "official"
    },
    {
      "title": "2026 Trimestre 3 — Semana 11",
      "type": "event",
      "discipline": null,
      "date": "2026-09-28",
      "time": null,
      "description": "Atividades típicas: VISTA DO AT, REENTREGA DO AT / ESTUDO DA ETAPA 6 / APRESENTAÇÕES DE PROJETOS DE BLOCO Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-099"
    },
    {
      "title": "2026 Trimestre 4 — Semana 1",
      "type": "event",
      "discipline": null,
      "date": "2026-10-05",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 1 / ESTUDO DA ETAPA 6 | LEITURA EM AULA DO TP3 / ESTUDO DA ETAPA 1 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-100"
    },
    {
      "title": "2026 Trimestre 4 — Semana 2",
      "type": "event",
      "discipline": null,
      "date": "2026-10-12",
      "time": null,
      "description": "12: NOSSA SENHORA | 15: DIA DO PROFESSOR E DO ADMINISTRADOR ESCOLAR Atividades típicas: ESTUDO DA ETAPA 2 | LEITURA EM AULA DO TP1 / ESTUDO DA ETAPA 7 / ESTUDO DA ETAPA 1 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-101"
    },
    {
      "title": "NOSSA SENHORA",
      "type": "holiday",
      "discipline": null,
      "date": "2026-10-12",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 4 | Semana 2. Obs: 12: NOSSA SENHORA | 15: DIA DO PROFESSOR E DO ADMINISTRADOR ESCOLAR",
      "source": "official",
      "id": "event-102"
    },
    {
      "title": "DIA DO PROFESSOR E DO ADMINISTRADOR ESCOLAR",
      "type": "holiday",
      "discipline": null,
      "date": "2026-10-15",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 4 | Semana 2. Obs: 12: NOSSA SENHORA | 15: DIA DO PROFESSOR E DO ADMINISTRADOR ESCOLAR",
      "source": "official",
      "id": "event-103"
    },
    {
      "title": "2026 Trimestre 4 — Semana 3",
      "type": "event",
      "discipline": null,
      "date": "2026-10-19",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 3 / ESTUDO DA ETAPA 7 | ENTREGA DO TP3 / ESTUDO DA ETAPA 2 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-104"
    },
    {
      "id": "event-105",
      "title": "Teste de Performance - TP3 [Obrigatório]",
      "type": "assignment",
      "discipline": "Projeto de Bloco — Desenvolvimento Back-End",
      "date": "2026-10-19",
      "time": "23:59",
      "description": "Data de entrega segunda, 19 out 2026, 23:59",
      "source": "official"
    },
    {
      "title": "2026 Trimestre 4 — Semana 4",
      "type": "event",
      "discipline": null,
      "date": "2026-10-26",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 4, ENTREGA DO TP1. | LEITURA EM AULA DO TP2 / ESTUDO DA ETAPA 8 / ESTUDO DA ETAPA 2 | LEITURA EM AULA DO TP1 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-106"
    },
    {
      "title": "Teste de Performance - TP1 [Obrigatório]",
      "type": "assignment",
      "discipline": "Desenvolvimento Web com .NET e Bases de Dados",
      "date": "2026-10-26",
      "time": "23:59",
      "description": "Data de entrega segunda, 26 out 2026, 23:59",
      "source": "official",
      "id": "event-107"
    },
    {
      "title": "Teste de Performance - TP1 [Obrigatório]",
      "type": "assignment",
      "discipline": "Desenvolvimento de Serviços Web e Testes com Java",
      "date": "2026-10-26",
      "time": "23:59",
      "description": "Data de entrega segunda, 26 out 2026, 23:59",
      "source": "official",
      "id": "event-108"
    },
    {
      "title": "2026 Trimestre 4 — Semana 5",
      "type": "event",
      "discipline": null,
      "date": "2026-11-02",
      "time": null,
      "description": "2: FINADOS | 6: EVENTO \"APRESENTAÇÃO DE PORTFÓLIO DE PROJETOS\" Atividades típicas: ESTUDO DA ETAPA 5 / ESTUDO DA ETAPA 8 | LEITURA EM AULA DO TP4 / ESTUDO DA ETAPA 3 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-109"
    },
    {
      "title": "FINADOS",
      "type": "holiday",
      "discipline": null,
      "date": "2026-11-02",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 4 | Semana 5. Obs: 2: FINADOS | 6: EVENTO \"APRESENTAÇÃO DE PORTFÓLIO DE PROJETOS\"",
      "source": "official",
      "id": "event-110"
    },
    {
      "title": "EVENTO \"APRESENTAÇÃO DE PORTFÓLIO DE PROJETOS\"",
      "type": "event",
      "discipline": null,
      "date": "2026-11-06",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 4 | Semana 5. Obs: 2: FINADOS | 6: EVENTO \"APRESENTAÇÃO DE PORTFÓLIO DE PROJETOS\"",
      "source": "official",
      "id": "event-111"
    },
    {
      "title": "2026 Trimestre 4 — Semana 6",
      "type": "event",
      "discipline": null,
      "date": "2026-11-09",
      "time": null,
      "description": "15: PROCLAMAÇÃO DA REPÚBLICA Atividades típicas: ESTUDO DA ETAPA 6, ENTREGA DO TP2. | LEITURA EM AULA DO TP3 / ESTUDO DA ETAPA 9 / ESTUDO DA ETAPA 3 | ENTREGA DO TP1 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-112"
    },
    {
      "title": "Teste de Performance - TP2 [OBRIGATÓRIO]",
      "type": "assignment",
      "discipline": "Desenvolvimento Web com .NET e Bases de Dados",
      "date": "2026-11-09",
      "time": "23:59",
      "description": "Data de entrega segunda, 9 nov 2026, 23:59",
      "source": "official",
      "id": "event-113"
    },
    {
      "title": "Teste de Performance - TP2 [OBRIGATÓRIO]",
      "type": "assignment",
      "discipline": "Desenvolvimento de Serviços Web e Testes com Java",
      "date": "2026-11-09",
      "time": "23:59",
      "description": "Data de entrega segunda, 9 nov 2026, 23:59",
      "source": "official",
      "id": "event-114"
    },
    {
      "title": "PROCLAMAÇÃO DA REPÚBLICA",
      "type": "holiday",
      "discipline": null,
      "date": "2026-11-15",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 4 | Semana 6. Obs: 15: PROCLAMAÇÃO DA REPÚBLICA",
      "source": "official",
      "id": "event-115"
    },
    {
      "title": "2026 Trimestre 4 — Semana 7",
      "type": "event",
      "discipline": null,
      "date": "2026-11-16",
      "time": null,
      "description": "20: CONSCIÊNCIA NEGRA Atividades típicas: ESTUDO DA ETAPA 7 / ESTUDO DA ETAPA 9 | ENTREGA DO TP4 | LEITURA EM AULA DO TP5 / ESTUDO DA ETAPA 4 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-116"
    },
    {
      "id": "event-117",
      "title": "Teste de Performance - TP4 [OBRIGATÓRIO]",
      "type": "assignment",
      "discipline": "Projeto de Bloco — Desenvolvimento Back-End",
      "date": "2026-11-16",
      "time": "23:59",
      "description": "Data de entrega segunda, 16 nov 2026, 23:59",
      "source": "official"
    },
    {
      "title": "CONSCIÊNCIA NEGRA",
      "type": "holiday",
      "discipline": null,
      "date": "2026-11-20",
      "time": null,
      "description": "Calendário Acadêmico Discente Graduação 2026. Semana: 2026 Trim 4 | Semana 7. Obs: 20: CONSCIÊNCIA NEGRA",
      "source": "official",
      "id": "event-118"
    },
    {
      "title": "2026 Trimestre 4 — Semana 8",
      "type": "event",
      "discipline": null,
      "date": "2026-11-23",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 8, ENTREGA DO TP3 / ESTUDO DA ETAPA 10 | ENTREGA DO TP5 / ESTUDO DA ETAPA 4 | LEITURA EM AULA DO TP2 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-119"
    },
    {
      "title": "Teste de Performance - TP3 [Obrigatório]",
      "type": "assignment",
      "discipline": "Desenvolvimento Web com .NET e Bases de Dados",
      "date": "2026-11-23",
      "time": "23:59",
      "description": "Data de entrega segunda, 23 nov 2026, 23:59",
      "source": "official",
      "id": "event-120"
    },
    {
      "title": "Teste de Performance - TP3 [Obrigatório]",
      "type": "assignment",
      "discipline": "Desenvolvimento de Serviços Web e Testes com Java",
      "date": "2026-11-23",
      "time": "23:59",
      "description": "Data de entrega segunda, 23 nov 2026, 23:59",
      "source": "official",
      "id": "event-121"
    },
    {
      "id": "event-122",
      "title": "Teste de Performance - TP5 [OBRIGATÓRIO]",
      "type": "assignment",
      "discipline": "Projeto de Bloco — Desenvolvimento Back-End",
      "date": "2026-11-23",
      "time": "23:59",
      "description": "Data de entrega segunda, 23 nov 2026, 23:59",
      "source": "official"
    },
    {
      "title": "2026 Trimestre 4 — Semana 9",
      "type": "assessment",
      "discipline": null,
      "date": "2026-11-30",
      "time": null,
      "description": "Atividades típicas: ESTUDO DA ETAPA 9 | LEITURA EM AULA DO ASSESSMENT / ESTUDO DA ETAPA 10 | ENTREGA DO PROJETO DE BLOCO / ESTUDO DA ETAPA 5 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-123"
    },
    {
      "id": "event-124",
      "title": "Entrega de Projeto [Obrigatório]",
      "type": "delivery",
      "discipline": "Projeto de Bloco — Desenvolvimento Back-End",
      "date": "2026-12-04",
      "time": "23:59",
      "description": "Data de entrega sexta, 4 dez 2026, 23:59",
      "source": "official"
    },
    {
      "title": "2026 Trimestre 4 — Semana 10",
      "type": "assessment",
      "discipline": null,
      "date": "2026-12-07",
      "time": null,
      "description": "Atividades típicas: ENTREGA/ARGUIÇÃO DO ASSESSMENT / APRESENTAÇÕES DE PROJETOS DE BLOCO / ESTUDO DA ETAPA 5 | ENTREGA DO TP2 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-125"
    },
    {
      "title": "Assessment [Obrigatório]",
      "type": "assessment",
      "discipline": "Desenvolvimento Web com .NET e Bases de Dados",
      "date": "2026-12-08",
      "time": "23:59",
      "description": "Data de entrega terça, 8 dez 2026, 23:59",
      "source": "official",
      "id": "event-126"
    },
    {
      "title": "Assessment [Obrigatório]",
      "type": "assessment",
      "discipline": "Desenvolvimento de Serviços Web e Testes com Java",
      "date": "2026-12-08",
      "time": "23:59",
      "description": "Data de entrega terça, 8 dez 2026, 23:59",
      "source": "official",
      "id": "event-127"
    },
    {
      "title": "2026 Trimestre 4 — Semana 11",
      "type": "event",
      "discipline": null,
      "date": "2026-12-14",
      "time": null,
      "description": "SISTEMA DE REQUERIMENTOS FECHADO PARA AS FÉRIAS Atividades típicas: VISTA DO AT, REENTREGA DO AT / APRESENTAÇÕES DE PROJETOS DE BLOCO / ESTUDO DA ETAPA 6 Fonte: Calendário Acadêmico Discente Graduação 2026 (referência; entregas em vigor no Moodle).",
      "source": "official",
      "id": "event-128"
    },
    {
      "title": "FÉRIAS",
      "type": "holiday",
      "discipline": null,
      "date": "2026-12-21",
      "time": null,
      "description": "Período 2026-12-21 a 2026-12-26. INSTITUIÇÃO FECHADA, SEM ATENDIMENTO.\nNÃO É POSSÍVEL FAZER REQUERIMENTOS. Fonte: Calendário Acadêmico Discente Graduação 2026.",
      "source": "official",
      "id": "event-129"
    },
    {
      "title": "FÉRIAS",
      "type": "holiday",
      "discipline": null,
      "date": "2026-12-28",
      "time": null,
      "description": "Período 2026-12-28 a 2027-01-02. INSTITUIÇÃO FECHADA, SEM ATENDIMENTO.\nNÃO É POSSÍVEL FAZER REQUERIMENTOS. Fonte: Calendário Acadêmico Discente Graduação 2026.",
      "source": "official",
      "id": "event-130"
    }
  ],
  "_meta": {
    "sources": [
      "Moodle AVA Infnet (datas de entrega oficiais das disciplinas)",
      "Calendário Acadêmico Discente — Presencial e Live — Graduação 2026 (planilha institucional; entregas tipicas são referência — prevalece Moodle)"
    ],
    "note": "Em conflito entre planilha e Moodle para TPs/AT, prevalece o Moodle."
  }
}
```

Tipos reconhecidos: `assessment`, `exam`/`test`, `at`, `assignment`, `delivery`,
`seminar`, `class`, `event`, `holiday`.

Campos obrigatórios: `title` e `date` (`YYYY-MM-DD`). Fonte planilha: Calendário
Acadêmico Discente Presencial e Live — Graduação 2026.

## Informações importantes

- O Kernel calcula "quantos dias faltam" no servidor — mantenha as datas do
  `calendar.json` corretas e o resto acontece sozinho.
- Eventos passados continuam no ficheiro: o bot recebe um histórico compacto
  (até 30 eventos, com "foi há N dias" calculado) para responder "quando foi
  o AT?" e "o que aconteceu ontem?".
- Nunca coloque segredos (tokens, senhas) nestes ficheiros: o conteúdo entra
  no prompt do LLM e aparece nos traces.
