"""Folhas 3 a 7: Ethernet, CAN FD, RS485/RS232, I2C/GPS e PWM."""
from hw import Folha

R0603 = 'Resistor_SMD:R_0603_1608Metric'
C0603 = 'Capacitor_SMD:C_0603_1608Metric'
C0805 = 'Capacitor_SMD:C_0805_2012Metric'
R, C = 'Device:R', 'Device:C'
BORNE3 = 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-3_1x03_P5.00mm_Horizontal'
BORNE5 = 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-5_1x05_P5.00mm_Horizontal'
JMP2 = 'Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm'
JMP3 = 'Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm'


def ethernet():
    f = Folha('Ethernet', 'ethernet.kicad_sch', notas=[
        'LAN8742A em modo RMII com cristal de 25 MHz; o pino 14 fornece o REF_CLK de 50 MHz ao MCU (nINTSEL a 0).',
        'Configuração igual à da NUCLEO-H753ZI. Endereço PHY 0 e auto-negociação (strappings internos por omissão).',
    ])
    f.comp('U4', 'Interface_Ethernet:LAN8742A', 'LAN8742A', 150, 140, {
        'VDD1A': '+3V3', 'VDD2A': '+3V3', 'VDDIO': '+3V3', 'VDDCR': '/VDDCR', 'VSS': 'GND',
        'XTAL1/CLKIN': '/XI', 'XTAL2': '/XO', 'RBIAS': '/RBIAS',
        '~{INT}/REFCLKO': 'ETH_REF_CLK', 'LED2/~{INTSEL}': '/INTSEL', 'MDIO': 'ETH_MDIO', 'MDC': 'ETH_MDC',
        'CRS_DV/MODE2': 'ETH_CRS_DV', 'RXD0/MODE0': 'ETH_RXD0', 'RXD1/MODE1': 'ETH_RXD1',
        'TXEN': 'ETH_TX_EN', 'TXD0': 'ETH_TXD0', 'TXD1': 'ETH_TXD1', '~{RST}': 'ETH_NRST',
        'TXP': '/TXP', 'TXN': '/TXN', 'RXP': '/RXP', 'RXN': '/RXN'},
        nc=('RXER/PHYAD0', 'LED1/REGOFF'))
    f.comp('R30', R, '12,1k 1%', 100, 200, {1: '/RBIAS', 2: 'GND'}, R0603)
    f.comp('R31', R, '10k', 110, 200, {1: '/INTSEL', 2: 'GND'}, R0603)
    f.comp('R32', R, '10k', 120, 200, {1: '+3V3', 2: 'ETH_NRST'}, R0603)
    f.comp('R33', R, '1k5', 130, 200, {1: '+3V3', 2: 'ETH_MDIO'}, R0603)
    f.comp('C50', C, '1 uF', 60, 200, {1: '/VDDCR', 2: 'GND'}, C0603)
    f.comp('C51', C, '470 pF', 70, 200, {1: '/VDDCR', 2: 'GND'}, C0603)
    for i in range(3):
        f.comp(f'C{52 + i}', C, '100 nF', 60 + i * 10, 230, {1: '+3V3', 2: 'GND'}, C0603)
    f.comp('C55', C, '4,7 uF', 90, 230, {1: '+3V3', 2: 'GND'}, C0603)
    f.comp('Y3', 'Device:Crystal_GND24', '25 MHz', 60, 120, {1: '/XI', 3: '/XO', 2: 'GND', 4: 'GND'},
           'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm')
    f.comp('C56', C, '15 pF', 50, 140, {1: '/XI', 2: 'GND'}, C0603)
    f.comp('C57', C, '15 pF', 70, 140, {1: '/XO', 2: 'GND'}, C0603)
    # Terminações de 49,9 Ohm para a tomada central, como na nota de aplicação do LAN8742A
    for i, linha in enumerate(('/TXP', '/TXN', '/RXP', '/RXN')):
        f.comp(f'R{34 + i}', R, '49,9 1%', 230 + i * 10, 90, {1: linha, 2: '/CT'}, R0603)
    f.comp('FB2', 'Device:FerriteBead', '600 R a 100 MHz', 230, 60, {1: '+3V3', 2: '/CT'}, 'Inductor_SMD:L_0603_1608Metric')
    f.comp('C58', C, '100 nF', 260, 60, {1: '/CT', 2: 'GND'}, C0603)
    f.comp('C59', C, '100 nF', 270, 60, {1: '/CT', 2: 'GND'}, C0603)
    f.comp('J4', 'Connector:RJ45_Hanrun_HR911105A_Horizontal', 'HR911105A', 330, 140, {
        'TD+': '/TXP', 'TD-': '/TXN', 'RD+': '/RXP', 'RD-': '/RXN', 'TCT': '/CT', 'RCT': '/CT', 8: 'GND', 'SH': 'GND'},
        nc=('9', '10', '11', '12'))
    f.flag('/VDDCR', 40, 190)
    return f


