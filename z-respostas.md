/doc O que é o KernelBot?
Kernel · 10:06
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 01 visao geral
+1 ficheiro
O KernelBot (também chamado ACL — Agente de Contexto Local) é um tutor de chat que responde com base no material das suas aulas indexadas — Python, SQL, Projeto Bloco, planejamento de carreira, etc. — e não na internet aberta [Fonte: db:doc/00-inicio-publico] [Fonte: db:doc/19-faq-usuario].

Na prática, ele busca trechos relevantes numa base indexada (MySQL), monta a resposta com um modelo de linguagem e cita fontes quando possível, no formato [Fonte: db:disciplina/slug-da-aula] [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/01-visao-geral].

O que faz:

Explica conceitos das disciplinas com referência ao material do curso
Continua a conversa (memória local no browser)
Avisa quando o tema foge do que está indexado
O que não faz:

Substituir professor, portal da faculdade ou regulamento oficial
Entregar gabarito integral de TP/AT
Revelar senhas, API keys ou instruções internas do sistema [Fonte: db:doc/00-inicio-publico]
Para usar bem: combine disciplina + pergunta, ou um comando no início (/python, /visualizacao-sql, /projeto-bloco…) [Fonte: db:doc/19-faq-usuario]. Quer destrinchar alguma disciplina em específico?

Você · 10:06
/doc Onde fica guardado o histórico da minha conversa?
Kernel · 10:06
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 01 visao geral
+2 ficheiros
O histórico fica no seu browser, não numa conta de login no servidor [Fonte: db:doc/19-faq-usuario].

Onde exactamente

Chave localStorage: acl_conversation_v1 [Fonte: db:doc/08-frontend-ui] [Fonte: db:doc/07-apis-e-sse]
Estrutura guardada: session_id + lista de turnos (role, texto, fontes opcionais, timestamp) [Fonte: db:doc/08-frontend-ui]
O que isso implica na prática

Situação	O que acontece
Mesma aba / refresh / fechar e reabrir o browser	O Kernel lembra a conversa (mesmo computador, mesma origem) [Fonte: db:doc/19-faq-usuario]
Outro computador ou browser	Não partilha histórico [Fonte: db:doc/19-faq-usuario]
Botão Nova conversa (header)	Apaga o histórico local, gera novo session_id e limpa o pin [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/08-frontend-ui]
/reset ou /limpar	Limpa só o tema fixado no servidor — não apaga o histórico visual sozinho [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/08-frontend-ui]
Envio à API
A cada pergunta, o browser manda os turnos recentes no campo history do POST /chat. Só os mais recentes entram no prompt (truncagem automática — na UI, até ~12 turnos) [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/07-apis-e-sse] [Fonte: db:doc/08-frontend-ui].

Resumindo: local no seu browser; o servidor usa só um pedaço recente para contexto, mas não é um “backup na nuvem” da conversa inteira. Quer saber como limpar tudo de uma vez ou só mudar de disciplina?

/doc O que é o KernelBot?
Kernel · 10:05
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 01 visao geral
+1 ficheiro
Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.
O KernelBot (também chamado ACL — Agente de Contexto Local) é um tutor de chat que responde com base no material das suas aulas indexadas — Python, SQL, Projeto Bloco, planejamento de carreira, etc. — e não na internet aberta [Fonte: db:doc/00-inicio-publico] [Fonte: db:doc/19-faq-usuario].

Na prática, ele busca trechos relevantes numa base indexada (MySQL), monta a resposta com um modelo de linguagem e cita fontes quando possível, no formato [Fonte: db:disciplina/slug-da-aula] [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/01-visao-geral].

O que faz:

Explica conceitos das disciplinas com referência ao material do curso
Continua a conversa (memória local no browser)
Avisa quando o tema foge do que está indexado
O que não faz:

Substituir professor, portal da faculdade ou regulamento oficial
Entregar gabarito integral de TP/AT
Revelar senhas, API keys ou instruções internas do sistema [Fonte: db:doc/00-inicio-publico]
Para usar bem: combine disciplina + pergunta, ou um comando no início (/python, /visualizacao-sql, /projeto-bloco…) [Fonte: db:doc/19-faq-usuario]. Quer destrinchar alguma disciplina em específico?

/doc Quais comandos posso usar no início da mensagem para focar numa disciplina?
Kernel · 10:05
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 01 visao geral
+2 ficheiros
Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.
No início da mensagem, estes comandos focam o Kernel num silo (disciplina) — use no começo, seguido da pergunta [Fonte: db:doc/19-faq-usuario]:

Comando	Foco
/python	Python
/visualizacao-sql	Visualização de dados e SQL
/projeto-bloco	Projeto Bloco
/planejamento-curso-carreira	Graduação, carreira, competências
/doc	Documentação do bot (quando indexada)
Exemplo:

/python E o que é f-string?
Relacionados (não focam disciplina):

/reset ou /limpar — limpam o tema fixado (pin), útil quando mudou de assunto ou o rodapé avisa que as fontes misturam contextos [Fonte: db:doc/19-faq-usuario].
Se já estiver num tema fixado (badge Continuando: …), pode continuar com follow-ups normais no mesmo silo, ou usar o comando da nova disciplina — ou /reset — para mudar [Fonte: db:doc/19-faq-usuario].

/doc O que faz o comando /reset?
Kernel · 10:05
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 01 visao geral
+2 ficheiros
O /reset (ou /limpar) limpa o tema fixado no servidor — o “pin” que mantém a disciplina entre perguntas de follow-up (aquele badge tipo Continuando: … no campo de entrada). [Fonte: db:doc/19-faq-usuario]

O que muda na prática
Situação	Efeito do /reset
Você estava num tema fixo (ex.: SQL) e quer mudar de assunto	O pin some; a próxima pergunta não fica presa ao tema anterior
Rodapé avisa que fontes misturam contextos	/reset (ou o comando da disciplina certa, ex. /python …) recentra a busca [Fonte: db:doc/19-faq-usuario]
Histórico da conversa na tela	Não apaga — as mensagens antigas continuam visíveis [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/08-frontend-ui]
O que não faz sozinho
Não limpa o histórico visual da conversa no browser.
Para começar do zero (apagar turnos + novo ID de sessão + limpar pin), use o botão Nova conversa no header — ele faz tudo isso de uma vez. [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/08-frontend-ui]
Como usar
Escreva no início da mensagem:

/reset
ou, se quiser já ir para outra disciplina:

/python Me explica listas
(Comando de disciplina também substitui o pin anterior.) [Fonte: db:doc/19-faq-usuario]

Resumo: /reset = “esquece o tema que estava fixado no servidor”. Para apagar também o que você vê na tela, precisa de Nova conversa.

/doc O Kernel pode me dar o gabarito completo do trabalho prático?
Kernel · 10:05
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 01 visao geral
+2 ficheiros
Não — o Kernel não entrega o gabarito integral de TP ou AT [Fonte: db:doc/00-inicio-publico].

Ele explica conceitos com base no material das aulas, ajuda a entender o raciocínio e orienta estudo. Não substitui o professor, o portal da faculdade nem o regulamento oficial [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/00-inicio-publico].

O que dá para pedir em vez disso:

Explicar um conceito que o TP exige (ex.: loops, GROUP BY, estrutura do projeto)
Ajudar a entender um enunciado ou um erro no seu código
Mostrar um exemplo genérico parecido, sem ser a resposta pronta do trabalho
Se quiser, manda a disciplina e o trecho do enunciado que está travando — a gente destrincha a ideia, não a cola.

/doc Onde fica guardado o histórico da minha conversa?
Kernel · 10:06
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 01 visao geral
+2 ficheiros
O histórico fica no seu browser, não numa conta de login no servidor [Fonte: db:doc/19-faq-usuario].

Onde exactamente

Chave localStorage: acl_conversation_v1 [Fonte: db:doc/08-frontend-ui] [Fonte: db:doc/07-apis-e-sse]
Estrutura guardada: session_id + lista de turnos (role, texto, fontes opcionais, timestamp) [Fonte: db:doc/08-frontend-ui]
O que isso implica na prática

Situação	O que acontece
Mesma aba / refresh / fechar e reabrir o browser	O Kernel lembra a conversa (mesmo computador, mesma origem) [Fonte: db:doc/19-faq-usuario]
Outro computador ou browser	Não partilha histórico [Fonte: db:doc/19-faq-usuario]
Botão Nova conversa (header)	Apaga o histórico local, gera novo session_id e limpa o pin [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/08-frontend-ui]
/reset ou /limpar	Limpa só o tema fixado no servidor — não apaga o histórico visual sozinho [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/08-frontend-ui]
Envio à API
A cada pergunta, o browser manda os turnos recentes no campo history do POST /chat. Só os mais recentes entram no prompt (truncagem automática — na UI, até ~12 turnos) [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/07-apis-e-sse] [Fonte: db:doc/08-frontend-ui].

Resumindo: local no seu browser; o servidor usa só um pedaço recente para contexto, mas não é um “backup na nuvem” da conversa inteira. Quer saber como limpar tudo de uma vez ou só mudar de disciplina?

/doc O que significa [Fonte: db:python/variaveis-tipos-estilo-python] na resposta?
Kernel · 10:06
Tema fixado em «19 faq usuario». A pergunta parece ser de Python — use /python no início ou /reset para limpar o contexto fixado.
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 01 visao geral
+2 ficheiros
[Fonte: db:python/variaveis-tipos-estilo-python] indica que a resposta usou um trecho indexado de uma aula — não algo inventado nem buscado na internet aberta [Fonte: db:doc/19-faq-usuario].

A leitura é em duas partes:

Parte	Significado
python	Disciplina (silo)
variaveis-tipos-estilo-python	Slug da aula — o identificador daquele conteúdo na base
Ou seja: a resposta se apoiou no material da aula de Python sobre variáveis, tipos e estilo [Fonte: db:doc/19-faq-usuario].

Por que isso aparece?
O Kernel monta respostas a partir do material das aulas indexadas (MySQL) e cita a origem quando consegue [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/00-inicio-publico].

E se não aparecer fonte?
Se o tema estiver fora do material indexado, o Kernel deve dizer que não encontrou na base — em vez de inventar uma aula [Fonte: db:doc/19-faq-usuario].

Quer que eu explique outro badge ou aviso do rodapé (confiança, «Continuando…», etc.)?


/doc O que é o tema fixado ou o badge Continuando no chat?
Kernel · 10:06
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 01 visao geral
+2 ficheiros
O tema fixado (ou pin) é quando o Kernel “lembra” em que disciplina ou assunto você estava, para que perguntas curtas de follow-up façam sentido sem você repetir tudo. [Fonte: db:doc/19-faq-usuario]

O badge Continuando: …
Depois de algumas perguntas no mesmo fio, o chat pode fixar um tema — por exemplo, SQL. Aí aparece um badge tipo Continuando: … no campo de entrada, avisando que a próxima mensagem continua naquele contexto. [Fonte: db:doc/19-faq-usuario]

Isso permite coisas como:

Você: Como funciona GROUP BY com HAVING?
Depois: E o HAVING sozinho? — sem precisar dizer “em SQL” de novo.
O que fazer em cada situação
Situação	O que fazer
Quer continuar no mesmo tema	Pergunte normalmente (“E no meu exemplo?”) [Fonte: db:doc/19-faq-usuario]
Mudou de disciplina (SQL → Python)	Use /python … ou /reset [Fonte: db:doc/19-faq-usuario]
O rodapé avisa que as fontes misturam contextos	/reset ou o comando da disciplina certa [Fonte: db:doc/19-faq-usuario]
Onde isso “mora” (sem misturar com histórico)
São duas coisas diferentes:

Tema fixado (pin) — fica no servidor, ligado ao seu session_id. É isso que o /reset limpa. [Fonte: db:doc/08-frontend-ui] [Fonte: db:doc/19-faq-usuario]
Histórico da conversa — fica no browser (localStorage). Sobrevive a refresh e fechar aba, mas é independente do pin. [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/08-frontend-ui]
O pin também tem um tempo de vida limitado — após alguns turnos (ACL_PINNED_MAX_TURNS, default 5), ele vai expirando sozinho. [Fonte: db:doc/08-frontend-ui]

Resumo em uma frase
Continuando: … = “estou assumindo que você ainda está neste tema/disciplina”. Se mudou de assunto, manda /reset ou já abre com o comando certo (/python, /visualizacao-sql, etc.).  

/doc O que faz o comando /reset?
Kernel · 10:06
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 01 visao geral
+2 ficheiros
O /reset (ou /limpar) limpa o tema fixado no servidor — o “pin” que mantém a disciplina entre perguntas de follow-up (aquele badge tipo Continuando: … no campo de entrada). [Fonte: db:doc/19-faq-usuario]

O que muda na prática
Situação	Efeito do /reset
Você estava num tema fixo (ex.: SQL) e quer mudar de assunto	O pin some; a próxima pergunta não fica presa ao tema anterior
Rodapé avisa que fontes misturam contextos	/reset (ou o comando da disciplina certa, ex. /python …) recentra a busca [Fonte: db:doc/19-faq-usuario]
Histórico da conversa na tela	Não apaga — as mensagens antigas continuam visíveis [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/08-frontend-ui]
O que não faz sozinho
Não limpa o histórico visual da conversa no browser.
Para começar do zero (apagar turnos + novo ID de sessão + limpar pin), use o botão Nova conversa no header — ele faz tudo isso de uma vez. [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/08-frontend-ui]
Como usar
Escreva no início da mensagem:

/reset
ou, se quiser já ir para outra disciplina:

/python Me explica listas
(Comando de disciplina também substitui o pin anterior.) [Fonte: db:doc/19-faq-usuario]

Resumo: /reset = “esquece o tema que estava fixado no servidor”. Para apagar também o que você vê na tela, precisa de Nova conversa.

Você · 10:06
/doc O que é o tema fixado ou o badge Continuando no chat?
Kernel · 10:06
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 01 visao geral
+2 ficheiros
O tema fixado (ou pin) é quando o Kernel “lembra” em que disciplina ou assunto você estava, para que perguntas curtas de follow-up façam sentido sem você repetir tudo. [Fonte: db:doc/19-faq-usuario]

