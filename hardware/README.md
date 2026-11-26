# Hardware do gateway LASET

Projeto KiCad do gateway multiprotocolo. O esquema é **gerado por código** a partir de
`gerador/`: cada folha é um ficheiro Python com os componentes, os valores e a rede de
cada pino. Assim cada alteração fica revista em PR, como o relatório.

## Abrir o projeto (esquema e placa)

1. Abrir `laset_gateway.kicad_pro` no KiCad (8 ou 9). Se perguntar se quer atualizar o
   formato dos ficheiros, aceitar: o gerador escreve no formato do KiCad 6/7.
2. No editor de esquemas, a folha raiz mostra uma caixa por folha. Duplo clique entra
   na folha.
3. As ligações são feitas por **etiquetas** (texto junto a cada pino) e por símbolos de
   alimentação (GND, +5V, +3V3). Dois pinos com a mesma etiqueta estão ligados.
   Etiquetas com forma de seta são globais e ligam entre folhas.

## Verificar

1. `python3 -I gerador/verificar.py` (precisa do `kicad-cli`): exporta a netlist e falha se
   houver redes com um só pino ou sinais globais que não saem da folha onde nascem.
   Apanha etiquetas mal escritas e pinos esquecidos.
2. No KiCad: `Inspecionar > Verificador de regras elétricas > Executar ERC`. Os pinos sem
   ligação devem ser só os marcados com cruz (NC do LM5177, HO1_LL/HO2_LL, GPIO livres do
   MCU, LEDs do RJ45, sinais auxiliares dos transceivers). Qualquer outro erro deve ser
   reportado. O ERC não corre na linha de comandos do KiCad 7; no 8 ou 9:
   `kicad-cli sch erc laset_gateway.kicad_sch`.

## Regenerar depois de mudar o código

```sh
cd hardware/gerador
python3 -I gerar.py
python3 -I verificar.py
kicad-cli sch export pdf -o ../laset_gateway.pdf ../laset_gateway.kicad_sch
```

O Anexo A do relatório lê este PDF diretamente; basta recompilar o relatório.

O `gerar.py` recusa referências repetidas entre folhas. Não editar à mão os
`.kicad_sch` gerados: as alterações perdem-se na próxima geração. Arrumar a posição dos
componentes na interface é seguro só depois de congelarmos o gerador (fase de layout).

## Placa de circuito impresso (`laset_gateway.kicad_pcb`)

Também é gerada por código, em dois passos, a partir do esquema:

```sh
cd hardware/gerador
python3 pcb.py       # placa, disposição, planos e regras (refaz a placa de raiz)
python3 fanout.py    # vias dos pinos de massa e alimentação para os planos
python3 curtas.py    # rascunho: ligações de sinal curtas (F.Cu, ou B.Cu com duas vias)
python3 encaminhar.py   # rascunho: encaminhador em grelha (A*) para o resto, com vias
```

Ordem usada para a placa atual (refeita a 25 e 26/11 depois da revisão independente):

```sh
python3 pcb.py && python3 fanout.py      # 302 ligações por fazer
python3 pf.py                            # encaminhamento por congestionamento negociado (~60 min): 80
python3 encaminhar.py && FINO=1 python3 encaminhar.py               # 28 -> 21
VIA=0.5 python3 interior.py              # F.Cu + In2 (sinais lentos) e F/B com HV: 21 -> 16
python3 melhorar.py <base>               # pesquisa local (base = placa depois de fanout.py): 16 -> 12
VIA=0.5 BASE=<base> python3 interior.py  # com arranque: 12 -> 11
# fecho por coordenadas e arrancar_e_ordenar() (ver abaixo): 11 -> 0
python3 serigrafia.py                    # referências sem sobreposição e nome dos conectores
# 26/11, depois da revisão:
python3 vias_pad.py && REDUZIR=1 python3 vias_pad.py   # vias fora dos pads: 90 -> 12
python3 baixo.py C62:U5.4 C63:U5.4 C61:U5.3            # desacoplamento do U5 para B.Cu
# VCAP do STM32 (C34, C35) para B.Cu, arrancando e voltando a encaminhar as redes à volta
python3 limpar.py                        # retira pistas com uma ponta solta
python3 pilha.py                         # pilha JLC04161H-7628 no ficheiro da placa
python3 vista3d.py                       # texturas e componentes para hardware/3d/index.html
```

