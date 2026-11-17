"""Folha 2: microcontrolador STM32H743ZIT6 (LQFP144).

Atribuição de pinos verificada contra as funções alternativas do símbolo KiCad
(ver verificar_pinos() em baixo). A Ethernet usa os mesmos pinos da placa
NUCLEO-H753ZI, para o firmware correr sem alterações na Nucleo e na PCB.
"""
from hw import Folha, pinos, simbolo

R0603 = 'Resistor_SMD:R_0603_1608Metric'
C0603 = 'Capacitor_SMD:C_0603_1608Metric'

# pino do MCU -> (rede global, função alternativa esperada ou None para GPIO)
PINOS = {
    # Ethernet RMII (igual à NUCLEO-H753ZI)
    'PA1': ('ETH_REF_CLK', 'ETH_REF_CLK'), 'PA2': ('ETH_MDIO', 'ETH_MDIO'), 'PC1': ('ETH_MDC', 'ETH_MDC'),
    'PA7': ('ETH_CRS_DV', 'ETH_CRS_DV'), 'PC4': ('ETH_RXD0', 'ETH_RXD0'), 'PC5': ('ETH_RXD1', 'ETH_RXD1'),
    'PG11': ('ETH_TX_EN', 'ETH_TX_EN'), 'PG13': ('ETH_TXD0', 'ETH_TXD0'), 'PB13': ('ETH_TXD1', 'ETH_TXD1'),
    'PG14': ('ETH_NRST', None),
    # CAN FD
    'PD0': ('CAN1_RX', 'FDCAN1_RX'), 'PD1': ('CAN1_TX', 'FDCAN1_TX'), 'PG2': ('CAN1_STBY', None),
    'PB5': ('CAN2_RX', 'FDCAN2_RX'), 'PB6': ('CAN2_TX', 'FDCAN2_TX'), 'PG3': ('CAN2_STBY', None),
    # RS232 (USART2; o MAX3227E só tem TX/RX)
    'PD5': ('RS232_TX', 'USART2_TX'), 'PD6': ('RS232_RX', 'USART2_RX'),
    # RS485 (USART1, DE por hardware)
    'PA9': ('RS485_TX', 'USART1_TX'), 'PA10': ('RS485_RX', 'USART1_RX'), 'PA12': ('RS485_DE', 'USART1_DE'),
    'PA11': ('RS485_NRE', None),
    # GPS: NMEA por UART7, PPS na captura do TIM2 (32 bits)
    'PE7': ('GPS_RX', 'UART7_RX'), 'PE8': ('GPS_TX', 'UART7_TX'), 'PA15': ('GPS_PPS', 'TIM2_CH1'),
    # I2C
    'PB8': ('I2C1_SCL', 'I2C1_SCL'), 'PB9': ('I2C1_SDA', 'I2C1_SDA'),
    'PF1': ('I2C2_SCL', 'I2C2_SCL'), 'PF0': ('I2C2_SDA', 'I2C2_SDA'),
    # PWM (TIM1) e retorno do isolador
    'PE9': ('PWM1', 'TIM1_CH1'), 'PE11': ('PWM2', 'TIM1_CH2'), 'PE13': ('PWM3', 'TIM1_CH3'), 'PE14': ('PWM_FB', None),
    # Consola de depuração (USART3, a mesma da Nucleo)
    'PD8': ('/DBG_TX', 'USART3_TX'), 'PD9': ('/DBG_RX', 'USART3_RX'),
    # SWD
    'PA13': ('/SWDIO', 'DEBUG_JTMS-SWDIO'), 'PA14': ('/SWCLK', 'DEBUG_JTCK-SWCLK'), 'PB3': ('/SWO', 'DEBUG_JTDO-SWO'),
    # Estado das fontes e LED
    'PG0': ('PG_5V', None), 'PG1': ('PG_3V3', None), 'PB0': ('/LED1', None), 'PE1': ('/LED2', None),
    # Relógios
    'PH0': ('/OSC_IN', 'RCC_OSC_IN'), 'PH1': ('/OSC_OUT', 'RCC_OSC_OUT'),
    'PC14': ('/OSC32_IN', 'RCC_OSC32_IN'), 'PC15': ('/OSC32_OUT', 'RCC_OSC32_OUT'),
}


def verificar_pinos():
    alt = {}
    for p in pinos(simbolo('MCU_ST_STM32H7:STM32H743ZITx')):
        alt.setdefault(p.name, set()).update(a.pinName for a in (p.alternatePins or []))
    for pino, (rede, func) in PINOS.items():
        if pino not in alt:
            raise ValueError(f'{pino} não existe no STM32H743ZITx')
        if func and func not in alt[pino]:
            raise ValueError(f'{pino} não tem a função {func}')
    redes = [r for r, _ in PINOS.values()]
    if len(redes) != len(set(redes)):
        raise ValueError('rede atribuída a dois pinos')


