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

Na NUCLEO, a Ethernet funciona tal como na PCB (também usa um LAN8742A em RMII).

Os pinos são os mesmos nas duas (ver `hardware/gerador/folha_mcu.py` e `Core/Inc/placa.h`).
Na NUCLEO, o LD1 (verde, PB0) pisca a 2 Hz quando o firmware está a correr.

## Compilar

Precisa de `arm-none-eabi-gcc`, CMake ≥ 3.22 e Ninja ou Make. As bibliotecas da ST
(HAL e CMSIS), o FreeRTOS e o LwIP são descarregados na primeira configuração, nas versões
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

Os módulos sem hardware (encaminhamento, política de filas, COBS, CRC-16, NMEA,
ISO-TP, configuração e formato das tramas) têm testes que correm no PC:

```sh
cd firmware/testes
cmake -B build && cmake --build build && ./build/teste_modulos && ./build/teste_robustez
python3 ../ferramentas/laset_pc.py autoteste
```

`teste_robustez` passa milhões de entradas aleatórias ou corrompidas pelos módulos que
recebem dados de fora (COBS, tramas do PC, ISO-TP, NMEA, comandos de configuração),
compilado com AddressSanitizer e UndefinedBehaviorSanitizer: qualquer escrita fora de um
buffer para o programa. Confirma também que uma trama do PC com um byte trocado nunca é
aceite. Um dos testes lê uma trama gerada pela ferramenta do PC, o que garante que o Python e
o firmware usam o mesmo formato. `testes/pinos.py` confere os pinos configurados no
firmware (`stm32h7xx_hal_msp.c` e `placa.h`) com a tabela do esquema
(`hardware/gerador/folha_mcu.py`). A CI compila as duas placas e corre estes testes.

## Estado

| Parte | Estado |
|---|---|
| Relógios a 480 MHz, FDCAN a 80 MHz | feito |
| FDCAN1/2: 1 Mbit/s + 8 Mbit/s (BRS), TDC, autoteste em loopback no arranque, recuperação de bus-off | feito |
| Encaminhamento: fila de entrada, tabela, filas urgente/normal por saída, contadores de descarte | feito, com testes |
| Ligação ao PC por RS232: COBS + CRC-16, cabeçalho de 20 bytes | feito, com testes |
| Ligação ao PC por Ethernet: UDP para operações, TCP para configuração (LwIP) | feito (esboço) |
| Ligação ao PC por CAN FD 1 ou 2: ISO 15765-2 com tramas de 64 bytes | feito (esboço), com testes |
| Configuração persistente na flash, com dupla cópia (RF18) | feito (esboço), com testes |
| RS485 (DE automático, sem o eco do que emite), RS232 em bruto | feito |
| I2C1/I2C2: escrita e leitura com registo (início repetido), reinício do periférico se o barramento ficar preso | feito |
| PWM: 3 canais a 50 Hz, 0,5 µs, valor seguro sem comandos, paragem por hardware (BKIN) com rearme no comando seguinte, se a falha já tiver passado | feito |
| PPS no TIM2 (64 bits, compensação da deriva) + NMEA RMC | feito, com testes |

Tudo isto compila sem avisos mas **ainda não correu numa placa**. Para a PCB, os passos
do primeiro arranque estão em `hardware/ARRANQUE.md`. Primeiros ensaios na NUCLEO, por
esta ordem:

1. Consola (VCP, 115200): autoteste do CAN FD, "configuração: de fábrica" e o
   estado a cada 5 s.
2. Cabo de rede ao PC, com o PC em 192.168.1.x: `ping 192.168.1.50`, depois
   `laset_pc.py --udp 192.168.1.50 versao`.
3. `laset_pc.py --tcp 192.168.1.50 cfg-regra ...`, `cfg-gravar`, reiniciar a placa e
   ver "configuração: da flash" e a regra em `cfg-ler-regra 0`.

Simplificações deste esboço, a rever depois dos ensaios:

