# Smoke test — disciplinas, RAG e gates

Bateria de **100 perguntas** para validar retrieval, escopo por silo, `/doc`, modo geral e desambiguação.

**Base:** conteúdo indexado em `jsons/` (7 disciplinas de aula) + silo `doc` (wiki).

**Pré-requisitos:** `./bin/ingest-jsons.sh` (ou ingest ISS) + `./bin/ingest-wiki-doc.sh` + `/reload` ou restart.

## Protocolo de execução

1. **Nova conversa** antes de cada pergunta (evita pin e histórico residual).
2. Aguardar badge **Online** e `data: [DONE]` antes da seguinte.
3. Registar: `reason` (ACL_META), fontes no rodapé (`db:disciplina/slug`), badge de escopo.
4. Para perguntas **com comando**, o prefixo deve aparecer no início da mensagem.
5. Para perguntas **ambíguas**, anotar se houve chips de desambiguação, hard stop `ambiguous_retrieval` ou silo incorreto.

### Critérios rápidos

| Tipo | Sucesso mínimo |
|------|----------------|
| Com comando `/disciplina` | Fontes **apenas** do silo `db:<disciplina>/...` |
| Sem comando | Resposta ancorada ou hard stop honesto; silo coerente com o tema |
| Geral | Retrieval global ou catálogo; sem inventar fora da base |
| `/doc` | Conteúdo da wiki + `[Fonte: db:doc/…]` quando indexado |
| Ambígua | `ambiguous_retrieval`, chips, ou pedido de reformulação — **não** misturar silos sem aviso |

---

## 1. Fluência em IA (`fluencia-ia`)

### 1.1 Com `/fluencia-ia` (5)

| # | Pergunta | Aula / tema esperado |
|---|----------|----------------------|
| F1 | `/fluencia-ia Qual a diferença entre IA determinística, machine learning, deep learning e IA generativa?` | `introducao-fluencia-ia`, `ia-ml-deep-learning-generativa-pratica` |
| F2 | `/fluencia-ia O que são tokens e embeddings e por que importam em LLMs?` | `tokens-embeddings-prompt-temperatura` |
| F3 | `/fluencia-ia Como a temperatura do modelo afeta a criatividade da resposta?` | `tokens-embeddings-prompt-temperatura` |
| F4 | `/fluencia-ia Quais riscos de direitos autorais e plágio ao usar IA generativa na faculdade?` | `etica-automacao-humanizacao-direitos-autorais` |
| F5 | `/fluencia-ia Como agentes de IA usam ferramentas e RAG para decidir quando buscar contexto?` | `agentes-ia-rag-arquitetura` |

### 1.2 Sem comando (5)

| # | Pergunta | Aula / tema esperado |
|---|----------|----------------------|
| F6 | O que significa ter fluência em IA e por que validar o output antes de usar? | `introducao-fluencia-ia` |
| F7 | Como montar um prompt com persona, objetivo e critérios de qualidade? | `engenharia-de-prompt-fundamentos` |
| F8 | O que é decomposição de tarefas e auditoria em técnicas avançadas de prompt? | `tecnicas-avancadas-prompt-auditoria` |
| F9 | Como usar prompts estruturados para resumos de aula no NotebookLM? | `prompts-resumos-aula-notebooklm` |
| F10 | Por que verificação crítica e checagem de fontes são centrais no ecossistema de IAs generativas? | `etica-verificacao-critica-ecossistema-ias-generativas` |

---

## 2. Python — processamento de dados (`python-processamento-dados`)

### 2.1 Com `/python-processamento-dados` (5)

| # | Pergunta | Aula / tema esperado |
|---|----------|----------------------|
| PPD1 | `/python-processamento-dados Qual a diferença entre try, except, else e finally em pipelines de dados?` | `try-except-else-finally` |
| PPD2 | `/python-processamento-dados Como serializar e ler objetos Python em arquivos JSON?` | `json-python-serializacao-arquivos` |
| PPD3 | `/python-processamento-dados Como fazer requisição HTTP GET e POST com a biblioteca requests?` | `requisicoes-http-python-get-post` |
| PPD4 | `/python-processamento-dados Como expor uma rota simples em Flask para integrar com um LLM?` | `integracao-llms-servidor-flask` |
| PPD5 | `/python-processamento-dados Para que serve pass em exceções e quando usar pdb para depurar?` | `pass-excecoes-e-debug-pdb` |

