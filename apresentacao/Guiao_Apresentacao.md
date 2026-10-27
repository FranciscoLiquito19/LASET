# Guião de apresentação

Sistema de escrita e leitura multiprotocolo

Pedro Ribeiro e Francisco Liquito

Guião para a apresentação de 10 slides, na versão com o design revisto. Objetivo de ensaio: cerca de 9 minutos, dentro da duração prevista de 7 a 10 minutos.

## Divisão e tempos

**Pedro apresenta os slides 1 a 5:** enquadramento, estado da arte e casos de utilização. **Francisco Liquito apresenta os slides 6 a 10:** requisitos, arquitetura, validação e próximos passos. Há uma única passagem de palavra, no fim do slide 5.

| Slide | Tema | Orador | Tempo previsto | Tempo acumulado |
| --- | --- | --- | --- | --- |
| 1 | Abertura | Pedro | 0:25 | 0:25 |
| 2 | Problema e objetivo | Pedro | 0:45 | 1:10 |
| 3 | Estado da arte: tecnologias | Pedro | 0:55 | 2:05 |
| 4 | Estado da arte: plataformas | Pedro | 0:55 | 3:00 |
| 5 | Casos de utilização e passagem de palavra | Pedro | 1:10 | 4:10 |
| 6 | Requisitos de comunicação | Liquito | 1:10 | 5:20 |
| 7 | Atuação, sincronização e operação | Liquito | 1:10 | 6:30 |
| 8 | Arquitetura de alto nível | Liquito | 1:00 | 7:30 |
| 9 | Encaminhamento e validação | Liquito | 0:50 | 8:20 |
| 10 | Estado atual e próximos passos | Liquito | 0:30 | 8:50 |

**Total:** Pedro, 4 min 10 s. Liquito, 4 min 40 s. Apresentação, 8 min 50 s, com margem até aos 10 minutos. São referências para o ensaio, sem contar com perguntas do docente.

### Como usar este guião

Leiam as falas uma vez e ensaiem depois com o PowerPoint aberto. As falas sugeridas são uma base que podem adaptar à vossa forma de falar. As indicações «No slide» e «A reter» servem para preparação e não devem ser lidas em voz alta.

**Ideia que deve ficar clara:** nesta fase temos a análise de requisitos e uma arquitetura conceptual. A seleção dos componentes, a implementação e os resultados experimentais pertencem à fase seguinte.

<!-- pagebreak -->

## Pedro: abertura e tecnologias

### Slide 1. Sistema de escrita e leitura multiprotocolo

**Pedro. 25 segundos.**

**Fala sugerida**

> Bom dia. Somos o Pedro Ribeiro e o Francisco Liquito. Vamos apresentar o trabalho desenvolvido no projeto de escrita e leitura multiprotocolo. Começamos pelo problema e pelo estado da arte, passamos aos casos de utilização e aos requisitos, e terminamos com a arquitetura de alto nível e o trabalho previsto para a fase de projeto.

**No slide:** olhar para o público e apresentar os dois autores. Avançar quando terminar o enquadramento.

**A reter:** a apresentação corresponde ao trabalho de análise e conceção já documentado.

### Slide 2. Problema e objetivo

**Pedro. 45 segundos.**

**Fala sugerida**

> O problema é integrar, a partir de um PC, dispositivos que usam interfaces de comunicação diferentes. A unidade embebida deverá permitir enviar comandos, adquirir dados de sensores e comandar atuadores.
>
> Para isso, cada operação tem de identificar a origem e o destino e preservar o significado da informação. Também é necessário gerir comunicações concorrentes, porque as interfaces podem produzir e transmitir dados a ritmos diferentes. Por fim, precisamos de uma referência temporal que permita relacionar os dados e os eventos com outras fontes de informação.

**No slide:** acompanhar os três pontos da direita com o olhar. Usá-los como sequência da explicação.

**A reter:** integração de interfaces, concorrência e associação temporal são necessidades do sistema.

### Slide 3. Estado da arte: tecnologias

**Pedro. 55 segundos.**

**Fala sugerida**

> No estado da arte começámos por comparar a organização das cinco tecnologias. I2C permite partilhar um barramento local. RS232 estabelece uma ligação ponto a ponto, enquanto RS485 permite uma rede multiponto, cuja configuração exige atenção à topologia e à terminação.
>
> CAN FD utiliza arbitragem e obriga a definir a configuração das suas fases. Em Ethernet, distinguimos a taxa nominal da ligação do débito útil efetivamente obtido.
>
> Esta análise também mostra que temos de especificar os protocolos de aplicação e o significado dos dados. A presença das interfaces físicas, por si só, não resolve a integração entre dispositivos.

**No slide:** percorrer a primeira coluna e destacar a implicação de cada tecnologia. Evitar ler todas as células.

**A reter:** os protocolos e os mapeamentos continuam a exigir decisões de projeto.

<!-- pagebreak -->

## Pedro: plataformas e utilização

### Slide 4. Estado da arte: plataformas

**Pedro. 55 segundos.**

**Fala sugerida**