O badge Continuando: …
Depois de algumas perguntas no mesmo fio, o chat pode fixar um tema — por exemplo, SQL. Aí aparece um badge tipo Continuando: … no campo de entrada, avisando que a próxima mensagem continua naquele contexto. [Fonte: db:doc/19-faq-usuario]

Isso permite coisas como:

Você: Como funciona GROUP BY com HAVING?
Depois: E o HAVING sozinho? — sem precisar dizer “em SQL” de novo.
O que fazer em cada situação
Situação	O que fazer
Quer continuar no mesmo tema	Pergunte normalmente (“E no meu exemplo?”) [Fonte: db:doc/19-faq-usuario]
Mudou de disciplina (SQL → Python)	Use /python … ou /reset [Fonte: db:doc/19-faq-usuario]
O rodapé avisa que as fontes misturam contextos	/reset ou o comando da disciplina certa [Fonte: db:doc/19-faq-usuario]
Onde isso “mora” (sem misturar com histórico)
São duas coisas diferentes:

Tema fixado (pin) — fica no servidor, ligado ao seu session_id. É isso que o /reset limpa. [Fonte: db:doc/08-frontend-ui] [Fonte: db:doc/19-faq-usuario]
Histórico da conversa — fica no browser (localStorage). Sobrevive a refresh e fechar aba, mas é independente do pin. [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/08-frontend-ui]
O pin também tem um tempo de vida limitado — após alguns turnos (ACL_PINNED_MAX_TURNS, default 5), ele vai expirando sozinho. [Fonte: db:doc/08-frontend-ui]

Resumo em uma frase
Continuando: … = “estou assumindo que você ainda está neste tema/disciplina”. Se mudou de assunto, manda /reset ou já abre com o comando certo (/python, /visualizacao-sql, etc.).

/doc O que é o KernelBot?
Kernel · 10:06
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 01 visao geral
+1 ficheiro
O KernelBot (também chamado ACL — Agente de Contexto Local) é um tutor de chat que responde com base no material das suas aulas indexadas — Python, SQL, Projeto Bloco, planejamento de carreira, etc. — e não na internet aberta [Fonte: db:doc/00-inicio-publico] [Fonte: db:doc/19-faq-usuario].

Na prática, ele busca trechos relevantes numa base indexada (MySQL), monta a resposta com um modelo de linguagem e cita fontes quando possível, no formato [Fonte: db:disciplina/slug-da-aula] [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/01-visao-geral].

O que faz:

Explica conceitos das disciplinas com referência ao material do curso
Continua a conversa (memória local no browser)
Avisa quando o tema foge do que está indexado
O que não faz:

Substituir professor, portal da faculdade ou regulamento oficial
Entregar gabarito integral de TP/AT
Revelar senhas, API keys ou instruções internas do sistema [Fonte: db:doc/00-inicio-publico]
Para usar bem: combine disciplina + pergunta, ou um comando no início (/python, /visualizacao-sql, /projeto-bloco…) [Fonte: db:doc/19-faq-usuario]. Quer destrinchar alguma disciplina em específico?

Você · 10:06
/doc Onde fica guardado o histórico da minha conversa?
Kernel · 10:06
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 01 visao geral
+2 ficheiros
O histórico fica no seu browser, não numa conta de login no servidor [Fonte: db:doc/19-faq-usuario].

Onde exactamente

Chave localStorage: acl_conversation_v1 [Fonte: db:doc/08-frontend-ui] [Fonte: db:doc/07-apis-e-sse]
Estrutura guardada: session_id + lista de turnos (role, texto, fontes opcionais, timestamp) [Fonte: db:doc/08-frontend-ui]
O que isso implica na prática

Situação	O que acontece
Mesma aba / refresh / fechar e reabrir o browser	O Kernel lembra a conversa (mesmo computador, mesma origem) [Fonte: db:doc/19-faq-usuario]
Outro computador ou browser	Não partilha histórico [Fonte: db:doc/19-faq-usuario]
Botão Nova conversa (header)	Apaga o histórico local, gera novo session_id e limpa o pin [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/08-frontend-ui]
/reset ou /limpar	Limpa só o tema fixado no servidor — não apaga o histórico visual sozinho [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/08-frontend-ui]
Envio à API
A cada pergunta, o browser manda os turnos recentes no campo history do POST /chat. Só os mais recentes entram no prompt (truncagem automática — na UI, até ~12 turnos) [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/07-apis-e-sse] [Fonte: db:doc/08-frontend-ui].

Resumindo: local no seu browser; o servidor usa só um pedaço recente para contexto, mas não é um “backup na nuvem” da conversa inteira. Quer saber como limpar tudo de uma vez ou só mudar de disciplina?

doc O KernelBot usa busca semântica ou embeddings como o ChatGPT?
Kernel · 10:09
Documentação · 01 visao geral
Documentação · 00 inicio publico
Documentação · 17 prompts referencia
Documentação · 06 gates e decisoes
Não. O KernelBot não usa busca semântica nem embeddings para recuperar o material das aulas.

O que ele faz é recuperação léxica com BM25 sobre o conteúdo indexado no MySQL — ou seja, casa termos da sua pergunta com o texto dos chunks, não “entende” significado por vetores como muitos sistemas com embeddings. [Fonte: db:doc/01-visao-geral]

Na prática isso implica:

Aspecto	KernelBot (ACL)
Tipo de busca	BM25 léxico
Embeddings / semântica	Não
Fonte do índice	MySQL (knowledge.content), busca em RAM no processo
LLM	Entra em (quase) todos os turnos para gerar a resposta — mas o retrieval que traz as fontes é léxico, não semântico [Fonte: db:doc/01-visao-geral]
Limitação honesta do material: sinónimos e paráfrases podem falhar se o termo exacto não existir no chunk — é consequência directa de não haver busca semântica. [Fonte: db:doc/01-visao-geral]

Extensão pedagógica (fora do material indexado):
Muitos chats “genéricos” (incluindo variantes do ChatGPT em diferentes modos) podem combinar recuperação semântica, browsing ou conhecimento pré-treinado. O KernelBot foi desenhado de propósito para o material da faculdade com um trade-off: mais controlo e menos alucinação sobre o corpus, em troca de recall pior em perguntas vagas ou com vocabulário diferente do das aulas.

Se quiseres, posso explicar como formular perguntas que o BM25 apanha melhor (termos das aulas, comandos /python, /doc, etc.).

/doc Qual a diferença entre /reset e o botão Nova conversa?
Kernel · 10:10
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Boa pergunta — são parecidos, mas não fazem a mesma coisa.

/reset (ou /limpar)
Limpa só o tema fixado (pin) no servidor. Exemplo: você estava em SQL e quer mudar para Python sem arrastar o contexto anterior.

O histórico continua visível na tela
O localStorage não é apagado
O session_id permanece o mesmo
Para apagar o histórico visual, o material indica usar Nova conversa — /reset sozinho não faz isso [Fonte: db:doc/19-faq-usuario].

Botão Nova conversa (header)
É o reset completo da conversa no browser:

Apaga o histórico local (localStorage, chave acl_conversation_v1)
Gera um novo session_id
Também limpa o pin (envia /reset ao servidor)
Ou seja: conversa nova de verdade, do zero [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/08-frontend-ui].

Quando usar cada um
Situação	O que usar
Mudou de disciplina (SQL → Python) mas quer manter o histórico na tela	/reset ou comando da disciplina (/python …)
Quer começar do zero, sem mensagens antigas	Nova conversa
Rodapé avisa que fontes misturam contextos	/reset ou Nova conversa, conforme quiser manter ou não o histórico
Resumo: /reset = solta o tema fixado; Nova conversa = histórico novo + sessão nova + pin limpo. Se quiser zerar tudo, use o botão. Se só quiser trocar de silo mantendo as mensagens na tela, /reset basta.

/doc O que é a política de grounding anchored e o que significa Modo didático na interface?
Kernel · 10:10
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 17 prompts referencia
+1 ficheiro
Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.
Vou cruzar o material do FAQ com a documentação de gates e da UI para explicar anchored e o que é “Modo didático”.
São duas peças do mesmo puzzle: a política de grounding define como o Kernel usa o material das aulas; o badge Modo didático é só o rótulo na interface quando essa política está activa.

Política anchored (grounding)
É o default do projeto (ACL_GROUNDING_POLICY=anchored) [Fonte: db:doc/06-gates-e-decisoes].

Ideia central: os trechos [Fonte: …] do RAG são evidência primária — não a única fonte de verdade, mas o ponto de partida obrigatório para factos do curso.

Aspecto	Comportamento em anchored
Factos do curso	Ancorados nos trechos; cite a fonte quando usar
Lacunas	Se o excerto não cobre, o Kernel declara — não inventa
Extensão pedagógica	Permitida, desde que rotulada explicitamente: Extensão pedagógica (fora do material indexado):
Pós-geração	Se a checagem automática detectar desvio, emite aviso suave (post_generation_advisory) — a resposta é mantida [Fonte: db:doc/06-gates-e-decisoes]
Contraste com strict	Em strict, os trechos são SSOT absoluto; desvio gera override destrutivo com disclaimer «Revisão» [Fonte: db:doc/06-gates-e-decisoes] [Fonte: db:doc/08-frontend-ui]
Em resumo: anchored equilibra fidelidade ao material com didática — pode explicar com analogias ou estrutura extra, mas separando claramente o que veio das aulas do que é complemento.

O prompt injectado ao modelo vem de grounding_anchored.txt (excepto em desambiguação, que usa outro contrato) [Fonte: db:doc/06-gates-e-decisoes].

Badge «Modo didático» na interface
É o rótulo visual da política anchored no meta da resposta (grounding_policy no [ACL_META]) [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/08-frontend-ui].

O que significa para ti:

O Kernel está a operar no modo didático — pode complementar o material indexado com extensão pedagógica rotulada.
Não é um toggle que mudas no chat; reflecte a configuração do servidor.
Badges relacionados que podes ver junto:
Complemento pedagógico — a resposta incluiu bloco de extensão explícito [Fonte: db:doc/19-faq-usuario]
Aviso amarelo suave — revisão sugerida, mas resposta mantida (anchored) [Fonte: db:doc/19-faq-usuario]
Revisão (modo rigoroso) — só no strict, quando a resposta pode ter saído do escopo [Fonte: db:doc/19-faq-usuario]
Síntese rápida
anchored  →  badge «Modo didático»  →  aulas primeiro + extensão rotulada permitida
strict    →  badge «Modo rigoroso»   →  só o que está nos trechos; desvio = «Revisão»
Se quiseres, no próximo turno posso contrastar anchored com hybrid ou explicar quando aparece o aviso amarelo vs. os chips de desambiguação.



/doc Quantas palavras tem cada chunk BM25 e qual o overlap entre janelas?
Kernel · 10:10
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 17 prompts referencia
+3 ficheiros
Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.
A resposta está na documentação de chunking do BM25 (Opção B2).

Tamanho do chunk e overlap
Parâmetro	Valor	Significado
Palavras por chunk	500	Tamanho de cada janela sobre o clean_body da aula
Overlap	50	Palavras que se repetem entre janelas consecutivas
Esses valores vêm das constantes DB_CHUNK_WORDS e DB_CHUNK_OVERLAP em engine/database.py [Fonte: db:doc/05-bm25-chunking].

Como isso funciona na prática
O pipeline divide o texto assim:

MySQL guarda 1 row por aula (documento unificado).
Em RAM, o KernelBot faz _chunk_text com janelas de 500 palavras e 50 de overlap.
O chunk 0 inclui título + bloco meta + primeiras ~500 palavras do body; chunks ≥1 são só continuação do body (sem repetir meta) — isso é a Opção B2 [Fonte: db:doc/05-bm25-chunking].
Resumo: cada chunk BM25 tem 500 palavras, com 50 palavras de overlap entre janelas vizinhas.    

/doc Por que os metadados léxicos B2 vão só no chunk 0 e não em todos os chunks?
Kernel · 10:10
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 17 prompts referencia
+3 ficheiros
Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.
Boa pergunta — isso é decisão de engenharia de busca, não só de organização do texto.

Ideia central
No Opção B2, o bloco meta léxico (conceitos, keywords, objetivos da ISS) entra só no chunk 0 de cada aula. Os chunks seguintes carregam título + continuação do corpo, sem repetir o meta [Fonte: db:doc/05-bm25-chunking].

O motivo: evitar colapso do IDF no BM25 dentro da mesma aula.

O que acontece se o meta for em todos os chunks
Cada aula vira vários “documentos” no mini-índice BM25 (um por chunk). Se a keyword transformers está no header/meta e esse bloco se repete em todos os chunks:

a palavra aparece em N chunks da mesma aula;
o IDF trata isso como termo ultra-comum dentro daquele silo → tende a 0;
os scores ficam nulos ou inúteis;
o gate pode cair em insufficient_context mesmo com a aula certa no índice [Fonte: db:doc/05-bm25-chunking] [Fonte: db:doc/11-enriquecimento-lexico-b2].
Comparativo documentado:

Abordagem	Query tipo transformers (keyword no meta)
B1 — meta em todos os chunks	~4 scores ≈ 0
B2 — meta só no chunk 0	chunk 0 > 0, outros 0
Ou seja: com B2, a keyword aparece uma vez por aula → o IDF continua útil → o chunk 0 ganha score quando a busca é por termo léxico [Fonte: db:doc/05-bm25-chunking].

E quando o termo está no meio da aula?
Aí o chunk certo é o que contém o trecho no body (chunk ≥1), não o 0. O B2 não prejudica isso — pelo contrário, separa bem:

busca por keyword/conceito do meta → chunk 0;
busca por conteúdo só no corpo → chunk do meio/fim da aula [Fonte: db:doc/05-bm25-chunking].
Trade-off consciente
O objetivo de negócio do enriquecimento léxico B2 é melhorar recall BM25 para termos dos JSONs da ISS (keywords, concepts, learning_objectives, etc.) sem relaxar os gates de hard stop [Fonte: db:doc/11-enriquecimento-lexico-b2].

