"""Vias de ligação aos planos (fanout) para os pinos SMD de massa e alimentação.

Uso:  python3 fanout.py      (depois de pcb.py)

Cada pad SMD numa rede com plano interior recebe uma pista curta e uma via para esse
plano: GND e as massas isoladas em In1, +3V3 e +5V em In2 (só onde o plano de In2 é
dessa rede). A via vai para o lado de fora do componente. Depois corre o DRC e retira
as vias que causem violações, até não haver nenhuma.

Os pads com vias térmicas no próprio footprint (LM5177, TPS62162, LAN8742A) e os pads
de furo passante já ligam aos planos e ficam como estão.
"""
import math
import os
import re
import sys
import tempfile

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcb import PCB, OX, OY, W, H, BARREIRA, ISO  # noqa: E402

VIA, FURO, PISTA = 0.6, 0.3, 0.3
AFAST = 0.25           # afastamento mínimo a cobre de outras redes (mm), acima da regra de 0,15
ZONAS_5V = [(0.5, 10.0, 32.0, 36.0), (0.5, 63.5, W - 0.5, BARREIRA[0])]
PLANO_IN1 = {'GND', '/CAN FD/GND_CAN1', '/CAN FD/GND_CAN2', '/RS485 e RS232/GND_485', '/PWM isolado/GND_PWM'}


def mm(v):
    return pcbnew.FromMM(float(v))


def loc(p):
    return pcbnew.ToMM(p.x) - OX, pcbnew.ToMM(p.y) - OY


def dentro(x, y, r):
    return r[0] <= x <= r[2] and r[1] <= y <= r[3]


def plano(rede, x, y):
    """Camada interior com plano desta rede no ponto (x, y), ou None."""
    if rede in PLANO_IN1:
        return pcbnew.In1_Cu
    if y >= BARREIRA[0] or not (0.5 < x < W - 0.5):
        return None
    em5 = any(dentro(x, y, r) for r in ZONAS_5V)
    if rede == '+5V' and em5:
        return pcbnew.In2_Cu
    if rede == '+3V3' and not em5:
        return pcbnew.In2_Cu
    return None


def caixa_pad(p, folga):
    b = p.GetBoundingBox()
    return (pcbnew.ToMM(b.GetX()) - OX - folga, pcbnew.ToMM(b.GetY()) - OY - folga,
            pcbnew.ToMM(b.GetRight()) - OX + folga, pcbnew.ToMM(b.GetBottom()) - OY + folga)


def sobrepoe(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def segmento_livre(x0, y0, x1, y1, largura, rede, obst, afast=AFAST):
    """True se o segmento (com a largura e o afastamento) não toca cobre de outras redes."""
    n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 0.05))
    r = largura / 2 + afast
    perto = [o for o, rd in obst if rd != rede and o[0] - r < max(x0, x1) and min(x0, x1) < o[2] + r
             and o[1] - r < max(y0, y1) and min(y0, y1) < o[3] + r]
    for i in range(n + 1):
        x, y = x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n
        for o in perto:
            if o[0] - r < x < o[2] + r and o[1] - r < y < o[3] + r:
                return False
    return True


