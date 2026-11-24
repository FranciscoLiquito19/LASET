"""Folha 6: dois I2C com tradução de nível (TCA9406) e ligação ao recetor GPS.

Sensores suportados: 3,3 V e 5 V (VPU escolhida por jumper, que também alimenta o
sensor pelo conector). Cobre os módulos habituais (Qwiic/STEMMA a 3,3 V, módulos
antigos a 5 V). Sensores só de 1,8 V ligam-se por um módulo com tradutor próprio.

TCA9406 (TI): VCCA = 3,3 V (MCU), VCCB = VPU; aceita VCCA = VCCB, ao contrário do
PCA9306, que pedia o lado do sensor acima do lado do MCU e ficava fora do recomendado
com sensores de 3,3 V. Tem 10 kOhm de pull-up internos em cada pino; as resistências
externas baixam o valor equivalente para os 400 kHz. OE comum aos dois, comandado pelo
MCU (PG0) com 10 kOhm a GND: as saídas ficam em alta impedância até as alimentações
estarem estáveis, como recomenda a TI.

GPS: conector JST-PH de 5 vias para um módulo com UART e PPS (por exemplo NEO-M8N).
O PPS segue por 100 Ohm para PA0 (TIM2_CH1, captura do flanco). Resistências de 33 Ohm
em série nas linhas UART limitam correntes se o módulo for ligado com a placa desligada.
"""
from hw import Folha
from comum import R, C, R0603, C0603, C1206, JP3, jst_ph


def i2c(f, n, y):
    vpu = f'/VPU{n}'
    sda, scl = f'/SDA{n}_EXT', f'/SCL{n}_EXT'
    r = 50 + 10 * n
    f.comp(f'U{8 + n}', 'Interface:TCA9406DC', 'TCA9406DCUR', 170, y, {
        'GND': 'GND', 'VCCA': '+3V3', 'SCL_A': f'I2C{n}_SCL', 'SDA_A': f'I2C{n}_SDA',
        'SDA_B': sda, 'SCL_B': scl, 'VCCB': vpu, 'OE': 'I2C_OE'}, 'Package_SO:VSSOP-8_2.3x2mm_P0.5mm')
    f.comp(f'C{90 + 2 * n}', C, '100 nF', 230, y + 5, {1: vpu, 2: 'GND'}, C0603)
    f.comp(f'R{r + 1}', R, '2,2k', 110, y - 20, {1: '+3V3', 2: f'I2C{n}_SCL'}, R0603)
    f.comp(f'R{r + 2}', R, '2,2k', 120, y - 20, {1: '+3V3', 2: f'I2C{n}_SDA'}, R0603)
    f.comp(f'R{r + 3}', R, '4,7k', 255, y - 20, {1: vpu, 2: scl}, R0603)
    f.comp(f'R{r + 4}', R, '4,7k', 265, y - 20, {1: vpu, 2: sda}, R0603)
    f.comp(f'JP{3 + n}', 'Jumper:Jumper_3_Bridged12', 'VPU: 3,3 V (1-2) ou 5 V (2-3)', 290, y - 15, {
        1: '+3V3', 2: vpu, 3: '+5V'}, JP3)
    f.comp(f'C{91 + 2 * n}', C, '1 uF', 300, y + 10, {1: vpu, 2: 'GND'}, C0603)
    f.comp(f'D{6 + n}', 'Power_Protection:PRTR5V0U2X', 'PRTR5V0U2X', 315, y - 25, {
        'GND': 'GND', 'I/O1': sda, 'I/O2': scl, 'VCC': vpu})
    f.comp(f'J{7 + n}', 'Connector_Generic:Conn_01x04', f'I2C{n} (VPU, SDA, SCL, GND)', 335, y, {
        1: vpu, 2: sda, 3: scl, 4: 'GND'}, jst_ph(4))


def folha():
    f = Folha('I2C e GPS', 'i2c_gps.kicad_sch', notas=[
        'Dois I2C com tradução de nível (TCA9406) para sensores de 3,3 V ou 5 V, escolhidos por jumper.',
        'GPS: UART7 e PPS em TIM2_CH1 (RF16, DP14).',
    ])
    i2c(f, 1, 70)
    i2c(f, 2, 150)

    f.comp('J10', 'Connector_Generic:Conn_01x05', 'GPS (3V3, GND, TX, RX, PPS)', 335, 215, {
        1: '+3V3', 2: 'GND', 3: '/GPS_TXD', 4: '/GPS_RXD', 5: '/GPS_PPS_IN'}, jst_ph(5))
    f.comp('R80', R, '33', 200, 215, {1: '/GPS_TXD', 2: 'GPS_RX'}, R0603)
    f.comp('R81', R, '33', 225, 215, {1: 'GPS_TX', 2: '/GPS_RXD'}, R0603)
    f.comp('R82', R, '100', 250, 215, {1: '/GPS_PPS_IN', 2: 'GPS_PPS'}, R0603)
    f.comp('D9', 'Power_Protection:ESDA6V1-5SC6', 'ESDA6V1-5SC6', 200, 245, {
        'IO1': '/GPS_TXD', 'GND': 'GND', 'IO2': '/GPS_RXD', 'IO3': '/GPS_PPS_IN'}, nc=('IO4', 'IO5'))
    f.comp('TP9', 'Connector:TestPoint', 'PPS', 250, 245, {1: 'GPS_PPS'}, 'TestPoint:TestPoint_Pad_D1.5mm')
    f.comp('C96', C, '10 uF', 290, 230, {1: '+3V3', 2: 'GND'}, C1206)
    # OE dos tradutores: a GND até o firmware os ligar
    f.comp('R60', R, '10k', 120, 250, {1: 'I2C_OE', 2: 'GND'}, R0603)
    return f