def can():
    f = Folha('CAN FD', 'can.kicad_sch', notas=[
        'Dois ADM3057E isolados (3 kV), com alimentação isolada integrada. CAN1: ligação ao PC; CAN2: nós externos (DP01).',
        'STBY com pull-down: transceiver ativo no arranque. Terminação de 120 Ohm ativada por jumper de solda.',
    ])
    for k, (x, u) in enumerate(((120, 'U5'), (300, 'U6'))):
        n = k + 1
        g = f'/GNDISO{n}'
        f.comp(u, 'Interface_CAN_LIN:ADM3057ExRW', 'ADM3057E', x, 120, {
            'VCC': '+5V', 'VIO': '+3V3', 'GND1': 'GND', 'TXD': f'CAN{n}_TX', 'RXD': f'CAN{n}_RX',
            'STBY': f'CAN{n}_STBY', 'SILENT': 'GND', 'AUXIN': 'GND', 'VISOOUT': f'/VISO{n}', 'VISOIN': f'/VISO{n}',
            'GND2': g, 'GNDISO': g, 'RS': g, 'CANH': f'/CANH{n}', 'CANL': f'/CANL{n}'}, nc=('AUXOUT',))
        b = 40 + k * 20
        f.comp(f'R{40 + k}', R, '10k', x - 60, 170, {1: f'CAN{n}_STBY', 2: 'GND'}, R0603)
        f.comp(f'C{60 + 4 * k}', C, '10 uF', x - 50, 200, {1: '+5V', 2: 'GND'}, C0805)
        f.comp(f'C{61 + 4 * k}', C, '100 nF', x - 40, 200, {1: '+3V3', 2: 'GND'}, C0603)
        f.comp(f'C{62 + 4 * k}', C, '10 uF', x + 40, 200, {1: f'/VISO{n}', 2: g}, C0805)
        f.comp(f'C{63 + 4 * k}', C, '100 nF', x + 50, 200, {1: f'/VISO{n}', 2: g}, C0603)
        f.comp(f'R{42 + k}', R, '120', x + 60, 80, {1: f'/CANH{n}', 2: f'/TERM{n}'}, 'Resistor_SMD:R_1206_3216Metric')
        f.comp(f'JP{1 + k}', 'Jumper:Jumper_2_Open', 'Terminação', x + 60, 50, {'A': f'/TERM{n}', 'B': f'/CANL{n}'}, JMP2)
        f.comp(f'J{5 + k}', 'Connector:Screw_Terminal_01x03', f'CAN{n} (H, L, GND iso)', x + 90, 120,
               {1: f'/CANH{n}', 2: f'/CANL{n}', 3: g}, BORNE3)
    return f