- A Ethernet copia cada trama para buffers fixos na SRAM D2 (sem cache) em vez de
  passar os pbufs ao DMA: mais simples, um pouco mais lento.
- O LwIP corre sem sistema operativo (`NO_SYS`), numa só tarefa; as outras tarefas
  passam-lhe mensagens por uma fila.
- O IP é fixo (192.168.1.50 de fábrica, alterável com `cfg-rede`); não há DHCP.
- Uma cópia da configuração meio escrita (falta de alimentação durante a gravação) tem
  o ECC errado e lê-la dá uma falha de barramento. A leitura é protegida: o
  `BusFault_Handler` salta a instrução, a cópia fica inválida e usa-se a outra (a região
  está sem cache na MPU). Ainda não foi provocado na placa: confirmar desligando a
  alimentação durante um `cfg-gravar`.

## Protocolo com o PC

Todas as ligações levam a mesma mensagem: cabeçalho de 20 bytes (`Core/Inc/mensagem.h`)
seguido de até 64 bytes de dados.

| Ligação | Como vai a mensagem |
|---|---|
| RS232 (USART2, 1 Mbit/s, PD5 = TX, PD6 = RX) | COBS(mensagem + CRC-16 LE) + 0x00 |
| Ethernet UDP, porta 5000 | um datagrama por mensagem; as respostas vão para o último endereço que enviou |
| Ethernet TCP, porta 5001 | como na série; a configuração por TCP é aceite mesmo que o PC esteja noutra ligação |
| CAN FD 1 ou 2 | ISO-TP: PC → unidade no id 0x7E0, unidade → PC no id 0x7E8, tramas FD de 64 bytes com BRS |

A ligação ao PC por omissão é o RS232; muda-se com `cfg-ligacao` e guarda-se com
`cfg-gravar`. Na NUCLEO, sem a PCB, liga-se um conversor USB-série de 3,3 V aos pinos
PD5/PD6 (ver no manual da placa em que conector ficam) e GND.

- O bit 7 do campo `tipo` marca a mensagem como urgente (RF14).
- Em CAN FD, o campo `endereco` leva o identificador nos bits 0–28; o bit 31 indica
  identificador estendido, o bit 30 trama FD e o bit 29 comutação de taxa (BRS).
- Mensagens para a interface `sistema`: `PEDIDO` devolve a versão; `CONFIG` executa um
  comando de configuração (lista em `Core/Inc/config.h`). A resposta é `CONFIRMACAO`
  ou `ERRO` e começa pelo número do comando.

`ferramentas/laset_pc.py` envia e recebe tramas (a série precisa de `pip install pyserial`):

```sh
python3 ferramentas/laset_pc.py --porta COM5 versao
python3 ferramentas/laset_pc.py --udp 192.168.1.50 can --canal 1 --id 0x123 --fd --brs 01 02 03
python3 ferramentas/laset_pc.py --porta COM5 pwm --canal 0 --us 1500
python3 ferramentas/laset_pc.py --porta COM5 i2c-ler --canal 0 --end 0x48 --n 2 --reg 0x00
python3 ferramentas/laset_pc.py --tcp 192.168.1.50 cfg-ler
python3 ferramentas/laset_pc.py --tcp 192.168.1.50 cfg-regra --de canfd:1 --para rs485:0 --ids 0x100-0x1ff --urgente
python3 ferramentas/laset_pc.py --tcp 192.168.1.50 cfg-gravar
```

## Configuração na flash

Fica nos setores 0 e 1 do banco 2 (0x08100000 e 0x08120000), fora da zona do
programa, por isso reprogramar o firmware não a apaga. Cada gravação vai para o setor
que não tem a cópia mais recente, com um número de sequência e um CRC-32; no arranque
usa-se a cópia válida com a maior sequência, ou os valores de fábrica se não houver
nenhuma. Guarda a tabela de encaminhamento (até 32 regras), a ligação ao PC, o IP,
as portas UDP/TCP e as velocidades do RS232 e do RS485 (estas três últimas só
contam a partir do arranque seguinte).