As últimas 11 foram fechadas com pistas e vias postas por coordenadas (afastamento
verificado à mão e depois pelo DRC) ou arrancando e voltando a encaminhar só as redes
vizinhas:

- LM5177: SW2 do pino ao C10 e à zona SW2 por B.Cu, à volta da diagonal do HO2; LA, EN e VIN
  pelo `interior.py` com a área `lm5177` (ver abaixo).
- LAN8742A: via de 0,5 mm do +3V3 do pino 30.25 em (79,1; 30,4), com o GND do C41 a partilhar
  a via do C48; NRST, TX_EN e TXD0 descem em paralelo pelo corredor entre C44 e C42; TXP em
  F.Cu entre RXN e TXN até baixo do R37 e depois por B.Cu entre as resistências de terminação
  (a via do TXN desceu 0,35 mm para lhe dar passagem). R32 saiu do esquema: o REGOFF tem
  pull-down interno e a flutuar o regulador de 1,2 V fica ligado (folha do LAN8742A, 3.7.3.2).
- STM32: I2C1_SCL e GPS_TX com o vizinho (SDA, RX) arrancado e encaminhado depois.
- ETH_REF_CLK: tem 33 Ω em série junto ao PHY (R94). Ao refazer a zona do VCAP (26/11)
  saiu de In2: passa agora por F.Cu (37 mm) e B.Cu (3 mm), com 4 vias.

Área `lm5177`: área de regra sem restrições à volta do LM5177 e dos seus passivos (x 30 a
50, y 26 a 42). Lá dentro a classe HV usa 0,15 mm em vez de 0,6 mm (`.kicad_dru`): sob
máscara de solda, 0,13 mm chegam até 100 V (IPC-2221B, B4). O `interior.py` usa o mesmo
afastamento na grelha.

O `interior.py` usa a camada In2 (plano de 3,3 V) para sinais lentos: cada pista em In2
recorta o plano. Não podem ir para In2 as classes HV e P5V (nós de comutação e potência), a
classe ETH (pares) nem o REF_CLK, a não ser por exceção explícita. As vias de saída são de
0,5/0,2 mm (anel de 0,15 mm) com pelo menos 0,8 mm entre centros. Estão em In2: GPS_TX
(35 mm), GPS_RX (27 mm), CAN1_TX (27 mm), I2C_OE (19 mm), RS485_TX (7 mm) e RBIAS (4 mm),
todos lentos (UART, CAN a 1 Mbit/s no máximo, níveis estáticos). Com a pilha JLC04161H-7628
(`pilha.py`), In2 fica a 0,21 mm de B.Cu e a 1,07 mm de In1: a referência destas pistas é o
plano de 3,3 V à volta e o cobre de B.Cu, não o plano de massa.

Vias e pads (`vias_pad.py`, 26/11): uma via não tapada dentro de um pad, ou encostada a ele,
puxa a solda para o furo e a junta fica fraca. Os encaminhadores deixaram 90 assim; 78 foram
mudadas para o sítio livre mais perto (fora do pad, 0,1 mm de folga) com uma pista curta, 7
delas com 0,5/0,2 mm para caber. Ficam 12 sem lugar (VCC do LM5177, os VISOOUT e o RS485 do
lado isolado do U7, CANH1 no D4, RXN, VDDCR, PWM_FALHA no R86 e o +3V3 do U6): ou se mudam à
mão, ou se pedem à JLCPCB vias cheias e tapadas (POFV, pago em 4 camadas). As vias dos pads
térmicos (Q1 a Q4) ficam, como é normal.

