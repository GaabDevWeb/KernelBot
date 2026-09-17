# Assessment — Fundamentos de Desenvolvimento com C# [26E3_2]

- **Disciplina:** Fundamentos de Desenvolvimento com C# [26E3_2]
- **Curso Moodle:** [26T3-ADS-R1C1N2L1-DVBE-L2](https://lms.infnet.edu.br/moodle/course/view.php?id=10020)
- **Atividade:** [Assessment (Obrigatório)](https://lms.infnet.edu.br/moodle/mod/assign/view.php?id=471840)
- **Tipo:** Tarefa (entrega em PDF)
- **Data de entrega:** terça, 22 set 2026, 23:59
- **Tentativas:** 2 permitidas
- **Nome do arquivo:** `nome_sobrenome_DR2_AT.PDF`
- **Status observado:** nenhuma tentativa

## Enunciado

Olá Gabriel,

Chegamos no momento mais importante! Você veio ao longo dos TPs se preparando e agora chegou a hora da sua avaliação. 

Uso de IAs: Sinal Vermelho 🔴

Todas as partes deste trabalho devem ser da autoria do aluno. Qualquer uso de ferramentas generativas de IA, como ChatGPT, é proibido. O uso de IA generativa será considerado má conduta acadêmica e estará sujeito à aplicação do código disciplinar, pois as tarefas deste trabalho foram elaboradas para desafiar o aluno a desenvolver conhecimentos de base, pensamento crítico e habilidades de resolução de problemas. O uso da tecnologia de IA limitaria sua capacidade de desenvolver essas competências e de atingir os objetivos de aprendizagem desta disciplina.

Parte 1: Preparar Ambiente para Desenvolvimento Local com C# e .NET
Exercício 1: Criando e Executando seu Primeiro Programa

Enunciado:

Instale e configure o Visual Studio Community 2022.
Crie um novo projeto do tipo Console Application em C#.
No método Main(), escreva um programa que imprima no terminal:
Olá, meu nome é [Seu Nome]!
Nasci em [sua data de nascimento] e estou aprendendo C#!
Compile e execute o programa.

Observações:

✔ Envie uma captura de tela do código no Visual Studio.
✔ Envie uma captura de tela da saída do programa.

Critérios de Avaliação:

✔ Configuração correta do ambiente de desenvolvimento.
✔ Uso correto da sintaxe do C#.
✔ Programa funcionando conforme esperado.

Parte 2: Escrever Programas em C# Usando seus Elementos Básicos
Exercício 2: Manipulação de Strings - Cifrador de Nome

Enunciado:

Crie um programa que receba seu nome completo e desloque cada letra duas posições para frente no alfabeto.

✔ Entrada: "Carlos Silva"
✔ Saída esperada: "Ectnquu Ukngxc"

Observações:

✔ Utilize arrays e manipulação de caracteres.
✔ Ignore espaços e acentos no deslocamento.
✔ Não utilize bibliotecas de criptografia prontas.

Critérios de Avaliação:

✔ Implementação correta do deslocamento.
✔ Uso correto de arrays e manipulação de strings.
✔ Código organizado e comentado.

Exercício 3: Calculadora de Operações Matemáticas

Enunciado:

Crie um programa que solicite dois números e peça ao usuário para escolher uma operação matemática:

Soma
Subtração
Multiplicação
Divisão

O programa deve calcular e exibir o resultado da operação escolhida.

Observações:

✔ O programa deve aceitar apenas números válidos.
✔ A operação deve ser escolhida digitando 1, 2, 3 ou 4.
✔ Evite divisões por zero!

Critérios de Avaliação:

✔ Implementação correta da lógica matemática.
✔ Validação de entrada funcionando corretamente.
✔ Código organizado e comentado.

Exercício 4: Manipulação de Datas - Dias até o Próximo Aniversário

Enunciado:

Crie um programa que peça sua data de nascimento e informe quantos dias faltam para seu próximo aniversário.

✔ Regras:

Utilize a classe DateTime.
Considere anos bissextos.
Se faltar menos de 7 dias, exibir uma mensagem especial.

Critérios de Avaliação:

✔ Manipulação correta de datas.
✔ Cálculo correto do intervalo de dias.
✔ Exibição da saída formatada corretamente.

Exercício 5: Tempo Restante para Conclusão do Curso - Diferença Entre Datas

Contexto:

Como estudante do Instituto Infnet, você deseja acompanhar quanto tempo falta para sua formatura. Para isso, você decidiu criar um programa que calcula quantos anos, meses e dias restam até a data prevista para a conclusão do curso.

No ambiente acadêmico, a manipulação correta de datas é essencial para organizar prazos de disciplinas, entrega de TCCs, estágios obrigatórios e colação de grau. Este exercício ajudará a desenvolver habilidades fundamentais para a criação de sistemas acadêmicos, como portais do aluno e gerenciadores de calendário acadêmico.

Enunciado:

Implemente um programa que peça ao usuário a data atual e compare com a data prevista de sua formatura (definida manualmente no código). O programa deve exibir:

📌 Saídas esperadas:
✔ Quanto tempo falta para a formatura (anos, meses e dias).
✔ Se faltar menos de 6 meses, exibir a mensagem especial:
A reta final chegou! Prepare-se para a formatura!
✔ Se a data de formatura já tiver passado, exibir a mensagem:
Parabéns! Você já deveria estar formado!

Regras:

✔ O aluno deve definir manualmente sua data prevista de formatura no código.
✔ O programa deve pedir a data atual (input do usuário).
✔ Utilize a classe DateTime para manipular as datas corretamente.
✔ Evitar erros com datas inválidas (exemplo: usuário inserindo datas futuras como data atual).

Exemplo de Entrada e Saída

📌 Entrada:

Digite a data atual (dd/MM/yyyy): 10/04/2024

📌 Data de formatura (definida no código):

DateTime dataFormatura = new DateTime(2026, 12, 15);

📌 Saída esperada:

Faltam 2 anos, 8 meses e 5 dias para sua formatura!

Se faltar menos de 6 meses:

Faltam 5 meses e 10 dias para sua formatura!

A reta final chegou! Prepare-se para a formatura!

Se a data de formatura já tiver passado:

Parabéns! Você já deveria estar formado!

Se a data atual for futura:

Erro: A data informada não pode ser no futuro!

Critérios de Avaliação:

✔ Manipulação correta de datas usando DateTime.
✔ Cálculo correto do tempo restante até a formatura.
✔ Tratamento adequado para datas inválidas (exemplo: usuário inserindo data futura como data atual).
✔ Exibição formatada corretamente e código bem estruturado.

Parte 3: Escrever Programas em C# que Utilizem Classes e Objetos
Exercício 6: Cadastro de Alunos

Enunciado:

Crie uma classe Aluno que contenha:

Nome
Matrícula
Curso
Média das Notas

✔ Métodos:

ExibirDados(): Exibe os dados do aluno.
VerificarAprovacao(): Retorna "Aprovado" se a média for ≥ 7, senão "Reprovado".

✔ No Main(), crie um objeto com seus próprios dados e exiba as informações.

Critérios de Avaliação:

✔ Implementação correta da classe e métodos.
✔ Teste funcional no método Main().
✔ Código organizado e comentado.

Parte 4: Utilizar os Pilares da Programação Orientada a Objetos
Exercício 7: Banco Digital (Encapsulamento)

Enunciado:

Imagine que você foi contratado para desenvolver um sistema bancário digital para uma fintech inovadora. Neste sistema, é fundamental garantir a segurança e integridade dos dados dos clientes, evitando que informações sensíveis, como o saldo da conta, sejam acessadas ou modificadas diretamente. No mercado de trabalho, o encapsulamento é um princípio essencial da Programação Orientada a Objetos (POO) que protege os dados dentro de uma classe e permite que eles sejam manipulados apenas por meio de métodos específicos. Isso evita alterações indevidas e aumenta a confiabilidade do sistema. 

Para garantir essa segurança, sua tarefa será implementar uma classe ContaBancaria que proteja o saldo do usuário, permitindo apenas operações seguras por meio de métodos específicos.

Implemente uma classe ContaBancaria com os seguintes atributos e métodos:

📌 Atributos:

Titular (Nome do cliente, público)
Saldo (privado, não pode ser acessado diretamente)

📌 Métodos:

Depositar(decimal valor): Permite adicionar um valor à conta.
Sacar(decimal valor): Permite retirar um valor, mas somente se houver saldo suficiente.
ExibirSaldo(): Exibe o saldo atual da conta, sem permitir acesso direto ao atributo.

Regras:

✔ O saldo não pode ser acessado diretamente, apenas através dos métodos definidos.
✔ Saque só pode ser realizado se houver saldo suficiente. Caso contrário, exibir a mensagem:

Saldo insuficiente para realizar o saque!

✔ Depósitos não podem ser negativos. Caso contrário, exibir a mensagem:

O valor do depósito deve ser positivo!

✔ O sistema deve impedir que um usuário altere o saldo manualmente.

Exemplo de Uso no Main()

Após implementar a classe, no método Main(), crie um objeto ContaBancaria, simule algumas transações e exiba os resultados.

Exemplo de Saída Esperada:

Titular: João Silva

Depósito de R$ 500,00 realizado com sucesso!

Saldo atual: R$ 500,00

Tentativa de saque: R$ 700,00

Saldo insuficiente para realizar o saque!

Saque de R$ 200,00 realizado com sucesso!

Saldo atual: R$ 300,00

Critérios de Avaliação:

✔ Uso correto de encapsulamento para proteger o saldo da conta.
✔ Implementação correta dos métodos de depósito e saque.
✔ Validação correta para impedir saques indevidos e depósitos negativos.
✔ Código bem estruturado, organizado e comentado.

Conclusão:

Ao final deste exercício, você terá aplicado um conceito fundamental da Programação Orientada a Objetos (POO), garantindo segurança e controle sobre os dados de uma aplicação. Este princípio é amplamente utilizado em aplicações bancárias, fintechs, ERPs e sistemas que lidam com informações sensíveis.

Exercício 8: Cadastro de Funcionários (Herança)

Enunciado:

Crie uma classe Funcionario com:

Nome
Cargo
Salário base

Crie uma subclasse Gerente que:

Receba um bônus de 20% no salário.

✔ No Main(), crie um objeto de cada classe e exiba os salários corretamente.

Critérios de Avaliação:

✔ Uso correto de herança.
✔ Implementação correta dos cálculos.
✔ Código funcional e organizado.

Parte 5: Escrever Programas em C# com Arrays, Arquivos e Recursos Avançados
Exercício 9: Controle de Estoque via Linha de Comando

Contexto: Você é responsável por criar um pequeno sistema de gerenciamento de estoque para um comércio. O sistema rodará no terminal (linha de comando) e permitirá ao usuário inserir produtos e listar produtos cadastrados.

A) Manipulação de Arrays

Na primeira versão do programa, os produtos serão armazenados em um array dentro do código.

Requisitos:

✔ O programa exibe um menu de opções:

Inserir Produto
Listar Produtos
Sair

✔ O usuário pode inserir até 5 produtos (e não mais do que 5), cada um com:

Nome
Quantidade em estoque
Preço unitário

✔ Caso o usuário escolha "Listar Produtos", o programa exibe todos os produtos cadastrados no seguinte formato:

Produto: Notebook | Quantidade: 2 | Preço: R$ 4500,00

Produto: Mouse | Quantidade: 10 | Preço: R$ 75,50

✔ Se o usuário tentar inserir mais de 5 produtos, exiba uma mensagem: Limite de produtos atingido!

✔ O programa só encerra quando o usuário escolher "Sair".

B) Persistência com Arquivos

