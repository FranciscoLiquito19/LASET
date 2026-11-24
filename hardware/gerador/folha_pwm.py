"""Folha 7: três saídas PWM isoladas (ADuM6401), RF15 e DP12.

ADuM6401 (Analog Devices): três canais no sentido MCU -> carga e um de retorno.
  VDD1 e VDDL ligados à mesma fonte (5 V), como exige a folha de características.
  VSEL a VISO -> VISO = 5 V. 10 uF + 100 nF em cada lado (10 a 33 uF recomendados).
  Sem alimentação do lado primário, as saídas isoladas ficam no nível baixo.
Como o ADuM6401 está a 5 V e o MCU a 3,3 V, cada PWM passa por um 74AHCT1G125
alimentado a 5 V (entradas TTL, V_IH = 2 V), que entrega 5 V ao isolador.
O canal de retorno (falha) sai a 5 V e chega a PE15 (TIM1_BKIN) por um divisor 10k/20k.
"""
from hw import Folha
from comum import R, C, R0603, C0603, C1206, SOT23_5, jst_ph, desacoplamento


def folha():
    f = Folha('PWM isolado', 'pwm.kicad_sch', notas=[
        'Três PWM isolados a 5 kV (RF15). Saídas a nível baixo até existir configuração válida (firmware) e sem alimentação primária (isolador).',
        'VISO no conector serve só para lógica/opto da carga: o ADuM6401 dá ~400 mW a 5 V, partilhados com o lado isolado.',
    ])
    for k in range(3):
        y = 50 + 30 * k
        f.comp(f'U{11 + k}', '74xGxx:74AHCT1G125', '74AHCT1G125', 80, y, {
            1: 'GND', 2: f'PWM{k + 1}', 3: 'GND', 4: f'/PWM{k + 1}_5V', 5: '+5V'}, SOT23_5)
        f.comp(f'C{100 + k}', C, '100 nF', 40, y, {1: '+5V', 2: 'GND'}, C0603)

    gi, viso = '/GND_PWM', '/VISO_PWM'
    f.comp('U14', 'laset:ADuM6401', 'ADuM6401ARWZ', 190, 120, {
        'VDD1': '+5V', 'VDDL': '+5V', 'GND1': 'GND',
        'VIA': '/PWM1_5V', 'VIB': '/PWM2_5V', 'VIC': '/PWM3_5V', 'VOD': '/FALHA_5V',
        'VISO': viso, 'VSEL': viso, 'GNDISO': gi,
        'VOA': '/PWM1_ISO', 'VOB': '/PWM2_ISO', 'VOC': '/PWM3_ISO', 'VID': '/FALHA_ISO'})
    desacoplamento(f, ['C103', 'C104'], ['10 uF', '100 nF'], '+5V', 'GND', 130, 170)
    desacoplamento(f, ['C105', 'C106'], ['10 uF', '100 nF'], viso, gi, 240, 170)

    # Retorno de falha: 5 V -> 3,3 V para o MCU
    f.comp('R85', R, '10k', 120, 210, {1: '/FALHA_5V', 2: 'PWM_FALHA'}, R0603)
    f.comp('R86', R, '20k', 135, 210, {1: 'PWM_FALHA', 2: 'GND'}, R0603)

    # Lado isolado
    for k in range(3):
        f.comp(f'R{87 + k}', R, '47', 270, 95 + 16 * k, {1: f'/PWM{k + 1}_ISO', 2: f'/PWM{k + 1}_OUT'}, R0603)
    f.comp('R90', R, '10k', 270, 150, {1: viso, 2: '/FALHA_ISO'}, R0603)
    f.comp('D10', 'Power_Protection:ESDA6V1-5SC6', 'ESDA6V1-5SC6', 300, 165, {
        'IO1': '/PWM1_OUT', 'GND': gi, 'IO2': '/PWM2_OUT', 'IO3': '/PWM3_OUT', 'IO4': '/FALHA_ISO'}, nc=('IO5',))
    for k in range(3):
        f.comp(f'TP{5 + k}', 'Connector:TestPoint', f'PWM{k + 1}', 300 + 10 * k, 75, {1: f'/PWM{k + 1}_OUT'}, 'TestPoint:TestPoint_Pad_D1.5mm')
    f.comp('TP8', 'Connector:TestPoint', 'GND_PWM', 330, 75, {1: gi}, 'TestPoint:TestPoint_Pad_D1.5mm')
    f.comp('J11', 'Connector_Generic:Conn_01x06', 'PWM isolado (PWM1-3, FALHA, VISO, GND_ISO)', 335, 120, {
        1: '/PWM1_OUT', 2: '/PWM2_OUT', 3: '/PWM3_OUT', 4: '/FALHA_ISO', 5: viso, 6: gi}, jst_ph(6))
    return f