Desacoplamento em B.Cu (`baixo.py`, 26/11): os condensadores que estavam longe do pino
passaram para a face de baixo, por baixo dele, com uma via de 0,6/0,3 mm ao pino e outra ao
plano de massa: C34 e C35 (VCAP do STM32) de 8,3 e 7,2 mm para 1,2 e 1,0 mm; C61, C62 e C63
(U5) de 6,7, 9,2 e 11,5 mm para 2,5, 1,5 e 1,0 mm. São as únicas 5 peças em B.Cu, o que
obriga à montagem Standard da JLCPCB (duas faces).

O `serigrafia.py` corre uma vez, no fim: põe cada referência (1,0 mm de altura e 0,15 mm de
traço, o que a JLCPCB recomenda) no sítio livre mais perto da peça, sem tocar em pads,
noutras linhas nem no bordo, e esconde as que não cabem (36 na placa atual, passivos em zonas
apertadas). Acrescenta o nome de cada conector
(VIN, ETH, SWD, RS232, I2C1, I2C2, GPS, CAN1, CAN2, RS485, PWM) e desloca o bloco de texto
LASET se tocar em alguma peça. Recusa correr numa placa que já tenha os nomes.

Visualização 3D: `python3 vista3d.py` gera as texturas das duas faces e a lista de
componentes para `3d/index.html` (three.js; abre-se com `python3 -m http.server` na pasta
`3d`). Os footprints têm os modelos 3D do KiCad (o do LM5177 usa o do TSSOP-38), por isso
no KiCad basta `Ver > Visualizador 3D` (Alt+3); se o KiCad 9 não encontrar os modelos,
`Ferramentas > Atualizar footprints a partir da biblioteca` corrige o caminho.

Freerouting (testado em 25/11 na placa anterior, versão 1.9.0 sem janela e 2.1.0, Java 21): não fecha
nenhuma das 16. Com as pistas atuais fixas só acrescenta cobre redundante; a refazer todo o
encaminhamento de sinal (cobre de `pcb.py` e `fanout.py` fixo) volta às mesmas 16; com o
afastamento da classe HV reduzido a 0,15 mm chega a 14, mas com 13 violações de 0,6 mm
fora do LM5177, e depois de limpas ficam 19. O `encaminhar.py` com `JANELA=25` e o
`melhorar.py` com `LIMITE=4000000` também não baixam das 16. O RXP nem tem caminho com
só o cobre de base: as vias de fanout à volta do LAN8742A fecham a saída.

Variáveis do `pf.py`: `ITERACOES`, `HIST` (custo de histórico por conflito) e `CRESCE`
(fator de subida do custo de ocupação por iteração). Mover o STM32 2 mm para baixo e
alargar os corredores do LM5177 foi experimentado e deu 19 ligações em falta, pior que a
disposição atual.

O `pf.py` (PathFinder) encaminha todas as ligações ao mesmo tempo: o cobre das outras
redes não bloqueia, custa, e o custo das zonas disputadas sobe a cada iteração até as
redes se afastarem. Foi o que mais reduziu as ligações em falta.

O `encaminhar.py` demora 10 a 20 minutos. Encaminha primeiro as redes críticas (Ethernet,
comando dos MOSFET, CAN), das mais longas para as mais curtas, e depois o resto. Procura cada ligação em falta numa grelha de
0,1 mm nas duas camadas exteriores, com afastamentos pela classe de cada rede, sem
passar pelas zonas de potência nem pela faixa de isolamento, e retira as rotas que o
DRC do KiCad acusar. Variáveis opcionais: `JANELA` (mm à volta das pontas), `LIMITE`
(nós por procura) e `RONDAS`.

