# Guião de apresentação

Sistema de escrita e leitura multiprotocolo

Pedro Ribeiro e Francisco Liquito

Versão de 29 de outubro de 2026. Preparação para os 10 slides sobre integração de equipamentos em sistemas robóticos. Objetivo de ensaio: cerca de 9 minutos, dentro da duração prevista de 7 a 10 minutos.

## Divisão e tempos

**Pedro apresenta os slides 1 a 5:** aplicação, problema, fundamentos, estado da arte e exemplo de utilização. **Francisco Liquito apresenta os slides 6 a 10:** capacidades requeridas, atuação e tempo, arquitetura, verificação e contributo. Há uma única passagem de palavra, no fim do slide 5.

| Slide | Tema | Orador | Tempo previsto | Tempo acumulado |
| --- | --- | --- | --- | --- |
| 1 | Abertura e aplicação | Pedro | 0:40 | 0:40 |
| 2 | Integração num sistema robótico | Pedro | 0:50 | 1:30 |
| 3 | Fundamentos das interfaces | Pedro | 0:55 | 2:25 |
| 4 | Estado da arte: plataformas | Pedro | 0:50 | 3:15 |
| 5 | Exemplo de comando e utilização | Pedro | 1:00 | 4:15 |
| 6 | Capacidades de comunicação | Liquito | 1:05 | 5:20 |
| 7 | Atuação, tempo e concorrência | Liquito | 1:15 | 6:35 |
| 8 | Arquitetura de alto nível | Liquito | 0:55 | 7:30 |
| 9 | Verificação das capacidades | Liquito | 0:55 | 8:25 |
| 10 | Contributo e próxima fase | Liquito | 0:35 | 9:00 |

**Total:** Pedro, 4 min 15 s. Liquito, 4 min 45 s. Apresentação, 9 minutos, sem contar com perguntas. Ajustem estes tempos no ensaio conjunto.

### Ideia que orienta a apresentação

Mostrar como a unidade poderá facilitar a integração de equipamentos com interfaces diferentes e preparar a sua reutilização em sistemas robóticos. Cada requisito deve ter uma função compreensível nesse contexto.

As falas são uma base para explicar os slides. As indicações «No slide» e «A reter» servem para preparação. Nesta fase existem análise de requisitos e arquitetura conceptual. A implementação e os resultados experimentais pertencem à fase seguinte.

<!-- pagebreak -->

## Pedro: aplicação e problema

### Slide 1. Sistema de escrita e leitura multiprotocolo

**Pedro. 40 segundos.**

**Fala sugerida**

> Bom dia. Somos o Pedro Ribeiro e o Francisco Liquito.
>
> Num sistema robótico, motores, baterias e sensores podem utilizar interfaces de comunicação diferentes. O nosso objetivo é desenvolver uma unidade que concentre o acesso a esses equipamentos, permitindo ao PC enviar comandos e receber dados através das interfaces previstas. Pretendemos facilitar a integração e preparar a reutilização da unidade em diferentes sistemas.
>
> Hoje apresentamos o problema, os requisitos e a arquitetura prevista.

**No slide:** apresentar os autores e começar logo pela aplicação. A abertura deve tornar clara a utilidade pretendida.

**A reter:** a reutilização é um objetivo. Cada aplicação exige protocolos, configurações e mapeamentos compatíveis.

### Slide 2. Integração num sistema robótico

**Pedro. 50 segundos.**

**Fala sugerida**

> Consideremos um sistema com um motor em CAN, uma bateria em RS485 e um sensor em I2C ou RS232. São exemplos de equipamentos referidos pelo docente. O PC precisa de lhes aceder para enviar comandos e recolher informação.
>
> A dificuldade envolve identificar o destino de cada pedido, interpretar os dados e gerir operações que decorrem com ritmos diferentes. Também precisamos de relacionar os instantes das medições com outras fontes de informação.
>
> A unidade que propomos concentra estas ligações. Os equipamentos concretos e os respetivos mapeamentos serão definidos para a aplicação.

**No slide:** apontar para os equipamentos da direita e explicar as dificuldades da esquerda. As ligações representam necessidades funcionais de acesso.

**A reter:** o esquema é ilustrativo. A ligação física aos barramentos requer a adaptação apropriada. Não se promete compatibilidade automática entre quaisquer robôs.