> Comparámos também quatro exemplos de plataformas e gateways. GoWired e IOT-GATE-iMX7 ilustram soluções programáveis. Na comparação do relatório, as características do GoWired são anunciadas e o desempenho está por verificar. No IOT-GATE-iMX7, a opção CAN substitui RS485, o que mostra a importância de verificar as combinações de interfaces.
>
> MGate e Anybus mostram integrações entre protocolos específicos, com funções e mapeamentos definidos. Estes exemplos ajudam a perceber os modelos de integração e as suas limitações. A seleção da nossa plataforma continua para a fase de projeto e terá de considerar o conjunto dos requisitos.

**No slide:** comparar os dois primeiros exemplos com os dois últimos. Destacar a substituição de RS485 por CAN no IOT-GATE-iMX7.

**A reter:** a comparação ainda não demonstra que uma destas soluções satisfaça todos os requisitos do projeto.

### Slide 5. Casos de utilização

**Pedro. 1 minuto e 10 segundos, incluindo a passagem de palavra.**

**Fala sugerida**

> Organizámos a utilização do sistema em sete casos. Os três primeiros correspondem às operações mais diretas: comandar um dispositivo pelo PC, adquirir dados de sensores e atuar através de PWM. Por exemplo, um pedido do PC deve chegar ao destino escolhido e devolver feedback quando a operação o prevê.
>
> Os restantes casos cobrem a execução concorrente, a sincronização por PPS e GPS, o funcionamento elétrico e ambiental e a disponibilização ou o registo de dados. Em particular, a aquisição de sensores permanece genérica e o armazenamento em microSD é opcional.
>
> Estes cenários orientam os requisitos e os ensaios previstos. O Francisco vai agora apresentar as capacidades exigidas ao sistema e a arquitetura que as organiza.

**No slide:** começar pela coluna da esquerda e depois passar à da direita. Fazer uma pausa curta antes de entregar a palavra.

**A reter:** a garra, quando usada como exemplo, ocupa um dos três PWM. As condições ambientais quantitativas ainda estão por definir.

### Passagem para o Liquito

**Pedro termina:** «O Francisco vai agora apresentar as capacidades exigidas ao sistema e a arquitetura que as organiza.»

**Liquito começa, já no slide 6:** «A partir destes casos de utilização, definimos as capacidades de comunicação que estão resumidas nesta tabela.»

O Pedro avança para o slide 6 e deixa o Liquito começar. A partir daí, o Liquito pode assumir o controlo dos slides. Se usarem apenas um comando, combinem antes quem avança.

<!-- pagebreak -->

## Liquito: requisitos do sistema

### Slide 6. Requisitos de comunicação

**Liquito. 1 minuto e 10 segundos.**

**Fala sugerida**

> A partir destes casos de utilização, definimos as capacidades de comunicação que estão resumidas nesta tabela.
>
> Exigimos dois barramentos I2C independentes em Standard mode. Em RS232, a operação é a 500 kbit/s, com capacidade e ensaio também a 1 Mbit/s. Para RS485, usamos aproximadamente 16 a 32 nós como referência, sem estabelecer 32 como limite rígido. A taxa e o protocolo ainda estão em aberto.
>
> O sistema deve ter três barramentos CAN FD, cada um com capacidade até 8 Mbit/s. Em Ethernet, o mínimo nominal é 100 Mbit/s e Gigabit é desejável.
>
> O PC dispõe das alternativas RS232, CAN e Ethernet, todas bidirecionais, sem obrigatoriedade de as usar simultaneamente. As configurações restantes serão definidas no projeto.

**No slide:** seguir a tabela de cima para baixo e terminar na frase sobre RF09. Fazer uma pausa entre a taxa operacional RS232 e a capacidade máxima.

**A reter:** 100 Mbit/s é uma capacidade nominal. Os 8 Mbit/s de CAN FD não fixam separadamente as taxas das fases de arbitragem e de dados.

### Slide 7. Atuação, sincronização e operação

**Liquito. 1 minuto e 10 segundos.**

**Fala sugerida**

> Além das comunicações, exigimos três saídas PWM eletricamente protegidas, a 50 Hz, com largura de impulso entre 1100 e 1900 microssegundos. A resolução PWM, as cargas e os detalhes da proteção ficam para projeto.
>
> A sincronização utiliza PPS a um impulso por segundo e informação temporal GPS entre impulsos. A associação temporal dos dados deve ter resolução da ordem dos microssegundos. Vamos medir o erro absoluto e avaliar a incerteza da medição. Esta resolução não garante, por si só, uma exatidão absoluta de um microssegundo.
>
> A alimentação de entrada deve aceitar de 5 a 60 volts, incluindo os limites. O RTOS é obrigatório, mas FreeRTOS é apenas candidato. A plataforma e o dimensionamento continuam por selecionar.

**No slide:** explicar as três colunas da esquerda para a direita. Dar ênfase à distinção entre resolução temporal e erro absoluto.

**A reter:** 1100 a 1900 µs é largura de impulso, não frequência. A gama de 5 a 60 V corresponde à entrada de alimentação e não determina a tensão das cargas PWM.

<!-- pagebreak -->

## Liquito: arquitetura, validação e fecho

