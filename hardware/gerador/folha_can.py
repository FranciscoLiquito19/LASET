"""Folha 4: dois barramentos CAN FD isolados (ADM3057E), RF04.

Ligações segundo a folha de características do ADM3055E/ADM3057E (Analog Devices):
  VCC = 5 V (isoPower), VIO = 3,3 V (lógica do MCU).
  RS a GND2 -> modo de alta velocidade (necessário para 8 Mbit/s na fase de dados).
  STBY e AUXIN a GND (modo normal, canal auxiliar sem uso); SILENT ao MCU, para
  escutar o barramento sem enviar ACK.
  VISOOUT liga a VISOIN e GNDISO liga a GND2, cada um por uma ferrite.
Terminação dividida (2 x 60,4 Ohm + 4,7 nF) ativada por jumper, para a unidade poder
ficar no meio ou na ponta do barramento. NUP2105L protege CANH/CANL contra transitórios.
"""
from hw import Folha
from comum import R, C, FB, R0603, C0603, C1206, FB0603, SOT23, JP2, BORNE3, desacoplamento


def canal(f, n, y, base):
    g, gi = f'/GND_CAN{n}', f'/GNDISO_CAN{n}'
    h, l = f'/CANH{n}', f'/CANL{n}'
    c = base
    f.comp(f'U{4 + n}', 'Interface_CAN_LIN:ADM3057ExRW', 'ADM3057EBRWZ', 170, y, {
        'GND1': 'GND', 'VCC': '+5V', 'VIO': '+3V3', 'RXD': f'CAN{n}_RX', 'TXD': f'CAN{n}_TX',
        'SILENT': f'CAN{n}_SILENT', 'STBY': 'GND', 'AUXIN': 'GND', 'RS': g,
        'GND2': g, 'GNDISO': gi, 'VISOOUT': f'/VISOOUT{n}', 'VISOIN': f'/VISO_CAN{n}',
        'CANH': h, 'CANL': l}, nc=('AUXOUT',))
    desacoplamento(f, [f'C{c}', f'C{c + 1}'], ['10 uF', '100 nF'], '+5V', 'GND', 40, y - 30)
    desacoplamento(f, [f'C{c + 2}', f'C{c + 3}'], ['100 nF', '10 nF'], '+3V3', 'GND', 70, y - 30)
    desacoplamento(f, [f'C{c + 4}', f'C{c + 5}'], ['10 uF', '220 nF'], f'/VISOOUT{n}', gi, 40, y + 10)
    desacoplamento(f, [f'C{c + 6}', f'C{c + 7}'], ['100 nF', '10 nF'], f'/VISO_CAN{n}', g, 70, y + 10)
    f.comp(f'FB{2 * n}', FB, '600 Ohm @ 100 MHz', 100, y - 10, {1: f'/VISOOUT{n}', 2: f'/VISO_CAN{n}'}, FB0603)
    f.comp(f'FB{2 * n + 1}', FB, '600 Ohm @ 100 MHz', 100, y + 15, {1: gi, 2: g}, FB0603)

    # Proteção e terminação
    f.comp(f'D{3 + n}', 'Power_Protection:NUP2105L', 'NUP2105L', 245, y - 15, {1: h, 2: l, 3: g}, SOT23)
    f.comp(f'R{39 + 2 * n}', R, '60,4 1%', 265, y - 15, {1: h, 2: f'/MID{n}'}, R0603)
    f.comp(f'R{40 + 2 * n}', R, '60,4 1%', 265, y + 5, {1: f'/MID{n}', 2: f'/TL{n}'}, R0603)
    f.comp(f'C{c + 8}', C, '4,7 nF', 280, y - 5, {1: f'/MID{n}', 2: g}, C0603)
    f.comp(f'JP{n}', 'Jumper:Jumper_2_Open', 'Terminação 120 Ohm', 295, y + 10, {1: f'/TL{n}', 2: l}, JP2)
    f.comp(f'J{3 + n}', 'Connector:Screw_Terminal_01x03', f'CAN FD {n}', 330, y, {1: h, 2: l, 3: g}, BORNE3)


def folha():
    f = Folha('CAN FD', 'can.kicad_sch', notas=[
        'Dois CAN FD isolados (RF04, DP01): CAN FD 1 dedicado ao PC, CAN FD 2 a nós externos.',
        'RS a GND2 (alta velocidade): usar cabo blindado/entrançado, como recomenda a folha de características.',
    ])
    canal(f, 1, 75, 60)
    canal(f, 2, 205, 70)
    return f
