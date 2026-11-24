"""Folha 2: microcontrolador STM32H743ZIT6 (LQFP-144).

Atribuição de pinos (funções alternativas da folha de características DS12110 da ST;
o percurso Ethernet RMII é o mesmo da NUCLEO-H743ZI, o que permite reaproveitar o
projeto CubeMX da placa de avaliação):

  Ethernet RMII  PA1 REF_CLK, PA2 MDIO, PC1 MDC, PA7 CRS_DV, PC4 RXD0, PC5 RXD1,
                 PG11 TX_EN, PG13 TXD0, PB13 TXD1
  FDCAN1         PD0 RX, PD1 TX          SILENT do transceiver: PG2
  FDCAN2         PB5 RX, PB6 TX          SILENT do transceiver: PG3
  RS232 (USART2) PD5 TX, PD6 RX
  RS485 (USART6) PC6 TX, PC7 RX, PG8 DE (controlo automático do emissor)
  GPS (UART7)    PE8 TX, PE7 RX; PPS em PA0 = TIM2_CH1 (temporizador de 32 bits)
  I2C1           PB8 SCL, PB9 SDA
  I2C2           PF1 SCL, PF0 SDA
  PWM (TIM1)     PE9 CH1, PE11 CH2, PE13 CH3; PE15 = TIM1_BKIN (falha isolada)
  SWD            PA13 SWDIO, PA14 SWCLK, PB3 SWO
  Estado         PB0 LED; PF2 PG_5V; PF3 PG_3V3
"""
from hw import Folha, simbolo, pinos
from comum import (R, C, FB, R0603, C0603, C0805, FB0603, LED0603, XTAL3225, JP2, desacoplamento)

MCU = 'MCU_ST_STM32H7:STM32H743ZITx'

PINOS = {
    # alimentação
    'VDD': '+3V3', 'VDD33_USB': '+3V3', 'VBAT': '+3V3', 'VSS': 'GND', 'VSSA': 'GND',
    # PDR_ON a VDD liga o supervisor interno (reset por queda de tensão), como na NUCLEO;
    # flutuante fica indefinido.
    'PDR_ON': '+3V3',
    'VDDA': '/VDDA', 'VREF+': '/VDDA', 'VCAP': '/VCAP', 'NRST': 'NRST', 'BOOT0': '/BOOT0',
    'PH0': '/OSC_IN', 'PH1': '/OSC_OUT',
    # Ethernet RMII
    'PA1': 'ETH_REF_CLK', 'PA2': 'ETH_MDIO', 'PC1': 'ETH_MDC', 'PA7': 'ETH_CRS_DV',
    'PC4': 'ETH_RXD0', 'PC5': 'ETH_RXD1', 'PG11': 'ETH_TX_EN', 'PG13': 'ETH_TXD0', 'PB13': 'ETH_TXD1',
    # CAN FD
    'PD0': 'CAN1_RX', 'PD1': 'CAN1_TX', 'PG2': 'CAN1_SILENT',
    'PB5': 'CAN2_RX', 'PB6': 'CAN2_TX', 'PG3': 'CAN2_SILENT',
    # série
    'PD5': 'RS232_TX', 'PD6': 'RS232_RX',
    'PC6': 'RS485_TX', 'PC7': 'RS485_RX', 'PG8': 'RS485_DE',
    # GPS
    'PE8': 'GPS_TX', 'PE7': 'GPS_RX', 'PA0': 'GPS_PPS',
    # I2C
    'PB8': 'I2C1_SCL', 'PB9': 'I2C1_SDA', 'PF1': 'I2C2_SCL', 'PF0': 'I2C2_SDA', 'PG0': 'I2C_OE',
    # PWM
    'PE9': 'PWM1', 'PE11': 'PWM2', 'PE13': 'PWM3', 'PE15': 'PWM_FALHA',
    # depuração e estado
    'PA13': '/SWDIO', 'PA14': '/SWCLK', 'PB3': '/SWO', 'PB0': '/LED',
    'PF2': 'PG_5V', 'PF3': 'PG_3V3',
}


