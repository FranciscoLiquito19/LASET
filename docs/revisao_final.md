# Revisão final do relatório LaSET

> **Estado atual (23 de novembro de 2026):** o relatório tem 18 RF e 8 RNF, dois CAN FD,
> Ethernet só para o PC e configuração em flash (sem microSD). As secções abaixo de
> outubro descrevem a versão de então (17 RF) e ficam como histórico. A fase de Projeto
> está no Capítulo 5, com o estado das DP01–DP17 na Tabela 5.5, e o esquema no Anexo A.

Revisão consolidada de 27 de outubro de 2026, sobre a branch
`template-migration`, com base no commit `a3c2227`. Inclui a revisão de
conteúdo e apresentação de 23 de outubro e a clarificação de RF17 descrita abaixo.

O relatório foi revisto quanto à coerência técnica, rastreabilidade,
parâmetros confirmados, decisões em aberto, referências e apresentação.
Não foram identificadas incoerências impeditivas no âmbito revisto. Esta
nota serve de apoio à leitura conjunta dos autores.

**Reorganização visual e redução de texto**

O PDF passou de 74 para 49 páginas, com 9 figuras em vez de 2. A introdução,
a síntese e a arquitetura foram encurtadas para evitar repetir os mesmos
valores em várias secções. A reorganização preservou o texto normativo e
os critérios de rastreabilidade. A clarificação de 27 de outubro atualiza
RF17 e o respetivo ensaio, mantendo os restantes RF e RNF.

- Mapa de atores e dos sete casos de utilização.
- Esquemas comparados das topologias de comunicação.
- Diagrama das diferenças de taxa e do armazenamento temporário.
- Formas de onda PWM e linha temporal PPS/GPS, ambas esquemáticas.
- Cadeia visual entre necessidades, utilização, requisitos e verificação.
- Diagramas renovados das interfaces e do encaminhamento; mapa dos quatro
  pares Ethernet mínimos obrigatórios.
- Tabela compacta das DP01-DP17 e tabela de responsabilidades da arquitetura.
- Margens horizontais simétricas de 27,5 mm, mantendo letra de 11 pt e entrelinha 1,5 no
  corpo do texto. Tabelas e diagramas usam espaçamento próprio.
- Títulos dos requisitos mantidos junto do respetivo texto e índices com
  legendas curtas.

Os esquemas são vetoriais, editáveis em `template_laset/Figuras/diagramas/`,
e compilam com TikZ. Os gráficos temporais ilustram requisitos confirmados;
não apresentam resultados experimentais. Não foram escolhidos componentes
nem acrescentados valores aos requisitos. O período PWM de 20 ms é apenas
a conversão matemática da frequência confirmada de 50 Hz. Mantêm-se as correções anteriores dos
cabeçalhos, da numeração e da descrição do PDF versionado no README.

**Revisão de conteúdo académico**

Na comparação dos fontes anteriores à reorganização visual, verificou-se que as
definições dos 17 RF e dos 8 RNF e as linhas das duas tabelas de
rastreabilidade foram preservadas, descontando apenas a alteração de quebra
de linha que mantém o título junto do texto e a normalização da pontuação
dos identificadores. Foram sintetizadas repetições
e explicações de contexto; mantêm-se os quatro problemas, os sete casos de
utilização e as 17 decisões de projeto. A revisão de RF17 abaixo constitui
uma clarificação posterior, limitada ao âmbito do encaminhamento e à sua validação.

- O desenho PWM usa agora larguras proporcionais ao período. A amplitude
  continua sem valor especificado; não se representa uma medição real.