def serie():
    f = Folha('RS485 e RS232', 'serie.kicad_sch', notas=[
        'RS485: ADM2582E isolado, em half-duplex (A-Y e B-Z ligados). DE por hardware no USART1.',
        'RS232: MAX3227E a 1 Mbit/s, sempre ligado (FORCEON e FORCEOFF a 3,3 V).',
    ])
    f.comp('U7', 'Interface_UART:ADM2582E', 'ADM2582E', 110, 120, {
        'VCC': '+3V3', 'GND1': 'GND', 'TxD': 'RS485_TX', 'RxD': 'RS485_RX', 'DE': 'RS485_DE', '~{RE}': 'RS485_NRE',
        'Visoout': '/VISO485', 'Visoin': '/VISO485', 'GND2': '/GNDISO485', 'A': '/A', 'Y': '/A', 'B': '/B', 'Z': '/B'})
    f.comp('R50', R, '10k', 50, 170, {1: 'RS485_DE', 2: 'GND'}, R0603)
    f.comp('R51', R, '10k', 60, 170, {1: '+3V3', 2: 'RS485_NRE'}, R0603)
    f.comp('C70', C, '10 uF', 50, 200, {1: '+3V3', 2: 'GND'}, C0805)
    f.comp('C71', C, '100 nF', 60, 200, {1: '+3V3', 2: 'GND'}, C0603)
    f.comp('C72', C, '10 uF', 160, 200, {1: '/VISO485', 2: '/GNDISO485'}, C0805)
    f.comp('C73', C, '100 nF', 170, 200, {1: '/VISO485', 2: '/GNDISO485'}, C0603)
    f.comp('R52', R, '120', 170, 80, {1: '/A', 2: '/TERM485'}, 'Resistor_SMD:R_1206_3216Metric')
    f.comp('JP3', 'Jumper:Jumper_2_Open', 'Terminação', 170, 50, {'A': '/TERM485', 'B': '/B'}, JMP2)
    f.comp('J7', 'Connector:Screw_Terminal_01x03', 'RS485 (A, B, GND iso)', 200, 120, {1: '/A', 2: '/B', 3: '/GNDISO485'}, BORNE3)
    f.flag('/GNDISO485', 200, 170)

    f.comp('U8', 'Interface_UART:MAX3227', 'MAX3227E', 300, 130, {
        'VCC': '+3V3', 'GND': 'GND', 'T1IN': 'RS232_TX', 'R1OUT': 'RS232_RX', 'T1OUT': '/T1OUT', 'R1IN': '/R1IN',
        'C1+': '/C1P', 'C1-': '/C1N', 'C2+': '/C2P', 'C2-': '/C2N', 'V+': '/VP', 'V-': '/VN',
        'FORCEON': '+3V3', '~{FORCEOFF}': '+3V3'}, nc=('READY', '~{INVALID}'))
    for i, (a, b) in enumerate((('/C1P', '/C1N'), ('/C2P', '/C2N'), ('/VP', 'GND'), ('/VN', 'GND'), ('+3V3', 'GND'))):
        f.comp(f'C{74 + i}', C, '100 nF', 250 + i * 10, 200, {1: a, 2: b}, C0603)
    f.comp('J8', 'Connector:Screw_Terminal_01x03', 'RS232 (TX, RX, GND)', 370, 130,
           {1: '/T1OUT', 2: '/R1IN', 3: 'GND'}, BORNE3)
    return f