<!-- pagebreak -->

## Pedro: fundamentos e soluções existentes

### Slide 3. Fundamentos das interfaces de comunicação

**Pedro. 55 segundos.**

**Fala sugerida**

> Para integrar estes equipamentos, começámos por estudar as diferenças entre as cinco tecnologias. I2C partilha um barramento local. RS232 estabelece uma ligação ponto a ponto e RS485 permite uma rede multiponto, cujo protocolo de aplicação tem de ser definido.
>
> CAN FD utiliza arbitragem e identificadores de trama e exige configurar as fases de transmissão. Em Ethernet, temos de distinguir a taxa nominal do débito útil e definir o formato das mensagens.
>
> Estas diferenças explicam a necessidade de mapeamentos: cada operação deve preservar o significado do comando ou dos dados ao passar entre protocolos. Esse tratamento será parte do projeto.

**No slide:** escolher as diferenças que explicam o trabalho de integração. Terminar com a conclusão sobre o significado dos dados.

**A reter:** a interface física não define o protocolo de aplicação. O identificador CAN não equivale automaticamente a um endereço de nó. Nenhum transporte concreto está selecionado.

### Slide 4. Estado da arte: plataformas

**Pedro. 50 segundos.**

**Fala sugerida**

> Analisámos plataformas programáveis e conversores dedicados para perceber como outras soluções fazem esta integração.
>
> GoWired anuncia recursos de comunicação cujo desempenho não avaliámos. No IOT-GATE-iMX7, a opção CAN substitui RS485, mostrando que é necessário verificar as combinações disponíveis. MGate e Anybus integram protocolos e papéis específicos, com mapeamentos definidos.
>
> Para o nosso projeto, esta comparação mostra que a seleção terá de considerar o conjunto das interfaces e as operações pretendidas. A plataforma permanece por selecionar. Ainda não demonstrámos que uma destas soluções satisfaça todos os requisitos.

**No slide:** usar um exemplo de plataforma e um de conversor para explicar a conclusão. Evitar ler todas as células.

**A reter:** não afirmar ausência de solução comercial compatível, redução de custos ou superioridade de desempenho sem evidência.

<!-- pagebreak -->

## Pedro e Liquito: utilização e capacidades pedidas

### Slide 5. Um comando do PC até ao dispositivo

**Pedro. 1 minuto, incluindo a passagem de palavra.**

**Fala sugerida**

> Retomemos o motor em CAN. Neste exemplo, o PC envia uma operação por Ethernet. A unidade identifica o canal e o destino e aplica o mapeamento necessário para enviar o comando ao dispositivo. Quando a operação prevê feedback, a resposta regressa ao PC.
>
> A aquisição de sensores e a atuação por PWM completam as operações principais. Os restantes casos de utilização cobrem concorrência, sincronização, condições de funcionamento e disponibilização de dados, com registo local opcional.
>
> Este percurso mostra a função da unidade. O Francisco vai agora apresentar as capacidades pedidas pelos docentes e a arquitetura que as organiza.

**No slide:** percorrer o esquema da esquerda para a direita e explicar o retorno. Relacionar os restantes casos com essa operação.

**A reter:** o exemplo usa Ethernet, mas o PC também deve poder aceder por RS232 e CAN. UC01 a UC07 mantêm o âmbito do relatório.

### Passagem para o Liquito

**Pedro termina:** «O Francisco vai agora apresentar as capacidades pedidas pelos docentes e a arquitetura que as organiza.»

**Liquito começa, no slide 6:** «Estas são as quantidades e capacidades confirmadas pelos docentes para a unidade.»

### Slide 6. Capacidades de comunicação requeridas

**Liquito. 1 minuto e 5 segundos.**

**Fala sugerida**

> Estas são as quantidades e capacidades confirmadas pelos docentes para a unidade.
>
> São dois I2C independentes em Standard mode. RS232 deve operar a 500 kbit/s, com capacidade e ensaio também a 1 Mbit/s. RS485 usa aproximadamente 16 a 32 nós como referência, sem teto rígido de 32. A taxa e o protocolo estão em aberto.
>
> Exigem-se três CAN FD no total, cada um com capacidade até 8 Mbit/s. Ethernet deve suportar pelo menos 100 Mbit/s nominais, com Gigabit desejável.
>
> O PC terá as alternativas RS232, CAN e Ethernet, todas bidirecionais, sem utilização simultânea obrigatória. A configuração e o dimensionamento ficam para projeto.

