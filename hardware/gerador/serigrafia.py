"""Arruma a serigrafia da placa: referências sem sobreposição e nome de cada conector.

Uso:  python3 serigrafia.py      (no fim, depois do encaminhamento)

Para cada peça procura uma posição para a referência (texto de 0,8 mm) à volta do
courtyard ou, nos circuitos integrados e conectores grandes, no meio do corpo. A posição
não pode tocar em pads, noutras linhas de serigrafia, noutros textos nem no bordo da
placa. Escolhe a mais perto do centro da peça. Se não houver nenhuma, esconde a
referência (a lista sai no fim). Os conectores levam também o nome do barramento.
"""
import os
import sys

import numpy as np
import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcb import PCB, OX, OY, W, H  # noqa: E402

ALTURA = 0.8          # mm (mínimo do .kicad_pro)
ESPESSURA = 0.12
FOLGA = 0.15          # mm entre a serigrafia e os pads
MARGEM_BORDO = 0.6

NOMES = {
    'J1': 'VIN 5-60V', 'J2': 'SWD', 'J3': 'ETH', 'J4': 'CAN1', 'J5': 'CAN2', 'J6': 'RS485',
    'J7': 'RS232', 'J8': 'I2C1', 'J9': 'I2C2', 'J10': 'GPS', 'J11': 'PWM',
}
GRANDES = ('U', 'J', 'L1', 'Y')


def mm(v):
    return pcbnew.FromMM(float(v))


def caixa(bb, m=0.0):
    return (pcbnew.ToMM(bb.GetX()) - m, pcbnew.ToMM(bb.GetY()) - m,
            pcbnew.ToMM(bb.GetRight()) + m, pcbnew.ToMM(bb.GetBottom()) + m)


class Ocupacao:
    def __init__(self):
        self.r = np.zeros((0, 4))

    def add(self, c):
        self.r = np.vstack([self.r, c])

    def livre(self, c):
        if not len(self.r):
            return True
        r = self.r
        return not np.any((r[:, 0] < c[2]) & (r[:, 2] > c[0]) & (r[:, 1] < c[3]) & (r[:, 3] > c[1]))


def obstaculos(b):
    o = Ocupacao()
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.IsOnLayer(pcbnew.F_Cu) or p.IsOnLayer(pcbnew.F_Mask):
                o.add(caixa(p.GetBoundingBox(), FOLGA))
        for g in f.GraphicalItems():
            if g.GetLayer() == pcbnew.F_SilkS and g.IsVisible() if hasattr(g, 'IsVisible') else g.GetLayer() == pcbnew.F_SilkS:
                o.add(caixa(g.GetBoundingBox(), 0.1))
    return o


def mover_logotipo(b, ocup):
    """Os textos da placa (nome e versão) andam em bloco até um sítio livre perto do original."""
    ts = [d for d in b.GetDrawings() if d.GetLayer() == pcbnew.F_SilkS and isinstance(d, pcbnew.PCB_TEXT)]
    if not ts:
        return
    cs = np.array([caixa(t.GetBoundingBox(), 0.1) for t in ts])
    passos = sorted(((dx, dy) for dx in np.arange(-8, 8.01, 0.25) for dy in np.arange(-8, 8.01, 0.25)),
                    key=lambda d: d[0] ** 2 + d[1] ** 2)
    for dx, dy in passos:
        c = cs + [dx, dy, dx, dy]
        if all(dentro(x) and ocup.livre(x) for x in c):
            for t in ts:
                t.Move(pcbnew.VECTOR2I(mm(dx), mm(dy)))
            for x in c:
                ocup.add(x)
            if dx or dy:
                print(f'textos da placa deslocados {dx:+.2f} {dy:+.2f} mm')
            return
    print('sem lugar livre para os textos da placa')


def dentro(c):
    x0, y0 = OX + MARGEM_BORDO, OY + MARGEM_BORDO
    x1, y1 = OX + W - MARGEM_BORDO, OY + H - MARGEM_BORDO
    return c[0] >= x0 and c[1] >= y0 and c[2] <= x1 and c[3] <= y1