- A associação conceptual entre captura PPS e código temporal é
  fundamentada na [RFC 2783, secções 1–2](https://www.rfc-editor.org/rfc/rfc2783.html).
  A API UNIX descrita nessa fonte não é adotada como solução do projeto.
  A escala temporal e a correspondência concreta entre mensagem e impulso
  permanecem em DP14, dependentes da documentação da solução selecionada.
- A secção 3.3 explicita o mensurando, os pontos de observação, as condições
  de ensaio e a apresentação da incerteza, com apoio no
  [JCGM 100:2008, secção 7](https://www.bipm.org/en/doi/10.59161/jcgm100-2008e).
  Resolução temporal, erro observado e incerteza são grandezas distintas.
- Os valores PWM confirmados são nominais. As tolerâncias e a regra de
  decisão de conformidade têm de ser documentadas no projeto antes dos
  ensaios de conformidade; não são inferidas da resolução do instrumento.
  Enquanto não existirem, a medição permite caracterização experimental,
  sem demonstrar cumprimento de uma tolerância não especificada.

Esta revisão verifica preservação, coerência e fundamentação no âmbito de
um relatório de análise de requisitos. Não certifica ausência absoluta de
erros científicos nem substitui a apreciação académica dos autores e do
docente. Os parâmetros ainda desconhecidos continuam identificados como
decisões de projeto, sem valores inventados ou presumidos como standard.

Os travessões longos dos títulos de necessidades, casos de utilização e
requisitos foram substituídos por pontos após o identificador. Nas três
referências bibliográficas afetadas, usam-se dois-pontos ou vírgula. As
continuações de tabelas surgem entre parênteses. Os intervalos numéricos e
a informação técnica mantêm-se.

**Verificações concluídas**

| Verificação | Resultado |
| --- | --- |
| Compilação final | Concluída com pdfLaTeX, BibTeX e latexmk, sem avisos |
| PDF final | 49 páginas A4; todas renderizadas e inspecionadas |
| Erros LaTeX | 0 |
| Referências e citações indefinidas | 0 |
| Caixas com texto a exceder a largura (`Overfull`) | 0 |
| Avisos BibTeX | 0 |
| Identificadores | P01–P04, UC01–UC07, RF01–RF17, RNF01–RNF08 e DP01–DP17 completos |
| Rastreabilidade | Uma entrada para cada um dos 17 RF e dos 8 RNF |
| Parâmetros e critérios | As 36 linhas da Tabela 3.3 preservam o conteúdo anterior à síntese |
| Bibliografia | 29 entradas distintas, todas citadas; sem chaves em falta |
| Referências internas | 39 etiquetas distintas; 31 referências, todas resolvidas |
| Figuras e tabelas | 9 figuras e 10 tabelas; continuações verificadas |
| Margens | Mesma posição horizontal nos 36 cabeçalhos dos capítulos, sem alternância par/ímpar |
| Páginas em branco e texto fora da página | Nenhum caso detetado |
| Espaços em branco no diff | `git diff --check` sem ocorrências |

A compilação final não apresenta avisos `Underfull` ou `Overfull`. A
verificação formal da bibliografia não equivale a uma auditoria integral
de todas as fontes externas.

**Clarificação de RF17, em 27 de outubro**

- Os quatro pares Ethernet com CAN, RS485, RS232 e I2C, nos dois sentidos,
  constituem o mínimo obrigatório.
- Outros percursos, como CAN para RS485, podem ser definidos e implementados
  em projeto, com operações, protocolos e mapeamentos compatíveis. Ethernet
  não tem de intermediar todo o encaminhamento.
- RF17, DP01, a arquitetura, a Figura 4.3 e a rastreabilidade usam esta distinção.
  Os ensaios abrangem os pares mínimos e cada percurso adicional efetivamente definido.
- A operação autónoma sem intervenção do PC continua opcional e distingue-se
  da definição de percursos adicionais.
- A apresentação atualizada e o guião seguem a mesma formulação. Mantêm-se
  os 10 slides e a divisão: Pedro nos slides 1 a 5, Francisco Liquito nos slides 6 a 10.

**Pontos de atenção para a vossa análise**

- Os valores confirmados coincidem entre casos de utilização, requisitos,
  tabelas, critérios de ensaio e arquitetura: I2C Standard mode; RS232
  operacional a 500 kbit/s e com capacidade até 1 Mbit/s; RS485 com
  aproximadamente 16–32 nós de referência; dois CAN FD até 8 Mbit/s;
  três PWM protegidos a 50 Hz e 1100–1900 µs; PPS a 1 Hz e informação
  temporal GPS. Mantêm-se Ethernet nominal de pelo menos 100 Mbit/s,
  RTOS obrigatório e entrada de 5–60 V.
- As configurações, cargas, níveis de proteção, resolução PWM, limites de
  desempenho e restantes parâmetros desconhecidos estão nas DP01–DP17.
  Continuam em aberto para projeto, sem valores por omissão apresentados
  como requisitos confirmados.
- RF16 distingue resolução temporal da ordem dos microssegundos do erro
  absoluto de sincronização. O erro será medido e reportado, sem precisão
  absoluta de ±1 µs garantida. Também não está estabelecida resolução
  PWM de 1 µs.
- A secção 2.13 fundamenta a associação conceptual PPS/código temporal na
  RFC 2783. A associação concreta entre mensagens GPS e impulsos deverá
  acompanhar a solução selecionada no projeto, conforme DP14.
- A distribuição dos dois CAN FD entre PC e nós externos, os papéis das
  interfaces e os protocolos permanecem decisões de projeto. Os diagramas
  representam funções e papéis; não acrescentam canais físicos nem
  selecionam componentes.
- RNF01–RNF03 e RNF05 estão identificados como propostas. PoE é
  opcional; Gigabit Ethernet é desejável. Convém manter estes estados
  explícitos durante a vossa revisão.
- A aquisição de sensores continua genérica. Sensores de pressão e
  funcionamento sob pressão não foram tratados como requisitos específicos.
- Antes da entrega, rever os dados da capa, a designação do curso/unidade
  curricular e a identificação institucional. Os nomes dos docentes não
  foram preenchidos por não constarem da informação disponível. Os dois
  comentários TODO existentes nos fontes referem-se apenas a esta
  identificação e ao enquadramento institucional; não aparecem no PDF.

**Roteiro de leitura**

As páginas abaixo correspondem à numeração impressa do relatório.

| Leitura | Localização | Foco |
| --- | --- | --- |
| Visão visual do sistema | Figuras 1.1, 2.1–2.4 e 4.1–4.3 | Começar pelos atores, ligações, temporização e percursos |
| Problema e utilização | Secções 1.1–1.2, pp. 1–3 | Confirmar que os cenários refletem o uso pretendido |
| Requisitos | Secções 3.1–3.2, pp. 20–26 | Rever âmbito e distinção entre confirmado e proposto |
| Rastreabilidade e ensaios | Secções 3.3–3.4, pp. 27–32 | Comparar cada requisito com a respetiva validação |
| Decisões em aberto | Secção 3.7, pp. 34–35 | Registar decisões durante a fase de projeto |
| Arquitetura | Capítulo 4, pp. 36–40 | Conferir interfaces, papéis e percursos obrigatórios |
| Sincronização e bibliografia | Secção 2.13, pp. 16–17; RF16, pp. 23–24 | Rever resolução, erro e fundamentação PPS/GPS |

PDF atualizado: [Modelo_LaSET.pdf](../template_laset/build/Modelo_LaSET.pdf).
O comando de compilação encontra-se no [README](../README.md).

**Atualização de 17 de novembro de 2026**

Incorpora o feedback dos docentes (commit `49fa413`) e uma correção posterior
da quantidade de CAN FD. Os pontos de atenção acima já refletem estas alterações;
a tabela de verificações corresponde à revisão de 27 de outubro.

- CAN FD: dois barramentos no total, cada um até 8 Mbit/s (RF04, Tabela 3.3,
  DP01, Figura 4.1 e Tabela 4.2).
- Ethernet dedicada à ligação ao PC; deixa de ser interface para dispositivos
  externos. Os quatro percursos mínimos de RF17 passam a ser entre o PC, via
  Ethernet, e CAN FD, RS485, RS232 e I2C.
- PWM: isolamento galvânico obrigatório nos três canais, além da proteção (RF15, DP12).
- Registo opcional em microSD removido. Novo RF18: configuração guardada em
  flash e reposta após reinício, tolerante a interrupções durante a escrita (DP15).
- Passam a existir 18 RF e 8 RNF.

**Atualização de 24 de novembro de 2026**

- Esquema: corrigidas as saídas PWM 2 e 3 (R88 e R89 fundiam redes por etiquetas
  sobrepostas) e ligado o PDR_ON do STM32 a 3,3 V. O `verificar.py` passa a comparar
  cada pino com a rede pretendida no gerador. ERC do KiCad 9 com um único erro, aceite
  (VCAP unidos, como pede a ST).
- Placa gerada por código (`hardware/gerador/pcb.py` e `fanout.py`): 100 × 100 mm,
  quatro camadas, disposição por zonas, faixa de isolamento, andar de potência por zonas
  em cobre e vias aos planos. Falta o encaminhamento dos sinais.
- Relatório: Secção 5.3 com a descrição da placa e a Figura 5.2.
- Firmware: exclusão mútua na transmissão de cada FDCAN.