Agora, o programa armazenará os produtos em um arquivo de texto (estoque.txt), permitindo que os dados persistam após o encerramento do programa.

Requisitos adicionais:

✔ Quando o usuário escolhe "Inserir Produto", os produtos são salvos no arquivo (um por linha).
✔ Quando o usuário escolhe "Listar Produtos", o programa lê os produtos do arquivo e os exibe na tela.
✔ O arquivo deve seguir este formato:

Notebook,2,4500.00

Mouse,10,75.50

✔ Se o arquivo não existir, o programa deve criar um novo arquivo.
✔ Caso o arquivo esteja vazio, exibir a mensagem:

Nenhum produto cadastrado.

Restrições e Dicas:

Não utilize bancos de dados, apenas arrays e arquivos.
Utilize StreamWriter e StreamReader para manipular arquivos.
Evite sobrescrever o arquivo acidentalmente! Use AppendText para adicionar novos produtos.
Trate possíveis erros (exemplo: arquivo corrompido ou formato incorreto).
Exercício 10: Jogo de Adivinhação

✔ O usuário deve adivinhar um número de 1 a 50.
✔ Ele tem 5 tentativas.
✔ Se digitar um número fora do intervalo, exibir um erro.

Critérios de Avaliação:

✔ Uso correto de números aleatórios.
✔ Tratamento de exceções funcionando corretamente.
✔ Loop controlando o número de tentativas.