Precisam do módulo `pcbnew` (vem com o KiCad; no Windows correr com o Python do KiCad,
"KiCad Command Prompt"). **Só se correm enquanto a placa não tiver pistas desenhadas à
mão**: refazem o ficheiro. A partir do momento em que se começa a encaminhar no KiCad,
as alterações ao esquema passam para a placa com `Ferramentas > Atualizar PCB a partir
do esquema` (F8); os símbolos têm UUIDs fixos, por isso o F8 reconhece todas as peças.

| Item | Valor |
|---|---|
| Dimensões | 100 × 100 mm (escalão mais barato da JLCPCB), furos M3 nos cantos |
| Camadas | F.Cu sinal, In1 `GND`, In2 `PWR` (3,3 V, com zonas de 5 V), B.Cu sinal; 1,6 mm |
| Regras mínimas | pista 0,15 mm, afastamento 0,15 mm, via 0,5/0,2 mm (as vias térmicas dos footprints são de 0,2 a 0,25 mm), cobre ao bordo 0,5 mm |
| Classes | `HV` (VIN e nós de comutação): pista 1,5 mm, afastamento 0,6 mm (IPC-2221B, 60 V); `P5V`: 1,0 mm; `BUS` (CAN e RS485): 0,4 mm; `ETH`: 0,25 mm |
| Regras próprias (`.kicad_dru`) | dentro do LM5177, dos MOSFET, dos díodos e do conector de entrada vale o passo do fabricante em vez dos 0,6 mm |

Disposição (Figura 5.2 do relatório):

- Conectores nos bordos: entrada (J1) e RJ45 (J3) em cima, DE-9 (J7) à esquerda, I2C e
  GPS (J8 a J10) à direita, CAN FD (J4, J5), RS485 (J6) e PWM (J11) em baixo.
- Fonte em cima, à esquerda do RJ45. Desde 25/11 (revisão independente) o andar de potência
  está espelhado para cada perna ficar do lado dos seus pinos no LM5177: a entrada (J1) está
  em cima ao centro e a corrente corre da direita para a esquerda, J1 → F1 → D1 → D2 →
  C1 a C3 e C108 → perna buck Q1/Q2 (à esquerda do LM5177, junto a HO1, LO1, HB1 e SW1) →
  R10 → L1 → perna boost Q3/Q4 (à direita, junto a HO2, LO2, HB2 e SW2) → C11, C109, C110
  → R13 → +5 V. Os bootstrap C8 e C10 e o VCC (C7) estão junto aos pinos. O TPS62162 (U2,
  L2) subiu para a esquerda, alimentado pelo plano de 5 V em In2.
- Desacoplamento: cada condensador fica junto ao circuito integrado a que pertence no
  esquema (o mais próximo na folha), e é colocado logo a seguir a esse CI, antes dos outros
  passivos.
- Isolamento: faixa de 6,8 mm sem cobre (todas as camadas, área `isolamento`) por baixo
  dos quatro isoladores, com o lado lógico em cima; os quatro lados isolados estão
  separados por 2,5 mm e cada um tem a sua massa em In1.
- Blindagem do RJ45: zona `CHASSIS` em In1 e In2 a 2 mm da massa; liga à massa só por
  C50 (1 nF 2 kV) e R38 (1 MΩ).
- As peças principais têm posição fixa (`ANCORAS` em `pcb.py`); os passivos são postos
  automaticamente o mais perto possível do pino a que ligam (o desacoplamento junto ao
  pino de alimentação do circuito integrado), sem sobreposição e no seu domínio.

Estado (26/11): 212 componentes colocados (5 em B.Cu), andar de potência espelhado e ligado por
zonas em F.Cu, encaminhamento completo, serigrafia arrumada, DRC sem violações de cobre, de
courtyard nem de serigrafia, pilha JLC04161H-7628 definida. Comprimentos no andar de potência:
HO1 19 mm (era 52), LO1 17, HO2 22, LO2 19, HB1 6, HB2 10. Vias: 359 de 0,6/0,3 mm e 93 de
0,5/0,2 mm; nenhum par de furos de redes diferentes a menos de 0,5 mm (regra da JLCPCB). Os
pads expostos do LM5177 e do LAN8742A, o pino 3 do J2 e o pino 1 do JP6 ligam aos planos sem
alívio térmico. Falta:

1. Rever o encaminhamento, que foi todo feito por programa: comando das portas dos MOSFET e
   o seu retorno, CSA/CSB, os pares Ethernet (TXP e TXN têm vias), REF_CLK (40 mm, 4 vias)
   e as 12 vias que ainda tocam em pads.
2. Na encomenda: pilha JLC04161H-7628, montagem Standard (duas faces). O footprint do LM5177
   confere com o desenho DCP0038 da TI (pads 1,475 × 0,3 mm a ±2,86 mm contra 1,5 × 0,3 a
   ±2,9; pad exposto 2,9 × 4,7 mm igual); a pasta no pad exposto cobre 64 % e passa por cima
   de 4 das 6 vias térmicas, que a TI pede cheias, tapadas ou com a pasta afastada.
3. Correr o DRC no KiCad (`Inspecionar > Verificador de regras de desenho`) e gerar os
   ficheiros de fabrico com `python3 -I gerador/fabrico.py`: escreve em `hardware/fabrico/`
   (fora do repositório) o zip dos Gerbers e da furação para a JLCPCB e as posições para
   a montagem (CPL, origem no canto inferior esquerdo). Na montagem da JLCPCB, confirmar a
   rotação de cada peça polarizada na pré-visualização: as bibliotecas do KiCad e da JLCPCB
   nem sempre usam a mesma orientação de referência.

### Ligações em falta

Nenhuma: o DRC dá 0 ligações em falta e 0 violações de cobre. Os ficheiros de fabrico
saem com `python3 -I gerador/fabrico.py`.

## Bibliotecas do projeto

- `lib/laset.kicad_sym`: LM5177 e ADuM6401 (não existem nas bibliotecas do KiCad).
- `lib/laset.pretty`: footprint HTSSOP-38 do LM5177 com pad exposto de 2,90 × 4,70 mm
  (abertura do stencil do exemplo da TI) e vias térmicas. **Confirmar com o desenho DCP0038
  antes do fabrico.**

## Folha 1: Alimentação (`alimentacao.kicad_sch`)

Percurso: J1 (entrada 5 a 60 V) → F1 (fusível 3 A, 125 V DC) → D1 (TVS) → D2 (Schottky contra
inversão) → **U1 LM5177** (buck-boost, 5 V) → **U2 TPS62162** (3,3 V).