### Slide 8. Arquitetura de alto nível

**Liquito. 1 minuto.**

**Fala sugerida**

> A arquitetura organiza estas funções numa unidade embebida central. À esquerda temos o PC, a referência PPS e GPS e a alimentação. À direita estão os dispositivos externos.
>
> A unidade concentra as comunicações, o processamento e o encaminhamento, com coordenação por RTOS e associação temporal. Na base surgem os três PWM protegidos e a opção de registo em microSD.
>
> Os três CAN FD são o total do sistema, incluindo os papéis de ligação ao PC e aos nós externos. A sua representação em pontos diferentes do diagrama não acrescenta canais. Nesta fase, os blocos representam responsabilidades funcionais. A distribuição pelos componentes e pelas tarefas de software será definida no projeto.

**No slide:** apontar primeiro para o centro, depois para as ligações externas e, por fim, para PWM e microSD. Identificar o tracejado como opção.

**A reter:** o diagrama não escolhe componentes nem tarefas. Ethernet não tem de intermediar todos os percursos.

### Slide 9. Encaminhamento e validação

**Liquito. 50 segundos.**

**Fala sugerida**

> RF17 exige, como mínimo, os quatro pares Ethernet com CAN, RS485, RS232 e I2C, nos dois sentidos. Outros percursos, como CAN para RS485, podem ser definidos e implementados em projeto, com operações, protocolos e mapeamentos compatíveis. Ethernet não tem de intermediar tudo.
>
> Nos ensaios, verificaremos os pares mínimos e os percursos adicionais definidos, comparando dados conhecidos. Mediremos também PWM, alimentação e sincronização, distinguindo resolução, erro e incerteza.
>
> As condições e as tolerâncias serão definidas antes dos ensaios de conformidade. Ainda não existem resultados experimentais.

**No slide:** apresentar o esquema da esquerda e depois o plano de ensaios da direita. Usar verbos no futuro para os ensaios.

### Slide 10. Estado atual e próximos passos

**Liquito. 30 segundos.**

**Fala sugerida**

> Temos documentados o estado da arte, sete casos de utilização, 17 requisitos funcionais e oito não funcionais, com os estados de proposta identificados. Temos também a rastreabilidade, o plano de ensaios e a arquitetura funcional.
>
> O próximo passo é fechar as decisões de projeto, selecionar a plataforma e preparar a implementação e a validação experimental. Obrigado. Estamos disponíveis para questões.

**No slide:** destacar o que está documentado e depois a coluna de decisões em aberto. Terminar a olhar para o público.

**A reter:** RNF01 a RNF03 e RNF05 são propostas. MicroSD e PoE são opcionais. Gigabit Ethernet é desejável.

<!-- pagebreak -->

## Perguntas para ensaiar: enquadramento e âmbito

As respostas seguintes servem de base ao ensaio. O orador indicado responde primeiro. O outro complementa quando houver um ponto concreto a acrescentar.

### 1. Qual é o contributo do projeto face aos gateways existentes?

**Pedro responde.**

«O trabalho reúne e organiza os requisitos de comunicação, atuação, sincronização e alimentação deste sistema. O estado da arte ajuda-nos a avaliar modelos de integração e limitações. A escolha e a avaliação da solução concreta pertencem à fase de projeto.»

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

### 5. Porque ficaram parâmetros por definir?

**Pedro responde e o Liquito complementa, se necessário.**

«Identificámos esses parâmetros nas decisões DP01 a DP17. Serão definidos na fase de projeto, em função da plataforma, dos dispositivos, das cargas e das condições de ensaio. Mantemos os valores já confirmados e documentaremos as decisões restantes antes de dimensionar e validar a solução.»

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

### 10. Já construíram e testaram o protótipo?

**Liquito responde.**

«O trabalho apresentado corresponde à análise de requisitos e à arquitetura conceptual. A implementação e os ensaios experimentais são os próximos passos. Nesta apresentação mostramos capacidades exigidas e métodos de validação previstos.»

<!-- pagebreak -->

## Ensaio e folha de memória

### Ensaio conjunto

1. **Primeiro ensaio:** cada um explica a sua parte com os slides abertos, usando o guião apenas para recuperar a sequência.
2. **Segundo ensaio:** cronometrar do início ao fim, incluindo a passagem de palavra. Apontar onde o ritmo abranda e ajustar as explicações.
3. **Terceiro ensaio:** alternar as dez perguntas anteriores. Ambos devem saber explicar os valores principais e a arquitetura.

Se precisarem de encurtar a apresentação, reduzam os exemplos e os comentários sobre plataformas. Conservem os valores confirmados, o âmbito dos percursos e a distinção entre requisitos e resultados medidos.

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
| Propostas e opções | RNF01 a RNF03 e RNF05 são propostas. MicroSD e PoE opcionais | Não apresentar estes estados como obrigações confirmadas |

**Apoio para estudar:** o [PowerPoint atualizado](output/Apresentacao_LaSET_Atualizada.pptx) e o [relatório](../template_laset/build/Modelo_LaSET.pdf). Para aprofundar: secções 1.2, 2.8, 3.1 a 3.7 e capítulo 4 do relatório.