Exercício 11: Manipulação de Arquivos - Cadastro e Listagem de Contatos

Enunciado:

Implemente um programa em C# que permita cadastrar e listar contatos utilizando manipulação de arquivos. Os contatos devem ser armazenados de forma persistente em um arquivo chamado contatos.txt, garantindo que os dados não sejam perdidos ao encerrar o programa.

O programa deve oferecer ao usuário um menu interativo com as seguintes opções:

1 - Adicionar novo contato

2 - Listar contatos cadastrados

3 - Sair

Requisitos Técnicos

📌 Cadastro de Contatos:

O programa deve solicitar ao usuário os seguintes dados para cada contato:
Nome
Telefone
Email

Os contatos devem ser salvos no arquivo contatos.txt, um por linha, seguindo o formato:

João Silva,21 99999-9999,joao@email.com

Maria Oliveira,11 98888-7777,maria@email.com

📌 Listagem de Contatos:

Ao selecionar a opção de listar contatos, o programa deve ler todos os registros do arquivo contatos.txt e exibi-los de forma organizada no console. Caso o arquivo ainda não exista ou não contenha contatos, exibir a mensagem:
Nenhum contato cadastrado.

📌 Encerramento Seguro:

O programa só deve encerrar quando o usuário escolher explicitamente a opção "Sair" no menu.

