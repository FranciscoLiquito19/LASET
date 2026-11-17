"""Folha 1: alimentação 5 a 60 V -> 5 V (LM5177, buck-boost) -> 3,3 V (TPS62162).

Valores calculados a partir da folha de características do LM5177 (TI SNVSBU4F):
  UVLO: V_on = 1,25 V x (1 + 53,6k/20,5k) = 4,52 V
  FB:   V_out = 1,0 V x (1 + 40,2k/10k) = 5,02 V
  R_CS = 10 mOhm -> limite de corrente de pico 50 mV/10 mOhm = 5 A (mín. 3,85 A)
  R_SLOPE = L/R_CS x 50e6 = 15 uH / 10 mOhm x 50e6 = 75 kOhm
  R_RT = 78,7 kOhm -> 400 kHz (exemplo da folha de características)
  L1 = 15 uH: ondulação ~0,76 A a 60 V -> 5 V, 400 kHz
"""
from hw import Folha

R0603 = 'Resistor_SMD:R_0603_1608Metric'
C0603 = 'Capacitor_SMD:C_0603_1608Metric'
C1206 = 'Capacitor_SMD:C_1206_3216Metric'
C1210 = 'Capacitor_SMD:C_1210_3225Metric'
MOSFET = 'Package_TO_SOT_SMD:TDSON-8-1'