O custo: se a query recuperar só chunks ≥1, o meta pode não ir para o prompt do LLM na decisão actual (recomendação A). Isso está no backlog como melhoria futura [Fonte: db:doc/05-bm25-chunking].

Síntese
Meta em todos os chunks = duplicação artificial → IDF zerado → busca quebra.
Meta só no chunk 0 = recall OK para termos léxicos + chunks do body continuam funcionando para o meio da aula.

Se quiser, no próximo turno dá para destrinchar o formato exacto do bloco meta indexado ou o fluxo MySQL → RAM → BM25.

/doc O que é index_gap no retrieval e quando acontece?
Kernel · 10:10
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 17 prompts referencia
+3 ficheiros
Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.
Buscando na documentação e no código quando index_gap é disparado no retrieval.
index_gap é um sinal de lacuna entre catálogo e índice — não um gate BM25 clássico.

O que é
É um reason de decisão que significa: a sua pergunta bate com confiança numa aula do catálogo ISS (lessons.json / search-index.json), mas essa aula ainda não está no índice de busca (MySQL → chunks BM25 em RAM) [Fonte: db:doc/15-glossario] [Fonte: db:doc/06-gates-e-decisoes].

Em termos práticos: o Kernel sabe qual aula você quer, mas não tem o texto indexado para buscar trechos.

Quando acontece
O fluxo é este:

O catálogo lexical está activo (ACL_CATALOG_ENABLED) [Fonte: db:doc/10-integracao-iss-fase5b].
A query faz match confiante no catálogo (is_confident()).
A chave da aula (discipline:slug) não está no conjunto de chaves indexadas (fetch_indexed_lesson_keys()).
Isso é detectado em engine/context.py — não em build_decision() do BM25 [Fonte: db:doc/06-gates-e-decisoes] [Fonte: db:doc/04-dados-e-mysql].

Cenários típicos
Situação	reason provável
/python sobre aula que existe no ISS mas não foi ingerida	index_gap [Fonte: db:doc/13-staging-testes]
Pergunta sobre AT/TP fora do material indexado	insufficient_context ou index_gap [Fonte: db:doc/13-staging-testes]
Aula indexada, BM25 encontra chunks	ok (ou outro gate normal)
O glossário resume como drift: divergência catálogo ↔ chaves indexadas [Fonte: db:doc/15-glossario].

O que o Kernel faz (comportamento)
Ponto importante: index_gap não bloqueia o LLM na configuração actual.

Aspecto	Comportamento
LLM chamado?	Sim — allow_generation=true, decision=answer [Fonte: db:doc/06-gates-e-decisoes]
RAG BM25	Continua normalmente com o que encontrar
Papel do index_gap	Advisory — aviso no meta/UI, não hard stop de retrieval [Fonte: db:doc/06-gates-e-decisoes]
UI	Badge advisory; o componente IndexGapAlert só aparece se allow_generation=false (hard stop estruturado) [Fonte: db:doc/08-frontend-ui]
Ou seja: o modelo pode responder, mas o sistema avisa que a aula-alvo do catálogo não está no índice. A resposta pode vir de chunks fracos ou de outras fontes — daí o advisory.

Diferença de insufficient_context
index_gap	insufficient_context
Origem	Catálogo ISS vs índice MySQL/RAM	Gate BM25 (build_decision)
Condição	Match confiante no catálogo, chave ausente no índice	Sem hits ou top_score < MIN_SCORE
Sabe qual aula?	Sim (catálogo identificou)	Não necessariamente
Resumo
index_gap = “essa aula existe no currículo ISS, mas ainda não foi indexada no KernelBot”. Acontece quando o catálogo lexical identifica a aula com confiança e a chave discipline:slug falta no índice MySQL/RAM. O LLM ainda gera resposta; o sistema sinaliza a lacuna para você (e para operadores via drift em /health/catalog).

Se quiser, no próximo turno posso detalhar como corrigir isso operacionalmente (/reload, ingest ISS) — mas isso exigiria trechos da wiki de staging/integração que não estão neste turno.



/doc Como a documentação da wiki entra no MySQL para o comando /doc funcionar?
Kernel · 10:10
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 17 prompts referencia
+3 ficheiros
Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.
Vou localizar na wiki e no código como a documentação é ingerida no MySQL para o silo /doc.
O /doc só funciona porque a wiki não fica só em ficheiros — ela passa por um pipeline de ingestão até ao MySQL e, depois, o BM25 em memória a indexa como silo doc.