**No slide:** destacar as quantidades e separar a operação RS232 da capacidade máxima. Os valores têm origem nos requisitos recebidos.

**A reter:** o cenário ilustrativo não fundamenta numericamente estas quantidades. Os 8 Mbit/s não fixam as taxas separadas das fases CAN FD.

<!-- pagebreak -->

## Liquito: funções e arquitetura

### Slide 7. Atuação, referência temporal e concorrência

**Liquito. 1 minuto e 15 segundos.**

**Fala sugerida**

> A unidade também deve atuar sobre cargas. Exigimos três PWM eletricamente protegidos, a 50 Hz, com impulsos entre 1100 e 1900 microssegundos. As cargas e a proteção concreta serão definidas no projeto.
>
> Para relacionar dados no tempo, usamos PPS a um impulso por segundo e informação temporal GPS entre impulsos. Esta associação deve permitir resolução da ordem dos microssegundos. Mediremos o erro e avaliaremos a incerteza, porque a resolução não garante igual exatidão absoluta.
>
> A concorrência exige gerir filas e prioridades entre operações com ritmos diferentes. O RTOS é obrigatório e FreeRTOS é candidato. As cargas admissíveis e a política de atendimento serão especificadas.
>
> A entrada de alimentação deve aceitar de 5 a 60 volts, incluindo os limites.

**No slide:** ligar cada coluna à necessidade de utilização. Os esquemas temporais são ilustrativos e não estão à escala.

**A reter:** definir resolução PWM, cargas, tolerâncias e recuperação temporal. O RTOS não garante sozinho cumprimento de prazos. A alimentação de entrada não determina a tensão das cargas PWM.

### Slide 8. Arquitetura de alto nível

**Liquito. 55 segundos.**

**Fala sugerida**

> A arquitetura organiza estas funções numa unidade embebida central. O PC acede pelas interfaces previstas e a unidade trata operações e mapeamentos, gere filas e prioridades sobre RTOS e associa informação temporal.
>
> À direita estão os equipamentos externos. A referência PPS e GPS alimenta a sincronização do relógio. Os PWM comandam as cargas e a microSD permanece uma opção de registo.
>
> Os três CAN FD são o total do sistema, incluindo os diferentes papéis de ligação. Os blocos representam responsabilidades funcionais. A distribuição por componentes e tarefas será definida no projeto.

**No slide:** seguir o percurso do comando apresentado no slide 5 e mostrar as funções que o suportam.

**A reter:** Ethernet não tem de intermediar todos os percursos. O desenho não acrescenta portas dedicadas nem seleciona componentes ou tarefas de software.

<!-- pagebreak -->

## Liquito: verificação e contributo

### Slide 9. Verificação das capacidades previstas

**Liquito. 55 segundos.**

**Fala sugerida**

> Para demonstrar estas capacidades, os ensaios vão retomar os percursos e as condições definidos na especificação.
>
> RF17 exige, como mínimo, os quatro pares Ethernet com CAN, RS485, RS232 e I2C, nos dois sentidos. Outros percursos, como CAN para RS485, podem ser definidos em projeto, com operações, protocolos e mapeamentos compatíveis.
>
> Verificaremos cada percurso definido com dados conhecidos e avaliaremos a concorrência nas cargas especificadas. Mediremos os PWM, o funcionamento elétrico e a sincronização, distinguindo resolução, erro e incerteza.
>
> As condições e as tolerâncias serão definidas antes dos ensaios de conformidade. Ainda não existem resultados experimentais.

**No slide:** apresentar o mínimo obrigatório à esquerda e ligar os ensaios às capacidades à direita. Usar verbos no futuro.

**A reter:** todos os percursos adicionais efetivamente definidos também serão ensaiados. A representação com Ethernet não limita todas as operações a essa interface.

### Slide 10. Contributo pretendido e próxima fase

**Liquito. 35 segundos.**

**Fala sugerida**

