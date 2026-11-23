"""Folha 6: dois I2C com tradução de nível (PCA9306) e ligação ao recetor GPS.

PCA9306 (TI): VREF1 = 3,3 V do lado do MCU. VREF2 e EN ficam juntos e ligam à tensão
do sensor (VPU) por 200 kOhm, com 100 nF a GND, como no circuito típico da TI.
VPU é escolhida por jumper (3,3 V ou 5 V) e sai no conector para alimentar o sensor.
Resistências de pull-up nos dois lados.

GPS: conector JST-PH de 5 vias para um módulo com UART e PPS (por exemplo NEO-M8N).
O PPS segue por 100 Ohm para PA0 (TIM2_CH1, captura do flanco). Resistências de 33 Ohm
em série nas linhas UART limitam correntes se o módulo for ligado com a placa desligada.
"""
from hw import Folha
from comum import R, C, R0603, C0603, C1206, JP3, jst_ph


def i2c(f, n, y):
    vref2, vpu = f'/VREF2_{n}', f'/VPU{n}'
    sda, scl = f'/SDA{n}_EXT', f'/SCL{n}_EXT'
    r = 50 + 10 * n
    f.comp(f'U{8 + n}', 'Interface:PCA9306D', 'PCA9306DR', 170, y, {
        'GND': 'GND', 'VREF1': '+3V3', 'SCL1': f'I2C{n}_SCL', 'SDA1': f'I2C{n}_SDA',
        'SDA2': sda, 'SCL2': scl, 'VREF2': vref2, 'EN': vref2})
    f.comp(f'R{r}', R, '200k', 230, y - 20, {1: vpu, 2: vref2}, R0603)
    f.comp(f'C{90 + 2 * n}', C, '100 nF', 230, y + 5, {1: vref2, 2: 'GND'}, C0603)
    f.comp(f'R{r + 1}', R, '2,2k', 110, y - 20, {1: '+3V3', 2: f'I2C{n}_SCL'}, R0603)
    f.comp(f'R{r + 2}', R, '2,2k', 120, y - 20, {1: '+3V3', 2: f'I2C{n}_SDA'}, R0603)
    f.comp(f'R{r + 3}', R, '4,7k', 255, y - 20, {1: vpu, 2: scl}, R0603)
    f.comp(f'R{r + 4}', R, '4,7k', 265, y - 20, {1: vpu, 2: sda}, R0603)
    f.comp(f'JP{3 + n}', 'Jumper:Jumper_3_Bridged12', 'VPU: 3,3 V (1-2) ou 5 V (2-3)', 290, y - 15, {
        1: '+3V3', 2: vpu, 3: '+5V'}, JP3)
    f.comp(f'C{91 + 2 * n}', C, '1 uF', 300, y + 10, {1: vpu, 2: 'GND'}, C0603)
    f.comp(f'J{7 + n}', 'Connector_Generic:Conn_01x04', f'I2C{n} (VPU, SDA, SCL, GND)', 335, y, {
        1: vpu, 2: sda, 3: scl, 4: 'GND'}, jst_ph(4))


def folha():
    f = Folha('I2C e GPS', 'i2c_gps.kicad_sch', notas=[
        'Dois I2C com tradução de nível (PCA9306) e alimentação do sensor escolhida por jumper.',
        'GPS: UART7 e PPS em TIM2_CH1 (RF16, DP14).',
    ])
    i2c(f, 1, 70)
    i2c(f, 2, 150)

    f.comp('J10', 'Connector_Generic:Conn_01x05', 'GPS (3V3, GND, TX, RX, PPS)', 335, 215, {
        1: '+3V3', 2: 'GND', 3: '/GPS_TXD', 4: '/GPS_RXD', 5: '/GPS_PPS_IN'}, jst_ph(5))
    f.comp('R80', R, '33', 200, 215, {1: '/GPS_TXD', 2: 'GPS_RX'}, R0603)
    f.comp('R81', R, '33', 225, 215, {1: 'GPS_TX', 2: '/GPS_RXD'}, R0603)
    f.comp('R82', R, '100', 250, 215, {1: '/GPS_PPS_IN', 2: 'GPS_PPS'}, R0603)
    f.comp('C96', C, '10 uF', 290, 230, {1: '+3V3', 2: 'GND'}, C1206)
    return f
