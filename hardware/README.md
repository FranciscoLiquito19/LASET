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

## Verificar (ERC)

`Inspecionar > Verificador de regras elétricas > Executar ERC`.
Os únicos pinos sem ligação devem ser os NC do LM5177 e os HO1_LL/HO2_LL, que estão
marcados com cruz. Qualquer outro erro deve ser reportado.

Avisos esperados e inofensivos: `lib_symbol_mismatch` (a cópia do símbolo guardada no
esquema vem da biblioteca do KiCad 7; resolve-se com `Ferramentas > Atualizar símbolos
a partir da biblioteca`) e `Global label only appears once` enquanto faltarem as
folhas que usam essas etiquetas (PG_5V, PG_3V3).

## Regenerar depois de mudar o código

```sh
cd hardware/gerador
python3 -I gerar.py
```

Não editar à mão os `.kicad_sch` gerados: as alterações perdem-se na próxima geração.
Arrumar a posição dos componentes na interface é seguro só depois de congelarmos o
gerador (fase de layout).

## Folha 1: Alimentação (`alimentacao.kicad_sch`)

Percurso: J1 (entrada 5 a 60 V) → F1 (polyfuse) → D1 (TVS) → D2 (Schottky contra
inversão) → **U1 LM5177** (buck-boost, 5 V) → **U2 TPS62162** (3,3 V).

| Bloco | Componentes | Como se chegou ao valor |
|---|---|---|
| UVLO | R1 53,6k, R2 20,5k | Liga a 1,25 V × (1 + 53,6/20,5) = 4,52 V |
| Tensão de saída | R7 40,2k, R8 10k | 1,0 V × (1 + 40,2/10) = 5,02 V |
| Frequência | R5 78,7k | 400 kHz (exemplo da folha de características) |
| Sensor de corrente | R10 10 mΩ, R11/R12 10 Ω, C9 180 pF | Limite 50 mV / 10 mΩ = 5 A típico (3,85 A mínimo) |
| Rampa | R4 75k | L / R_CS × 50×10⁶ = 15 µH / 10 mΩ × 50×10⁶ |
| Bobina | L1 15 µH, Isat ≥ 6 A | Ondulação ≈ 0,76 A no pior caso (60 V → 5 V) |
| MOSFET | Q1 a Q4 BSC070N10NS5 (100 V, 7 mΩ) | O lado de entrada tem de aguentar os 60 V com margem; usa-se o mesmo nos quatro para simplificar a compra |
| Pinos de modo | MODE e SYNC a VCC, DTRK e BIAS a GND | MODE alto = PWM forçado (frequência fixa, menos ruído) |

**Alteração face ao relatório:** o LM74700-Q1 saiu. Aguenta no máximo 65 V e, com
entrada nominal de 60 V, o TVS de proteção limita acima disso. Passou a ser um
Schottky de 100 V (D2): mais simples e robusto, à custa de ~0,5 V de queda.

**Ainda por fechar nesta folha (marcado no esquema):**
- Rede de compensação R6/C5/C6: valores do exemplo da TI, recalcular no WEBENCH para
  15 µH e 5 V.
- Referência exata da bobina.
- Footprint do LM5177: o KiCad não tem o HTSSOP-38 de 4,4 mm com pad exposto; está
  provisoriamente o TSSOP-38 sem pad. É preciso criar o footprint.
- Pino FB do TPS62162 (versão fixa de 3,3 V) a GND: confirmar na folha de características.

## Folha 2: Microcontrolador (`mcu.kicad_sch`)

STM32H743ZIT6 com 11 condensadores de 100 nF (um por VDD) + 4,7 µF, VDDA filtrado por
ferrite, 2 × 2,2 µF no VCAP, cristal de 25 MHz (o PLL dá 80 MHz exatos para o FDCAN a
8 Mbit/s), cristal de 32,768 kHz para o RTC, conector SWD de 10 pinos, consola em USART3
e dois LED.

O gerador **recusa gerar** se algum pino não tiver a função alternativa pedida
(`verificar_pinos()` em `folha_mcu.py`). Atribuição:

| Função | Pinos |
|---|---|
| Ethernet RMII (igual à NUCLEO-H753ZI) | PA1 REF_CLK, PA2 MDIO, PC1 MDC, PA7 CRS_DV, PC4/PC5 RXD0/1, PG11 TX_EN, PG13/PB13 TXD0/1, PG14 reset do PHY |
| CAN FD 1 / 2 | PD0/PD1 (FDCAN1), PB5/PB6 (FDCAN2); PG2/PG3 STBY |
| RS485 (USART1, DE por hardware) | PA9 TX, PA10 RX, PA12 DE, PA11 nRE |
| RS232 (USART2) | PD5 TX, PD6 RX |
| GPS | PE7/PE8 (UART7), PA15 PPS (TIM2_CH1, 32 bits) |
| I2C 1 / 2 | PB8/PB9, PF1/PF0 |
| PWM (TIM1) | PE9, PE11, PE13; PE14 retorno do isolador |
| Consola, SWD | PD8/PD9 (USART3); PA13, PA14, PB3 |
| Estado | PG0 PG_5V, PG1 PG_3V3, PB0 e PE1 LED |

## Folhas 3 a 7: interfaces

| Folha | Conteúdo |
|---|---|
| Ethernet | LAN8742A em RMII, cristal 25 MHz, REF_CLK de 50 MHz para o MCU, terminações de 49,9 Ω, RJ45 com magnéticos HR911105A |
| CAN FD | 2 × ADM3057E isolados; STBY com pull-down; terminação de 120 Ω por jumper de solda; bornes H, L, GND isolado |
| RS485 e RS232 | ADM2582E isolado em half-duplex com terminação por jumper; MAX3227E sempre ligado |
| I2C e GPS | 2 × PCA9306 (lado do sensor a 3,3 ou 5 V por JP4); conector GPS com PPS protegido por 100 Ω |
| PWM isolado | ADuM6401: 3 canais isolados + retorno do PWM1 isolado para diagnóstico; VSEL a VISO (5 V) |

## Verificação feita aqui

161 componentes, 218 redes, nenhuma etiqueta global sem par, nenhuma referência
repetida. O ERC final é no KiCad (a versão de linha de comandos que tenho não o faz).

## A verificar antes do fabrico

- **ADuM6401:** símbolo próprio em `lib/laset.kicad_sym`; pino 7 (VDDL) ligado a VDD1, confirmado na Tabela 22 da folha de características.
- **HR911105A:** pinos dos LED (9 a 12) sem ligação; confirmar o pino 8 (blindagem).
- **LM5177:** compensação (WEBENCH) e footprint com pad exposto.
- **TPS62162:** FB a GND na versão fixa de 3,3 V.
- **Footprints no KiCad 9:** alguns nomes podem ter mudado. Ver o passo seguinte.

## Passo seguinte: footprints e PCB

1. No editor de esquemas: **Ferramentas > Atualizar PCB a partir do esquema** (F8).
   Abre o editor de PCB e lista os footprints que não encontrou. Manda-me essa lista.
2. Com todos os footprints encontrados, definimos o contorno da placa, as 4 camadas
   (sinal, GND, alimentação, sinal) e as zonas de isolamento antes de colocar componentes.