Fluxo em 4 passos
flowchart LR
  A["docs/wiki/*.md
(SSOT)"] --> B["bin/ingest-wiki-doc.sh"]
  B --> C["engine/wiki_doc.py
UPSERT MySQL"]
  C --> D["knowledge\ndiscipline=doc"]
  D --> E["/reload ou restart
BM25 rebuild"]
  E --> F["/doc pergunta
→ db:doc/slug"]
1. Fonte de verdade: ficheiros Markdown
A wiki vive em docs/wiki/*.md — cada ficheiro é uma página [Fonte: db:doc/18-contribuir] [Fonte: db:doc/00-inicio-publico].

Isso é independente do pipeline das aulas ISS (content/ → JSON → ingest-knowledge.py). A wiki do bot tem o seu próprio script.

2. Ingestão: script → Python → MySQL
Corres:

# Staging (MySQL local, porta 3307)
KERNELBOT_ENV=staging ./bin/ingest-wiki-doc.sh

# Produção (DB_* no .env apontando para Aiven/Railway)
./bin/ingest-wiki-doc.sh
[Fonte: db:doc/18-contribuir] [Fonte: db:doc/13-staging-testes]

O shell script:

valida .venv e dependências;
em staging, carrega .env.staging.local;
executa python -m engine.wiki_doc.
O módulo engine/wiki_doc.py lê todos os *.md, extrai slug (nome do ficheiro), título (primeiro # … do Markdown) e order (prefixo numérico do slug, ex. 06-gates → 6), e faz UPSERT na tabela knowledge:

Campo	Valor
discipline	sempre doc
slug	ex. 19-faq-usuario
content	texto completo do .md
active	1
[Fonte: db:doc/03-estrutura-codigo] — detalhe em engine/wiki_doc.py (código, não trecho injectado).

No staging, o staging-setup.sh já corre este ingest automaticamente [Fonte: db:doc/13-staging-testes].

3. Rebuild do índice BM25
Gravar no MySQL não basta — o KernelBot constrói o BM25 em RAM a partir das rows [Fonte: db:doc/05-bm25-chunking].

Depois de editar a wiki ou correr o ingest, precisas de:

reiniciar o bot, ou
enviar /reload no chat (POST /chat com message=/reload, com Bearer token) [Fonte: db:doc/18-contribuir] [Fonte: db:doc/07-apis-e-sse]
Só então o silo doc entra no índice BM25 (chunking 500 palavras / overlap 50, Opção B2 — igual às outras disciplinas) [Fonte: db:doc/05-bm25-chunking].

4. Como o /doc usa isso no chat
Quando envias /doc O que é o KernelBot?:

O parser detecta o prefixo /doc e fixa o escopo no silo doc [Fonte: código engine/context.py — comportamento descrito na wiki].
A busca BM25 corre só dentro de discipline=doc.
As fontes aparecem como db:doc/{slug} — ex.: [Fonte: db:doc/19-faq-usuario] [Fonte: db:doc/18-contribuir] [Fonte: db:doc/19-faq-usuario].
Se o silo doc estiver vazio (ingest não corrido ou sem /reload), o /doc não encontra material indexado.

Resumo operacional
Passo	Acção
Editar	docs/wiki/*.md
Ingerir	./bin/ingest-wiki-doc.sh (ou variante staging)
Actualizar índice	restart ou /reload
Testar	/doc O que é o KernelBot? → fontes db:doc/…
Se quiseres, no próximo turno posso contrastar isto com o pipeline ISS das aulas (staging-ingest-iss.sh) ou listar o que o staging-setup.sh faz de ponta a ponta.

/doc Com ACL_GROUNDING_POLICY=hybrid, em que condições o Kernel injeta grounding_permissive.txt em vez de grounding_anchored.txt, e o LLM é chamado na mesma?
Kernel · 10:10
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 17 prompts referencia
+3 ficheiros
Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.
Vou confirmar no código a lógica exata de hybrid e quando o LLM é chamado.
Com ACL_GROUNDING_POLICY=hybrid, a escolha do contrato de grounding passa por _select_grounding() em engine/context.py [Fonte: db:doc/06-gates-e-decisoes] [Fonte: db:doc/17-prompts-referencia].

Quando entra grounding_permissive.txt
Só em hybrid, e só nesta combinação:

decision.reason está em _WEAK_GROUNDING_REASONS:

insufficient_context
context_misaligned
underspecified_query
low_confidence
vague_but_high_risk
E decision.selected_candidates está vazio (nenhum chunk [Fonte: …] no prompt).

def _select_grounding(decision: RetrievalDecision, settings: Settings) -> str:
    """Escolhe o contrato de grounding conforme política, decisão e flags de produto."""
    if decision.reason == "ambiguous_retrieval" and settings.disambiguation_enabled:
        return settings.grounding_disambiguation
    if settings.grounding_policy == "strict":
        return settings.grounding_strict
    if settings.grounding_policy == "anchored":
        return settings.grounding_anchored
    # hybrid
    if decision.reason == "ok" and decision.selected_candidates:
        return settings.grounding_anchored
    if decision.reason in _WEAK_GROUNDING_REASONS:
        if decision.selected_candidates:
            return settings.grounding_anchored
        return settings.grounding_permissive
    return settings.grounding_anchored
Tabela resumida (hybrid)
Situação	Contrato injectado	Chunks no prompt
reason=ok + há candidatos	grounding_anchored.txt	Sim
reason fraco + há candidatos	grounding_anchored.txt	Sim (mesmo com confidence=low)
reason fraco + sem candidatos	grounding_permissive.txt	Não
ambiguous_retrieval + ACL_DISAMBIGUATION_ENABLED=true	grounding_disambiguation.txt	Sim, numerados
Qualquer outro reason (ex.: index_gap)	grounding_anchored.txt (fallback)	Depende do retrieval
O caso típico de permissive é insufficient_context sem hits (BM25 não devolveu nada útil). Se houver hits fracos (top_score < MIN_SCORE), os chunks ainda entram e o contrato fica anchored, não permissive [Fonte: db:doc/06-gates-e-decisoes].

O que o permissive manda ao modelo: aviso obrigatório no início («Não encontrei este tópico exato…») e permissão para conhecimento geral didático, sem fingir que veio das aulas [Fonte: db:doc/17-prompts-referencia].

O LLM é chamado na mesma?
Sim. Nos cenários de retrieval fraco (incluindo permissive sem chunks), o LLM é chamado.

Os gates de retrieval classificam reason e confidence e escolhem o grounding — não bloqueiam a geração por defeito [Fonte: db:doc/06-gates-e-decisoes] [Fonte: db:doc/17-prompts-referencia]:

build_decision() define allow_generation=True sempre.
context.py monta o prompt e marca trace.decision="answer".
O reason fraco (ex.: insufficient_context) vai para telemetria/ACL_META, não para cortar o LLM.
Hard stop real (sem LLM) fica restrito a casos como provider_error ou trace.decision == "hard_stop" — não é o fluxo normal dos gates de retrieval [Fonte: db:doc/06-gates-e-decisoes] [Fonte: db:doc/17-prompts-referencia].

Fluxo mental
hybrid + retrieval fraco
    │
    ├─ há chunks? ──sim──► grounding_anchored.txt + [Fonte: …] ──► LLM chamado
    │
    └─ sem chunks? ──► grounding_permissive.txt (aviso + teoria geral) ──► LLM chamado
Nota: ACL_RETRIEVAL_MODE está deprecado; em hybrid o que manda é a política de grounding acima, não esse flag legado [Fonte: db:doc/06-gates-e-decisoes].

Se quiseres, no próximo turno posso dar um exemplo concreto de pergunta que cai em permissive vs. uma que cai em anchored com reason=insufficient_context mas ainda com chunks fracos.


/doc Quais flags dispara post_generation_flags após o LLM responder, qual o limiar de termos não suportados em strict vs anchored, e quando anchored_post_generation_advisory_flags suprime o advisory amarelo?
Kernel · 10:10
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 17 prompts referencia
+3 ficheiros
Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.
Vou localizar no código e na wiki os detalhes de post_generation_flags, limiares e supressão do advisory em anchored.
Encontrei uma divergência entre a wiki e o código nos limiares; vou confirmar os detalhes completos.
Três flags possíveis, dois caminhos depois do LLM (strict vs anchored), e uma função extra que filtra o aviso amarelo. Detalhe abaixo.

Onde corre
post_generation_flags() em engine/retrieval.py executa depois da resposta do LLM, em chat_provider.py → _maybe_override_post_generation() [Fonte: db:doc/06-gates-e-decisoes] [Fonte: db:doc/07-apis-e-sse].

As 3 flags de post_generation_flags
Flag	O que detecta
missing_informative_terms	A resposta não contém nenhum termo informativo da query
missing_source_entities	Há chunks seleccionados, mas a resposta não menciona fonte (db:…) nem partilha tokens longos (>4 chars) com o texto dos chunks
introduced_unsupported_terms	Demasiados tokens «técnicos» (≥5 chars, com letra minúscula) que não aparecem nos chunks nem nos termos informativos da query
[Fonte: db:doc/06-gates-e-decisoes]

Limiar de introduced_unsupported_terms (strict vs anchored)
A wiki documenta [Fonte: db:doc/06-gates-e-decisoes]:

Política	Limiar
strict	>25 termos não suportados
anchored / hybrid	>35 termos não suportados
Nota de implementação: no código actual (engine/retrieval.py, linha 896), o limiar em anchored/hybrid está em 50, não 35 — possível drift wiki ↔ código. Em runtime, vale o que está no código até a wiki ser alinhada.

Diferenças strict vs anchored na geração das flags
Em anchored/hybrid (relaxed_anchored=True), a heurística já é mais permissiva antes do filtro de advisory:

Flag	strict	anchored / hybrid
missing_informative_terms	Dispara se decision.reason == "ok" e nenhum termo informativo aparece	Nunca é adicionada (not relaxed_anchored bloqueia)
missing_source_entities	Sempre avaliada	Omitida se a resposta cita fonte ([Fonte: ou db:) ou tem marcador de extensão pedagógica
introduced_unsupported_terms	Limiar >25	Limiar >50 no código (wiki: >35); omitida por completo se cita fonte ou tem extensão pedagógica rotulada
O que acontece depois das flags
Política	Com flags	Efeito na UI
strict	Qualquer flag	Override destrutivo: post_generation_override, reason=post_generation_misalignment, badge «Revisão», disclaimer no stream; todas as flags vão em post_generation_flags no meta [Fonte: db:doc/06-gates-e-decisoes] [Fonte: db:doc/08-frontend-ui]
anchored / hybrid	Passa por filtro	Advisory suave: post_generation_advisory: true; resposta mantida [Fonte: db:doc/06-gates-e-decisoes]
Em anchored, não entram no aviso amarelo:

missing_informative_terms (nem é gerada)
missing_source_entities (mesmo que exista, não está em _ANCHORED_ADVISORY_STRONG_FLAGS)
Só introduced_unsupported_terms é «flag forte» para advisory.

Quando anchored_post_generation_advisory_flags() suprime o aviso amarelo
Função B3.1 em engine/retrieval.py [Fonte: db:doc/06-gates-e-decisoes]. Mesmo com introduced_unsupported_terms nas flags brutas, não emite advisory se a resposta:

Condição	Detecção
Cita fonte indexada	Regex [Fonte (case-insensitive) ou substring db:
Declara lacuna ou recusa	Padrões _LACUNA_OR_REFUSAL_RE (ex.: «não há trecho», «lacuna declarada», «não aparece nos trechos»…)
Inclui extensão pedagógica rotulada	Marcador extensão pedagógica (fora do material indexado)
Se qualquer condição acima for verdadeira → retorna [] → sem segundo [ACL_META] com advisory amarelo.

Se nenhuma se aplicar e restar introduced_unsupported_terms → emite post_generation_advisory: true + post_generation_flags: ["introduced_unsupported_terms"].

Fluxo resumido
LLM responde
    ↓
post_generation_flags()  →  até 3 flags
    ↓
┌─ strict ─────────────────────────────────────────┐
│  qualquer flag → override «Revisão» + disclaimer │
└──────────────────────────────────────────────────┘
┌─ anchored/hybrid ────────────────────────────────┐
│  anchored_post_generation_advisory_flags()       │
│    → só introduced_unsupported_terms conta         │
│    → suprimido se [Fonte:/db:, lacuna, extensão  │
│  se sobreviver flag → advisory amarelo (mantém)  │
└──────────────────────────────────────────────────┘
Síntese directa
Flags possíveis: missing_informative_terms, missing_source_entities, introduced_unsupported_terms.
Limiar unsupported: wiki diz >25 (strict) e >35 (anchored); código actual usa >25 e >50.
Supressão do amarelo em anchored: só introduced_unsupported_terms chega ao advisory; é suprimido se a resposta cita [Fonte:…]/db:, declara lacuna/recusa, ou traz bloco Extensão pedagógica (fora do material indexado).
Queres que eu detalhe os padrões exactos de _LACUNA_OR_REFUSAL_RE ou o formato do segundo [ACL_META] no SSE?

/doc O stream SSE pode emitir dois [ACL_META] no mesmo turno? Em que ordem e com que campos extra no segundo evento?
Kernel · 10:10
Documentação · 19 faq usuario
Documentação · 07 apis e sse
Documentação · 00 inicio publico
Documentação · 08 frontend ui
Documentação · 17 prompts referencia
+3 ficheiros
Buscando na documentação e no código os detalhes do segundo [ACL_META] no stream SSE.
Sim — no mesmo turno o stream pode ter dois [ACL_META]. O segundo é opcional e só aparece depois de a resposta do LLM ter sido streamada [Fonte: db:doc/07-apis-e-sse].

Ordem no stream
Sequência típica de um turno com geração:

data: [ACL_META]{...}          ← meta inicial (sempre primeiro, antes de qualquer texto)

data: <fragmento de texto>     ← um ou mais chunks durante a geração
data: <mais texto...>

data: [ACL_META]{...}          ← segundo meta (opcional, pós-geração)

data: <texto extra>            ← só em override strict (disclaimer)

data: [DONE]
Regras importantes:

O primeiro [ACL_META] sai sempre antes de qualquer fragmento de texto [Fonte: db:doc/07-apis-e-sse].
O segundo (se existir) vem depois do texto gerado — para override/advisory ou desambiguação [Fonte: db:doc/07-apis-e-sse] [Fonte: db:doc/06-gates-e-decisoes].
O cliente distingue tudo pelo prefixo da linha ([ACL_META], texto livre, [DONE]) — não há event: nomeado no SSE [Fonte: db:doc/07-apis-e-sse].
A UI trata cada [ACL_META] via callback onMeta — o meta pode chegar incompleto no primeiro chunk em rede lenta [Fonte: db:doc/13-staging-testes].
O que traz o primeiro vs. o segundo
O primeiro meta carrega o contrato v=3 completo do turno: v, label, sources, decision, reason, confidence, allow_generation, llm_called, tokens_used, mode, pin, etc. [Fonte: db:doc/07-apis-e-sse].

O segundo reutiliza essa base e acrescenta ou altera campos conforme o cenário pós-geração:

Cenário	Campos extra / alterados no 2.º meta	Política
Advisory suave	post_generation_advisory: true, post_generation_flags	anchored / hybrid
Override destrutivo	post_generation_override: true, misalignment: true, post_generation_flags; além disso decision: "hard_stop", reason: "post_generation_misalignment", confidence: "low", allow_generation: false	strict
Desambiguação estruturada	disambiguation_options, payload (ex.: suggested_candidates)	ambiguous_retrieval com geração
[Fonte: db:doc/07-apis-e-sse] [Fonte: db:doc/08-frontend-ui]

Comportamento na UI
post_generation_advisory → hint amarelo suave; a resposta permanece [Fonte: db:doc/08-frontend-ui] [Fonte: db:doc/06-gates-e-decisoes].
post_generation_override → badge «Revisão», header de aviso e disclaimer no fim do stream (texto extra após o 2.º meta) [Fonte: db:doc/08-frontend-ui].
disambiguation_options → reforço para os DisambiguationChips (além do XML `
A resposta foi interrompida antes de concluir as opções. Reformule a pergunta ou tente novamente.

/doc O stream SSE pode emitir dois [ACL_META] no mesmo turno? Em que ordem e com que campos extra no segundo evento?
Kernel · 10:13
Documentação · 07 apis e sse
Documentação · 08 frontend ui
Documentação · 06 gates e decisoes
Sim — no mesmo turno o SSE pode emitir dois [ACL_META]. O material do curso descreve isso de forma explícita.

Ordem no stream
Primeiro [ACL_META] — sai antes de qualquer texto da resposta (incluindo fragmentos do LLM ou mensagem fixa de hard stop).
Conteúdo do turno — deltas de texto (stream do modelo ou texto fixo, conforme allow_generation).
Segundo [ACL_META] (opcional) — emitido pós-geração, para override, advisory ou desambiguação [Fonte: db:doc/07-apis-e-sse].
Fluxo resumido:

sequenceDiagram
    participant S as Servidor SSE
    participant UI as Frontend
    S->>UI: [ACL_META] inicial (v=3)
    alt allow_generation=true
        S->>UI: fragmentos de texto
    else hard stop
        S->>UI: mensagem fixa
    end
    opt checagem pós-geração
        S->>UI: [ACL_META] segundo
    end
    S->>UI: data: [DONE]
Campos do primeiro evento
O primeiro meta traz o contrato v=3 completo: label, sources, decision, reason, confidence, allow_generation, llm_called, tokens_used, mode, estado de pin, etc. [Fonte: db:doc/07-apis-e-sse]

Opcionais relevantes já no início: grounding_policy, hints de escopo/pin, disambiguation_options (se aplicável), e em hard stop catalog_match / payload.

Campos extra no segundo evento
O segundo meta refina o turno após a checagem de grounding — não substitui o contrato base, mas acrescenta sinais de pós-geração [Fonte: db:doc/07-apis-e-sse] [Fonte: db:doc/08-frontend-ui] [Fonte: db:doc/06-gates-e-decisoes]:

Campo	Quando aparece	Efeito
post_generation_override: true	ACL_GROUNDING_POLICY=strict + misalignment	Override destrutivo — UI mostra badge misalignment, header “Revisão”, disclaimer no fim
post_generation_advisory: true	anchored / hybrid	Aviso suave — resposta mantida, hint amarelo
post_generation_flags	Flags detalhadas da checagem	Complemento ao advisory/override
misalignment	Override strict	Alinhado com post_generation_misalignment
allow_generation: false	Após override strict	Impede tratar o turno como sucesso (ex.: desambiguação)
grounding_policy	Sempre que há trace	Badge “Modo didático” / “Modo rigoroso” na UI
Em anchored (default), o segundo meta tende a ser advisory (hint suave), não override destrutivo [Fonte: db:doc/08-frontend-ui]. Em strict, pode vir override com disclaimer no stream [Fonte: db:doc/06-gates-e-decisoes].

Supressão do advisory em anchored
O advisory não é emitido quando a resposta já [Fonte: db:doc/06-gates-e-decisoes]:

cita o corpus ([Fonte:),
declara lacuna ou recusa,
inclui Extensão pedagógica (fora do material indexado): rotulada.
Síntese
Dois [ACL_META] no mesmo turno: sim. Ordem: meta inicial → texto → meta pós-geração (se houver) → [DONE]. O segundo evento acrescenta sobretudo post_generation_advisory ou post_generation_override (e flags/misalignment associados), conforme a política de grounding — advisory em anchored/hybrid, override destrutivo em strict.

Quer que eu detalhe como a UI reage a cada reason no primeiro meta (ambiguous_retrieval, index_gap, provider_error, etc.)?

/doc Com ACL_DISAMBIGUATION_ENABLED=true e reason ambiguous_retrieval, como o modelo deve formatar as opções, que ficheiro de grounding entra no prompt e como o frontend evita mostrar XML cru na bolha?
Kernel · 10:13
Documentação · 07 apis e sse
Documentação · 08 frontend ui
Documentação · 06 gates e decisoes
Documentação · 17 prompts referencia
Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.
Confirmando nos ficheiros referenciados na documentação como o XML é parseado e removido da bolha.
Com ACL_DISAMBIGUATION_ENABLED=true e reason=ambiguous_retrieval, o fluxo encaixa numa cadeia curta: gates → grounding específico → saída estruturada do modelo → UI que parseia e esconde o XML.

1. Como o modelo deve formatar as opções
Quando os trechos numerados são incompatíveis ou igualmente plausíveis sem critério claro para escolher um, o contrato em grounding_disambiguation.txt manda não responder em prosa aberta nem listar opções em Markdown. A saída deve ser só o bloco estruturado [Fonte: db:doc/17-prompts-referencia].

Formato preferido (XML):



Regras importantes do mesmo ficheiro [Fonte: `grounding_disambiguation.txt` via doc/17]:

- Cada `<option>` deve fechar sintaticamente com `/>` (ou `<option …></option>`).
- `discipline` e `slug` vêm do caminho da fonte (`[Fonte N: disciplina/arquivo.json]`).
- `label` é um título curto para o utilizador.
- **Alternativa:** uma linha JSON mínima: `{"disambiguation_options":[{"discipline":"...","slug":"...","label":"..."}]}`.

Se o modelo **consegue** escolher uma fonte clara, ou os trechos são complementares, responde em prosa citando `[Fonte N]` — o bloco XML só entra na regra 4 (ambiguidade real) [Fonte: db:doc/17-prompts-referencia].

O backend pode reemitir as mesmas opções no segundo `[ACL_META]` via `disambiguation_options` ou `payload.suggested_candidates` [Fonte: db:doc/08-frontend-ui].

---

## 2. Que ficheiro de grounding entra no prompt

Não entra `grounding_anchored.txt` nem `grounding_strict.txt` neste caso. A seleção em `_select_grounding()` (`engine/context.py`) é:

- Se `decision.reason == "ambiguous_retrieval"` **e** `ACL_DISAMBIGUATION_ENABLED=true` → **`grounding_disambiguation.txt`** [Fonte: db:doc/06-gates-e-decisoes].

Os chunks no prompt também mudam de formato: passam a **`[Fonte 1: …]`, `[Fonte 2: …]`** (numerados), em vez de `[Fonte: …]` simples [Fonte: db:doc/06-gates-e-decisoes] — implementado em `_format_chunks_for_prompt()`.

Tabela resumida do contrato condicional:

| Condição | Ficheiro de grounding | Formato dos chunks |
|----------|----------------------|-------------------|
| `ambiguous_retrieval` + desambiguação ON | `grounding_disambiguation.txt` | `[Fonte 1: …]`, `[Fonte 2: …]` |
| default `anchored` | `grounding_anchored.txt` | `[Fonte: path \| Score: …]` |

---

## 3. Como o frontend evita XML cru na bolha

Com `allow_generation=true` e `ambiguous_retrieval`, a UI faz stream de markdown **sem** mostrar o XML [Fonte: db:doc/08-frontend-ui]. A lógica vive em `parseAclMeta.js` + `parseAmbiguityOptions.js` + `ambiguityStreamBuffer.js` (`frontend/src/ui.js` orquestra).

**Pipeline durante o SSE (`onDelta`):**

1. **`processAmbiguityStreamDisplay()`** percorre o texto acumulado, localiza `` e **separa** prosa antes e depois do bloco — o XML fica fora de `displayText`.
2. **`stripPartialAmbiguityTagSuffix()`** corta sufixos parciais de tag (ex.: `<ambiguity` a meio do stream) para não piscar markup incompleto.
3. **`parseAmbiguityOptionsFromText()`** extrai `<option discipline="…" slug="…" label="…"/>` (ou o JSON equivalente).
4. **`renderStreamBubble()`** renderiza só `proseBefore` / `proseAfter` como markdown; as opções vão para **`DisambiguationChips`**, não para a bolha como texto cru.
5. Enquanto o bloco está aberto mas ainda sem opções fechadas, mostra placeholder: *"A preparar opções de escolha com base no material indexado…"*.

**No fim do stream:** `finalizeAmbiguityStreamDisplay()` confirma opções; `mergeDisambiguationOptions()` dá prioridade ao meta do backend sobre o parse do texto.

**Hard stop** (`allow_generation=false`): `onDelta` é ignorado; chips ou texto fixo vêm do meta/payload, sem stream LLM [Fonte: db:doc/08-frontend-ui].

---

## Diagrama rápido

```mermaid
sequenceDiagram
    participant G as Gates (ambiguous_retrieval)
    participant C as context.py
    participant LLM as Modelo
    participant UI as ui.js + ambiguityStreamBuffer

    G->>C: reason=ambiguous_retrieval
    C->>C: grounding_disambiguation.txt + [Fonte 1], [Fonte 2]
    C->>LLM: system prompt
    LLM-->>UI: stream com


/doc Como funciona o merge entre chunks fixados (pin) e a busca BM25 do turno actual, e quando aparece sources_note na UI?
Kernel · 10:13
Várias fontes próximas — escolha uma aula abaixo ou continue no texto.
Documentação · 07 apis e sse
Documentação · 08 frontend ui
Documentação · 06 gates e decisoes
Documentação · 17 prompts referencia
Documentação · 19 faq usuario
Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.
Vou cruzar o material indexado com o código de pin e sources_note para explicar o merge e quando a UI mostra a nota.

Visão geral
Num turno com pin activo, o backend não substitui o contexto fixado pela busca BM25 — combina os dois. A BM25 corre sempre para a query actual; os chunks do pin entram primeiro no prompt, e o retrieval só acrescenta fontes que ainda não estavam no pin.

[Fonte: db:doc/09-fluxos-operacionais]

Merge: pin + BM25
A função _merge_pin_and_retrieval_chunks() em engine/context.py segue esta ordem:

Chunks do pin (contexto do turno anterior, guardado em PinnedSessionStore).
Chunks do retrieval (decision.selected_candidates da BM25 deste turno).
Dedupe por source — se a mesma aula já veio no pin, o retrieval não a repete.
Corte por tamanho — _trim_pin_chunks() respeita ACL_PINNED_MAX_CHARS (default 24 000).
O resultado alimenta o grounding ([Fonte: …]), entra em trace.sources do [ACL_META], e no fim do turno é gravado de volta no pin via _save_pin() — ou seja, o pin evolui com o merge, não fica congelado no turno N−1.

[Fonte: db:doc/09-fluxos-operacionais]

Ciclo de vida do pin (contexto do merge)
Momento	O que acontece
Turno com RAG//doc e chunks	set_pinned() após o turno
Turno seguinte	get() → merge com BM25
Início de cada mensagem	begin_turn() decrementa TTL (ACL_PINNED_MAX_TURNS, default 5)
Scope diferente (/python vs pin em SQL)	_pin_conflicts → pin limpo
/reset	pin limpo
TTL = 0	pin removido
[Fonte: db:doc/09-fluxos-operacionais]

O campo pin_chunks_used: true no [ACL_META] indica que este turno efectivamente injectou chunks do pin (bool(pin and pin.chunks)). A UI usa isso para o badge «Continuando: {name}» no campo de entrada.

[Fonte: db:doc/08-frontend-ui]

Quando aparece sources_note
sources_note não é o advisory amarelo de pós-geração — é uma nota informativa no rodapé (classe .message-sources-note), montada a partir de meta.sources_note via sourcesNoteFromMeta().

[Fonte: db:doc/06-gates-e-decisoes] · [Fonte: db:doc/08-frontend-ui]

Aparece quando a função _retrieval_adds_sources_beyond_pin() detecta que a BM25 deste turno trouxe pelo menos uma fonte que não estava no pin anterior:

pin existe e tem chunks;
algum source em selected_candidates não pertence ao conjunto de fontes do pin guardado.
Nesse caso _build_scope_ui_hints() preenche:

«Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.»

[Fonte: db:doc/06-gates-e-decisoes]

Quando não aparece
Sem pin activo.
BM25 só confirma/repete as mesmas fontes do pin (nada novo além do pin).
Pin expirou ou foi limpo por conflito de scope antes do merge.
O backlog confirma a intenção: sources_note é condicional — só quando o retrieval adiciona fontes além do pin.

[Fonte: db:doc/16-backlog]

Não confundir com scope_hint
São sinais diferentes no [ACL_META]:

Campo	Dispara quando	Efeito na UI
sources_note	Fontes do turno ≠ só pin (mix pin + retrieval)	Nota no rodapé dos breadcrumbs
scope_hint	Pin numa disciplina, pergunta/comando noutra	Hint no header / tooltip do badge «Continuando»
pin_chunks_used	Merge activo com chunks do pin	Badge «Continuando: …» no input
[Fonte: db:doc/08-frontend-ui]

Fluxo resumido (turno N com pin)
sequenceDiagram
  participant UI
  participant CM as ContextManager
  participant PS as PinnedSessionStore
  participant BM25 as SearchEngine

  UI->>CM: POST /chat (session_id)
  CM->>PS: get pin → begin_turn (TTL--)
  CM->>BM25: search_candidates(query)
  CM->>CM: merge pin + selected (dedupe, trim)
  CM->>CM: monta prompt + ACL_META
  Note over CM: sources_note se retrieval trouxe fonte nova
  CM->>PS: _save_pin(merged) após turno
  CM-->>UI: SSE [ACL_META] + stream
Detalhe extra (follow-ups curtos)
Com pin activo, perguntas curtas de continuação («E o HAVING?») podem ter o reason relaxado de underspecified_query para ok — o pin dá contexto suficiente para não bloquear o turno.

Extensão pedagógica (fora do material indexado): pensa no pin como «cola de contexto» e na BM25 como «busca fresca». O merge garante continuidade (não perdes a aula anterior) sem ignorar o que a query actual pede; o sources_note avisa quando essas duas camadas não coincidem — sinal para usar /reset ou um comando de disciplina explícito.

Se quiseres, no próximo turno posso detalhar só o TTL (begin_turn) ou só a diferença entre pinned_active e pin_chunks_used no meta.

Qual destas aulas corresponde melhor à sua pergunta?


06 gates e decisoes
db:doc · 06-gates-e-decisoes

07 apis e sse
db:doc · 07-apis-e-sse

19 faq usuario
db:doc · 19-faq-usuario

08 frontend ui
db:doc · 08-frontend-ui

/doc Quais validações o servidor aplica ao campo history do POST /chat, que roles são rejeitados, e como isso difere do que fica no localStorage do browser?
Kernel · 10:13
Documentação · 07 apis e sse
Documentação · 08 frontend ui
Documentação · 06 gates e decisoes
Documentação · 17 prompts referencia
Documentação · 19 faq usuario
Vou localizar no código e na documentação como o POST /chat valida history e como isso se compara ao que o browser guarda no localStorage.
O servidor trata history como entrada validada; o browser guarda mais contexto e só manda um recorte na API. Resumo alinhado ao material e ao código.

Validações no servidor (POST /chat)
O campo é opcional — omitido ou null vira lista vazia [Fonte: db:doc/07-apis-e-sse]. A validação está em _normalize_conversation_history (engine/context.py), chamada por api/routes.py; falha → HTTP 400.

Regra	Comportamento
Tipo	Tem de ser lista (ou omitido)
Tamanho	Máx. 40 itens (_MAX_HISTORY_ITEMS_RAW) — acima disso → 400
Cada item	Tem de ser objeto com role + content
content	String não vazia após strip() — ausente/vazio → 400
content longo	Truncado a 8192 chars por item (não rejeita)
Truncagem no prompt	Depois da validação: últimos ACL_CHAT_HISTORY_MAX_TURNS (12 default) e até ACL_CHAT_HISTORY_MAX_CHARS (12000 default) [Fonte: db:doc/07-apis-e-sse]
Ordem no prompt do LLM: system (RAG + grounding, só servidor) → history truncado → user (mensagem actual em message) [Fonte: db:doc/07-apis-e-sse].

Roles rejeitados
Só são aceites user e assistant (_VALID_HISTORY_ROLES) [Fonte: db:doc/07-apis-e-sse].

Role enviada pelo cliente	Resultado
system	400 — mensagem explícita: reservado ao servidor
Qualquer outra (bot, function, etc.)	400 — tem de ser user ou assistant
O system do prompt (grounding, fontes, pin) nunca vem do history do cliente — o servidor injecta-o em _merge_messages_with_history.

O que fica no localStorage do browser
Chave acl_conversation_v1, estrutura { session_id, turns: [...] } [Fonte: db:doc/08-frontend-ui] [Fonte: db:doc/07-apis-e-sse].

Aspecto	Browser (history.js)	API (history no POST)
Roles internas	user / bot	user / assistant
Campo de texto	text	content
Limite ao gravar	30 turnos, 200k chars totais	—
Limite ao enviar	getHistoryForApi() → últimos 12 turnos (MAX_API_MESSAGES)	Servidor aceita até 40 itens
Limite no prompt	—	12 turnos + 12000 chars (env vars)
Metadados extra	sources, ts, session_id	Não enviados no history
Validação	Filtra silenciosamente entradas inválidas ao carregar	400 em qualquer violação
system	Nem existe no storage	Rejeitado se o cliente tentar injectar
Na prática: a UI converte bot → assistant e text → content só no momento do POST (getHistoryForApi()). O que vês na bolha (fontes, timestamps) fica local; o servidor só vê pares { role, content }.

Diferença conceptual (POC)
localStorage = memória visual da conversa (persiste refresh/fechar aba) [Fonte: db:doc/19-faq-usuario].
history na API = contexto que o modelo recebe neste turno, já cortado e validado.
Sem autenticação: qualquer cliente pode forjar history — aceitável na demo local [Fonte: db:doc/07-apis-e-sse] [Fonte: db:doc/01-visao-geral].
Comandos que afectam o envio:

/reset / /limpar: a UI manda history: [] naquele POST (pin no servidor limpa-se à parte).
Nova conversa (header): apaga o localStorage, novo session_id, e envia /reset — o histórico visual some; o pin também [Fonte: db:doc/08-frontend-ui].
Síntese
O servidor é estrito (tipo, roles, contagem, conteúdo vazio) e trunca antes de montar o prompt. O browser é mais permissivo e mais rico (até 30 turnos guardados, role bot, metadados de fontes) e só manda os 12 turnos mais recentes já no formato da API. Se quiseres, no próximo turno detalho o algoritmo de truncagem por chars (_truncate_conversation_history) — útil para perceber por que um follow-up longo “some” do contexto do modelo.



/doc Na Opção B, o que fica gravado no MySQL por aula, onde ocorre o chunking 500/50, e o que acontece a uma row com content acima de MAX_CONTENT_CHARS?
Kernel · 10:13
Documentação · 07 apis e sse
Documentação · 08 frontend ui
Documentação · 06 gates e decisoes
Documentação · 17 prompts referencia
Documentação · 19 faq usuario
+2 ficheiros
Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.
Sim. Na Opção B, o MySQL guarda o documento inteiro por aula; o chunking 500/50 acontece só em RAM no KernelBot. A diferença em relação à B2 (actual) é onde o bloco meta entra nos chunks — não o que fica persistido.

O que fica gravado no MySQL (por aula)
Uma row por aula, com um content unificado — sem chunks separados na base [Fonte: db:doc/05-bm25-chunking] [Fonte: db:doc/11-enriquecimento-lexico-b2].

Formato típico:

[CONCEITOS E KEYWORDS DA AULA PARA INDEXAÇÃO LÉXICA]
Disciplina: …
Título: …
Conceitos: …
Keywords: …
Objetivos: …
====== FIM DOS METADADOS ======

{markdown body}
A ingestão ISS monta isso como meta_header + "\n " + markdown_sem_frontmatter [Fonte: db:doc/11-enriquecimento-lexico-b2].

Invariante: o MySQL não armazena chunks — só o documento unificado [Fonte: db:doc/05-bm25-chunking].

Onde ocorre o chunking 500/50
No KernelBot, em RAM, durante o rebuild do índice BM25 [Fonte: db:doc/05-bm25-chunking]:

content (MySQL)
    ▼
_split_meta_block() → meta_block | clean_body
    ▼
_chunk_text()  ← 500 palavras, overlap 50
    ▼
Tokenização por silo → BM25Okapi
Constantes em engine/database.py [Fonte: db:doc/05-bm25-chunking]:

Constante	Valor
DB_CHUNK_WORDS	500
DB_CHUNK_OVERLAP	50
MAX_CONTENT_CHARS	4_000_000
Na Opção B (rejeitada), o pipeline MySQL era o mesmo da B2; a diferença era na RAM: o bloco meta ia em todos os chunks, não só no chunk 0 [Fonte: db:doc/11-enriquecimento-lexico-b2].

Abordagem	MySQL	Chunking	Meta nos chunks
Opção B	1 doc unificado/aula	RAM (500/50)	Em todos os chunks
Opção B2 (actual)	Igual	RAM (500/50)	Só no chunk 0
Row com content acima de MAX_CONTENT_CHARS
Comportamento documentado em duas camadas:

Na ingestão ISS — trunca ou rejeita antes do UPSERT [Fonte: db:doc/11-enriquecimento-lexico-b2].
No fetch do KernelBot — a row é ignorada se content for maior que 4_000_000 caracteres [Fonte: db:doc/05-bm25-chunking].
Ou seja: ou não entra no MySQL, ou entra mas não é indexada no boot//reload. Boot e /reload não falham por causa disso — a aula simplesmente fica de fora do índice (padrão semelhante ao de rows legadas com meta malformado) [Fonte: db:doc/05-bm25-chunking].

Por que a Opção B foi abandonada
Com meta em todos os chunks, uma keyword do header (ex.: transformers) aparecia em N documentos do mini-índice da mesma aula → IDF → 0 → scores nulos → insufficient_context [Fonte: db:doc/05-bm25-chunking] [Fonte: db:doc/11-enriquecimento-lexico-b2].

A B2 mantém o mesmo modelo MySQL e o mesmo chunking 500/50 em RAM; só muda a regra de meta (chunk 0 apenas), corrigindo o colapso de IDF.

Quer o detalhe de como o chunk 0 vs chunks ≥1 afectam o que o LLM vê no prompt (context.py)?


/doc O que devolve GET /health/catalog, que autenticação exige, e como o Job 3 do workflow ISS usa essa rota para detectar drift?
Kernel · 10:13
Documentação · 07 apis e sse
Documentação · 08 frontend ui
Documentação · 06 gates e decisoes
Documentação · 17 prompts referencia
Documentação · 19 faq usuario
+2 ficheiros
Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.
Buscando no repositório detalhes sobre GET /health/catalog e o Job 3 do workflow ISS.
GET /health/catalog é o endpoint operacional que expõe o snapshot de drift entre o catálogo ISS e o índice BM25 do KernelBot — protegido, pensado para CI e operadores [Fonte: db:doc/07-apis-e-sse].

O que devolve
Resposta JSON montada em api/routes.py::health_catalog [Fonte: db:doc/07-apis-e-sse]:

Campo	Significado
catalog_enabled	Valor de ACL_CATALOG_ENABLED
indexed_lesson_keys_count	Quantidade de aulas no índice BM25 (RAM)
catalog_lesson_keys_count	Quantidade de aulas no catálogo ISS
catalog_only_count	Aulas que existem no catálogo sem row correspondente no MySQL/índice — isto é o drift
catalog_only_sample	Até 10 chaves de exemplo desse drift
O relatório completo de drift (incluindo index_only — aulas indexadas que não estão no catálogo) é calculado internamente em LessonCatalog.audit_drift(), mas não aparece na resposta pública do endpoint — só os campos acima [Fonte: db:doc/07-apis-e-sse].

A lógica de drift compara conjuntos de chaves discipline/slug:

catalog_only = chaves no catálogo ISS menos chaves indexadas → “aula no catálogo, ausente no índice”
Esse snapshot é recalculado no boot e após /reload via engine/catalog_sync.py [Fonte: db:doc/10-integracao-iss-fase5b].
Autenticação
Mesmo esquema Bearer do /reload [Fonte: db:doc/07-apis-e-sse]:

Situação	HTTP	Detalhe
Header Authorization: Bearer <token> válido	200	JSON do drift
Token inválido ou ausente	401	Invalid reload bearer token / Authorization Bearer token required
Servidor sem token configurado	503	reload token not configured
O token aceite é ACL_RELOAD_BEARER_TOKEN; o alias legado KERNELBOT_RELOAD_TOKEN também funciona (core/config.py) [Fonte: db:doc/07-apis-e-sse]. O workflow ISS envia o mesmo valor no secret KERNELBOT_RELOAD_TOKEN [Fonte: db:doc/10-integracao-iss-fase5b].

Exemplo:

curl -sS "http://127.0.0.1:8001/health/catalog" \
  -H "Authorization: Bearer $ACL_RELOAD_BEARER_TOKEN" | jq .
Como o Job 3 do workflow ISS usa a rota
O workflow sync-kernelbot-knowledge.yml (repo ISS) tem três jobs [Fonte: db:doc/10-integracao-iss-fase5b]:

Job	Função
1	validate-catalog.mjs — consistência do catálogo
2	ingest-knowledge.py — UPSERT no MySQL
3	verify-kernelbot-sync.mjs + reload-kernelbot.mjs — drift + reload
O Job 3 corre depois do ingest bem-sucedido e faz duas coisas [Fonte: db:doc/10-integracao-iss-fase5b]:

GET /health/catalog no KernelBot (URL via secret KERNELBOT_RELOAD_URL, token via KERNELBOT_RELOAD_TOKEN) — compara as chaves do catálogo ISS com indexed_lesson_keys expostas no JSON.
Falha a CI se houver drift crítico — tipicamente catalog_only_count > 0, ou seja, aulas presentes no catálogo ISS que ainda não estão indexadas no KernelBot [Fonte: db:doc/10-integracao-iss-fase5b].
Se a verificação passar, POST /chat com message: "/reload" (mesmo Bearer) para reconstruir o BM25 em RAM e refrescar o snapshot de drift [Fonte: db:doc/07-apis-e-sse, db:doc/09-fluxos-operacionais].
Fluxo resumido:

sequenceDiagram
    participant GHA as Job 3 (ISS GHA)
    participant KB as KernelBot
    participant MySQL as MySQL

    Note over GHA,MySQL: Job 2 já fez UPSERT
    GHA->>KB: GET /health/catalog (Bearer)
    KB-->>GHA: catalog_only_count, sample, contagens
    alt catalog_only_count > 0 (drift crítico)
        GHA-->>GHA: ❌ CI falha
    else sem drift crítico
        GHA->>KB: POST /chat message=/reload (Bearer)
        KB->>MySQL: fetch rows → rebuild BM25
        KB-->>GHA: SSE status + [DONE]
        GHA-->>GHA: ✅ sync confirmado
    end
Síntese
GET /health/catalog = painel de saúde catálogo ↔ índice, não é liveness (isso é GET /health, sem auth).
O sinal de drift que importa para CI é catalog_only_count: catálogo ISS à frente do que o KernelBot indexou.
O Job 3 verifica antes de recarregar; só depois de passar é que dispara o /reload para alinhar o índice RAM com o MySQL recém-ingestado.
Se quiseres, no próximo turno posso destrinchar o que acontece no chat quando uma pergunta bate numa aula catalog_only — o gate index_gap [Fonte: db:doc/10-integracao-iss-fase5b].

/doc Qual a ordem de avaliação dos gates em build_decision e que reason resulta de top_score abaixo de ACL_RETRIEVAL_MIN_SCORE versus margem entre 1º e 2º candidato abaixo de ACL_RETRIEVAL_MIN_SCORE_MARGIN?
Kernel · 10:13
Documentação · 07 apis e sse
Documentação · 08 frontend ui
Documentação · 06 gates e decisoes
Documentação · 17 prompts referencia
Documentação · 19 faq usuario
+2 ficheiros
Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.
Vou confirmar a ordem exata em build_decision() e como cada threshold mapeia para o reason.
A ordem real em build_decision() está no código de engine/retrieval.py; a secção «simplificada» da wiki troca alguns passos e omite o gate de low_confidence [Fonte: db:doc/06-gates-e-decisoes].

Ordem de avaliação (código)
Depois de ordenar candidatos, aplicar diversidade por fonte e calcular top, second e score_margin = top - second, os gates correm nesta ordem (só em mode == "strict" onde indicado):

#	Condição	reason
1	Sem candidatos selecionados ou top < ACL_RETRIEVAL_MIN_SCORE	insufficient_context
2	Menos de ACL_RETRIEVAL_MIN_TERMS termos informativos	underspecified_query
3	is_vague_but_high_risk(...)	vague_but_high_risk
4	2+ candidatos e score_margin < ACL_RETRIEVAL_MIN_SCORE_MARGIN	ambiguous_retrieval
5	Coverage do melhor chunk abaixo de ACL_RETRIEVAL_MIN_COVERAGE	context_misaligned
6	Confiança agregada calculada como "low" (ex.: coverage ponderada fraca, margem baixa, termos centrais em falta)	low_confidence
7	Passou tudo	ok
Defaults: ACL_RETRIEVAL_MIN_SCORE = 1.5, ACL_RETRIEVAL_MIN_SCORE_MARGIN = 0.15 [Fonte: db:doc/06-gates-e-decisoes].

Nota: na wiki, o bloco «Ordem dos gates (simplificado)» coloca ambiguous_retrieval antes de vague_but_high_risk e termina em ok sem mencionar low_confidence — no runtime, vague_but_high_risk vem antes da margem e há um passo extra de low_confidence antes de ok.

top_score < ACL_RETRIEVAL_MIN_SCORE → qual reason?
insufficient_context — gate 1, avaliado antes de qualquer outro.

Comportamento fino [Fonte: db:doc/06-gates-e-decisoes]:

Zero hits → insufficient_context, chunks vazios (ou fracos conforme política).
Há hits mas top < 1.5 → ainda insufficient_context, mas pode levar chunks fracos ao prompt se existirem.
Neste caso nunca se chega ao gate da margem: se o 1.º candidato não passa o score mínimo, a decisão para em insufficient_context.

score_margin < ACL_RETRIEVAL_MIN_SCORE_MARGIN → qual reason?
ambiguous_retrieval — gate 4, só se os gates 1–3 não dispararam.

Ou seja: precisa de top >= ACL_RETRIEVAL_MIN_SCORE, termos informativos suficientes, e não ser vague_but_high_risk. Condição: len(selected) > 1 e (top - second) < 0.15 [Fonte: db:doc/06-gates-e-decisoes].

Variantes dentro desse reason:

Situação	confidence	Efeito extra
ACL_DISAMBIGUATION_ENABLED=true e ≥2 candidatos com raw_score >= min_score	medium	debug.disambiguation_generation = true; entra grounding_disambiguation.txt + fontes numeradas [Fonte: db:doc/06-gates-e-decisoes]
Caso contrário (flag off ou <2 qualificados)	low	Mesmo ambiguous_retrieval, sem ramo de desambiguação estruturada
Em ambos os casos o LLM é chamado (allow_generation permanece true no contrato de retrieval) [Fonte: db:doc/06-gates-e-decisoes]; a diferença na UI (chips vs texto fixo) depende de allow_generation no meta e da flag — ver turno anterior sobre 08-frontend-ui.

Resumo prático (prioridade)
top < 1.5                    → insufficient_context   (para aqui)
     ↓ passou
margem < 0.15 (com 2+ hits)  → ambiguous_retrieval    (só se 1–3 passaram)
     ↓ passou
… coverage, low_confidence, ok
Não há cenário em que margem baixa «ganhe» a um top_score abaixo do mínimo: o score absoluto do 1.º candidato é sempre avaliado primeiro.

/doc Com ACL_CATALOG_ENABLED=true, o que é index_gap, bloqueia a geração do LLM, e que componentes carregam o catálogo lexical ISS?
Kernel · 10:13
Documentação · 07 apis e sse
Documentação · 08 frontend ui
Documentação · 06 gates e decisoes
Documentação · 17 prompts referencia
Documentação · 19 faq usuario
+2 ficheiros
Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.
Buscando no material e no código como index_gap se comporta com ACL_CATALOG_ENABLED=true e quais componentes carregam o catálogo ISS.
Com ACL_CATALOG_ENABLED=true, o index_gap é um sinal de drift por pergunta: o catálogo lexical ISS identifica com confiança uma aula, mas essa aula ainda não está no índice MySQL/RAM (BM25). [Fonte: db:doc/15-glossario | Score: implícito] [Fonte: db:doc/06-gates-e-decisoes]

O que é index_gap
Condições (todas precisam coincidir):

Catálogo activo (ACL_CATALOG_ENABLED=true).
A query faz match confiante no catálogo (is_confident() — score ≥ ACL_CATALOG_MIN_SCORE e margem ≥ ACL_CATALOG_MIN_MARGIN). [Fonte: db:doc/12-configuracao]
A aula no topo do match tem chave discipline:slug ausente do conjunto indexed_lesson_keys (chaves vindas do MySQL).
Em engine/context.py, isso vira trace_reason_override = "index_gap" antes do BM25 do turno — é telemetria/advisory, não um gate de build_decision(). [Fonte: db:doc/06-gates-e-decisoes] [Fonte: engine/retrieval.py — index_gap nunca é emitido em build_decision()]

Cenário típico: perguntas como /python quando existe aula Python no lessons.json do ISS, mas o conteúdo ainda não foi ingerido/reindexado no MySQL. [Fonte: db:doc/13-staging-testes]

Bloqueia a geração do LLM?
Não, no fluxo actual. [Fonte: db:doc/08-frontend-ui]

Campo	Valor com index_gap
decision	answer
allow_generation	true
Efeito	Badge advisory «Aula fora do índice»; o LLM é chamado com RAG normal
O build_decision() define allow_generation sempre como true; os gates de retrieval são classificação + escolha de grounding, não bloqueio pré-LLM. [Fonte: engine/retrieval.py]

O turno continua: BM25 → chunks no prompt → stream do modelo. O reason: "index_gap" vai no [ACL_META] para a UI avisar que a aula «certa» do currículo ainda não está indexada.

Nota: existe mensagem de hard stop e componente IndexGapAlert para index_gap + allow_generation=false, mas no caminho principal de context.py o trace fica com decision="answer". O alerta bloqueante só entraria num hard stop estruturado (caminho legado/planeado, não o advisory actual). [Fonte: db:doc/08-frontend-ui]

Componentes que carregam o catálogo lexical ISS
Componente	Papel
core/config.py	Lê ACL_CATALOG_ENABLED, ACL_CATALOG_JSON_DIR (default ../ISS/content se existir), thresholds (ACL_CATALOG_MIN_SCORE, etc.) e o prompt catalog_router.txt. [Fonte: db:doc/12-configuracao]
engine/lesson_catalog.py	LessonCatalog.load() — lê lessons.json + search-index.json (excerpts); BM25 lexical em memória sobre título/nome/slug/resumo; expõe match(), is_confident(), build_prompt_section(). [Fonte: db:doc/10-integracao-iss-fase5b]
engine/catalog_sync.py	bootstrap_catalog_state() no boot: carrega catálogo + fetch_indexed_lesson_keys() + audit_drift(); refresh_indexed_lesson_keys_state() após /reload. [Fonte: db:doc/03-estrutura-codigo]
main.py	Chama bootstrap_catalog_state() e injecta lesson_catalog + indexed_lesson_keys no ContextManager e AppServices.
engine/context.py	Usa o catálogo para match, rescue, detecção de index_gap, secção de prompt e narrowing de disciplina (is_strict_confident).
engine/database.py	fetch_indexed_lesson_keys() — snapshot das chaves no MySQL para comparar com o catálogo. [Fonte: db:doc/04-dados-e-mysql]
GET /health/catalog	Expõe drift (catalog_only_count, etc.) para o workflow ISS — não carrega o catálogo, só reporta. [Fonte: db:doc/07-apis-e-sse]
Fluxo resumido
sequenceDiagram
    participant Q as Query
    participant LC as LessonCatalog
    participant IK as indexed_lesson_keys
    participant BM25 as SearchEngine
    participant LLM as Provider

    Q->>LC: match() + is_confident()
    LC->>IK: lesson_key no índice?
    alt chave ausente
        Note over Q,LLM: reason = index_gap (advisory)
    end
    Q->>BM25: search_candidates()
    BM25->>LLM: chunks + grounding (decision=answer)
Drift vs index_gap
Drift global (catalog_only no boot/reload): aulas no catálogo sem row no MySQL — visto em logs e GET /health/catalog.
index_gap por turno: a pergunta aponta para uma dessas aulas com match confiante.
Ambos indicam que falta sync ISS → MySQL → /reload, mas só o segundo aparece no [ACL_META] da conversa.

Se quiseres, no próximo turno posso cruzar isso com o merge pin + BM25 (sources_note) num único diagrama de decisão do turno.

doc Enumera as camadas de decisão do KernelBot desde a validação em api/routes.py até o override pós-geração, e esclarece se allow_generation=false nos gates de retrieval bloqueia o LLM.
Kernel · 10:13
Documentação · 07 apis e sse
Documentação · 08 frontend ui
Documentação · 06 gates e decisoes
Documentação · 17 prompts referencia
Documentação · 19 faq usuario
+2 ficheiros
Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.
Vou mapear o fluxo de decisão no código — da validação em api/routes.py até o override pós-geração — para responder com precisão.
Boa pergunta — o fluxo mudou de desenho recente. Hoje os gates de retrieval classificam e telemetram, mas não cortam o LLM. A regra “na dúvida, não responder” migrou para grounding no prompt + sanity check pós-geração.

Camadas de decisão (de cima a baixo)
flowchart TD
  A[POST /chat — api/routes.py] --> B[ContextManager.build_messages]
  B --> C[BM25 + build_decision]
  C --> D[Montagem prompt + ACL_META inicial]
  D --> E[ChatProvider — LLM]
  E --> F[post_generation_flags]
  F --> G{ACL_GROUNDING_POLICY}
  G -->|strict + flags| H[Override: allow_generation=false]
  G -->|anchored/hybrid| I[Advisory amarelo — resposta mantida]
  G -->|sem flags| J[Fim]
1. Validação HTTP — api/routes.py
Antes de qualquer RAG:

Verificação	Falha
Corpo JSON válido	400
message não vazio	400
discipline string ou omitido	400
session_id formato 8–128 chars	400
history lista normalizada	400
Caminho especial: /reload exige Bearer (ACL_RELOAD_BEARER_TOKEN), reconstrói BM25 e devolve SSE sem LLM. [Fonte: db:doc/07-apis-e-sse]

Depois disso, delega para context_manager.build_messages() → chat_provider.stream_response().

2. Roteamento e escopo — engine/context.py
Etapa	O que decide
/reset / /limpar	Limpa pin da sessão
Prefixos (/doc, /content, /python…)	query limpa + effective_discipline
Pin (TTL)	Herda disciplina em follow-ups curtos; conflito de escopo limpa pin
Histórico	Truncagem (chat_history_max_turns/chars)
select_mode()	Hoje sempre strict (hook para assistive)
Catálogo ISS	index_gap advisory se aula confiante mas fora do índice; pode estreitar disciplina
index_gap não nasce em build_decision() — é emitido em context.py quando o catálogo aponta aula ausente do BM25. [Fonte: db:doc/06-gates-e-decisoes]

3. Retrieval lexical — engine/search.py → engine/retrieval.py
search_candidates() — BM25 por silo, top candidate_k
build_decision() — classifica reason + confidence, seleciona até top_k chunks
_try_catalog_rescue() — se ambiguous_retrieval, tenta re-buscar restrito à aula do catálogo
Ordem dos gates em build_decision() [Fonte: db:doc/06-gates-e-decisoes]:

Sem hits ou top_score < MIN_SCORE → insufficient_context
Poucos termos informativos → underspecified_query
Query estruturalmente vaga → vague_but_high_risk
Margem baixa entre top1/top2 → ambiguous_retrieval (com desambiguação se ACL_DISAMBIGUATION_ENABLED)
Coverage baixa → context_misaligned
Confiança agregada baixa → low_confidence
Caso contrário → ok
4. Montagem do prompt — ainda em context.py
Camada	Função	Efeito
Grounding	_select_grounding()	Escolhe grounding_strict/anchored/permissive/disambiguation conforme ACL_GROUNDING_POLICY + reason
Pin merge	_merge_pin_and_retrieval_chunks()	Pin primeiro, depois BM25; dedupe por source
Relaxamento pin	_relax_weak_reason_for_pinned_follow_up()	underspecified_query → ok em follow-up curto com pin activo
UI hints	_build_scope_ui_hints()	scope_hint, sources_note, etc.
Ponto crítico: o ContextTrace sai sempre com decision="answer" — mesmo quando reason é insufficient_context, ambiguous_retrieval, etc. Os gates influenciam qual contrato de grounding entra no system prompt e qual badge a UI mostra, não se o provider é chamado. [Fonte: db:doc/06-gates-e-decisoes]

5. Streaming SSE — engine/chat_provider.py
Situação	LLM?	allow_generation no meta
trace.decision == "hard_stop"	Não — texto fixo (provider_error, legado _hard_stop_result)	false
Turno normal (todos os reason de retrieval)	Sim	true (trace.decision == "answer")
Falha do provider (Cursor/OpenRouter)	Não	false + reason=provider_error
[ACL_META] v=3 inicial sai antes do texto; um segundo meta pode vir pós-geração. [Fonte: db:doc/07-apis-e-sse]

6. Pós-geração — post_generation_flags() em retrieval.py, aplicado em chat_provider.py
Depois que o LLM terminou, heurística não-LLM verifica:

Flag	Resumo
missing_informative_terms	Resposta não cobre termos da query
missing_source_entities	Não menciona fontes/entidades dos chunks
introduced_unsupported_terms	Muitos termos técnicos novos sem suporte nos chunks
Comportamento por política [Fonte: db:doc/06-gates-e-decisoes]:

ACL_GROUNDING_POLICY	Com flags
strict	Override destrutivo: segundo [ACL_META] com decision=hard_stop, reason=post_generation_misalignment, allow_generation=false + disclaimer no fim do stream
anchored / hybrid	Advisory apenas (post_generation_advisory); resposta mantida
Em anchored, advisory é suprimido se a resposta cita [Fonte:, declara lacuna, ou inclui Extensão pedagógica (fora do material indexado):.

Se ambiguous_retrieval + desambiguação activa, pode ainda sair um meta com disambiguation_options para os chips da UI. [Fonte: db:doc/08-frontend-ui]

Resposta directa: allow_generation=false nos gates de retrieval bloqueia o LLM?
Não. No runtime actual:

build_decision() define allow_generation=True sempre — os gates são telemetria + escolha de grounding, não bloqueio. [Fonte: db:doc/06-gates-e-decisoes]
context.py não chama mais _hard_stop_result() para insufficient_context, ambiguous_retrieval, etc. — esse caminho ficou legado (só referenciado na wiki de prompts). [Fonte: db:doc/17-prompts-referencia]
A UI documenta explicitamente: «Hard stop (provider_error, allow_generation=false): excepção; gates de retrieval não bloqueiam stream LLM». [Fonte: db:doc/08-frontend-ui]
Onde allow_generation=false realmente aparece hoje:

Momento	Causa
Inicial	provider_error (falha Cursor/OpenRouter)
Pós-geração (strict)	Override post_generation_misalignment — depois de já ter streamado a resposta do LLM
Legado	_hard_stop_result() — código presente, mas sem caller activo
Síntese mental
Camada	Pergunta que responde	Bloqueia LLM?
routes.py	Pedido válido?	Só HTTP 400 ou /reload
context.py	Qual escopo, pin, grounding, chunks?	Não
build_decision()	Qual reason/confidence?	Não (sempre allow_generation=true)
Grounding no prompt	Como o modelo deve usar fontes?	Não — regra pedagógica
post_generation_flags	Resposta alinhada aos chunks?	Só em strict — override após geração
provider_error	Provider respondeu?	Sim — hard stop sem LLM
Ou seja: um turno com reason=insufficient_context ou ambiguous_retrieval ainda chama o LLM; o que muda é o contrato de grounding injectado, os badges na UI e, em strict, a possibilidade de override no final.

Se quiser, no próximo turno posso mapear qual grounding_*.txt entra em cada combinação (reason × ACL_GROUNDING_POLICY × desambiguação activa).


/doc O ficheiro sticky_instruction.txt é injectado no prompt quando há pin activo? Onde está definido e qual o estado actual segundo a wiki?
Kernel · 10:13
Documentação · 07 apis e sse
Documentação · 08 frontend ui
Documentação · 06 gates e decisoes
Documentação · 17 prompts referencia
Documentação · 19 faq usuario
+2 ficheiros
Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.
Vou confirmar no código e na wiki se sticky_instruction.txt entra no prompt com pin activo.
Sim — com pin activo e display_name preenchido, o bloco de sticky_instruction.txt entra no system prompt. O que a wiki indexada ainda diz em alguns sítios está desactualizado em relação ao código.

Resposta directa
Pergunta	Resposta
É injectado com pin activo?	Sim, quando existe pin na sessão e pin.display_name não está vazio
Onde está definido?	Ficheiro + carregamento + wiring no prompt (ver abaixo)
Estado na wiki	Inconsistente — uma página diz “pendente”, outras e o backlog dizem “feito”
Onde está definido
1. Ficheiro de template

core/systemPrompt/sticky_instruction.txt — template com placeholder {name} para o tema fixado (ex.: «07 apis e sse»).

2. Carregamento no boot

core/config.py → Settings.load() lê o ficheiro para Settings.sticky_instruction. Se o ficheiro faltar, o servidor não arranca (obrigatório, como os outros prompts) [Fonte: db:doc/17-prompts-referencia].

3. Inject no prompt

Em engine/context.py:

_sticky_block_for_pin() — formata settings.sticky_instruction.format(name=pin.display_name) se houver pin com nome;
_assemble_system_content() — coloca o bloco sticky depois do catálogo e antes do grounding e dos trechos RAG [Fonte: db:doc/09-fluxos-operacionais] [Fonte: db:doc/12-configuracao].
Ordem efectiva do system prompt:

system_prompt.txt
→ catalog_router + catalog_section (se houver)
→ sticky_instruction (se pin activo)
→ grounding (strict/anchored/…)
→ trechos [Fonte: …]
Isto bate certo com o bloco «Sessão com contexto fixado» que estás a ver neste turno — é o conteúdo desse ficheiro formatado com o tema do pin.

Condição para injectar
Não basta “pin activo” abstracto: _sticky_block_for_pin devolve string vazia se:

não há pin na sessão, ou
pin.display_name está vazio.
O display_name vem do pin guardado em PinnedSessionStore após um turno com chunks (RAG ou /doc) [Fonte: db:doc/09-fluxos-operacionais].

Estado actual segundo a wiki (drift)
Há contradição entre páginas indexadas:

Documento	O que diz
17-prompts-referencia.md	«ainda não injectado em context.py»; backlog P1 ainda aberto [Fonte: db:doc/17-prompts-referencia]
16-backlog.md	B10 feito — «merge pin + sticky em context.py»
09-fluxos-operacionais.md	Sticky injectado antes do grounding em _assemble_system_content() [Fonte: db:doc/09-fluxos-operacionais]
12-configuracao.md	Merge no pin referenciado [Fonte: db:doc/12-configuracao]
Verdade operacional (código): implementado — o item P1/B10 da wiki ficou por actualizar em 17-prompts-referencia.md (incluindo a tabela de diagnóstico que ainda fala em «wiring pendente»).

Síntese
Runtime: sticky_instruction.txt é injectado em turnos com pin que tenha display_name.
Definição: core/systemPrompt/sticky_instruction.txt → Settings.sticky_instruction → _sticky_block_for_pin → _assemble_system_content.
Wiki: trata 09 + backlog B10 como SSOT do estado actual; ignora a linha desactualizada de 17-prompts-referencia até alguém sincronizar (backlog P4 — «Sincronizar esta página quando mudar core/systemPrompt/»).
Queres que no próximo turno detalhe a diferença entre pin activo (pinned_active no SSE) e pin_chunks_used (merge de chunks fixados vs retrieval)?

/doc Como o KernelBot protege segredos nos logs, o que acontece quando OpenRouter ou Cursor falham, e que superfícies exigem Bearer token?
Kernel · 10:14
Documentação · 07 apis e sse
Documentação · 08 frontend ui
Documentação · 06 gates e decisoes
Documentação · 17 prompts referencia
Documentação · 19 faq usuario
+2 ficheiros
Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.
Vou cruzar a documentação indexada com o código sobre logs/segredos, falhas de providers e superfícies com Bearer.
Três camadas distintas: observabilidade, degradação do LLM e auth operacional. Resumo ancorado no material indexado.

1. Proteção de segredos nos logs
O KernelBot usa uma pipeline de redacção em core/structured_log.py + core/logging_config.py [Fonte: db:doc/14-seguranca-observabilidade] [Fonte: db:doc/03-estrutura-codigo]:

Peça	Função
redact_secrets()	Sanitiza strings antes de irem para o log
SecretRedactingFilter	Filtro no handler — última linha de defesa sobre msg e exc_text
log_event()	Aplica redacção também em metadata e tracebacks JSON
Padrões mascarados hoje (regex em _SECRET_PATTERNS):

password= / DB_PASSWORD=
URLs com credenciais (//user:***@host)
Fragmentos PyMySQL com password
Princípio importante: exc_info=True não amputa stack traces — só redige credenciais dentro deles [Fonte: db:doc/14-seguranca-observabilidade].

Outros segredos (fora do redactor automático):

Secret	Onde vive	Nota
OPENROUTER_API_KEY	.env	Wiki indica redacção em logs; backlog B5 pede expandir padrões (mais API keys, URLs com credenciais) [Fonte: db:doc/14-seguranca-observabilidade] [Fonte: db:doc/16-backlog]
ACL_RELOAD_BEARER_TOKEN	.env / GHA secrets	Só no header HTTP — não deve ir para logs
MySQL password	.env	Coberto pelos padrões password/DB_PASSWORD
Regra de ouro: nunca commitar .env ou .env.staging.local [Fonte: db:doc/14-seguranca-observabilidade]. Na ingest ISS, _sanitize_error() em ingest-knowledge.py evita vazar passwords em logs de CI [Fonte: db:doc/14-seguranca-observabilidade].

2. Quando OpenRouter ou Cursor falham
provider_error é o único DecisionReason de retrieval/gates que não chama o LLM para gerar resposta — emite texto fixo [Fonte: db:doc/06-gates-e-decisoes].

OpenRouter (ACL_LLM_PROVIDER=openrouter)
Fluxo em engine/chat_provider.py:

Emite [ACL_META] inicial (llm_called=true).
Percorre a lista de modelos (ACL_MODELS) com fallback:
HTTP 429 → próximo modelo
HTTP ≥ 400 → log llm_http_error, próximo modelo
Timeout httpx → próximo modelo
Excepção → log + próximo modelo
Se todos falharem:
Novo [ACL_META]: decision=hard_stop, reason=provider_error, allow_generation=false, llm_called=false, confidence=low
Texto fixo streamed (sem tokens do modelo)
data: [DONE]
Mensagem ao utilizador (HARD_STOP_MESSAGES):

Tive um problema técnico ao contatar o modelo de linguagem.

Tente novamente em alguns instantes. Se persistir, avise o responsável.
[Fonte: db:doc/06-gates-e-decisoes] [Fonte: db:doc/08-frontend-ui]

Cursor SDK (default local)
Sem fallback multi-modelo. Falhas mapeadas para o mesmo provider_error:

Situação	Comportamento
Import de cursor_sdk falha	provider_error imediato
CursorAgentError	Log cursor_sdk_error → hard stop
Qualquer outra excepção	Log + hard stop
Contrato SSE idêntico ao OpenRouter [Fonte: db:doc/07-apis-e-sse].

O que a UI faz
Campo	Valor
reason	provider_error
allow_generation	false
decision	hard_stop
Efeito	Texto fixo streamed; sem markdown gerado pelo LLM [Fonte: db:doc/08-frontend-ui]
Gates de retrieval (insufficient_context, ambiguous_retrieval, etc.) continuam a chamar o LLM — só falha operacional do provider corta a geração [Fonte: db:doc/06-gates-e-decisoes] [Fonte: db:doc/01-visao-geral].

3. Superfícies que exigem Bearer token
Token: ACL_RELOAD_BEARER_TOKEN (alias legado KERNELBOT_RELOAD_TOKEN) [Fonte: db:doc/07-apis-e-sse] [Fonte: db:doc/12-configuracao].

Validação: _verify_reload_bearer() em api/routes.py — comparação timing-safe com secrets.compare_digest.

Superfície	Auth	Respostas de erro
POST /chat com {"message": "/reload"}	Authorization: Bearer <token>	Token ausente no servidor → 503; header inválido/ausente → 401
GET /health/catalog	Mesmo Bearer	Idem
Sem Bearer (acesso público na demo/POC):

Rota	Uso
GET /	UI do chat
POST /chat	Chat normal, /reset, perguntas
GET /health	Liveness (Docker/K8s) — sem auth [Fonte: db:doc/07-apis-e-sse]
Nota: não existe rota POST /reload dedicada — /reload é mensagem no corpo de POST /chat [Fonte: db:doc/07-apis-e-sse]. /reset não exige Bearer.

O workflow ISS sync-kernelbot-knowledge usa o mesmo token para /reload e GET /health/catalog (drift catálogo vs índice) [Fonte: db:doc/07-apis-e-sse].

Síntese
Logs: redacção em camadas (redact_secrets + filtro no handler); stack traces preservados; padrões focados em passwords/URLs — expansão para mais API keys está no backlog.
Falha LLM: provider_error → hard stop SSE, texto fixo, sem chamada efectiva ao modelo; OpenRouter tenta vários modelos antes de desistir; Cursor falha directo.
Bearer: só /reload (via POST /chat) e GET /health/catalog; chat normal e /health são abertos.
Quer o detalhe do que entra em GET /health/catalog (campos de drift) ou como o Job 3 da ISS encadeia reload + verificação?

/doc Com KERNELBOT_ENV=staging, qual ficheiro de ambiente tem prioridade sobre o .env principal para DB_HOST e DB_PORT, e por que não devo correr python main.py directamente contra Aiven por engano?
Kernel · 10:14
Tema fixado em «07 apis e sse». A pergunta parece ser de Python — use /python no início ou /reset para limpar o contexto fixado.
Documentação · 07 apis e sse
Documentação · 08 frontend ui
Documentação · 06 gates e decisoes
Documentação · 17 prompts referencia
Documentação · 19 faq usuario
+2 ficheiros
Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.
Vou localizar na documentação e no código como o KERNELBOT_ENV=staging escolhe o ficheiro de ambiente e o que isso implica para DB_HOST/DB_PORT.
Com KERNELBOT_ENV=staging, quem manda em DB_HOST e DB_PORT é o .env.staging.local, não o .env principal.

Prioridade dos ficheiros
Em Settings.load() (core/config.py), quando KERNELBOT_ENV=staging e o ficheiro existe, a sequência é:

Carrega .env.staging.local com override=True
Carrega .env (dotenv normal)
Volta a carregar .env.staging.local com override=True
Ou seja: o staging sobrepõe o .env nas variáveis que estiverem definidas nos dois — incluindo DB_HOST e DB_PORT [Fonte: db:doc/12-configuracao].

Ficheiro	Papel típico
.env	Produção/dev — provider LLM, credenciais Aiven, tokens
.env.staging.local	MySQL Docker local — :3307, DB kernelbot_staging [Fonte: db:doc/12-configuracao] [Fonte: db:doc/04-dados-e-mysql]
Valores esperados no staging [Fonte: db:doc/12-configuracao]:

DB_HOST → 127.0.0.1
DB_PORT → 3307 (em vez de 3306 do .env)
O .env.staging.local não entra no git; o modelo fica em .env.staging.example [Fonte: db:doc/12-configuracao] [Fonte: db:doc/13-staging-testes].

Por que não correr python main.py “a olho” contra Aiven
Três motivos práticos, todos documentados:

1. Sem KERNELBOT_ENV=staging, ganha o .env → Aiven
Se fizeres só python main.py, o Python não aplica o override do staging. Lê o .env principal, que normalmente aponta para MySQL gerido (Aiven/produção) [Fonte: db:doc/04-dados-e-mysql]. Resultado: ou ligas à base de prod por engano, ou o boot rebenta se Aiven não estiver acessível da tua máquina — a wiki regista exactamente isso na tabela de erros de staging [Fonte: db:doc/13-staging-testes].

2. O script de staging garante o contexto certo
bin/staging-serve.sh faz o que um python main.py solto não garante:

export KERNELBOT_ENV=staging
export ACL_CATALOG_ENABLED=false
# … source .env.staging.local no shell …
exec .venv/bin/python main.py
[Fonte: bin/staging-serve.sh via doc/13-staging-testes]

Sem isto, perdes o override de DB e flags de staging (ex.: catálogo desligado).

3. Separação intencional: DB local, chaves LLM no .env
O script não faz source .env no bash (API keys com caracteres especiais partem o shell). O Python carrega o .env para OPENROUTER_API_KEY / CURSOR_API_KEY, mas o MySQL fica ancorado no .env.staging.local via KERNELBOT_ENV [Fonte: db:doc/13-staging-testes].

Caminho seguro
./bin/staging-setup.sh   # uma vez
./bin/staging-serve.sh   # arrancar — não python main.py directo
Esperado: http://127.0.0.1:8001 com MySQL em 127.0.0.1:3307/kernelbot_staging [Fonte: db:doc/13-staging-testes].

Resumo: staging = .env.staging.local ganha em DB_*; python main.py sem o fluxo de staging arrisca Aiven (crash ou pior — escrita em prod). Usa os scripts bin/staging-*.sh.

/doc Qual a ordem exacta de _assemble_system_content no system prompt, e qual a precedência semântica entre grounding_strict, catálogo e trechos RAG segundo a wiki de prompts?
Kernel · 10:14
Documentação · 07 apis e sse
Documentação · 08 frontend ui
Documentação · 06 gates e decisoes
Documentação · 17 prompts referencia
Documentação · 19 faq usuario
+2 ficheiros
Rodapé deste turno combina fontes do contexto anterior com a busca atual — use /reset ou um comando de disciplina (/python, /visualizacao-sql…) para alinhar.
Vou localizar _assemble_system_content no código e cruzar com a wiki de prompts sobre precedência semântica.
A ordem física no system message vem de _assemble_system_content(); a precedência semântica (quem ganha em conflito) está na wiki §17 e espelhada em system_prompt.txt — são duas coisas relacionadas, mas não idênticas.

Ordem exacta em _assemble_system_content()
Implementação em engine/context.py:

def _assemble_system_content(
    base_prompt: str,
    catalog_router: str,
    catalog_section: str,
    grounding: str,
    chunk_context: str,
    *,
    sticky_block: str = "",
) -> str:
    parts = [base_prompt]
    if catalog_section:
        parts.append(catalog_router)
        parts.append(catalog_section)
    if sticky_block:
        parts.append(sticky_block)
    parts.append(grounding)
    if chunk_context:
        parts.append(chunk_context)
    return "

".join(parts)
#	Bloco	Origem	Condição
1	base_prompt	system_prompt.txt	Sempre
2	catalog_router	catalog_router.txt	Só se catalog_section não estiver vazio (match lexical no catálogo)
3	catalog_section	LessonCatalog.build_prompt_section()	Idem — dinâmico
4	sticky_block	sticky_instruction.txt formatado com {name} do pin	Só se há pin activo com display_name
5	grounding	_select_grounding() — strict | anchored | permissive | disambiguation	Sempre
6	chunk_context	Trechos RAG via _format_chunks_for_prompt()	Só se há chunks
Blocos unidos com `

` (dupla quebra de linha).

A wiki 17-prompts-referencia lista os passos 1–3, 5 e 6, mas omite o passo 4 (sticky_block). No runtime actual, com pin activo, o sticky entra entre catálogo e grounding [Fonte: db:doc/09-fluxos-operacionais] — a tabela da wiki §17 ainda diz que sticky_instruction.txt «ainda não injectado», o que está desactualizado face ao código.

Nota sobre grounding_strict: o slot 5 não é sempre grounding_strict.txt. _select_grounding() escolhe o ficheiro conforme ACL_GROUNDING_POLICY e decision.reason (default anchored; disambiguation em ambiguous_retrieval + flag ON) [Fonte: db:doc/06-gates-e-decisoes].

Precedência semântica (wiki de prompts)
Tabela da wiki §17 — prioridade em conflito, não ordem física [Fonte: db:doc/17-prompts-referencia]:

Prioridade	Camada	Origem
1 (máxima)	Grounding factual	grounding_strict.txt (ou variante activa: anchored, permissive, disambiguation)
2	Catálogo (escopo)	catalog_router.txt + secção dinâmica
3	Evidência	Trechos [Fonte: …] (ou [Fonte 1: …] na desambiguação)
4	Identidade e tom	system_prompt.txt
5 (mínima)	Dados do utilizador em Markdown	Tratados como dado, não como ordem
O mesmo contrato está declarado em system_prompt.txt §2 (grounding injectado > catálogo > trechos RAG > identidade > conteúdo do utilizador).

Como encaixam grounding_strict, catálogo e RAG
São papéis diferentes, com hierarquia explícita:

Grounding (ex.: grounding_strict.txt) — regras duras de como responder: só factos nos trechos, proibir inventar, declarar lacunas [Fonte: db:doc/17-prompts-referencia]. Em strict, «esta secção sobrepõe-se a qualquer instrução de tom» — ganha a identidade e ao tom didático.

Catálogo (catalog_router + secção dinâmica) — orienta escopo (título, disciplina, slug, resumo); não é prova factual [Fonte: db:doc/17-prompts-referencia]. O próprio catalog_router.txt reforça: meta «serve só para foco temático» e «não substituem os trechos RAG».

Trechos RAG [Fonte: …] — evidência indexada sobre a qual o grounding autoriza citar factos. Catálogo diz onde provavelmente está o tema; RAG traz o texto recuperado.

Resumo prático: grounding manda nas regras → catálogo manda no foco → RAG manda nos factos → identidade/tom só quando não há conflito.

A wiki §4 acrescenta o princípio de engenharia: «Meta orienta, dados provam» (catalog_router + build_prompt_section) e que a precedência operacional coloca o bloco de grounding por último antes dos chunks na montagem física — posição que reforça a prioridade semântica [Fonte: db:doc/17-prompts-referencia].

Montagem física vs precedência (diagrama)
ORDEM FÍSICA (top → bottom do system prompt):
  system_prompt.txt
  [catalog_router + catalog_section]     ← opcional
  [sticky_instruction]                 ← opcional (pin); wiki §17 incompleto
  grounding (strict|anchored|…)        ← regras duras
  [Fonte: …] trechos RAG               ← evidência

PRECEDÊNCIA SEMÂNTICA (conflito):
  grounding > catálogo > trechos RAG > system_prompt > dados do user
Se quiseres, no próximo turno posso cruzar isto com _select_grounding() turno a turno (ex.: pin activo + ambiguous_retrieval + catálogo match simultâneo).