Critérios de Avaliação

✔ Uso correto de StreamWriter e StreamReader para manipulação de arquivos.
✔ Persistência dos dados funcionando corretamente (contatos não devem ser perdidos entre execuções).
✔ Código bem estruturado, modularizado e com boas práticas de programação.
✔ Tratamento adequado de erros, evitando falhas na leitura e gravação do arquivo.

Exemplo de Execução

=== Gerenciador de Contatos ===

1 - Adicionar novo contato

2 - Listar contatos cadastrados

3 - Sair

Escolha uma opção: 1

Nome: João Silva

Telefone: (21) 99999-9999

Email: joao@email.com

Contato cadastrado com sucesso!

=== Gerenciador de Contatos ===

1 - Adicionar novo contato

2 - Listar contatos cadastrados

3 - Sair

Escolha uma opção: 2

Contatos cadastrados:

Nome: João Silva | Telefone: (21) 99999-9999 | Email: joao@email.com

=== Gerenciador de Contatos ===

1 - Adicionar novo contato

2 - Listar contatos cadastrados

3 - Sair

Escolha uma opção: 3

Encerrando programa...

Exercício 12: Manipulação de Arquivos com Herança e Polimorfismo - Formatos de Exibição

Enunciado:

Aprimore o programa de gerenciamento de contatos para permitir diferentes formatos de exibição dos dados utilizando herança e polimorfismo.

O programa deve continuar armazenando os contatos no arquivo contatos.txt, mas agora deve permitir que o usuário escolha como deseja visualizar os dados:

1️⃣ Markdown (formato estruturado para exibição em Markdown)
2️⃣ Tabela (formatado como uma tabela no terminal)
3️⃣ Texto Puro (exibição simples em texto)

Requisitos Técnicos

O programa deve continuar lendo e escrevendo os contatos em um arquivo contatos.txt.
Cada contato deve conter:
Nome
Telefone
Email
O usuário poderá cadastrar novos contatos e escolher entre os três formatos de exibição.
A implementação deve usar herança e polimorfismo:
Criar uma classe base ContatoFormatter que define um método ExibirContatos(List<Contato> contatos).
Criar três classes derivadas (MarkdownFormatter, TabelaFormatter, RawTextFormatter) que implementam o método de exibição de forma diferente.
O programa deve escolher a classe apropriada com base na entrada do usuário.

Detalhamento da Implementação

✔ Classe Contato: Representa um contato com os atributos Nome, Telefone, Email.
✔ Classe base ContatoFormatter: Contém o método virtual ExibirContatos(List<Contato> contatos).
✔ Subclasses MarkdownFormatter, TabelaFormatter e RawTextFormatter: Cada uma implementa ExibirContatos(List<Contato> contatos) de forma diferente.
✔ O programa principal (Main):

Permite cadastrar novos contatos.
Lê os contatos do arquivo contatos.txt.
Pergunta ao usuário em qual formato deseja exibir os contatos.
Exibe os contatos conforme a formatação escolhida.

Formato de Exibição