### 2.2 Sem comando (5)

| # | Pergunta | Aula / tema esperado |
|---|----------|----------------------|
| PPD6 | Como tokenizar e fatiar textos no pré-processamento de strings? | `indexacao-fatiamento-tokenizacao-textos` |
| PPD7 | Como usar list comprehension para contar e transformar tokens em uma coleção? | `funcoes-pre-processamento-list-comprehension-contagem` |
| PPD8 | Qual a diferença entre lista mutável e tupla imutável para coordenadas ou registros fixos? | `matrizes-listas-aninhadas-tuplas-imutaveis` |
| PPD9 | Como abrir arquivos em disco com with open e qual encoding usar para CSV? | `manipulacao-arquivos-disco` |
| PPD10 | Como usar conjuntos (set) para comparar vocabulários de dois textos? | `conjuntos-sets-python` |

---

## 3. SQL — modelagem relacional (`sql-modelagem-relacional`)

### 3.1 Com `/sql-modelagem-relacional` (5)

| # | Pergunta | Aula / tema esperado |
|---|----------|----------------------|
| SQL1 | `/sql-modelagem-relacional O que é cardinalidade 1:1, 1:N e N:N em um DER?` | `mer-der-cardinalidade-terminologia-design` |
| SQL2 | `/sql-modelagem-relacional Explique primeira, segunda e terceira formas normais com um exemplo de livraria.` | `modelo-logico-normalizacao-1fn-2fn-3fn`, `tp1-livraria-normalizacao-chaves-tipos` |
| SQL3 | `/sql-modelagem-relacional Como modelar reservas, ocupação e serviços em um sistema de hotel?` | `modelagem-hotel-reservas-ocupacao-servicos` |
| SQL4 | `/sql-modelagem-relacional Como ligar tabelas com INNER JOIN e LEFT JOIN no caso do hotel?` | `implementacao-hotel-sqlite-joins-pratica`, `joins-e-ligacao-de-tabelas` |
| SQL5 | `/sql-modelagem-relacional Como usar GROUP BY e HAVING para análise temporal de ocupação?` | `agregacoes-group-by-having-analise-temporal` |

### 3.2 Sem comando (5)

| # | Pergunta | Aula / tema esperado |
|---|----------|----------------------|
| SQL6 | Qual a diferença entre modelo conceitual, lógico e físico na modelagem relacional? | `modelagem-dados-relacional-fundamentos` |
| SQL7 | Como desenhar um DER com chave primária e estrangeira no BRModelo? | `modelagem-conceitual-listas-der-brmodelo` |
| SQL8 | Como normalizar uma planilha desnormalizada até o MER de entidade-relacionamento? | `tp2-planilha-normalizacao-mer` |
| SQL9 | Como corrigir dados sujos com UPDATE e diagnosticar qualidade no SQLiteStudio? | `qualidade-de-dados-update-sql` |
| SQL10 | Quando usar ALTER TABLE e como fazer backup antes de excluir dados? | `exclusao-dados-backup-alter-table` |

---

## 4. Python (`python`)

### 4.1 Com `/python` (5)

| # | Pergunta | Aula / tema esperado |
|---|----------|----------------------|
| PY1 | `/python Como declarar variáveis e seguir snake_case no estilo Python?` | `variaveis-tipos-estilo-python` |
| PY2 | `/python Qual a diferença entre aspas simples, duplas e strings multilinha?` | `strings-literais-multilinhas` |
| PY3 | `/python Como usar f-strings para interpolar variáveis em uma mensagem?` | `strings-interpolacao-input` |
| PY4 | `/python Como escolher entre if, elif e else em uma regra de desconto?` | `desvios-condicionais-if-elif-else` |
| PY5 | `/python Como usar for com range e enumerate em uma tabuada?` | `loops-for-range-listas`, `aula-13-pratica-teste-mesa-tabuada-enumerate-matriz` |

