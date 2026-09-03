# TP3 — Fundamentos de Desenvolvimento com Java [26E3_1]

- **Disciplina:** Fundamentos de Desenvolvimento com Java [26E3_1]
- **Curso Moodle:** [26T3-ADS-R1C1N2L1-DVBE-L1](https://lms.infnet.edu.br/moodle/course/view.php?id=10021)
- **Atividade:** [Teste de Performance - TP3 (Obrigatório)](https://lms.infnet.edu.br/moodle/mod/assign/view.php?id=471848)
- **Tipo:** Tarefa (entrega em PDF)
- **Data de entrega:** segunda, 7 set 2026, 23:59
- **Nome do arquivo:** `nome_sobrenome_DR1_TP3.PDF`
- **Status observado:** nenhuma tentativa (prazo ainda aberto)

## Enunciado

Olá Gabriel,

Chegamos em uma das etapas de preparação! A cada Teste de Performance (TP) você terá a oportunidade de praticar os conhecimentos adquiridos e receber feedbacks relevantes para o seu aprendizado.

Uso de IAs: Sinal Vermelho 🔴

Todas as partes deste trabalho devem ser da autoria do aluno. Qualquer uso de ferramentas generativas de IA, como ChatGPT, é proibido. O uso de IA generativa será considerado má conduta acadêmica e estará sujeito à aplicação do código disciplinar, pois as tarefas deste trabalho foram elaboradas para desafiar o aluno a desenvolver conhecimentos de base, pensamento crítico e habilidades de resolução de problemas. O uso da tecnologia de IA limitaria sua capacidade de desenvolver essas competências e de atingir os objetivos de aprendizagem desta disciplina.

Competência: Escrever programas em Java que utilizem classes e objetos

Exercício 1 Conceitos de Classe, Objeto, Campos e Métodos

Enunciado: Com base no conteúdo estudado sobre Programação Orientada a Objetos em Java, elabore uma explicação clara e objetiva dos conceitos de classe, objeto, campos (ou atributos) e métodos. Em seguida, crie um exemplo simples (em pseudocódigo ou em Java) que ilustre esses conceitos na prática. Seu exemplo deve conter: 

Declaração de uma classe.
Pelo menos dois campos (ou atributos) diferentes.
Pelo menos um método que utilize ou manipule os campos da classe.
Criação de um objeto a partir da classe declarada.

Observações:

Você pode usar exemplos do dia a dia (como “Carro”, “ContaBancaria”, etc.) para tornar a explicação mais clara.
Procure relacionar cada conceito com o exemplo criado, explicando o que cada parte representa na prática.
Seja sucinto, mas inclua detalhes suficientes para demonstrar compreensão do assunto.

Considerações:

Clareza e correção conceitual na explicação dos termos (classe, objeto, campos, métodos).
Qualidade do exemplo prático e conexão com a teoria.
Organização do texto e uso correto da linguagem de programação (caso opte por Java).

Contexto para as próximas questões:

Imagine que você é responsável pelo gerenciamento de produtos em um pequeno supermercado. É preciso cadastrar cada item com nome, preço e quantidade disponível em estoque, bem como atualizar esses dados sempre que houver mudanças. Ao final, você deve exibir as informações do produto para ter um registro atualizado no sistema.

Exercício 2 Criando a Classe “Produto” (Com Contexto de Usuário)

Enunciado: Com base nessa história de usuário, vamos criar uma classe que represente um produto de supermercado. Sua tarefa é declarar a classe e os atributos:

Crie uma classe chamada Produto.
Insira nela, pelo menos, os atributos: nome (String), preco (double) e quantidadeEmEstoque (int).
Explique brevemente por que cada atributo é importante no contexto de gerenciamento de produtos.

Considerações:

Declaração correta dos atributos e criação da classe Produto.

Exercício 3 Métodos Básicos da Classe “Produto”

Enunciado: Dando continuidade ao contexto em que você é responsável pelo gerenciamento de produtos em um pequeno supermercado, agora vamos aprimorar a classe Produto adicionando métodos básicos de manipulação:

Implementar Método de Atualização de Preço
Crie um método chamado alterarPreco que receba um novo preço (do tipo double) e atualize o atributo preco do produto.
Implementar Método de Atualização de Quantidade
Crie um método chamado alterarQuantidade que receba um valor inteiro representando a nova quantidade e atualize o atributo quantidadeEmEstoque.
Exibir Informações do Produto
Crie um método chamado exibirInformacoes, que mostre (no console ou como retorno) o nome, o preço e a quantidade em estoque do produto, refletindo o estado atual do objeto.

Considerações:

Correta implementação dos métodos solicitados.
Clareza e objetividade no código, evidenciando como cada método cumpre sua função de atualizar ou exibir informações.
Utilização adequada dos atributos já criados na classe Produto.

Exercício 4 Testando a Classe “Produto”

Enunciado: Dando sequência ao contexto de gerenciamento de produtos em um pequeno supermercado, agora é hora de testar a classe Produto que você desenvolveu. Para isso:

Criar Classe de Teste ou Método main
Crie uma nova classe (por exemplo, AppProduto ou Main) ou utilize um método principal (main) em alguma classe existente.
Instanciar um Produto
Dentro do main, instancie (crie um objeto) da classe Produto.
Atribua valores iniciais aos atributos nome, preco e quantidadeEmEstoque.
Chamar os Métodos de Atualização
Chame os métodos alterarPreco e alterarQuantidade para modificar o preço e a quantidade em estoque do produto que você criou.
Exibir Informações
Por fim, chame o método exibirInformacoes para confirmar se as alterações foram aplicadas corretamente, exibindo as informações atualizadas do produto no console (ou retornando-as de alguma forma).

Considerações:

Criação correta de uma classe ou método principal que possa executar o código.
Instanciação da classe Produto e atribuição de valores iniciais.
Uso correto dos métodos implementados para atualizar e exibir as informações do produto.
Clareza na organização do código de teste (legibilidade e boa prática).

Exercício 5 Criando Métodos de Propriedade (Getters e Setters)

Enunciado: Continuando no contexto do pequeno supermercado que gerencia produtos, vamos criar métodos que permitam ler e alterar os valores dos atributos sem precisar acessá-los diretamente. Esses métodos são frequentemente chamados de “getters” e “setters” e ajudam a organizar o código, pois centralizam o modo como cada atributo pode ser modificado ou obtido.

Métodos “Get” (Leitura):
Crie um método que retorne o valor de cada atributo. Por exemplo:
getNome() deve retornar o valor de nome.
getPreco() deve retornar o valor de preco.
getQuantidadeEmEstoque() deve retornar o valor de quantidadeEmEstoque.
Métodos “Set” (Atualização):
Crie um método que receba um novo valor para cada atributo. Por exemplo:
setNome(String novoNome) deve atualizar o valor de nome.
setPreco(double novoPreco) deve atualizar o valor de preco.
setQuantidadeEmEstoque(int novaQuantidade) deve atualizar o valor de quantidadeEmEstoque.
Exemplo de Uso:
Mostre (no main ou em uma classe de teste) como invocar esses métodos de leitura e atualização.
Por exemplo, chame setPreco(3.75) e depois getPreco() para confirmar que o valor foi atualizado.

Observações:

Você não precisa, neste momento, utilizar modificadores de visibilidade (public, private, protected). Basta criar métodos simples de “get” e “set” para cada atributo.
Explique com suas próprias palavras por que esses métodos (getters e setters) podem ser úteis no código, mesmo que não esteja usando modificadores de acesso.

Considerações:

Criação de métodos de leitura (getters) e métodos de atualização (setters) para cada atributo.
Demonstração de uso desses métodos (chamada em um main ou classe de teste).
Clareza e objetividade na explicação sobre a função dos getters e setters no gerenciamento de produtos.

Exercício 6 Adicionando Construtores à Classe “Produto”

Enunciado: Você continua responsável pelo gerenciamento de produtos no pequeno supermercado. Agora, deseja facilitar a criação de novos produtos no sistema, definindo valores iniciais de maneira mais simples e organizada.

Criar Construtor
Na classe Produto, crie um construtor que receba parâmetros para inicializar obrigatoriamente os atributos nome, preco e quantidadeEmEstoque.
Descreva rapidamente como o construtor se comporta ao receber os valores.
Exemplificar o Uso
No método main ou em outra classe de teste, crie um objeto do tipo Produto usando o construtor que recebe parâmetros.
Atribua valores para nome, preco e quantidadeEmEstoque, e então exiba as informações do produto (usando o método exibirInformacoes ou métodos getters) para confirmar que os valores iniciais foram atribuídos corretamente.
Justificativa
Explique por que usar um construtor facilita a criação de objetos em relação a atribuir valores por vários métodos “set” ou chamadas separadas.

Considerações:

Declaração correta de um construtor que receba parâmetros na classe Produto.
Atribuição adequada dos atributos nome, preco e quantidadeEmEstoque dentro do construtor.
Demonstração clara do uso do construtor (instanciando um objeto, exibindo informações).
Clareza na explicação sobre a utilidade do construtor no contexto de criação de produtos.

Exercício 7 Modelando uma Conta Bancária

Enunciado: Imagine que você é responsável por criar um sistema simples de gerenciamento de contas bancárias. Esse sistema deverá cadastrar informações básicas sobre a conta, bem como realizar operações essenciais, como saque e depósito.

Criar a Classe Conta
Nome da classe: Conta (respeitando convenções Java).
A classe deve conter no mínimo os seguintes atributos:
titular (String) – representa o nome do dono da conta.
numero (int) – identifica a conta.
agencia (String) – identifica a agência bancária.
saldo (double) – indica o valor atualmente disponível na conta.
dataAbertura (String) – registra quando a conta foi aberta.

Exercício 8 Criando Métodos

Enunciado: Continuamos no cenário onde você é responsável por criar o sistema de gerenciamento de contas e agora você já definiu a Classe Conta. Vamos agora definir os métodos:

saca(double valor): recebe um valor como parâmetro e o retira do saldo da conta.
deposita(double valor): recebe um valor como parâmetro e o adiciona ao saldo da conta.
calculaRendimento(): não recebe nenhum parâmetro e devolve (retorna) o valor do saldo multiplicado por 0.1 (representando um rendimento mensal de 10%, por exemplo).

Exercício 9 Vamos testar nossa classe

Enunciado: Continuamos no cenário aonde você é responsável por criar o sistema de gerenciamento de contas e agora você já definiu a Classe Conta. Vamos agora criar a Classe de Teste! Crie uma classe (por exemplo, TestaConta) que contenha o método main. Dentro de main:

Instancie um objeto da classe Conta.
Atribua valores aos atributos da conta (titular, número, agência, saldo, data de abertura).
Chame os métodos saca, deposita e calculaRendimento para testar o comportamento da conta.
Exiba informações relevantes (por exemplo, saldo antes e depois de cada operação, valor do rendimento etc.) para verificar se tudo está funcionando corretamente.

Observações:

Utilize a convenção de nomes e padrões Java (por exemplo, nomes de métodos iniciando em minúsculo, nomes de classes iniciando em maiúsculo etc.).
Você pode criar a classe Conta e a classe de teste (TestaConta) em arquivos separados ou no mesmo arquivo. Para organização, recomendamos separar.
Caso opte por separar, lembre-se de compilar ambas as classes (por exemplo, javac Conta.java TestaConta.java). Em seguida, rode a classe com o método main (java TestaConta).

Considerações:

Presença e correta implementação de todos os atributos solicitados.
Funcionamento adequado dos métodos saca, deposita e calculaRendimento.
Clareza e objetividade no código, seguindo convenções Java.
Execução correta do programa de teste (instanciação e uso dos métodos da classe Conta).

Exercício 10 Definindo Classes para Formas Geométricas

Enunciado: Você está desenvolvendo um sistema simples para calcular áreas (para figuras 2D) e volumes (para figuras 3D). Ainda não foram apresentados conceitos avançados (como herança), então você criará classes independentes para cada forma.

Classes Iniciais:
Crie a classe Circulo com, no mínimo, o atributo raio (do tipo double).
Crie a classe Esfera com, no mínimo, o atributo raio (do tipo double).
Definição de Atributos:
Explique por que o atributo raio é fundamental para cada uma dessas classes.
Não é preciso criar métodos de cálculo ainda – apenas estruture as classes e seus atributos.

Observações:

As classes podem ficar em arquivos separados (Circulo.java e Esfera.java) ou no mesmo arquivo.
Utilize convenções básicas de Java (nomes de classes iniciando em maiúscula, etc.).

Considerações:

Declaração correta das classes Circulo e Esfera.
Presença e clareza na definição do(s) atributo(s) necessário(s).
Código organizado e fácil de ler, sem uso de conceitos não ensinados (como herança ou polimorfismo).

Exercício 11 Criando Métodos de Cálculo

Enunciado: Agora, você adicionará métodos para calcular a área do círculo e o volume da esfera:

Cálculo da Área do Círculo
Na classe Circulo, crie um método (por exemplo, calcularArea()) que retorne a área, dada por π * (raio * raio).
Cálculo do Volume da Esfera
Na classe Esfera, crie um método (por exemplo, calcularVolume()) que retorne o volume, dado por (4.0 / 3.0) * π * (raio * raio * raio).
Valor de π
Você pode usar Math.PI (fornecido pelo Java) ou declarar uma constante (por exemplo, static final double PI = 3.14159;), conforme desejar.

Observações:

Lembre-se de retornar o resultado dos cálculos ao invés de apenas imprimir.
Não utilize recursos avançados (como herança), apenas métodos simples dentro de cada classe.

Considerações:

Métodos de cálculo corretos e funcionais (calcularArea() no círculo, calcularVolume() na esfera).
Retorno adequado dos valores (sem prints dentro dos métodos, a menos que queira exibir para conferência).

Exercício 12 Testando as Classes de Figuras

Enunciado: Finalmente, é hora de testar as classes que você criou. Crie uma classe de teste (por exemplo, TestaFiguras) com um método main para:

Instanciar um objeto da classe Circulo e outro da classe Esfera.
Atribuir valores de raio (ex.: 3.0 para o círculo, 5.0 para a esfera).
Chamar os métodos de cálculo (calcularArea() e calcularVolume()).
Exibir os resultados no console para verificar se os métodos estão funcionando corretamente.

Observações:

Caso opte por arquivos separados, lembre-se de compilar ambos (por exemplo, javac Circulo.java Esfera.java TestaFiguras.java) e depois rodar a classe que tem o main.
Não use conceitos como herança; limite-se a instanciar e chamar os métodos.

Considerações:

Criação de uma classe de teste com método main.
Instanciação correta das classes Circulo e Esfera, atribuindo valores ao atributo raio.
Chamadas corretas aos métodos de cálculo, exibindo resultados plausíveis.
Organização e legibilidade do código, seguindo convenções Java.

Assim que terminar, salve seu trabalho em PDF nomeando o arquivo conforme a regra “nome_sobrenome_DR1_TP3.PDF” e poste como resposta a este TP.

## Rubrica

Níveis de cada item: **Não demonstrou o item de rubrica** / **Demonstrou o item de rubrica**.

3. Escrever programas em Java que utilizem classes e objetos  
O aluno executou corretamente 25% dos exercícios da lista proposta? **25%**

3. Escrever programas em Java que utilizem classes e objetos  
O aluno executou corretamente 50% dos exercícios da lista proposta? **50%**

3. Escrever programas em Java que utilizem classes e objetos  
O aluno executou corretamente 75% dos exercícios da lista proposta? **75%**

3. Escrever programas em Java que utilizem classes e objetos  
O aluno executou corretamente 100% dos exercícios da lista proposta? **100%**