> O contributo pretendido é uma unidade que concentre o acesso aos equipamentos e possa ser reutilizada em diferentes sistemas, com os protocolos e mapeamentos apropriados.
>
> Temos os requisitos e a arquitetura documentados. Seguem-se a seleção da plataforma, o dimensionamento, a implementação e os ensaios.
>
> O funcionamento em óleo e sob pressão surge como possibilidade futura, cujas condições e validação permanecem por definir. Obrigado. Estamos disponíveis para questões.

**No slide:** terminar na utilidade pretendida e explicar o estado de desenvolvimento. Apresentar pressão como possibilidade futura.

**A reter:** RNF01 a RNF03 e RNF05 são propostas. MicroSD e PoE são opcionais. Gigabit é desejável. Não há resistência à pressão demonstrada.

<!-- pagebreak -->


## Perguntas para ensaiar: enquadramento e âmbito

As respostas seguintes servem de base ao ensaio. O orador indicado responde primeiro. O outro complementa quando houver um ponto concreto a acrescentar.

### 1. Qual é o contributo do projeto face aos gateways existentes?

**Pedro responde.**

«Pretendemos concentrar o acesso a equipamentos com interfaces diferentes e preparar a reutilização da unidade em sistemas robóticos, com os protocolos e mapeamentos apropriados. O estado da arte esclarece possibilidades e limitações. A escolha e a avaliação da solução concreta pertencem à fase de projeto.»

**Cuidado:** a comparação feita ainda não permite afirmar que não exista uma solução comercial compatível ou que tenhamos demonstrado superioridade de desempenho.

### 2. Porque compararam plataformas programáveis com conversores dedicados?

**Pedro responde.**

«São modelos de integração diferentes. Nas plataformas programáveis temos de avaliar a configuração de hardware e o software. Nos conversores dedicados, as funções dependem dos protocolos e papéis suportados. Esta distinção ajuda a identificar o que precisamos de desenvolver e verificar.»

### 3. O PC tem de usar RS232, CAN e Ethernet ao mesmo tempo?

**Liquito responde.**

«As três alternativas têm de ser suportadas de forma bidirecional. A especificação não exige a sua utilização simultânea pelo PC. A concorrência entre operações e interfaces continua a fazer parte dos requisitos do sistema.»

**Referência:** RF09 e RF12. Evitar confundir as alternativas de acesso do PC com a gestão de comunicações concorrentes.

### 4. Conseguem converter qualquer interface em qualquer outra?

**Liquito responde.**

«O mínimo obrigatório inclui Ethernet com CAN, RS485, RS232 e I2C, nos dois sentidos. Outros percursos, como CAN para RS485, podem ser definidos e implementados em projeto, com os protocolos e mapeamentos necessários. Ethernet não tem de intermediar todas as operações.»

**Referência:** RF17 e DP01 a DP02. Distinguir o mínimo obrigatório dos percursos adicionais. Cada percurso definido terá de ser ensaiado, sem prometer conversão semântica automática.

### 5. De onde vêm os valores e porque ficaram parâmetros por definir?

**Pedro responde e o Liquito complementa, se necessário.**

«As quantidades e os valores confirmados provêm das indicações dos docentes. Identificámos os parâmetros restantes nas decisões DP01 a DP17. Serão definidos na fase de projeto, em função da plataforma, dos dispositivos, das cargas e das condições de ensaio. Mantemos os valores já confirmados e documentaremos as decisões restantes antes de dimensionar e validar a solução.»

**Cuidado:** evitar apresentar um valor por omissão como requisito confirmado. Uma norma não resolve todas as configurações da aplicação.


<!-- pagebreak -->


## Perguntas para ensaiar: decisões técnicas

### 6. Porque precisam de RTOS? Já escolheram FreeRTOS?

**Liquito responde.**

«O RTOS é uma restrição confirmada do projeto e suporta a organização da concorrência, das prioridades e da temporização. FreeRTOS é candidato. A escolha concreta e a organização das tarefas ficam para projeto. A presença de RTOS não estabelece, por si só, uma garantia de tempo real estrito.»

### 7. A sincronização garante um erro de um microssegundo?

**Liquito responde.**