def folha():
    verificar_pinos()
    f = Folha('Microcontrolador', 'mcu.kicad_sch', notas=[
        'STM32H743ZIT6. Pinos da Ethernet iguais aos da NUCLEO-H753ZI; funções alternativas verificadas pelo gerador.',
        'HSE 25 MHz (PLL dá 80 MHz exatos para o FDCAN a 8 Mbit/s). LSE 32,768 kHz para o RTC.',
    ])
    R, C = 'Device:R', 'Device:C'
    lig = {pino: rede for pino, (rede, _) in PINOS.items()}
    lig.update({'VDD': '+3V3', 'VDD33_USB': '+3V3', 'VBAT': '+3V3', 'PDR_ON': '+3V3',
                'VDDA': '/VDDA', 'VREF+': '/VDDA', 'VSS': 'GND', 'VSSA': 'GND', 'VCAP': '/VCAP',
                'NRST': '/NRST', 'BOOT0': '/BOOT0'})
    f.comp('U3', 'MCU_ST_STM32H7:STM32H743ZITx', 'STM32H743ZIT6', 200, 150, lig, resto_nc=True)

    # Desacoplamento: 100 nF por cada um dos 11 pinos VDD + 4,7 uF
    for i in range(11):
        f.comp(f'C{20 + i}', C, '100 nF', 30 + i * 8, 255, {1: '+3V3', 2: 'GND'}, C0603)
    f.comp('C31', C, '4,7 uF', 125, 255, {1: '+3V3', 2: 'GND'}, C0603)
    # VDDA/VREF+ com filtro de ferrite
    f.comp('FB1', 'Device:FerriteBead', '600 R a 100 MHz', 40, 40, {1: '+3V3', 2: '/VDDA'}, 'Inductor_SMD:L_0603_1608Metric')
    f.comp('C32', C, '1 uF', 55, 50, {1: '/VDDA', 2: 'GND'}, C0603)
    f.comp('C33', C, '100 nF', 65, 50, {1: '/VDDA', 2: 'GND'}, C0603)
    # VCAP (regulador interno do núcleo)
    f.comp('C34', C, '2,2 uF', 80, 50, {1: '/VCAP', 2: 'GND'}, C0603)
    f.comp('C35', C, '2,2 uF', 90, 50, {1: '/VCAP', 2: 'GND'}, C0603)
    # Reset e arranque
    f.comp('C36', C, '100 nF', 40, 80, {1: '/NRST', 2: 'GND'}, C0603)
    f.comp('R20', R, '10k', 55, 80, {1: '/BOOT0', 2: 'GND'}, R0603)
    # HSE 25 MHz e LSE 32,768 kHz
    f.comp('Y1', 'Device:Crystal_GND24', '25 MHz', 40, 115, {1: '/OSC_IN', 3: '/OSC_OUT', 2: 'GND', 4: 'GND'},
           'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm')
    f.comp('C37', C, '12 pF', 30, 135, {1: '/OSC_IN', 2: 'GND'}, C0603)
    f.comp('C38', C, '12 pF', 50, 135, {1: '/OSC_OUT', 2: 'GND'}, C0603)
    f.comp('Y2', 'Device:Crystal', '32,768 kHz', 40, 165, {1: '/OSC32_IN', 2: '/OSC32_OUT'},
           'Crystal:Crystal_SMD_3215-2Pin_3.2x1.5mm')
    f.comp('C39', C, '6,8 pF', 30, 180, {1: '/OSC32_IN', 2: 'GND'}, C0603)
    f.comp('C40', C, '6,8 pF', 50, 180, {1: '/OSC32_OUT', 2: 'GND'}, C0603)
    # SWD (conector ARM 10 pinos, 1,27 mm) e consola
    f.comp('J2', 'Connector:Conn_ARM_JTAG_SWD_10', 'SWD', 340, 60, {
        'VTref': '+3V3', 'SWDIO/TMS': '/SWDIO', 'SWCLK/TCK': '/SWCLK', 'SWO/TDO': '/SWO', '~{RESET}': '/NRST',
        3: 'GND', 5: 'GND', 'GNDDetect': 'GND'}, 'Connector_PinHeader_1.27mm:PinHeader_2x05_P1.27mm_Vertical_SMD',
        nc=('KEY', 'NC/TDI'))
    f.comp('J3', 'Connector_Generic:Conn_01x03', 'Consola (TX, RX, GND)', 340, 120,
           {1: '/DBG_TX', 2: '/DBG_RX', 3: 'GND'}, 'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical')
    # LED de estado
    for i, (led, r) in enumerate((('D3', 'R21'), ('D4', 'R22'))):
        f.comp(r, R, '1k', 330 + i * 20, 170, {1: f'/LED{i + 1}', 2: f'/LED{i + 1}_A'}, R0603)
        f.comp(led, 'Device:LED', 'Verde' if i == 0 else 'Amarelo', 330 + i * 20, 195,
               {'A': f'/LED{i + 1}_A', 'K': 'GND'}, 'LED_SMD:LED_0603_1608Metric')
    # PWR_FLAG: redes alimentadas por componentes passivos ou pelo regulador interno
    f.flag('/VDDA', 110, 40)
    f.flag('/VCAP', 120, 40)
    return f