### 4.2 Sem comando (5)

| # | Pergunta | Aula / tema esperado |
|---|----------|----------------------|
| PY6 | Por que Python é indicado para quem está começando em programação? | `por-que-programar-python` |
| PY7 | O que é um algoritmo e como o Jupyter Notebook ajuda no pensamento computacional? | `algoritmos-e-notebooks` |
| PY8 | Como converter texto em número com int() sem gerar ValueError? | `conversao-tipos-operadores-aritmeticos` |
| PY9 | Como fazer slice em uma string para pegar os três primeiros caracteres? | `strings-indices-slice-metodos` |
| PY10 | Como usar operadores lógicos and e or em uma condição composta? | `operadores-logicos-match-case` |

---

## 5. Visualização SQL (`visualizacao-sql`)

### 5.1 Com `/visualizacao-sql` (5)

| # | Pergunta | Aula / tema esperado |
|---|----------|----------------------|
| VS1 | `/visualizacao-sql Como conectar um CSV ao Looker Studio e montar a primeira visualização?` | `visualizar-dados-csv-looker-studio` |
| VS2 | `/visualizacao-sql Como criar gráfico de pizza e barras para tipos de transação bancária?` | `dashboard-pizza-barras-transacoes-looker` |
| VS3 | `/visualizacao-sql Qual a diferença entre WHERE e HAVING em uma agregação com GROUP BY?` | `sql-group-by-having-agregacoes` |
| VS4 | `/visualizacao-sql Como criar tabela e inserir linhas no SQLiteStudio?` | `criando-tabelas-sqlite-dml-basica` |
| VS5 | `/visualizacao-sql Como ordenar relatório de vendas com ORDER BY em mais de uma coluna?` | `sql-order-by-ordenacao-resultados` |

### 5.2 Sem comando (5)

| # | Pergunta | Aula / tema esperado |
|---|----------|----------------------|
| VS6 | Como integrar Google Planilhas com Looker para relatório de conta corrente? | `conta-bancaria-google-sheets-looker` |
| VS7 | Quais métricas e dimensões usar no dashboard da cafeteria Herman? | `dashboard-cafeteria-herman` |
| VS8 | O que são tipos de dados SQL e por que importam no CREATE TABLE? | `introducao-bancos-dados-tipos-dados-sql` |
| VS9 | Como filtrar clientes por UF com WHERE e operadores de comparação? | `consultas-sql-tabela-clientes-pratica` |
| VS10 | Como comparar vendas entre anos no mesmo dashboard Looker? | `dashboard-comparacao-anos-conta-bancaria-looker` |

---

## 6. Projeto de bloco (`projeto-bloco`)

### 6.1 Com `/projeto-bloco` (5)

| # | Pergunta | Aula / tema esperado |
|---|----------|----------------------|
| PB1 | `/projeto-bloco Qual a diferença entre metodologia tradicional em cascata e ágil em projeto de dados?` | `metodologias-projeto-de-dados` |
| PB2 | `/projeto-bloco Como ingerir CSV e Excel com pandas e gravar no SQLite?` | `ingestao-csv-excel-pandas-sqlite` |
| PB3 | `/projeto-bloco Como implementar CRUD em PostgreSQL a partir de Python?` | `python-jupyter-crud-bancos-relacionais`, `integracao-python-sql-crud-regras-negocio` |
| PB4 | `/projeto-bloco Como evoluir do MER ao SQLite no projeto e-commerce do bloco?` | `modelagem-conceitual-logica-fisica-normalizacao-sqlite-ecommerce` |
| PB5 | `/projeto-bloco O que documentar na POC de persistência antes do AT?` | `requisitos-persistencia-poc-sqlite-ecommerce` |

### 6.2 Sem comando (5)

