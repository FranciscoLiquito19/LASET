"""Folha 1: alimentação 5 a 60 V -> 5 V (LM5177, buck-boost) -> 3,3 V (TPS62162).

Valores calculados a partir da folha de características do LM5177 (TI SNVSBU4F):
  UVLO (Eq. 1): V_on = 1,25 V x (1 + 41,2k/20,5k) + 41,2k x 5 uA = 3,97 V no pino VIN
        (máx. 1,28 V e 6 uA: 4,10 V); com a queda do D2 (até ~0,7 V) arranca com 4,8 V à
        entrada. Desliga a 1,2 V x 3,01 = 3,61 V. A corrente de histerese (5 uA) só corre
        abaixo do limiar, por isso soma-se ao arranque (o valor antigo, 53,6k, dava 4,79 V).
  MOSFET de nível lógico (BSC070N10LS5): o LM5177 tem drivers lógicos alimentados por VCC
        = 5 V e o patamar de Miller tem de ficar abaixo da tensão mínima de entrada.
  BIAS a GND: com saída de 5 V não se atinge o limiar de 6,5 V de comutação para BIAS.
  FB:   V_out = 1,0 V x (1 + 40,2k/10k) = 5,02 V
  R_CS = 10 mOhm -> limite de corrente de pico 50 mV/10 mOhm = 5 A (mín. 3,85 A)
  R_SLOPE = L/R_CS x 50e6 = 18 uH / 10 mOhm x 50e6 = 90 kOhm -> 90,9 kOhm
  R_RT = 75 kOhm -> 400 kHz (Eq. 17 e Tabela 8-3; o texto do exemplo diz 78,7k, que é gralha)
  L1 = 18 uH (SRP1245A-180M, Isat 11 A): ondulação ~0,63 A a 60 V -> 5 V, 400 kHz

Compensação (equações 3 a 10 e 45 a 47 da folha de características), para
I_O,max = 2 A, C_O efetiva ~140 uF, V_IN,min = 4,5 V (D_max = 0,19 com 90 % de rendimento):
  f_RHPZ = V_O (1-D)^2 / (2 pi I_O L) = 14,5 kHz -> f_BW = 4 kHz (< f_RHPZ/3)
  R_COMP = 2 pi f_BW / gm x (V_O/V_FB) x A_CS R_CS C_O / (1-D) x 1/(1+(f_BW/f_RHPZ)^2)
         = 2,0 kOhm. A folha de características dá gm = 600 uS mas não dá A_CS; a razão
           A_CS/gm foi calibrada pelo exemplo da TI (R_COMP = 1,9 kOhm), por isso o resultado não
           depende de se conhecer A_CS em separado.
  f_pole = 2 I_O / (2 pi V_O C_O) = 0,91 kHz; f_CZ = 1,5 f_pole = 1,36 kHz -> C_COMP = 56 nF
  C_HF = 1 / (2 pi 10 f_BW R_COMP) = 2,0 nF -> 2,2 nF
  Confirmar a margem de fase no protótipo (ou no WEBENCH) antes de fechar.
"""
from hw import Folha

R0603 = 'Resistor_SMD:R_0603_1608Metric'
C0603 = 'Capacitor_SMD:C_0603_1608Metric'
C1206 = 'Capacitor_SMD:C_1206_3216Metric'
C1210 = 'Capacitor_SMD:C_1210_3225Metric'
MOSFET = 'Transistor_FET:BSC160N10NS3G'  # símbolo e pinos do TDSON-8 (SuperSO8); peça: BSC070N10LS5, nível lógico