| Bloco | Componentes | Como se chegou ao valor |
|---|---|---|
| UVLO | R1 41,2k, R2 20,5k | Eq. 1: 1,25 V × (1 + 41,2/20,5) + 41,2k × 5 µA = 3,97 V no pino VIN (máx. 4,10 V); com a queda do D2 arranca com cerca de 4,8 V à entrada. Desliga a 3,61 V. O valor antigo (53,6k) dava 4,79 V no pino porque a corrente de histerese se soma ao arranque, e a placa não arrancava a 5 V |
| Tensão de saída | R7 40,2k, R8 10k | 1,0 V × (1 + 40,2/10) = 5,02 V |
| Frequência | R5 75k | 400 kHz (Eq. 17 e Tabela 8-3; o texto do exemplo da TI diz 78,7k, que é gralha) |
| Sensor de corrente | R10 10 mΩ, R11/R12 10 Ω, C9 180 pF | Limite 50 mV / 10 mΩ = 5 A típico (3,85 A mínimo) |
| Rampa | R4 90,9k | L / R_CS × 50×10⁶ = 18 µH / 10 mΩ × 50×10⁶ = 90k |
| Bobina | L1 SRP1245A-180M, 18 µH, Isat 11 A, 45 mΩ | Ondulação ≈ 0,63 A no pior caso (60 V → 5 V). Tem footprint na biblioteca do KiCad; o SRP1265A de 15 µH não tem |
| MOSFET | Q1 a Q4 BSC070N10LS5 (100 V, nível lógico, SuperSO8/TDSON-8, Qg 16 nC de 0 a 4,5 V) | O LM5177 tem drivers lógicos alimentados por VCC = 5 V e o patamar de Miller tem de ficar abaixo da tensão mínima de entrada; o BSC160N10NS3 G anterior era de nível normal (RDS(on) só especificado a 6 e 10 V). O mesmo nos quatro para ter uma só referência. Confirmar o patamar de Miller na folha de características |
| Fusível | F1 Littelfuse 0451003.MRL (3 A, 125 V DC, 50 A de corte, NANO2 2410) | O polyfuse MF-MSMF300 anterior era de 6 V: num curto com mais de 6 V à entrada podia ser destruído |
| VCC | C7 22 µF 10 V X7R 1206 | A folha de características pede 10 µF efetivos; o 4,7 µF 0603 anterior dava cerca de 2 µF a 5 V |
| Condensadores extra | C107 100 nF 100 V no pino VIN, C108 100 nF 100 V de alta frequência junto a Q1, C109 e C110 22 µF em 5V_PRE junto a Q3 | Caminho curto para os picos de corrente das duas pernas |
| Compensação | R6 2,0k, C5 56 nF, C6 2,2 nF | f_BW = 4 kHz, abaixo de f_RHPZ/3 (14,5 kHz no modo elevador a 4,5 V e 2 A); contas no cabeçalho de `folha_alimentacao.py` |
| Pinos de modo | MODE e SYNC a VCC, DTRK e BIAS a GND | MODE alto = PWM forçado (frequência fixa, menos ruído). BIAS fica a GND: com 5 V de saída não se chega ao limiar de 6,5 V a partir do qual o VCC passa a vir de BIAS |
| TPS62162 | FB a GND | Versão fixa de 3,3 V: a TI recomenda FB a AGND para melhor dissipação |

**Alteração face ao relatório inicial:** o LM74700-Q1 saiu. Aguenta no máximo 65 V e, com
entrada nominal de 60 V, o TVS de proteção limita acima disso. Passou a ser um Schottky
de 100 V e 5 A em SMC (D2, Panjit MB510): mais simples e robusto, à custa de ~0,6 V de
queda. O STPS5H100 que chegou a ser indicado só existe em DPAK. O capítulo de Projeto
já reflete isto.

## Folha 2: Microcontrolador (`mcu.kicad_sch`)

STM32H743ZIT6, 11 × 100 nF + 4,7 µF no 3,3 V, VDDA filtrado por ferrite, 2 × 2,2 µF nos
VCAP, cristal de 25 MHz, BOOT0 a GND com jumper (JP6) para entrar no bootloader, LED de
estado e conector SWD de 6 pinos a 2,54 mm na mesma ordem do CN4 das NUCLEO (1 VDD,
2 SWCLK, 3 GND, 4 SWDIO, 5 NRST, 6 SWO): programa-se com o ST-LINK de uma NUCLEO e um
cabo direto.
Atribuição de pinos (confirmada nas funções alternativas do STM32H743):

| Função | Pinos |
|---|---|
| Ethernet RMII (igual à NUCLEO-H743ZI) | PA1 REF_CLK, PA2 MDIO, PC1 MDC, PA7 CRS_DV, PC4/PC5 RXD0/1, PG11 TX_EN, PG13 TXD0, PB13 TXD1 |
| FDCAN1 / FDCAN2 | PD0/PD1 e PB5/PB6; SILENT dos transceivers em PG2/PG3 |
| RS232 (USART2) | PD5 TX, PD6 RX |
| RS485 (USART6) | PC6 TX, PC7 RX, PG8 RTS/DE (emissor controlado pelo periférico) |
| GPS (UART7) | PE8 TX, PE7 RX; PPS em PA0 = TIM2_CH1 (32 bits) |
| I2C1 / I2C2 | PB8/PB9 e PB10/PB11 (SCL/SDA) |
| PWM (TIM1) | PE9, PE11, PE13; falha em PE15 = TIM1_BKIN |
| Estado | PB0 LED, PF2 PG_5V, PF3 PG_3V3, PG0 OE dos tradutores I2C |

