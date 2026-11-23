# Hardware do gateway LASET

Projeto KiCad do gateway multiprotocolo. O esquema é **gerado por código** a partir de
`gerador/`: cada folha é um ficheiro Python com os componentes, os valores e a rede de
cada pino. Assim cada alteração fica revista em PR, como o relatório.

## Abrir o projeto

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

## Bibliotecas do projeto

- `lib/laset.kicad_sym`: LM5177 e ADuM6401 (não existem nas bibliotecas do KiCad).
- `lib/laset.pretty`: footprint HTSSOP-38 do LM5177 com pad exposto de 2,90 × 4,70 mm
  (abertura do stencil do exemplo da TI) e vias térmicas. **Confirmar com o desenho DCP0038
  antes do fabrico.**

## Folha 1: Alimentação (`alimentacao.kicad_sch`)

Percurso: J1 (entrada 5 a 60 V) → F1 (polyfuse) → D1 (TVS) → D2 (Schottky contra
inversão) → **U1 LM5177** (buck-boost, 5 V) → **U2 TPS62162** (3,3 V).

| Bloco | Componentes | Como se chegou ao valor |
|---|---|---|
| UVLO | R1 53,6k, R2 20,5k | Liga a 1,25 V × (1 + 53,6/20,5) = 4,52 V |
| Tensão de saída | R7 40,2k, R8 10k | 1,0 V × (1 + 40,2/10) = 5,02 V |
| Frequência | R5 75k | 400 kHz (Eq. 17 e Tabela 8-3; o texto do exemplo da TI diz 78,7k, que é gralha) |
| Sensor de corrente | R10 10 mΩ, R11/R12 10 Ω, C9 180 pF | Limite 50 mV / 10 mΩ = 5 A típico (3,85 A mínimo) |
| Rampa | R4 90,9k | L / R_CS × 50×10⁶ = 18 µH / 10 mΩ × 50×10⁶ = 90k |
| Bobina | L1 SRP1245A-180M, 18 µH, Isat 11 A, 45 mΩ | Ondulação ≈ 0,63 A no pior caso (60 V → 5 V). Tem footprint na biblioteca do KiCad; o SRP1265A de 15 µH não tem |
| MOSFET | Q1 a Q4 BSC160N10NS3 G (100 V, 16 mΩ, TDSON-8) | Os do lado de entrada têm de aguentar 60 V com margem; usa-se o mesmo nos quatro para ter uma só referência |
| Compensação | R6 2,0k, C5 56 nF, C6 2,2 nF | f_BW = 4 kHz, abaixo de f_RHPZ/3 (14,5 kHz no modo elevador a 4,5 V e 2 A); contas no cabeçalho de `folha_alimentacao.py` |
| Pinos de modo | MODE e SYNC a VCC, DTRK e BIAS a GND | MODE alto = PWM forçado (frequência fixa, menos ruído) |
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
| I2C1 / I2C2 | PB8/PB9 e PF1/PF0 (SCL/SDA) |
| PWM (TIM1) | PE9, PE11, PE13; falha em PE15 = TIM1_BKIN |
| Estado | PB0 LED, PF2 PG_5V, PF3 PG_3V3 |

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

Dois PCA9306 com VREF1 = 3,3 V; VREF2/EN por 200 kΩ à tensão do sensor (VPU), escolhida
por jumper entre 3,3 V e 5 V. Pull-ups de 2,2 kΩ do lado do MCU e 4,7 kΩ do lado do
sensor. PRTR5V0U2X em cada conector I2C. Conector GPS JST-PH de 5 vias (3V3, GND, TX, RX,
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

Total por placa (23/11/2026): **116,94 €**, dos quais 100,68 € com preço consultado e
16,26 € estimados. Não inclui o fabrico da PCB, as fichas fêmea dos conectores JST, a
NUCLEO nem o recetor GPS. O HR911105A só aparece na LCSC; os restantes foram vistos na
DigiKey, na RS ou no capítulo de Projeto.

## Consumo por barramento

Valores máximos das folhas de características, salvo onde diz estimativa. Serve para
validar a corrente de 2 A usada na compensação do LM5177 e o limite de 1 A do TPS62162.

| Barramento | Carga | Corrente |
|---|---|---|
| 3,3 V | STM32H743 a 480 MHz (275 µA/MHz sem periféricos, + periféricos; estimativa) | 300 mA |
| 3,3 V | ADM2582E a 16 Mbit/s com 54 Ω (máx.) | 230 mA |
| 3,3 V | LAN8742A, MAX3227E, PCA9306, LED (estimativa) | 80 mA |
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
- **PCA9306:** a TI pede VREF1 abaixo de VREF2 (cerca de 1 V). Com VPU = 5 V está bem; com
  VPU = 3,3 V funciona no limite. Para sensores de 1,8 V seria preciso trocar os lados ou
  usar outro tradutor. **Decisão do grupo:** que sensores se querem suportar.
- **Cristais:** condensadores de 15 pF assumem C_L = 10 pF; ajustar ao cristal comprado.
- **ERC completo:** corre na CI (KiCad 9) em cada PR; ver `.github/workflows/ci.yml`.
- **Layout** (fase seguinte).