def i2c_gps():
    f = Folha('I2C e GPS', 'i2c_gps.kicad_sch', notas=[
        'Dois PCA9306: lado 1 a 3,3 V (MCU), lado 2 a 3,3 V ou 5 V escolhido por jumper de solda (JP4).',
        'GPS: módulo externo (ex.: NEO-M9N) com NMEA por UART7 e PPS na captura do TIM2.',
    ])
    f.comp('JP4', 'Jumper:SolderJumper_3_Bridged12', 'VDPU 3,3 V / 5 V', 40, 60, {'A': '+3V3', 'C': '/VDPU', 'B': '+5V'}, JMP3)
    for k in range(2):
        n = k + 1
        x = 130 + k * 160
        f.comp(f'U{9 + k}', 'Interface:PCA9306DC', 'PCA9306', x, 120, {
            'GND': 'GND', 'VREF1': '+3V3', 'SCL1': f'I2C{n}_SCL', 'SDA1': f'I2C{n}_SDA',
            'VREF2': f'/EN{n}', 'EN': f'/EN{n}', 'SCL2': f'/SCL{n}B', 'SDA2': f'/SDA{n}B'})
        f.comp(f'R{60 + 6 * k}', R, '200k', x + 40, 70, {1: '/VDPU', 2: f'/EN{n}'}, R0603)
        f.comp(f'C{80 + 2 * k}', C, '100 nF', x + 50, 70, {1: f'/EN{n}', 2: 'GND'}, C0603)
        f.comp(f'C{81 + 2 * k}', C, '100 nF', x - 50, 70, {1: '+3V3', 2: 'GND'}, C0603)
        f.comp(f'R{61 + 6 * k}', R, '4k7', x - 40, 170, {1: '+3V3', 2: f'I2C{n}_SCL'}, R0603)
        f.comp(f'R{62 + 6 * k}', R, '4k7', x - 30, 170, {1: '+3V3', 2: f'I2C{n}_SDA'}, R0603)
        f.comp(f'R{63 + 6 * k}', R, '4k7', x + 30, 170, {1: '/VDPU', 2: f'/SCL{n}B'}, R0603)
        f.comp(f'R{64 + 6 * k}', R, '4k7', x + 40, 170, {1: '/VDPU', 2: f'/SDA{n}B'}, R0603)
        f.comp(f'J{9 + k}', 'Connector_Generic:Conn_01x04', f'I2C{n} (VDPU, GND, SCL, SDA)', x + 70, 120,
               {1: '/VDPU', 2: 'GND', 3: f'/SCL{n}B', 4: f'/SDA{n}B'},
               'Connector_JST:JST_PH_B4B-PH-K_1x04_P2.00mm_Vertical')
    f.comp('R72', R, '100', 120, 230, {1: '/PPS_EXT', 2: 'GPS_PPS'}, R0603)
    f.comp('J11', 'Connector_Generic:Conn_01x05', 'GPS (3V3, GND, RX, TX, PPS)', 60, 230,
           {1: '+3V3', 2: 'GND', 3: 'GPS_TX', 4: 'GPS_RX', 5: '/PPS_EXT'},
           'Connector_JST:JST_PH_B5B-PH-K_1x05_P2.00mm_Vertical')
    f.flag('/EN1', 200, 40)
    f.flag('/EN2', 360, 40)
    return f


def pwm():
    f = Folha('PWM isolado', 'pwm.kicad_sch', notas=[
        'ADuM6401: 3 canais PWM isolados (5 kV) e alimentação isolada de 5 V (VSEL a VISO). O canal D devolve o PWM1 do lado isolado ao MCU.',
        'Pino 7 (VDDL) ligado a VDD1, como exige a folha de características do ADuM6401 (Tabela 22).',
        'VISO no conector serve só sinais de referência (máx. 500 mW); os servos têm alimentação própria.',
    ])
    f.comp('U11', 'laset:ADuM6401', 'ADuM6401', 180, 130, {
        'VDD1': '+5V', 'GND1': 'GND', 'VIA': 'PWM1', 'VIB': 'PWM2', 'VIC': 'PWM3', 'VOD': 'PWM_FB',
        'VDDL': '+5V', 'VISO': '/VISO', 'GNDISO': '/GNDISO_PWM', 'VSEL': '/VISO',
        'VOA': '/PWM1_ISO', 'VOB': '/PWM2_ISO', 'VOC': '/PWM3_ISO', 'VID': '/PWM1_ISO'},
        'Package_SO:SOIC-16W_7.5x10.3mm_P1.27mm')
    f.comp('C90', C, '10 uF', 110, 190, {1: '+5V', 2: 'GND'}, C0805)
    f.comp('C91', C, '100 nF', 120, 190, {1: '+5V', 2: 'GND'}, C0603)
    f.comp('C92', C, '10 uF', 240, 190, {1: '/VISO', 2: '/GNDISO_PWM'}, C0805)
    f.comp('C93', C, '100 nF', 250, 190, {1: '/VISO', 2: '/GNDISO_PWM'}, C0603)
    for i in range(3):
        f.comp(f'R{80 + i}', R, '100', 260, 90 + i * 15, {1: f'/PWM{i + 1}_ISO', 2: f'/PWM{i + 1}_OUT'}, R0603)
    f.comp('J12', 'Connector:Screw_Terminal_01x05', 'PWM (GND iso, 1, 2, 3, VISO)', 320, 120,
           {1: '/GNDISO_PWM', 2: '/PWM1_OUT', 3: '/PWM2_OUT', 4: '/PWM3_OUT', 5: '/VISO'}, BORNE5)
    f.flag('/VISO', 230, 60)
    f.flag('/GNDISO_PWM', 240, 230)
    return f