«O requisito estabelece resolução temporal da ordem dos microssegundos. O erro absoluto face à referência e a incerteza da sua medição serão avaliados separadamente. A escala temporal, a associação entre mensagens e impulsos e a recuperação após perda de referência ficam em DP14.»

### 8. Os 8 Mbit/s são a taxa de ambas as fases de CAN FD?

**Liquito responde.**

«Temos três barramentos, cada um com capacidade até 8 Mbit/s. A indicação recebida não fixa separadamente as taxas das fases de arbitragem e de dados. Documentaremos essa configuração no projeto e usá-la-emos nos ensaios.»

### 9. Como demonstram conformidade se ainda faltam tolerâncias?

**Liquito responde.**

«Os valores nominais orientam as medições, mas as tolerâncias e a regra de decisão têm de estar definidas antes dos ensaios de conformidade. Para grandezas sem limite de aceitação, faremos caracterização experimental e reportaremos o resultado e a incerteza, sem declarar cumprimento de um limite inexistente.»

### 10. Quando poderá ser utilizada num robô ou sob pressão?

**Liquito responde.**

«Temos a análise de requisitos e a arquitetura conceptual. É necessário selecionar e dimensionar a solução, implementar e realizar os ensaios. A utilização num sistema concreto depende da compatibilidade com os seus equipamentos. Óleo e pressão surgiram como interesse ideal e um possível acrescento, sem condições quantitativas confirmadas. Essa aplicação precisa de especificação e validação próprias.»


<!-- pagebreak -->


## Ensaio e folha de memória

### Ensaio conjunto

1. **Primeiro ensaio:** cada um explica a sua parte com os slides abertos, usando o guião apenas para recuperar a sequência.
2. **Segundo ensaio:** cronometrar do início ao fim, incluindo a passagem de palavra. Apontar onde o ritmo abranda e ajustar as explicações.
3. **Terceiro ensaio:** alternar as dez perguntas anteriores. Ambos devem saber explicar os valores principais e a arquitetura.

Se precisarem de encurtar a apresentação, reduzam os comentários sobre plataformas. Conservem o cenário que explica a utilidade da unidade. Conservem os valores confirmados, o âmbito dos percursos e a distinção entre requisitos e resultados medidos.

**Antes de apresentar:** confirmar a versão do PowerPoint, testar a projeção e o comando, combinar quem avança os slides e fechar a última frase de cada bloco.

### Valores e estados para fixar

| Tema | Valor ou estado | Atenção na explicação |
| --- | --- | --- |
| I2C | 2 barramentos independentes, Standard mode | Restantes configurações para projeto |
| RS232 | Operação a 500 kbit/s, capacidade até 1 Mbit/s | Inclui ensaio de comunicação a 1 Mbit/s |
| RS485 | Aproximadamente 16 a 32 nós de referência | Sem teto rígido de 32, taxa em aberto |
| CAN FD | 3 barramentos no total, até 8 Mbit/s em cada | Distribuição e taxas de cada fase por definir |
| Ethernet | Mínimo nominal de 100 Mbit/s | Gigabit desejável, débito útil a avaliar |
| Encaminhamento | Quatro pares mínimos Ethernet, nos dois sentidos | Outros percursos podem ser definidos em projeto e ensaiados |
| PWM | 3 protegidos, 50 Hz, impulsos de 1100 a 1900 µs | Resolução, cargas e tolerâncias em aberto |
| PPS/GPS | PPS a 1 Hz, GPS entre impulsos, resolução da ordem dos µs | Medir erro e avaliar incerteza |
| Alimentação e RTOS | Entrada de 5 a 60 V, RTOS obrigatório | FreeRTOS candidato, componentes por selecionar |
| Reutilização e pressão | Reutilização pretendida com configuração. Óleo e pressão como possibilidade futura | Condições e validação próprias por definir |
| Propostas e opções | RNF01 a RNF03 e RNF05 são propostas. MicroSD e PoE opcionais | Não apresentar estes estados como obrigações confirmadas |

**Apoio para estudar:** o [PowerPoint atualizado](output/Apresentacao_LaSET_Integracao_Robotica_Revista.pptx) e o [relatório](../template_laset/build/Modelo_LaSET.pdf). Para aprofundar: secções 1.2, 2.8, 3.1 a 3.7 e capítulo 4 do relatório.