| # | Pergunta | Aula / tema esperado |
|---|----------|----------------------|
| PB6 | Quais são as etapas do Projeto de Bloco na formação em dados? | `introducao-projeto-bloco-formacao` |
| PB7 | Como montar um laboratório local com Python, Jupyter e banco relacional? | `laboratorio-dados-python-sql` |
| PB8 | Como escolher entre PostgreSQL, MySQL e SQL Server no pipeline? | `pipeline-ferramentas-bancos-dados` |
| PB9 | Qual a diferença entre perfil engenheiro de dados e cientista de dados? | `perfis-profissionais-case-consumidores` |
| PB10 | Como usar placeholders em INSERT para evitar concatenação insegura de SQL? | `ingestao-csv-excel-pandas-sqlite` |

---

## 7. Planejamento de curso e carreira (`planejamento-curso-carreira`)

### 7.1 Com `/planejamento-curso-carreira` (5)

| # | Pergunta | Aula / tema esperado |
|---|----------|----------------------|
| PC1 | `/planejamento-curso-carreira Como estruturar currículo para passar em ATS em vagas de tecnologia?` | `curriculo-ats-experiencias` |
| PC2 | `/planejamento-curso-carreira Como aplicar análise SWOT no plano de carreira?` | `planejamento-carreira-swot` |
| PC3 | `/planejamento-curso-carreira Como otimizar título e resumo do LinkedIn para recrutadores?` | `linkedin-carreira-oportunidades` |
| PC4 | `/planejamento-curso-carreira O que avaliar em entrevista por competências com rubrica comportamental?` | `competencias-rubricas-entrevista-comportamental` |
| PC5 | `/planejamento-curso-carreira Como funcionam blocos, estágio e atividades complementares na graduação?` | `bloco-entrada-estagio-atividades-complementares` |

### 7.2 Sem comando (5)

| # | Pergunta | Aula / tema esperado |
|---|----------|----------------------|
| PC6 | Como organizar roteiro de apresentação do AT antes de montar os slides? | `at-apresentacao-oratoria` |
| PC7 | Quais técnicas de respiração e ensaio reduzem medo de falar em público? | `at-apresentacao-oratoria` |
| PC8 | Como dar feedback objetivo em apresentações entre pares? | `apresentacoes-entre-pares-rodadas` |
| PC9 | Como reconhecer privilégio e gatilhos emocionais em equipes diversas? | `privilegios-etica-diversidade-gatilhos` |
| PC10 | Por que proatividade e hábitos de estudo impactam empregabilidade em dados? | `habitos-mudanca-equipes-proatividade` |

---

## 8. Perguntas gerais / isoladas (10)

Sem prefixo de disciplina nem `/doc`. Testam modo global, catálogo lexical e gates de consulta vaga.

| # | Pergunta | Comportamento esperado |
|---|----------|------------------------|
| G1 | Como funciona um laço for com range em Python? | Silo `python` ou resposta ancorada; não inventar |
| G2 | O que é GROUP BY em SQL? | Pode cair em `visualizacao-sql` ou `sql-modelagem-relacional` — verificar fontes |
| G3 | Qual a diferença entre machine learning e deep learning? | Tende a `fluencia-ia` |
| G4 | Como normalizar uma tabela até a 3FN? | Tende a `sql-modelagem-relacional` |
| G5 | Como montar portfólio para estágio em desenvolvimento? | Tende a `planejamento-curso-carreira` |
| G6 | O que é um dashboard no Looker Studio? | Tende a `visualizacao-sql` |
| G7 | Como tratar exceções em scripts Python de dados? | Tende a `python-processamento-dados` |
| G8 | O que é ingestão ETL de CSV para banco relacional? | Tende a `projeto-bloco` |
| G9 | Como escrever um prompt objetivo para um LLM? | Tende a `fluencia-ia` |
| G10 | `oi` | Hard stop `underspecified_query` |

---

## 9. Perguntas `/doc` — documentação do bot (10)

