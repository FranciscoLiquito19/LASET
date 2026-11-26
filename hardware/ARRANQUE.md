# Primeiro arranque da placa

Passos para quando a placa chegar montada, por esta ordem. Cada passo só depende dos
anteriores: se um falhar, parar e resolver antes de continuar. Material: fonte de bancada
com limite de corrente, multímetro, cabo SWD (o ST-LINK de uma NUCLEO serve), conversor
USB-RS232 que aguente 1 Mbit/s (por exemplo com FTDI), cabo de rede e, para o fim,
osciloscópio.

Pontos de teste na placa: TP1 entrada (VIN), TP2 +5V, TP3 +3V3, TP4 massa, TP5 a TP7
saídas PWM, TP8 massa isolada do PWM, TP9 PPS do GPS.

## 1. Antes de ligar

1. Ver a placa à lupa: peças em falta, pontes de solda nos pinos do STM32 (U3), do
   LAN8742A (U4) e do LM5177 (U1), peças rodadas (ponto do pino 1 contra a marca na placa).
2. Com o multímetro em resistência, medir para a massa (TP4): TP1, TP2 e TP3. Nenhuma pode
   dar perto de 0 Ω. Ao princípio o valor sobe devagar (os condensadores estão a carregar),
   é normal.
3. Soldar as peças que não vêm montadas: U14 (ADuM6401ARWZ) e J7 (DE-9). Se a montagem foi
   só numa face, também C34, C35, C61, C62 e C63 por baixo.
4. Jumpers: JP6 (BOOT0) aberto; JP1 a JP3 (terminações) abertos; JP4 e JP5 em 1-2 (3,3 V).

## 2. Alimentação

1. Fonte a 12 V com o limite de corrente em 0,3 A, ligada a J1: pino 1 (quadrado) ao
   positivo, pino 2 à massa. O díodo D2 protege contra a inversão, mas é melhor não testar.
2. Ligar e ver a corrente. Com o STM32 ainda sem programa deve ficar bem abaixo do limite.
   Se a fonte entrar em limite de corrente, desligar logo e procurar o curto.
3. Medir TP2: 5,0 V (±2 %). Medir TP3: 3,3 V (±3 %).
4. Tocar ao de leve (ou usar câmara térmica) em U1, Q1 a Q4, L1, U2: nada deve aquecer
   em vazio.
5. Repetir a 5 V, 24 V e 48 V. A 5 V a placa liga a partir de cerca de 4,0 V e desliga
   abaixo de 3,6 V. Não passar de 60 V.

## 3. Programar

1. Ligar o cabo SWD a J2 (mesma ordem de pinos do conector SWD das NUCLEO: 1 +3V3,
   2 SWCLK, 3 GND, 4 SWDIO, 5 NRST, 6 SWO).
2. Compilar o firmware para esta placa:
   ```sh
   cd firmware
   cmake -B build-pcb -DPLACA=LASET -DCMAKE_TOOLCHAIN_FILE=cmake/gcc-arm-none-eabi.cmake
   cmake --build build-pcb
   ```
3. Programar `build-pcb/laset_gateway.elf` com o STM32CubeProgrammer.
4. O LED verde D3 pisca a 2 Hz: o relógio de 25 MHz e o FreeRTOS estão a funcionar.
   Se não piscar, ver com o osciloscópio se o cristal Y1 oscila.

Na PCB não há consola; os ensaios seguintes fazem-se pela ferramenta do PC
(`firmware/ferramentas/laset_pc.py`, precisa de `pip install pyserial`).

## 4. Interfaces, uma a uma

| Interface | Como testar | Resultado esperado |
|---|---|---|
| RS232 (J7) | `python3 laset_pc.py --porta COM5 versao` (1 Mbit/s) | resposta com a versão |
| Ethernet (J3) | PC em 192.168.1.x; `ping 192.168.1.50`; `laset_pc.py --udp 192.168.1.50 versao` | LEDs do RJ45 acesos, ping e versão |
| Configuração | `laset_pc.py --tcp 192.168.1.50 cfg-ler`, `cfg-gravar`, desligar e voltar a ligar | a configuração mantém-se |
| CAN FD 1 e 2 (J4, J5) | fechar JP1 e JP2; ligar CANH, CANL e massa a um adaptador CAN FD ou a outra placa; `laset_pc.py ... can --canal 0 --id 0x123 --fd --brs 01 02 03` | trama vista do outro lado a 1/8 Mbit/s |
| RS485 (J6) | fechar JP3; adaptador USB-RS485; regra de encaminhamento com `cfg-regra` | bytes nos dois sentidos |
| I2C1, I2C2 (J8, J9) | sensor de 3,3 V (JP4/JP5 em 1-2); `laset_pc.py ... i2c-ler --canal 0 --end 0x48 --n 2 --reg 0x00` | leitura do registo |
| PWM (J11) | `laset_pc.py ... pwm --canal 0 --us 1500`; osciloscópio em TP5, massa em TP8 | impulso de 1,5 ms a 50 Hz; sem comandos volta ao valor seguro |
| GPS (J10) | recetor com PPS; ver o impulso em TP9 | 1 impulso por segundo |

## 5. Ensaios da fonte (com osciloscópio)

1. Ondulação: ponta curta (mola de massa) em TP2. Esperado: algumas dezenas de mV.
2. Degrau de carga: carga eletrónica na saída de 5 V, de 0,2 A para 1 A. A tensão deve
   recuperar sem oscilar mais de 2 ou 3 ciclos; oscilação longa indica margem de fase
   curta (a compensação foi calculada para 4 kHz e ainda não foi medida).
3. Repetir a 5 V e a 48 V de entrada: o LM5177 passa de elevador a redutor e a
   resposta muda.

Registar os valores medidos: vão para o capítulo de Resultados do relatório.