## Folha 3: Ethernet (`ethernet.kicad_sch`)

LAN8742A com cristal de 25 MHz a gerar os 50 MHz do RMII (REFCLKO, nINTSEL a GND),
regulador interno ligado (REGOFF a GND), endereço 0 e autonegociação pelas resistências
internas. Linhas com 49,9 Ω para 3,3 V; RJ45 HR911105A com magnéticos e derivações
centrais a 3,3 V. Blindagem para GND por 1 nF 2 kV ∥ 1 MΩ. Reset partilhado com o MCU.

## Folha 4: CAN FD (`can.kicad_sch`)

Dois ADM3057E: VCC 5 V, VIO 3,3 V, RS a GND2 (alta velocidade, para os 8 Mbit/s), STBY e
AUXIN a GND, SILENT ao MCU (escuta sem ACK). VISOOUT→VISOIN e GNDISO→GND2 por ferrite,
como pede a folha de características. NUP2105L nas linhas, terminação dividida
2 × 60,4 Ω + 4,7 nF ativada por jumper, borne de 3 vias (CANH, CANL, GND isolada).

## Folha 5: RS485 e RS232 (`serie.kicad_sch`)

ADM2582E a 3,3 V em meio-duplex (A–Y, B–Z), DE ao USART6, ~RE a GND (lê o próprio eco),
VISOOUT ligado a VISOIN, SM712, terminação de 120 Ω por jumper. MAX3227E sempre ligado
(FORCEON e ~FORCEOFF a 3,3 V) e DE-9 fêmea como DCE (2 = para o PC, 3 = do PC, 5 = GND).

## Folha 6: I2C e GPS (`i2c_gps.kicad_sch`)

Dois TCA9406 com VCCA = 3,3 V (MCU) e VCCB à tensão do sensor (VPU), escolhida por
jumper entre 3,3 V e 5 V; a VPU também alimenta o sensor pelo conector. **Sensores
suportados: 3,3 V e 5 V.** Os de 1,8 V ligam-se por um módulo com tradutor próprio. O
TCA9406 aceita VCCA = VCCB (o PCA9306 anterior ficava fora do recomendado com sensores
de 3,3 V). OE dos dois em PG0, com 10 kΩ a GND: os tradutores só ligam depois de o
firmware arrancar. Pull-ups de 2,2 kΩ do lado do MCU e 4,7 kΩ do lado do sensor, em
paralelo com os 10 kΩ internos. PRTR5V0U2X em cada conector I2C. Conector GPS JST-PH de 5 vias (3V3, GND, TX, RX,
PPS) com resistências em série e ESDA6V1-5SC6.

## Pontos de teste e mecânica

TP1–TP4: VIN, 5 V, 3,3 V e GND. TP5–TP8: as três saídas PWM e a massa isolada. TP9: PPS.
Quatro furos M3 (H1–H4).

## Folha 7: PWM isolado (`pwm.kicad_sch`)

Três 74AHCT1G125 a 5 V passam os PWM de 3,3 V para 5 V (o ADuM6401 a 5 V não reconhece
3,3 V como nível alto). ADuM6401 com VDD1 = VDDL = 5 V e VSEL a VISO (5 V isolados).
Saídas com 47 Ω, entrada de falha com pull-up para VISO, que volta ao MCU por um divisor
10k/20k até ao TIM1_BKIN. ESDA6V1-5SC6 no lado isolado e conector JST-PH de 6 vias.

## Lista de material