| # | Pergunta | Tema wiki esperado |
|---|----------|-------------------|
| D1 | `/doc O que é o KernelBot e qual o papel do ACL?` | Identidade, tutor ancorado na base |
| D2 | `/doc Liste todos os comandos de disciplina disponíveis no chat.` | Comandos incluindo as 7 disciplinas |
| D3 | `/doc Qual a diferença entre /reset e Nova conversa no UI?` | Pin vs histórico localStorage |
| D4 | `/doc Como funciona o pin de contexto entre turnos?` | PinnedSessionStore, scope_key |
| D5 | `/doc O que é BM25 e como o índice é reconstruído?` | Chunking, `/reload` |
| D6 | `/doc O que significa index_gap no chat?` | Catálogo vs MySQL |
| D7 | `/doc O bot pode entregar o gabarito integral do AT?` | Limites pedagógicos |
| D8 | `/doc Onde ficam guardadas as mensagens do histórico?` | Browser, sem conta |
| D9 | `/doc Como ingerir conteúdo novo no silo doc?` | `ingest-wiki-doc.sh` |
| D10 | `/doc O que é ACL_META v=3 na resposta SSE?` | Contrato meta, allow_generation |

---

## 10. Perguntas ambíguas (10)

Projetadas para **cruzar silos** ou **ficar subespecificadas**. Registar se o bot desambigua, pede reformulação ou restringe ao silo errado.

| # | Pergunta | Por que é ambígua | Resultado aceitável |
|---|----------|-------------------|---------------------|
| A1 | Como usar JOIN em SQL? | Visualização SQL vs modelagem relacional | Chips, `ambiguous_retrieval`, ou pedido de contexto |
| A2 | Como trabalhar com listas em Python? | Python básico vs processamento de dados | Desambiguação ou fontes de um silo só |
| A3 | Como modelar um e-commerce com banco de dados? | Projeto bloco vs SQL modelagem | Não misturar silos sem aviso |
| A4 | Como usar pandas para limpar dados? | Projeto bloco (ingestão) vs PPD | Desambiguação ou escopo explícito |
| A5 | `performance` | Consulta vaga, alto risco | `vague_but_high_risk` ou `underspecified_query` |
| A6 | Como montar um dashboard de vendas? | Looker (visualização) vs métricas de negócio genéricas | Silo correto ou reformulação |
| A7 | Posso usar ChatGPT no trabalho da faculdade? | Fluência IA (ética) vs planejamento (integridade acadêmica) | Resposta com fontes de um domínio ou desambiguação |
| A8 | O que é normalização de dados? | 3FN (modelagem) vs limpeza de strings (PPD) | Não confundir conceitos |
| A9 | Como integrar Python com MySQL? | Projeto bloco, PPD (API), visualização | Chips ou pergunta de follow-up |
| A10 | SQL para analisar ocupação de hotel | Modelagem (caso hotel) vs visualização (agregações) | Fontes de um silo ou desambiguação |

---

## Resumo da bateria

| Bloco | Quantidade |
|-------|------------|
| Por disciplina (7 × 10) | 70 |
| Gerais / isoladas | 10 |
| `/doc` | 10 |
| Ambíguas | 10 |
| **Total** | **100** |

## Anti-vazamento (spot check)

Após a bateria principal, repetir **uma** pergunta de cada par com comando **do silo oposto**:

| Pergunta (silo ativo) | Não deve trazer fontes de |
|------------------------|---------------------------|
| `/visualizacao-sql normalização 3FN` | `sql-modelagem-relacional` |
| `/sql-modelagem-relacional dashboard Looker` | `visualizacao-sql` |
| `/python try except em Flask` | `python-processamento-dados` |
| `/python-processamento-dados o que é f-string` | `python` |

---

Ver também: [`PERGUNTAS-SMOKE-DOC-WIKI.md`](PERGUNTAS-SMOKE-DOC-WIKI.md) (bateria estendida só `/doc`), [`docs/RELATORIO-INTEGRACAO-DISCIPLINAS.md`](docs/RELATORIO-INTEGRACAO-DISCIPLINAS.md).