def folha():
    f = Folha('Alimentação', 'alimentacao.kicad_sch', notas=[
        'Entrada 5 a 60 V (RNF08). LM5177 buck-boost gera 5 V mesmo com 5 V à entrada; TPS62162 gera 3,3 V.',
        'D1 (SMCJ60CA) limita até 96,8 V à corrente de pico, acima dos 85 V máximos do LM5177: protege contra ESD e transitórios curtos, não contra surtos normalizados (ver README).',
        'Compensação calculada para f_BW = 4 kHz (ver gerador/folha_alimentacao.py); confirmar a margem de fase no protótipo.',
        'Footprint do LM5177 (HTSSOP-38 com pad 2,9 x 4,7 mm) criado em lib/laset.pretty: confirmar com o desenho DCP0038 da TI.',
    ])
    R, C = 'Device:R', 'Device:C'

    # Entrada e proteção
    f.comp('J1', 'Connector:Screw_Terminal_01x02', 'Entrada 5-60 V', 25, 60, {1: '/VIN_RAW', 2: 'GND'},
           'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-2_1x02_P5.00mm_Horizontal')
    f.comp('F1', 'Device:Fuse', '3 A 125 V DC (0451003.MRL)', 45, 60, {1: '/VIN_RAW', 2: '/VIN_F'},
           'Fuse:Fuse_Littelfuse-NANO2-451_453')
    f.comp('D1', 'Device:D_TVS', 'SMCJ60CA (V_BR 66,7 V)', 60, 75, {1: '/VIN_F', 2: 'GND'}, 'Diode_SMD:D_SMC')
    f.comp('D2', 'Device:D_Schottky', 'MB510 (100 V, 5 A, SMC)', 75, 60, {2: '/VIN_F', 1: 'VIN'}, 'Diode_SMD:D_SMC')
    f.comp('C1', C, '4,7 uF 100 V', 95, 75, {1: 'VIN', 2: 'GND'}, C1210)
    f.comp('C2', C, '4,7 uF 100 V', 105, 75, {1: 'VIN', 2: 'GND'}, C1210)
    f.comp('C3', 'Device:C_Polarized', '47 uF 100 V', 115, 75, {1: 'VIN', 2: 'GND'}, 'Capacitor_SMD:CP_Elec_8x10')
    f.flag('VIN', 95, 50)
    f.flag('GND', 105, 50)

    # UVLO
    f.comp('R1', R, '41,2k', 30, 100, {1: 'VIN', 2: '/EN'}, R0603)
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
    f.comp('R4', R, '90,9k (SLOPE)', 120, 110, {1: '/SLOPE', 2: 'GND'}, R0603)
    f.comp('R5', R, '75k (400 kHz)', 130, 110, {1: '/RT', 2: 'GND'}, R0603)
    f.comp('C4', C, '18 nF (SS)', 110, 140, {1: '/SS', 2: 'GND'}, C0603)
    f.comp('R6', R, '2,0k', 120, 140, {1: '/COMP', 2: '/CZ'}, R0603)
    f.comp('C5', C, '56 nF', 120, 160, {1: '/CZ', 2: 'GND'}, C0603)
    f.comp('C6', C, '2,2 nF', 130, 140, {1: '/COMP', 2: 'GND'}, C0603)
    f.comp('R7', R, '40,2k', 110, 180, {1: '+5V', 2: '/FB'}, R0603)
    f.comp('R8', R, '10k', 110, 200, {1: '/FB', 2: 'GND'}, R0603)
    f.comp('C7', C, '22 uF 10 V X7R (VCC)', 130, 185, {1: '/VCC', 2: 'GND'}, C1206)
    f.comp('C107', C, '100 nF 100 V (VIN do LM5177)', 190, 250, {1: 'VIN', 2: 'GND'}, C0603)
    f.comp('R9', R, '10k', 140, 205, {1: '+3V3', 2: 'PG_5V'}, R0603)

    # Andar de potência
    f.comp('C8', C, '100 nF 25 V', 225, 85, {1: '/HB1', 2: '/SW1'}, C0603)
    f.comp('Q1', MOSFET, 'BSC070N10LS5 (buck alto)', 250, 85, {'D': 'VIN', 'G': '/HO1', 'S': '/SW1'})
    f.comp('Q2', MOSFET, 'BSC070N10LS5 (buck baixo)', 250, 115, {'D': '/SW1', 'G': '/LO1', 'S': 'GND'})
    f.comp('R10', R, '10 mOhm 1 W (R_CS)', 275, 100, {1: '/SW1', 2: '/LA'}, 'Resistor_SMD:R_2512_6332Metric')
    f.comp('R11', R, '10', 275, 130, {1: '/SW1', 2: '/CSA'}, R0603)
    f.comp('R12', R, '10', 285, 130, {1: '/LA', 2: '/CSB'}, R0603)
    f.comp('C9', C, '180 pF', 280, 150, {1: '/CSA', 2: '/CSB'}, C0603)
    f.comp('L1', 'Device:L', 'SRP1245A-180M (18 uH, Isat 11 A)', 305, 100, {1: '/LA', 2: '/SW2'}, 'Inductor_SMD:L_Bourns_SRP1245A')
    f.comp('C108', C, '100 nF 100 V (alta freq.)', 205, 250, {1: 'VIN', 2: 'GND'}, C0603)
    f.comp('C10', C, '100 nF 25 V', 320, 70, {1: '/HB2', 2: '/SW2'}, C0603)
    f.comp('Q3', MOSFET, 'BSC070N10LS5 (boost alto)', 335, 85, {'D': '/5V_PRE', 'G': '/HO2', 'S': '/SW2'})
    f.comp('Q4', MOSFET, 'BSC070N10LS5 (boost baixo)', 335, 115, {'D': '/SW2', 'G': '/LO2', 'S': 'GND'})
    f.comp('R13', R, '10 mOhm (R_ISNS)', 360, 85, {1: '/5V_PRE', 2: '+5V'}, 'Resistor_SMD:R_2512_6332Metric')
    for i, x in enumerate((345, 355, 365)):
        f.comp(f'C{11 + i}', C, '22 uF 10 V', x, 130, {1: '/5V_PRE' if i == 0 else '+5V', 2: 'GND'}, C1206)
    for i, x in enumerate((220, 235)):
        f.comp(f'C{109 + i}', C, '22 uF 10 V', x, 250, {1: '/5V_PRE', 2: 'GND'}, C1206)
    f.comp('C14', 'Device:C_Polarized', '100 uF 10 V polímero', 380, 130, {1: '+5V', 2: 'GND'}, 'Capacitor_SMD:CP_Elec_6.3x7.7')
    f.flag('+5V', 380, 70)

    # 3,3 V
    f.comp('U2', 'Regulator_Switching:TPS62162DSG', 'TPS62162', 300, 220, {
        'VIN': '+5V', 'EN': '+5V', 'PG': 'PG_3V3', 'AGND': 'GND', 'PGND': 'GND', 'PAD': 'GND',
        'SW': '/SW3', 'VOS': '+3V3', 'FB': 'GND'})
    f.comp('C15', C, '10 uF 10 V', 270, 240, {1: '+5V', 2: 'GND'}, C0603)
    f.comp('L2', 'Device:L', '2,2 uH', 335, 210, {1: '/SW3', 2: '+3V3'}, 'Inductor_SMD:L_Bourns_SRN6045TA')
    f.comp('C16', C, '22 uF 10 V', 350, 240, {1: '+3V3', 2: 'GND'}, C1206)
    f.comp('R14', R, '10k', 265, 205, {1: '+3V3', 2: 'PG_3V3'}, R0603)
    f.flag('+3V3', 360, 200)

    # Pontos de teste e furos de fixação
    for i, (rede, x) in enumerate([('VIN', 30), ('+5V', 45), ('+3V3', 60), ('GND', 75)]):
        f.comp(f'TP{i + 1}', 'Connector:TestPoint', rede, x, 255, {1: rede}, 'TestPoint:TestPoint_Pad_D1.5mm')
    for i in range(4):
        f.comp(f'H{i + 1}', 'Mechanical:MountingHole', 'M3', 110 + 15 * i, 260, {}, 'MountingHole:MountingHole_3.2mm_M3')
    return f