def main():
    b = pcbnew.LoadBoard(PCB)
    pads = [p for f in b.GetFootprints() for p in f.Pads()]
    # obstáculos: pads de todas as redes; courtyards dos outros componentes
    crt = {}
    for f in b.GetFootprints():
        f.BuildCourtyardCaches()
        c = f.GetCourtyard(pcbnew.F_CrtYd)
        if c.OutlineCount():
            bb = c.BBox()
            crt[f.GetReference()] = (pcbnew.ToMM(bb.GetX()) - OX, pcbnew.ToMM(bb.GetY()) - OY,
                                     pcbnew.ToMM(bb.GetRight()) - OX, pcbnew.ToMM(bb.GetBottom()) - OY)
    obst = []  # (caixa, rede)
    for p in pads:
        obst.append((caixa_pad(p, 0), p.GetNetname()))
    keep = [(0, BARREIRA[0], W, BARREIRA[1])]
    xs = sorted(ISO.values())
    for (a0, a1), (b0, b1) in zip(xs, xs[1:]):
        keep.append((a1, BARREIRA[1], b0, H))

    # números de pad com vias térmicas no footprint (pad passante com o mesmo número)
    termicos = set()
    for f in b.GetFootprints():
        nums = {}
        for p in f.Pads():
            nums.setdefault(p.GetNumber(), set()).add(p.GetAttribute())
        for n, ats in nums.items():
            if pcbnew.PAD_ATTRIB_PTH in ats and pcbnew.PAD_ATTRIB_SMD in ats:
                termicos.add((f.GetReference(), n))

    novos = []
    vias = []
    ligacoes = []
    for f in b.GetFootprints():
        ref = f.GetReference()
        cx, cy = loc(f.GetPosition())
        if ref in crt:
            c = crt[ref]
            cx, cy = (c[0] + c[2]) / 2, (c[1] + c[3]) / 2
        for p in f.Pads():
            if p.GetAttribute() != pcbnew.PAD_ATTRIB_SMD or (ref, p.GetNumber()) in termicos:
                continue
            rede = p.GetNetname()
            px, py = loc(p.GetPosition())
            camada = plano(rede, px, py)
            if camada is None:
                continue
            pb = caixa_pad(p, 0)
            # direção para fora do componente; tenta também as outras três
            dx, dy = px - cx, py - cy
            base = math.atan2(dy, dx) if (abs(dx) + abs(dy)) > 1e-3 else 0.0
            feito = False
            # primeiro as quatro direções dos eixos (pela ordem de alinhamento com a
            # direção para fora), depois as diagonais
            eixos = sorted((k * math.pi / 2 for k in range(4)), key=lambda a: abs(math.remainder(a - base, 2 * math.pi)))
            diag = sorted((math.pi / 4 + k * math.pi / 2 for k in range(4)), key=lambda a: abs(math.remainder(a - base, 2 * math.pi)))
            for ang in eixos + diag:
                ux, uy = math.cos(ang), math.sin(ang)
                # distância do centro do pad ao bordo do pad nesta direção
                hx, hy = (pb[2] - pb[0]) / 2, (pb[3] - pb[1]) / 2
                t = min(hx / abs(ux) if abs(ux) > 1e-6 else 1e9, hy / abs(uy) if abs(uy) > 1e-6 else 1e9)
                for extra in (0.25, 0.45, 0.7):
                    d = t + extra + VIA / 2
                    vx, vy = px + ux * d, py + uy * d
                    vc = (vx - VIA / 2 - AFAST, vy - VIA / 2 - AFAST, vx + VIA / 2 + AFAST, vy + VIA / 2 + AFAST)
                    if not (1.0 < vx < W - 1.0 and 1.0 < vy < H - 1.0):
                        continue
                    if any(sobrepoe(vc, k_) for k_ in keep):
                        continue
                    # pista do bordo do pad até à via
                    ex, ey = px + ux * t, py + uy * t
                    pista = (min(ex, vx) - PISTA / 2 - AFAST, min(ey, vy) - PISTA / 2 - AFAST,
                             max(ex, vx) + PISTA / 2 + AFAST, max(ey, vy) + PISTA / 2 + AFAST)
                    if any(sobrepoe(vc, o) or sobrepoe(pista, o) for o, r in obst if r != rede):
                        continue
                    # vias tapadas pela máscara podem ficar debaixo do corpo de outro
                    # componente, mas não debaixo de conectores nem de circuitos integrados
                    if any(sobrepoe((vx - VIA / 2, vy - VIA / 2, vx + VIA / 2, vy + VIA / 2), c)
                           for r2, c in crt.items() if r2 != ref and r2[0] in 'JUQLYHD'):
                        continue
                    if any(math.hypot(vx - qx, vy - qy) < VIA + 0.3 for qx, qy in vias):
                        continue
                    vias.append((vx, vy))
                    novos.append((p, rede, px, py, vx, vy))
                    obst.append(((vx - VIA / 2, vy - VIA / 2, vx + VIA / 2, vy + VIA / 2), rede))
                    feito = True
                    break
                if feito:
                    break
            if not feito:
                # sem espaço para a via: ligar a um pad da mesma rede ali perto
                # (normalmente o condensador de desacoplamento, que tem a sua via)
                cands = []
                for q in pads:
                    if q.GetNetname() == rede and q.GetParent().GetReference() != ref:
                        qx, qy = loc(q.GetPosition())
                        dd = math.hypot(qx - px, qy - py)
                        if dd < 4.0:
                            cands.append((dd, qx, qy))
                # sai do pad pelo eixo para fora e depois segue para o pad vizinho
                ax = eixos[0]
                ux, uy = round(math.cos(ax)), round(math.sin(ax))
                hx, hy = (pb[2] - pb[0]) / 2, (pb[3] - pb[1]) / 2
                t = hx if ux else hy
                LF = 0.25
                for dd, qx, qy in sorted(cands):
                    sx, sy = px + ux * (t + 0.35), py + uy * (t + 0.35)
                    if segmento_livre(px, py, sx, sy, LF, rede, obst, 0.17) and \
                       segmento_livre(sx, sy, qx, qy, LF, rede, obst, 0.17):
                        ligacoes.append((p, [(px, py), (sx, sy), (qx, qy)]))
                        for (x0, y0), (x1, y1) in (((px, py), (sx, sy)), ((sx, sy), (qx, qy))):
                            k = max(2, int(math.hypot(x1 - x0, y1 - y0) / 0.2))
                            for i in range(k + 1):
                                x, y = x0 + (x1 - x0) * i / k, y0 + (y1 - y0) * i / k
                                obst.append(((x - LF / 2, y - LF / 2, x + LF / 2, y + LF / 2), rede))
                        break

    itens = []
    for p, rede, px, py, vx, vy in novos:
        net = p.GetNet()
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(mm(OX + px), mm(OY + py)))
        t.SetEnd(pcbnew.VECTOR2I(mm(OX + vx), mm(OY + vy)))
        t.SetWidth(mm(PISTA))
        t.SetLayer(pcbnew.F_Cu)
        t.SetNet(net)
        b.Add(t)
        v = pcbnew.PCB_VIA(b)
        v.SetPosition(pcbnew.VECTOR2I(mm(OX + vx), mm(OY + vy)))
        v.SetViaType(pcbnew.VIATYPE_THROUGH)
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetWidth(mm(VIA))
        v.SetDrill(mm(FURO))
        v.SetNet(net)
        b.Add(v)
        itens.append((t, v))
    for p, pts in ligacoes:
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(mm(OX + x0), mm(OY + y0)))
            t.SetEnd(pcbnew.VECTOR2I(mm(OX + x1), mm(OY + y1)))
            t.SetWidth(mm(0.25))
            t.SetLayer(pcbnew.F_Cu)
            t.SetNet(p.GetNet())
            b.Add(t)
    print(f'{len(novos)} vias, {len(ligacoes)} ligações diretas a pads vizinhos')
    pcbnew.SaveBoard(PCB, b)

    # DRC: retirar vias/pistas que causem violações de cobre
    for volta in range(4):
        b = pcbnew.LoadBoard(PCB)
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
        with tempfile.TemporaryDirectory() as d:
            rpt = os.path.join(d, 'drc.rpt')
            pcbnew.WriteDRCReport(b, rpt, pcbnew.EDA_UNITS_MILLIMETRES, False)
            t = open(rpt, encoding='utf-8').read()
        maus = set()
        for bloco in re.split(r'\n(?=\[)', t):
            if not re.match(r'\[(clearance|shorting_items|hole_clearance|hole_to_hole|tracks_crossing|'
                            r'copper_edge_clearance|via_dangling|track_dangling|solder_mask_bridge|hole_near_hole)\]', bloco):
                continue
            for x, y in re.findall(r'@\(([\d.]+) mm, ([\d.]+) mm\): (?:Via|Track)', bloco):
                maus.add((round(float(x), 2), round(float(y), 2)))
        if not maus:
            break
        n = 0
        for it in list(b.GetTracks()):
            if it.GetClass() == 'PCB_VIA':
                q = it.GetPosition()
            else:
                q = it.GetEnd()
            chave = (round(pcbnew.ToMM(q.x), 2), round(pcbnew.ToMM(q.y), 2))
            s = it.GetStart() if it.GetClass() != 'PCB_VIA' else q
            chave2 = (round(pcbnew.ToMM(s.x), 2), round(pcbnew.ToMM(s.y), 2))
            if chave in maus or chave2 in maus:
                b.Remove(it)
                n += 1
        # retirar pistas órfãs (via removida) e vias órfãs (pista removida)
        vias = {(v.GetPosition().x, v.GetPosition().y) for v in b.GetTracks() if v.GetClass() == 'PCB_VIA'}
        centros = {(q.GetPosition().x, q.GetPosition().y) for f in b.GetFootprints() for q in f.Pads()}
        inicios = {(t.GetStart().x, t.GetStart().y) for t in b.GetTracks() if t.GetClass() != 'PCB_VIA'}
        for it in list(b.GetTracks()):
            fim = (it.GetEnd().x, it.GetEnd().y)
            if it.GetClass() != 'PCB_VIA' and fim not in vias and fim not in centros and fim not in inicios:
                b.Remove(it)
        fins = {(t.GetEnd().x, t.GetEnd().y) for t in b.GetTracks() if t.GetClass() != 'PCB_VIA'}
        for it in list(b.GetTracks()):
            if it.GetClass() == 'PCB_VIA' and (it.GetPosition().x, it.GetPosition().y) not in fins:
                b.Remove(it)
        pcbnew.SaveBoard(PCB, b)
        print(f'volta {volta + 1}: retiradas {n} vias/pistas com violações')

    b = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(PCB, b)
    nv = sum(1 for t in b.GetTracks() if t.GetClass() == 'PCB_VIA')
    print(f'ok: {nv} vias de ligação aos planos')


if __name__ == '__main__':
    main()
