"""Footprints e atalhos partilhados pelas folhas."""

R0603 = 'Resistor_SMD:R_0603_1608Metric'
C0603 = 'Capacitor_SMD:C_0603_1608Metric'
C0805 = 'Capacitor_SMD:C_0805_2012Metric'
C1206 = 'Capacitor_SMD:C_1206_3216Metric'
FB0603 = 'Inductor_SMD:L_0603_1608Metric'
LED0603 = 'LED_SMD:LED_0603_1608Metric'
XTAL3225 = 'Crystal:Crystal_SMD_3225-4Pin_3.2x2.5mm'
SOT23 = 'Package_TO_SOT_SMD:SOT-23'
SOT23_5 = 'Package_TO_SOT_SMD:SOT-23-5'
JP2 = 'Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical'
JP3 = 'Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical'
BORNE3 = 'TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-3_1x03_P5.00mm_Horizontal'


def jst_ph(n):
    return f'Connector_JST:JST_PH_B{n}B-PH-K_1x{n:02d}_P2.00mm_Vertical'


R, C, CP, FB = 'Device:R', 'Device:C', 'Device:C_Polarized', 'Device:FerriteBead'


def desacoplamento(f, refs, valores, rede, gnd, x, y, passo=10, fp=C0603):
    """Fila de condensadores de desacoplamento entre rede e gnd."""
    for i, (ref, v) in enumerate(zip(refs, valores)):
        f.comp(ref, C, v, x + i * passo, y, {1: rede, 2: gnd}, C1206 if 'uF' in v and float(v.split()[0].replace(',', '.')) >= 10 else fp)