def folha():
    f = Folha('Microcontrolador', 'mcu.kicad_sch', notas=[
        'STM32H743ZIT6 (DP03). Atribuição de pinos no cabeçalho de gerador/folha_mcu.py; os GPIO livres ficam marcados como não ligados.',
        'Condensadores de 100 nF junto a cada par VDD/VSS; VCAP com 2,2 uF de baixa ESR (< 100 mOhm) por pino.',
        'Cristal HSE de 25 MHz: condensadores de carga para C_L = 10 pF; ajustar se o cristal escolhido tiver outra C_L.',
    ])
    nomes = {p.name for p in pinos(simbolo(MCU))}
    for k in PINOS:
        assert k in nomes, k
    f.comp('U3', MCU, 'STM32H743ZIT6', 210, 150, PINOS, nc_resto=True)

    # Desacoplamento do domínio digital: um 100 nF por pino VDD + 4,7 uF de reserva
    refs = [f'C{20 + i}' for i in range(12)]
    desacoplamento(f, refs, ['100 nF'] * 11 + ['4,7 uF'], '+3V3', 'GND', 30, 40, passo=9)

    # VDDA e VREF+ filtrados
    f.comp('FB1', FB, '600 Ohm @ 100 MHz', 40, 80, {1: '+3V3', 2: '/VDDA'}, FB0603)
    f.comp('C32', C, '1 uF', 55, 80, {1: '/VDDA', 2: 'GND'}, C0603)
    f.comp('C33', C, '100 nF', 65, 80, {1: '/VDDA', 2: 'GND'}, C0603)

    # Regulador interno (VCAP)
    f.comp('C34', C, '2,2 uF (baixa ESR)', 40, 105, {1: '/VCAP', 2: 'GND'}, C0805)
    f.comp('C35', C, '2,2 uF (baixa ESR)', 52, 105, {1: '/VCAP', 2: 'GND'}, C0805)

    # Reset e arranque
    f.comp('C36', C, '100 nF', 40, 130, {1: 'NRST', 2: 'GND'}, C0603)
    f.comp('R20', R, '10k', 52, 130, {1: '/BOOT0', 2: 'GND'}, R0603)
    f.comp('JP6', 'Jumper:Jumper_2_Open', 'BOOT0 (fechar = bootloader)', 66, 145, {1: '+3V3', 2: '/BOOT0'}, JP2)

    # Oscilador HSE
    f.comp('Y1', 'Device:Crystal_GND24', '25 MHz (C_L 10 pF)', 60, 165, {1: '/OSC_IN', 3: '/OSC_OUT', 2: 'GND', 4: 'GND'}, XTAL3225)
    f.comp('C37', C, '15 pF', 40, 180, {1: '/OSC_IN', 2: 'GND'}, C0603)
    f.comp('C38', C, '15 pF', 80, 180, {1: '/OSC_OUT', 2: 'GND'}, C0603)

    # SWD
    # Mesma ordem do CN4 (SWD) do ST-LINK das placas NUCLEO: cabo direto de 6 vias
    f.comp('J2', 'Connector_Generic:Conn_01x06', 'SWD (CN4 da NUCLEO)', 340, 70, {
        1: '+3V3', 2: '/SWCLK', 3: 'GND', 4: '/SWDIO', 5: 'NRST', 6: '/SWO'},
        'Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical')

    # LED de estado
    f.comp('R21', R, '1k', 330, 130, {1: '/LED', 2: '/LED_A'}, R0603)
    f.comp('D3', 'Device:LED', 'Verde', 345, 130, {2: '/LED_A', 1: 'GND'}, LED0603)
    # PWR_FLAG: redes alimentadas por ferrite, resistência ou regulador interno (ERC)
    f.flag('/VDDA', 395, 40)
    return f