1️⃣ Markdown (MarkdownFormatter)

## Lista de Contatos

- **Nome:** João Silva

- 📞 Telefone: (21) 99999-9999

- 📧 Email: joao@email.com

- **Nome:** Maria Oliveira

- 📞 Telefone: (11) 98888-7777

- 📧 Email: maria@email.com

2️⃣ Tabela (TabelaFormatter)

----------------------------------------

| Nome | Telefone | Email |

----------------------------------------

| João Silva | 21 99999-9999 | joao@email.com |

| Maria Oliveira | 11 98888-7777 | maria@email.com |

----------------------------------------

3️⃣ Texto Puro (RawTextFormatter)

Nome: João Silva | Telefone: (21) 99999-9999 | Email: joao@email.com

Nome: Maria Oliveira | Telefone: (11) 98888-7777 | Email: maria@email.com

Critérios de Avaliação

✔ Uso correto de herança e polimorfismo.
✔ Leitura e escrita no arquivo contatos.txt funcionando corretamente.
✔ Seleção dinâmica da classe de formatação baseada na escolha do usuário.
✔ Código bem estruturado e modularizado.

Assim que terminar, salve seu trabalho em PDF nomeando o arquivo conforme a regra “nome_sobrenome_DR2_AT.PDF” e poste como resposta a este AT.

## Rubrica

Níveis de cada item: **Não demonstrou o item de rubrica** / **Demonstrou o item de rubrica**.

1. Preparar ambiente para desenvolvimento local com C# e .NET  
O aluno executou corretamente 25% dos exercícios da lista proposta? **25%**

1. Preparar ambiente para desenvolvimento local com C# e .NET  
O aluno executou corretamente 50% dos exercícios da lista proposta? **50%**

1. Preparar ambiente para desenvolvimento local com C# e .NET  
O aluno executou corretamente 75% dos exercícios da lista proposta? **75%**

1. Preparar ambiente para desenvolvimento local com C# e .NET  
O aluno executou corretamente 100% dos exercícios da lista proposta? **100%**

2. Escrever programas em C# usando seus elementos básicos  
O aluno executou corretamente 25% dos exercícios da lista proposta? **25%**

2. Escrever programas em C# usando seus elementos básicos  
O aluno executou corretamente 50% dos exercícios da lista proposta? **50%**

2. Escrever programas em C# usando seus elementos básicos  
O aluno executou corretamente 75% dos exercícios da lista proposta? **75%**

2. Escrever programas em C# usando seus elementos básicos  
O aluno executou corretamente 100% dos exercícios da lista proposta? **100%**

3. Escrever programas em C# que utilizem classes e objetos  
O aluno executou corretamente 25% dos exercícios da lista proposta? **25%**

3. Escrever programas em C# que utilizem classes e objetos  
O aluno executou corretamente 50% dos exercícios da lista proposta? **50%**

3. Escrever programas em C# que utilizem classes e objetos  
O aluno executou corretamente 75% dos exercícios da lista proposta? **75%**

3. Escrever programas em C# que utilizem classes e objetos  
O aluno executou corretamente 100% dos exercícios da lista proposta? **100%**

4. Utilizar os pilares do paradigma de orientação ao objeto para criação de programas em C#  
O aluno executou corretamente 25% dos exercícios da lista proposta? **25%**

4. Utilizar os pilares do paradigma de orientação ao objeto para criação de programas em C#  
O aluno executou corretamente 50% dos exercícios da lista proposta? **50%**

4. Utilizar os pilares do paradigma de orientação ao objeto para criação de programas em C#  
O aluno executou corretamente 75% dos exercícios da lista proposta? **75%**

4. Utilizar os pilares do paradigma de orientação ao objeto para criação de programas em C#  
O aluno executou corretamente 100% dos exercícios da lista proposta? **100%**

5. Escrever programas em C# com Arrays, arquivos e recursos mais avançados  
O aluno executou corretamente 25% dos exercícios da lista proposta? **25%**

5. Escrever programas em C# com Arrays, arquivos e recursos mais avançados  
O aluno executou corretamente 50% dos exercícios da lista proposta? **50%**

5. Escrever programas em C# com Arrays, arquivos e recursos mais avançados  
O aluno executou corretamente 75% dos exercícios da lista proposta? **75%**

5. Escrever programas em C# com Arrays, arquivos e recursos mais avançados  
O aluno executou corretamente 100% dos exercícios da lista proposta? **100%**