def folha():
    f = Folha('Alimentação', 'alimentacao.kicad_sch', notas=[
        'Entrada 5 a 60 V (RNF08). LM5177 buck-boost gera 5 V mesmo com 5 V à entrada; TPS62162 gera 3,3 V.',
        'A VERIFICAR antes do fabrico: rede de compensação (COMP), MOSFET e bobina com o WEBENCH da TI; footprint HTSSOP-38 com pad exposto.',
    ])
    R, C = 'Device:R', 'Device:C'

    # Entrada e proteção
    f.comp('J1', 'Connector:Screw_Terminal_01x02', 'Entrada 5-60 V', 25, 60, {1: '/VIN_RAW', 2: 'GND'},
           'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal')
    f.comp('F1', 'Device:Polyfuse', '3 A', 45, 60, {1: '/VIN_RAW', 2: '/VIN_F'}, 'Fuse:Fuse_1812_4532Metric')
    f.comp('D1', 'Device:D_TVS', 'SMCJ64CA', 60, 75, {1: '/VIN_F', 2: 'GND'}, 'Diode_SMD:D_SMC')
    f.comp('D2', 'Device:D_Schottky', 'STPS5H100 (100 V, 5 A)', 75, 60, {2: '/VIN_F', 1: 'VIN'}, 'Diode_SMD:D_SMC')
    f.comp('C1', C, '4,7 uF 100 V', 95, 75, {1: 'VIN', 2: 'GND'}, C1210)
    f.comp('C2', C, '4,7 uF 100 V', 105, 75, {1: 'VIN', 2: 'GND'}, C1210)
    f.comp('C3', 'Device:C_Polarized', '47 uF 100 V', 115, 75, {1: 'VIN', 2: 'GND'}, 'Capacitor_SMD:CP_Elec_8x10')
    f.flag('VIN', 95, 50)
    f.flag('GND', 105, 50)

    # UVLO
    f.comp('R1', R, '53,6k', 30, 100, {1: 'VIN', 2: '/EN'}, R0603)
    f.comp('R2', R, '20,5k', 30, 120, {1: '/EN', 2: 'GND'}, R0603)

    # Controlador
    f.comp('U1', 'laset:LM5177', 'LM5177', 170, 140, {
        'VIN': 'VIN', 'BIAS': 'GND', 'EN/UVLO': '/EN', 'DTRK': 'GND', 'SYNC': '/VCC', 'MODE': '/VCC',
        'CFG': '/CFG', 'SLOPE': '/SLOPE', 'RT': '/RT', 'SS/ATRK': '/SS', 'COMP': '/COMP', 'FB': '/FB',
        'IMONOUT': '/VCC', 'nFLT': 'PG_5V', 'VCC': '/VCC', 'HB1': '/HB1', 'HO1': '/HO1', 'SW1': '/SW1',
        'LO1': '/LO1', 'CSA': '/CSA', 'CSB': '/CSB', 'HB2': '/HB2', 'HO2': '/HO2', 'SW2': '/SW2',
        'LO2': '/LO2', 'VOUT': '+5V', 'ISNSP': '/5V_PRE', 'ISNSN': '+5V', 'AGND': 'GND', 'PGND': 'GND',
        'EP': 'GND'}, nc=('HO1_LL', 'HO2_LL'))
    f.comp('R3', R, '13,3k (CFG)', 110, 110, {1: '/CFG', 2: 'GND'}, R0603)
    f.comp('R4', R, '75k (SLOPE)', 120, 110, {1: '/SLOPE', 2: 'GND'}, R0603)
    f.comp('R5', R, '78,7k (400 kHz)', 130, 110, {1: '/RT', 2: 'GND'}, R0603)
    f.comp('C4', C, '18 nF (SS)', 110, 140, {1: '/SS', 2: 'GND'}, C0603)
    f.comp('R6', R, '1,91k (verificar)', 120, 140, {1: '/COMP', 2: '/CZ'}, R0603)
    f.comp('C5', C, '47 nF (verificar)', 120, 160, {1: '/CZ', 2: 'GND'}, C0603)
    f.comp('C6', C, '1,8 nF (verificar)', 130, 140, {1: '/COMP', 2: 'GND'}, C0603)
    f.comp('R7', R, '40,2k', 110, 180, {1: '+5V', 2: '/FB'}, R0603)
    f.comp('R8', R, '10k', 110, 200, {1: '/FB', 2: 'GND'}, R0603)
    f.comp('C7', C, '4,7 uF 10 V (VCC)', 130, 185, {1: '/VCC', 2: 'GND'}, C0603)
    f.comp('R9', R, '10k', 140, 205, {1: '+3V3', 2: 'PG_5V'}, R0603)

    # Andar de potência
    f.comp('C8', C, '100 nF 25 V', 225, 85, {1: '/HB1', 2: '/SW1'}, C0603)
    f.comp('Q1', 'Transistor_FET:BSC070N10NS5', 'BSC070N10NS5 (buck alto)', 250, 85, {'D': 'VIN', 'G': '/HO1', 'S': '/SW1'}, MOSFET)
    f.comp('Q2', 'Transistor_FET:BSC070N10NS5', 'BSC070N10NS5 (buck baixo)', 250, 115, {'D': '/SW1', 'G': '/LO1', 'S': 'GND'}, MOSFET)
    f.comp('R10', R, '10 mOhm 1 W (R_CS)', 275, 100, {1: '/SW1', 2: '/LA'}, 'Resistor_SMD:R_2512_6332Metric')
    f.comp('R11', R, '10', 275, 130, {1: '/SW1', 2: '/CSA'}, R0603)
    f.comp('R12', R, '10', 285, 130, {1: '/LA', 2: '/CSB'}, R0603)
    f.comp('C9', C, '180 pF', 280, 150, {1: '/CSA', 2: '/CSB'}, C0603)
    f.comp('L1', 'Device:L', '15 uH, Isat >= 6 A', 305, 100, {1: '/LA', 2: '/SW2'}, 'Inductor_SMD:L_12x12mm_H8mm')
    f.comp('C10', C, '100 nF 25 V', 320, 70, {1: '/HB2', 2: '/SW2'}, C0603)
    f.comp('Q3', 'Transistor_FET:BSC070N10NS5', 'BSC070N10NS5 (boost alto)', 335, 85, {'D': '/5V_PRE', 'G': '/HO2', 'S': '/SW2'}, MOSFET)
    f.comp('Q4', 'Transistor_FET:BSC070N10NS5', 'BSC070N10NS5 (boost baixo)', 335, 115, {'D': '/SW2', 'G': '/LO2', 'S': 'GND'}, MOSFET)
    f.comp('R13', R, '10 mOhm (R_ISNS)', 360, 85, {1: '/5V_PRE', 2: '+5V'}, 'Resistor_SMD:R_2512_6332Metric')
    for i, x in enumerate((345, 355, 365)):
        f.comp(f'C{11 + i}', C, '22 uF 10 V', x, 130, {1: '/5V_PRE' if i == 0 else '+5V', 2: 'GND'}, C1206)
    f.comp('C14', 'Device:C_Polarized', '100 uF 10 V polímero', 380, 130, {1: '+5V', 2: 'GND'}, 'Capacitor_SMD:CP_Elec_6.3x7.7')
    f.flag('+5V', 380, 70)

    # 3,3 V
    f.comp('U2', 'Regulator_Switching:TPS62162DSG', 'TPS62162', 300, 220, {
        'VIN': '+5V', 'EN': '+5V', 'PG': 'PG_3V3', 'AGND': 'GND', 'PGND': 'GND', 'PAD': 'GND',
        'SW': '/SW3', 'VOS': '+3V3', 'FB': 'GND'}, 'Package_SON:Texas_DSG0008A_WSON-8-1EP_2x2mm_P0.5mm_EP0.9x1.6mm_ThermalVias')
    f.comp('C15', C, '10 uF 10 V', 270, 240, {1: '+5V', 2: 'GND'}, C0603)
    f.comp('L2', 'Device:L', '2,2 uH', 335, 210, {1: '/SW3', 2: '+3V3'}, 'Inductor_SMD:L_Bourns_SRN6045TA')
    f.comp('C16', C, '22 uF 10 V', 350, 240, {1: '+3V3', 2: 'GND'}, C1206)
    f.comp('R14', R, '10k', 265, 205, {1: '+3V3', 2: 'PG_3V3'}, R0603)
    f.flag('+3V3', 360, 200)
    return f
