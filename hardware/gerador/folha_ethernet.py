"""Folha 3: Ethernet 10/100 (LAN8742A + RJ45 com magnéticos integrados).

Configuração por pinos de arranque (folha de características da Microchip, DS00001989):
  LED2/nINTSEL a GND (10k) -> pino 14 é REFCLKO: o PHY gera os 50 MHz do RMII a partir
                              do cristal de 25 MHz e alimenta o ETH_REF_CLK do MCU.
  LED1/REGOFF a GND (10k)  -> regulador interno de 1,2 V ligado (VDDCR).
  MODE[2:0] = 111 e PHYAD0 = 0 pelas resistências internas -> autonegociação, endereço 0.
As linhas TX/RX têm 49,9 Ohm para 3,3 V e as derivações centrais do transformador
ligam a 3,3 V (o emissor do LAN8742A é em modo de corrente).
"""
from hw import Folha
from comum import R, C, R0603, C0603, C0805, C1206, XTAL3225, desacoplamento


def folha():
    f = Folha('Ethernet', 'ethernet.kicad_sch', notas=[
        'LAN8742A em RMII com REFCLKO: o PHY fornece os 50 MHz ao MCU. Ethernet apenas para o PC (RF05).',
        'Partilha o NRST do MCU (como na NUCLEO-H743ZI).',
    ])
    f.comp('U4', 'Interface_Ethernet:LAN8742A', 'LAN8742A-CZ', 170, 150, {
        1: '+3V3', 19: '+3V3', 9: '+3V3', 6: '/VDDCR', 25: 'GND',
        5: '/XI', 4: '/XO', 24: '/RBIAS',
        2: '/NINTSEL', 3: '/REGOFF',
        7: 'ETH_RXD1', 8: 'ETH_RXD0', 11: 'ETH_CRS_DV', 12: 'ETH_MDIO', 13: 'ETH_MDC',
        14: '/REF_CLK_PHY', 15: 'NRST', 16: 'ETH_TX_EN', 17: 'ETH_TXD0', 18: 'ETH_TXD1',
        21: '/TXP', 20: '/TXN', 23: '/RXP', 22: '/RXN'}, nc=(10,))

    desacoplamento(f, ['C40', 'C41', 'C42', 'C43'], ['100 nF', '100 nF', '100 nF', '4,7 uF'], '+3V3', 'GND', 40, 50)
    f.comp('C44', C, '1 uF', 40, 80, {1: '/VDDCR', 2: 'GND'}, C0603)
    f.comp('C45', C, '470 pF', 52, 80, {1: '/VDDCR', 2: 'GND'}, C0603)
    f.comp('R30', R, '12,1k 1%', 40, 110, {1: '/RBIAS', 2: 'GND'}, R0603)
    f.comp('R31', R, '10k', 52, 110, {1: '/NINTSEL', 2: 'GND'}, R0603)
    f.comp('R32', R, '10k', 64, 110, {1: '/REGOFF', 2: 'GND'}, R0603)
    f.comp('R33', R, '1,5k', 76, 110, {1: '+3V3', 2: 'ETH_MDIO'}, R0603)
    # série no relógio de 50 MHz, junto ao PHY (amortece reflexões)
    f.comp('R94', R, '33', 110, 250, {1: '/REF_CLK_PHY', 2: 'ETH_REF_CLK'}, R0603)

    f.comp('Y2', 'Device:Crystal_GND24', '25 MHz (C_L 10 pF)', 60, 160, {1: '/XI', 3: '/XO', 2: 'GND', 4: 'GND'}, XTAL3225)
    f.comp('C46', C, '15 pF', 40, 180, {1: '/XI', 2: 'GND'}, C0603)
    f.comp('C47', C, '15 pF', 80, 180, {1: '/XO', 2: 'GND'}, C0603)

    # Terminações das linhas
    for i, rede in enumerate(['/TXP', '/TXN', '/RXP', '/RXN']):
        f.comp(f'R{34 + i}', R, '49,9 1%', 250 + i * 12, 90, {1: rede, 2: '+3V3'}, R0603)
    f.comp('C48', C, '100 nF', 250, 120, {1: '+3V3', 2: 'GND'}, C0603)
    f.comp('C49', C, '100 nF', 262, 120, {1: '+3V3', 2: 'GND'}, C0603)

    f.comp('J3', 'Connector:RJ45_Hanrun_HR911105A_Horizontal', 'HR911105A (magnéticos integrados)', 330, 150, {
        1: '/TXP', 2: '/TXN', 3: '/RXP', 6: '/RXN', 4: '+3V3', 5: '+3V3', 8: 'GND', 'SH': '/CHASSIS'},
        nc=(9, 10, 11, 12))
    f.comp('C50', C, '1 nF 2 kV', 320, 200, {1: '/CHASSIS', 2: 'GND'}, C1206)
    f.comp('R38', R, '1M', 335, 200, {1: '/CHASSIS', 2: 'GND'}, 'Resistor_SMD:R_1206_3216Metric')
    # PWR_FLAG: redes alimentadas por ferrite, resistência ou regulador interno (ERC)
    f.flag('/VDDCR', 395, 40)
    return f
