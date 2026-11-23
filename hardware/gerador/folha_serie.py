"""Folha 5: RS485 isolado (ADM2582E) e RS232 (MAX3227E).

RS485, ADM2582E (Analog Devices):
  VCC a 3,3 V (aceita 3,0 a 5,5 V). Meio-duplex: A liga a Y e B liga a Z.
  DE ao USART6_DE do MCU (o periférico controla o emissor); ~RE a GND, o recetor fica
  sempre ativo e a unidade lê o próprio eco, o que permite detetar colisões.
  VISOOUT liga diretamente a VISOIN (obrigatório). GND2 dos pinos 11 e 14 liga aos
  restantes GND2 por uma ferrite.
  Terminação de 120 Ohm por jumper; SM712 dimensionado para -7 a 12 V.
RS232, MAX3227E: um emissor e um recetor (TX/RX do USART2). FORCEON e ~FORCEOFF a
3,3 V mantêm o conversor sempre ligado. DE-9 fêmea a fazer de DCE: pino 2 = dados
para o PC, pino 3 = dados do PC, pino 5 = massa (cabo direto para o PC).
"""
from hw import Folha
from comum import R, C, FB, R0603, C0603, C1206, FB0603, SOT23, JP2, BORNE3, desacoplamento


def folha():
    f = Folha('RS485 e RS232', 'serie.kicad_sch', notas=[
        'RS485 isolado (ADM2582E, 16 Mbit/s, até 256 nós) e RS232 (MAX3227E, 1 Mbit/s).',
    ])
    g, gi = '/GND_485', '/GNDISO_485'
    f.comp('U7', 'Interface_UART:ADM2582E', 'ADM2582EBRWZ', 170, 80, {
        'GND1': 'GND', 'VCC': '+3V3', 'RxD': 'RS485_RX', 5: 'GND', 'DE': 'RS485_DE', 'TxD': 'RS485_TX',
        11: gi, 14: gi, 16: g, 20: g, 'Visoout': '/VISO_485', 'Visoin': '/VISO_485',
        'Y': '/RS485_A', 'A': '/RS485_A', 'Z': '/RS485_B', 'B': '/RS485_B'})
    desacoplamento(f, ['C80', 'C81'], ['10 uF', '100 nF'], '+3V3', 'GND', 40, 50)
    desacoplamento(f, ['C82', 'C83'], ['10 uF', '100 nF'], '/VISO_485', gi, 40, 90)
    desacoplamento(f, ['C84', 'C85'], ['100 nF', '10 nF'], '/VISO_485', g, 70, 90)
    f.comp('FB6', FB, '600 Ohm @ 100 MHz', 100, 110, {1: gi, 2: g}, FB0603)
    f.comp('D6', 'Diode:SM712_SOT23', 'SM712', 245, 65, {1: '/RS485_A', 2: '/RS485_B', 3: g}, SOT23)
    f.comp('R45', R, '120 1%', 265, 65, {1: '/RS485_A', 2: '/T485'}, R0603)
    f.comp('JP3', 'Jumper:Jumper_2_Open', 'Terminação 120 Ohm', 285, 80, {1: '/T485', 2: '/RS485_B'}, JP2)
    f.comp('J6', 'Connector:Screw_Terminal_01x03', 'RS485 (A, B, GND isolada)', 330, 80, {
        1: '/RS485_A', 2: '/RS485_B', 3: g}, BORNE3)

    # RS232
    f.comp('U8', 'Interface_UART:MAX3227', 'MAX3227EEAE', 170, 205, {
        'VCC': '+3V3', 'GND': 'GND', 'C1+': '/C1P', 'C1-': '/C1N', 'C2+': '/C2P', 'C2-': '/C2N',
        'V+': '/VP', 'V-': '/VN', 'T1IN': 'RS232_TX', 'R1OUT': 'RS232_RX', 'T1OUT': '/RS232_TXD',
        'R1IN': '/RS232_RXD', 'FORCEON': '+3V3', 16: '+3V3'}, nc=('READY', 10))
    f.comp('C86', C, '100 nF', 40, 190, {1: '/C1P', 2: '/C1N'}, C0603)
    f.comp('C87', C, '100 nF', 52, 190, {1: '/C2P', 2: '/C2N'}, C0603)
    f.comp('C88', C, '100 nF', 64, 190, {1: '/VP', 2: 'GND'}, C0603)
    f.comp('C89', C, '100 nF', 76, 190, {1: '/VN', 2: 'GND'}, C0603)
    f.comp('C90', C, '100 nF', 88, 190, {1: '+3V3', 2: 'GND'}, C0603)
    f.comp('J7', 'Connector:DE9_Receptacle', 'RS232 (DE-9 fêmea, DCE)', 320, 205, {
        2: '/RS232_TXD', 3: '/RS232_RXD', 5: 'GND'}, nc=(1, 4, 6, 7, 8, 9),
        footprint='Connector_Dsub:DSUB-9_Female_Horizontal_P2.77x2.84mm_EdgePinOffset7.70mm_Housed_MountingHolesOffset9.12mm')
    return f