`python3 -I gerador/bom.py` lê o esquema e escreve `bom/bom.csv` (abre no Excel), com
referências, quantidades, fabricante, referência do fabricante, preço unitário e subtotal.
Os preços estão em `bom/precos.csv`: os dos circuitos integrados e semicondutores foram
consultados (fonte e data em cada linha); os dos passivos e conectores são estimativas e
estão marcados como tal.

O que não está no esquema (NUCLEO-H753ZI, recetor GPS com PPS, fabrico da PCB, fichas e
contactos JST, cabos para os ensaios) está em `bom/extras.csv` e entra no mesmo ficheiro.

| Parte | Total (24/11/2026) |
|---|---|
| Componentes da placa (101,04 € consultados + 16,24 € estimados) | 117,28 € |
| Fora do esquema (87,45 € consultados + 35,00 € estimados) | 122,45 € |
| **Projeto completo** | **239,73 €** |

O fabrico assume uma placa até 10 × 10 cm (5 unidades na JLCPCB); se o layout ficar
maior, o preço sobe. O envio e os cabos são estimativas. O HR911105A só aparece na LCSC;
os restantes foram vistos na DigiKey, na RS ou no capítulo de Projeto.

## Consumo por barramento

Valores máximos das folhas de características, salvo onde diz estimativa. Serve para
validar a corrente de 2 A usada na compensação do LM5177 e o limite de 1 A do TPS62162.

| Barramento | Carga | Corrente |
|---|---|---|
| 3,3 V | STM32H743 a 480 MHz (275 µA/MHz sem periféricos, + periféricos; estimativa) | 300 mA |
| 3,3 V | ADM2582E a 16 Mbit/s com 54 Ω (máx.) | 230 mA |
| 3,3 V | LAN8742A, MAX3227E, TCA9406, LED (estimativa) | 80 mA |
| 3,3 V | Módulo GPS (estimativa) | 50 mA |
| **3,3 V** | **Total (TPS62162: 1 A)** | **≈ 0,66 A** |
| 5 V | 2 × ADM3057E, dominante em falha (máx. 260 mA cada) | 520 mA |
| 5 V | ADuM6401 com VISO à carga máxima (máx.) | 290 mA |
| 5 V | 3,3 V através do TPS62162 (2,2 W / 90 %) | ≈ 490 mA |
| **5 V** | **Total (pior caso)** | **≈ 1,3 A** |

Pior caso na entrada: ≈ 1,6 A a 4,5 V (fusível de 3 A, Schottky de 5 A, ≈ 1 W no D2).
A 60 V são ≈ 0,12 A.

## Ainda por fechar

- **Margem de fase do LM5177:** a compensação foi calculada pelas equações da folha de
  características; medir no protótipo (ou simular no WEBENCH) antes de fechar.
- **Footprint do LM5177:** confirmar o pad exposto com o desenho DCP0038.
- **Surtos na entrada:** o LM5177 aguenta 85 V (máximo absoluto). Nenhum TVS com tensão de
  trabalho de 60 V limita abaixo disso à corrente de pico: o SMCJ60CA começa a conduzir a
  66,7 V mas chega a 96,8 V a 15,5 A. Protege contra ESD e transitórios curtos com pouca
  energia. Se for preciso cumprir um ensaio de surto (por exemplo IEC 61000-4-5), é preciso
  um limitador ativo à entrada (surge stopper). Fica como risco no relatório.
- **Cristais:** condensadores de 15 pF assumem C_L = 10 pF; ajustar ao cristal comprado.
- **ERC completo:** corre na CI (KiCad 9) em cada PR; ver `.github/workflows/ci.yml`. Fica
  um erro aceite: os dois pinos VCAP do STM32H743 são saídas de alimentação ligadas entre
  si, como a ST pede para o LQFP144 (2 × 2,2 µF e os VCAP unidos); o KiCad acusa duas
  saídas de alimentação na mesma rede.
- **Encaminhamento da placa** (ver "Placa de circuito impresso").