def candidatos(f, larg, alt, grande):
    """Centros e ângulos possíveis: à volta do courtyard e, nas peças grandes, no meio."""
    bb = f.GetCourtyard(pcbnew.F_CrtYd).BBox() if f.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else f.GetBoundingBox(False, False)
    x0, y0, x1, y1 = caixa(bb)
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    out = []
    if grande:
        out += [(cx, cy, 0), (cx, cy, 90)]
    g = 0.15
    for ang in (0, 90):
        tw, th = (larg, alt) if ang == 0 else (alt, larg)
        passos = np.linspace(-1, 1, 9)
        for s in passos:
            out.append((cx + s * (x1 - x0) / 2, y0 - g - th / 2, ang))       # em cima
            out.append((cx + s * (x1 - x0) / 2, y1 + g + th / 2, ang))       # em baixo
            out.append((x0 - g - tw / 2, cy + s * (y1 - y0) / 2, ang))       # à esquerda
            out.append((x1 + g + tw / 2, cy + s * (y1 - y0) / 2, ang))       # à direita
        for d in (0.6, 1.2):                                                # um pouco mais longe
            out.append((cx, y0 - g - th / 2 - d, ang))
            out.append((cx, y1 + g + th / 2 + d, ang))
            out.append((x0 - g - tw / 2 - d, cy, ang))
            out.append((x1 + g + tw / 2 + d, cy, ang))
    out.sort(key=lambda c: (c[0] - cx) ** 2 + (c[1] - cy) ** 2 + (0 if c[2] == 0 else 0.05))
    # recurso: grelha de 0,25 mm até 2,5 mm para lá do courtyard
    r = max(x1 - x0, y1 - y0) / 2 + 2.5
    v = np.arange(-r, r + 1e-6, 0.25)
    grelha = [(cx + dx, cy + dy, a) for dx in v for dy in v for a in (0, 90) if dx * dx + dy * dy <= r * r]
    grelha.sort(key=lambda c: (c[0] - cx) ** 2 + (c[1] - cy) ** 2 + (0 if c[2] == 0 else 0.05))
    return out + grelha


def colocar(texto, cands, ocup):
    for x, y, ang in cands:
        texto.SetTextAngle(pcbnew.EDA_ANGLE(ang, pcbnew.DEGREES_T))
        texto.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        c = caixa(texto.GetBoundingBox(), 0.05)
        if dentro(c) and ocup.livre(c):
            ocup.add(c)
            return True
    return False


def main():
    b = pcbnew.LoadBoard(PCB)
    # retirar nomes de conectores de uma passagem anterior
    velhos = [d for d in b.GetDrawings() if d.GetLayer() == pcbnew.F_SilkS and isinstance(d, pcbnew.PCB_TEXT)
              and d.GetText() in NOMES.values()]
    if velhos:
        sys.exit('a placa já tem os nomes dos conectores: correr sobre a placa sem serigrafia arrumada')
    ocup = obstaculos(b)
    mover_logotipo(b, ocup)
    fps = sorted(b.GetFootprints(), key=lambda f: (not f.GetReference().startswith(GRANDES),
                                                     -f.GetBoundingBox(False, False).GetArea()))
    for f in fps:
        f.Reference().SetVisible(False)
    escondidas = []
    # nomes dos conectores primeiro (texto de 1 mm)
    for f in fps:
        ref = f.GetReference()
        if ref not in NOMES:
            continue
        t = pcbnew.PCB_TEXT(b)
        t.SetText(NOMES[ref])
        t.SetLayer(pcbnew.F_SilkS)
        t.SetTextSize(pcbnew.VECTOR2I(mm(1.0), mm(1.0)))
        t.SetTextThickness(mm(0.15))
        larg = pcbnew.ToMM(t.GetBoundingBox().GetWidth()) or len(NOMES[ref]) * 0.9
        if colocar(t, candidatos(f, larg, 1.0, False), ocup):
            b.Add(t)
        else:
            print(f'sem lugar para o nome de {ref}')
    for f in fps:
        ref = f.GetReference()
        if ref.startswith('H'):
            continue
        r = f.Reference()
        r.SetVisible(True)
        r.SetTextSize(pcbnew.VECTOR2I(mm(ALTURA), mm(ALTURA)))
        r.SetTextThickness(mm(ESPESSURA))
        r.SetKeepUpright(True)
        larg = pcbnew.ToMM(r.GetBoundingBox().GetWidth()) if r.GetTextAngleDegrees() % 180 == 0 \
            else pcbnew.ToMM(r.GetBoundingBox().GetHeight())
        if not colocar(r, candidatos(f, larg, ALTURA, ref.startswith(GRANDES)), ocup):
            r.SetVisible(False)
            escondidas.append(ref)
    pcbnew.SaveBoard(PCB, b)
    print(f'{len(fps) - len(escondidas)} referências visíveis, {len(escondidas)} escondidas: {" ".join(escondidas)}')


if __name__ == '__main__':
    main()
