# Firmware do gateway LASET

STM32H743/H753 a 480 MHz com FreeRTOS, organizado como no capítulo 5 do relatório
(Figura 5.2): as rotinas de receção colocam mensagens numa fila de entrada, uma tarefa
de encaminhamento aplica a tabela e cada saída tem duas filas (urgente e normal) e uma
tarefa de transmissão. Só alocação estática.

## Placas

| `PLACA` | Placa | Relógio | Notas |
|---|---|---|---|
| `NUCLEO` (omissão) | NUCLEO-H753ZI | HSE 8 MHz do ST-LINK (bypass) | consola no VCP (USART3, 115200); CAN FD em loopback interno (não há transceivers) |
| `LASET` | PCB do projeto (STM32H743ZIT6) | cristal de 25 MHz | CAN FD normal |

Os pinos são os mesmos nas duas (ver `hardware/gerador/folha_mcu.py` e `Core/Inc/placa.h`).
Na NUCLEO, o LD1 (verde, PB0) pisca a 2 Hz quando o firmware está a correr.

## Compilar

Precisa de `arm-none-eabi-gcc`, CMake ≥ 3.22 e Ninja ou Make. As bibliotecas da ST
(HAL e CMSIS) e o FreeRTOS são descarregados na primeira configuração, nas versões
fixadas em `CMakeLists.txt`.

```sh
cd firmware
cmake -B build -DPLACA=NUCLEO -DCMAKE_TOOLCHAIN_FILE=cmake/gcc-arm-none-eabi.cmake
cmake --build build
```

Gera `build/laset_gateway.elf`, `.hex` e `.bin`. Para programar: abrir o `.elf` no
STM32CubeProgrammer, ou na extensão STM32 do VS Code, ou arrastar o `.bin` para a
unidade USB que a NUCLEO cria.

No VS Code: instalar a extensão "STM32Cube for Visual Studio Code" (traz o compilador,
o CMake e o depurador ST-LINK) e abrir a pasta `firmware`.

## Testes

Os módulos sem hardware (encaminhamento, política de filas, COBS, CRC-16, NMEA e
cálculo do tempo) têm testes que correm no PC:

```sh
cd firmware/testes
cmake -B build && cmake --build build && ./build/teste_modulos
python3 ../ferramentas/laset_pc.py autoteste
```

Um dos testes lê uma trama gerada pela ferramenta do PC, o que garante que o Python e
o firmware usam o mesmo formato. A CI compila as duas placas e corre estes testes.

## Estado

| Parte | Estado |
|---|---|
| Relógios a 480 MHz, FDCAN a 80 MHz | feito |
| FDCAN1/2: 1 Mbit/s + 8 Mbit/s (BRS), TDC, autoteste em loopback no arranque | feito |
| Encaminhamento: fila de entrada, tabela, filas urgente/normal por saída, contadores de descarte | feito, com testes |
| Ligação ao PC por RS232: COBS + CRC-16, cabeçalho de 20 bytes | feito, com testes |
| RS485 (DE automático), RS232 em bruto | feito |
| I2C1/I2C2: escrita e leitura com registo | feito |
| PWM: 3 canais a 50 Hz, 0,5 µs, valor seguro sem comandos, paragem por hardware (BKIN) | feito |
| PPS no TIM2 (64 bits, compensação da deriva) + NMEA RMC | feito, com testes |
| Ethernet (LwIP: UDP para operações, TCP para configuração) | próxima fase |
| CAN FD 1 como ligação ao PC (segmentação ISO 15765-2) | próxima fase |
| Configuração persistente na flash (RF18) | próxima fase |

Tudo isto compila sem avisos mas **ainda não correu numa placa**: o primeiro ensaio
é ligar a NUCLEO e ver na consola o autoteste do CAN FD e o estado a cada 5 s.

## Protocolo com o PC

`ferramentas/laset_pc.py` envia e recebe tramas (precisa de `pip install pyserial`):

```sh
python3 ferramentas/laset_pc.py --porta COM5 versao
python3 ferramentas/laset_pc.py --porta COM5 can --canal 1 --id 0x123 --fd --brs 01 02 03
python3 ferramentas/laset_pc.py --porta COM5 pwm --canal 0 --us 1500
python3 ferramentas/laset_pc.py --porta COM5 i2c-ler --canal 0 --end 0x48 --n 2 --reg 0x00
```

- O bit 7 do campo `tipo` marca a mensagem como urgente (RF14).
- Em CAN FD, o campo `endereco` leva o identificador nos bits 0–28; o bit 31 indica
  identificador estendido, o bit 30 trama FD e o bit 29 comutação de taxa (BRS).
- Por omissão a ligação ao PC é o RS232 (USART2, 1 Mbit/s, pinos PD5 = TX e PD6 = RX).
  Na NUCLEO, sem a PCB, liga-se um conversor USB-série de 3,3 V a esses dois pinos
  (ver no manual da placa em que conector ficam) e GND.
