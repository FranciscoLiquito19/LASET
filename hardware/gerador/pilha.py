"""Escreve a pilha de camadas da JLCPCB (JLC04161H-7628, 1,6 mm) no ficheiro da placa.

Uso:  python3 pilha.py      (depois de pcb.py; pode correr mais de uma vez)

Valores da JLCPCB para a JLC04161H-7628: cobre exterior de 1 oz (35 um), interior de 0,5 oz
(15,2 um), pré-impregnado 7628 de 0,2104 mm (er 4,4) entre cada face e a camada interior
mais perto, núcleo de 1,065 mm (er 4,43) entre In1 e In2. Consequência para o desenho:
F.Cu tem o plano de massa (In1) a 0,21 mm; In2 fica a 0,21 mm de B.Cu e a 1,07 mm de In1.
Na encomenda escolher "Specify Stackup: JLC04161H-7628".
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcb import PCB  # noqa: E402

PILHA = '''    (stackup
      (layer "F.SilkS" (type "Top Silk Screen"))
      (layer "F.Paste" (type "Top Solder Paste"))
      (layer "F.Mask" (type "Top Solder Mask") (thickness 0.01))
      (layer "F.Cu" (type "copper") (thickness 0.035))
      (layer "dielectric 1" (type "prepreg") (thickness 0.2104) (material "7628") (epsilon_r 4.4) (loss_tangent 0.02))
      (layer "In1.Cu" (type "copper") (thickness 0.0152))
      (layer "dielectric 2" (type "core") (thickness 1.065) (material "FR4") (epsilon_r 4.43) (loss_tangent 0.02))
      (layer "In2.Cu" (type "copper") (thickness 0.0152))
      (layer "dielectric 3" (type "prepreg") (thickness 0.2104) (material "7628") (epsilon_r 4.4) (loss_tangent 0.02))
      (layer "B.Cu" (type "copper") (thickness 0.035))
      (layer "B.Mask" (type "Bottom Solder Mask") (thickness 0.01))
      (layer "B.Paste" (type "Bottom Solder Paste"))
      (layer "B.SilkS" (type "Bottom Silk Screen"))
      (copper_finish "HAL lead-free")
      (dielectric_constraints no)
    )
'''


def main():
    t = open(PCB, encoding='utf-8').read()
    t = re.sub(r'    \(stackup\n.*?\n    \)\n', '', t, flags=re.S)
    i = t.index('  (setup\n') + len('  (setup\n')
    t = t[:i] + PILHA + t[i:]
    open(PCB, 'w', encoding='utf-8').write(t)
    print('pilha JLC04161H-7628 escrita')


if __name__ == '__main__':
    main()
