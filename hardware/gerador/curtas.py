"""Encaminha as ligações de sinal curtas em F.Cu (rascunho que se revê à mão).

Uso:  python3 curtas.py      (depois de pcb.py e fanout.py)

Para cada rede de sinal liga os pads pela árvore de menor comprimento e desenha cada
ramo com menos de COMPR_MAX mm como pista reta ou em L (com saída pelo eixo do pad,
para os pinos de passo fino), só se não tocar em cobre de outras redes nem em zonas de
potência. Não usa vias. Depois corre o DRC e retira as pistas com violações.

Ficam por fazer as ligações longas, as que precisam de mudar de camada e as redes de
potência (HV e P5V), que se desenham à mão.
"""
import math
import os
import re
import sys
import tempfile

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcb import PCB, OX, OY, W, H, BARREIRA, ISO, POTENCIA  # noqa: E402

COMPR_MAX = 9.0
AFAST = 0.2            # acima dos 0,15 mm da regra
PLANOS = {'GND', '+3V3', '+5V', 'VIN'}
LARGURA = {'BUS': 0.4, 'ETH': 0.25}


def mm(v):
    return pcbnew.FromMM(float(v))


def loc(p):
    return pcbnew.ToMM(p.x) - OX, pcbnew.ToMM(p.y) - OY


def caixa(item, folga=0.0):
    b = item.GetBoundingBox()
    return (pcbnew.ToMM(b.GetX()) - OX - folga, pcbnew.ToMM(b.GetY()) - OY - folga,
            pcbnew.ToMM(b.GetRight()) - OX + folga, pcbnew.ToMM(b.GetBottom()) - OY + folga)


class Obstaculos:
    """Retângulos de cobre por rede, numa grelha de 2 mm para procurar depressa."""

    def __init__(self):
        self.cel = {}

    def _chaves(self, r):
        for i in range(int(r[0] // 2), int(r[2] // 2) + 1):
            for j in range(int(r[1] // 2), int(r[3] // 2) + 1):
                yield i, j

    def add(self, r, rede):
        for k in self._chaves(r):
            self.cel.setdefault(k, []).append((r, rede))

    def perto(self, r):
        vistos = set()
        for k in self._chaves(r):
            for o in self.cel.get(k, ()):
                if id(o) not in vistos:
                    vistos.add(id(o))
                    yield o


def livre(obs, x0, y0, x1, y1, w, rede, proibidas):
    r = w / 2 + AFAST
    caixa_seg = (min(x0, x1) - r, min(y0, y1) - r, max(x0, x1) + r, max(y0, y1) + r)
    if caixa_seg[0] < 0.6 or caixa_seg[1] < 0.6 or caixa_seg[2] > W - 0.6 or caixa_seg[3] > H - 0.6:
        return False
    for p in proibidas:
        if caixa_seg[0] < p[2] and p[0] < caixa_seg[2] and caixa_seg[1] < p[3] and p[1] < caixa_seg[3]:
            return False
    perto = [o for o, rd in obs.perto(caixa_seg) if rd != rede]
    n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 0.05))
    for i in range(n + 1):
        x, y = x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * i / n
        for o in perto:
            if o[0] - r < x < o[2] + r and o[1] - r < y < o[3] + r:
                return False
    return True


def marcar(obs, pts, w, rede):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        k = max(2, int(math.hypot(x1 - x0, y1 - y0) / 0.2))
        for i in range(k + 1):
            x, y = x0 + (x1 - x0) * i / k, y0 + (y1 - y0) * i / k
            obs.add((x - w / 2, y - w / 2, x + w / 2, y + w / 2), rede)


def saida(pad):
    """Ponto de saída pelo eixo maior do pad, para fora do componente."""
    px, py = loc(pad.GetPosition())
    b = caixa(pad)
    cx, cy = loc(pad.GetParent().GetPosition())
    if (b[2] - b[0]) >= (b[3] - b[1]):
        s = 1 if px >= cx else -1
        return px + s * ((b[2] - b[0]) / 2 + 0.3), py
    s = 1 if py >= cy else -1
    return px, py + s * ((b[3] - b[1]) / 2 + 0.3)


def caminhos(a, b):
    (ax, ay), (bx, by) = loc(a.GetPosition()), loc(b.GetPosition())
    sa, sb = saida(a), saida(b)
    # reta só se for quase horizontal ou vertical, ou muito curta; senão, em L
    if min(abs(ax - bx), abs(ay - by)) < 0.05 or math.dist((ax, ay), (bx, by)) < 1.5:
        yield [(ax, ay), (bx, by)]
    yield [(ax, ay), (bx, ay), (bx, by)]
    yield [(ax, ay), (ax, by), (bx, by)]
    for p in ([(ax, ay), sa, (sa[0], by), (bx, by)], [(ax, ay), sa, (bx, sa[1]), (bx, by)],
              [(ax, ay), sa, sb, (bx, by)], [(ax, ay), sa, (sb[0], sa[1]), sb, (bx, by)],
              [(ax, ay), sa, (sa[0], sb[1]), sb, (bx, by)]):
        yield p
    yield [(ax, ay), (bx, by)]


def main():
    b = pcbnew.LoadBoard(PCB)
    obs = Obstaculos()
    obs_b = Obstaculos()
    vias = []
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.IsOnLayer(pcbnew.F_Cu):
                obs.add(caixa(p), p.GetNetname())
            if p.IsOnLayer(pcbnew.B_Cu):
                obs_b.add(caixa(p), p.GetNetname())
            if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
                vias.append(loc(p.GetPosition()))
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            obs.add(caixa(t), t.GetNetname())
            obs_b.add(caixa(t), t.GetNetname())
            vias.append(loc(t.GetPosition()))
        elif t.GetLayer() == pcbnew.F_Cu:
            obs.add(caixa(t), t.GetNetname())
    proibidas = [(0, BARREIRA[0] - 0.3, W, BARREIRA[1] + 0.3)]
    xs = sorted(ISO.values())
    for (a0, a1), (b0, b1) in zip(xs, xs[1:]):
        proibidas.append((a1 - 0.3, BARREIRA[1], b0 + 0.3, H))
    pot = {}
    for rede, pol in POTENCIA:
        px, py = [p[0] for p in pol], [p[1] for p in pol]
        pot[rede] = (min(px) - 0.4, min(py) - 0.4, max(px) + 0.4, max(py) + 0.4)

    redes = {}
    for f in b.GetFootprints():
        for p in f.Pads():
            n = p.GetNetname()
            if n and not n.startswith('unconnected') and p.IsOnLayer(pcbnew.F_Cu):
                redes.setdefault(n, []).append(p)
    feitas = 0
    novas = []
    ramos = []
    for rede, pads in redes.items():
        classe = pads[0].GetNetClassName()
        if rede in PLANOS or classe in ('HV', 'P5V') or rede.rsplit('/', 1)[-1].startswith('GND') or len(pads) < 2:
            continue
        # árvore de menor comprimento (Prim) entre os pads da rede
        dentro_ = [pads[0]]
        fora = pads[1:]
        while fora:
            d, i, j = min((math.dist(loc(a.GetPosition()), loc(c.GetPosition())), i, j)
                          for i, a in enumerate(dentro_) for j, c in enumerate(fora))
            ramos.append((d, rede, classe, dentro_[i], fora[j]))
            dentro_.append(fora.pop(j))
    ramos.sort(key=lambda r: r[0])
    falhadas = []
    for d, rede, classe, a, c in ramos:
        if a.GetParent() == c.GetParent() and a.GetNumber() == c.GetNumber():
            continue
        if d > COMPR_MAX:
            falhadas.append((d, rede, classe, a, c))
            continue
        w = LARGURA.get(classe, 0.2)
        proib = proibidas + [r for n, r in pot.items() if n != rede]
        for pts in caminhos(a, c):
            if sum(math.dist(p, q) for p, q in zip(pts, pts[1:])) > COMPR_MAX * 1.6:
                continue
            # o primeiro e o último troço começam dentro do próprio pad
            if all(livre(obs, *p, *q, w, rede, proib) for p, q in zip(pts, pts[1:])):
                marcar(obs, pts, w, rede)
                novas.append((pts, w, a.GetNet()))
                feitas += 1
                break
        else:
            falhadas.append((d, rede, classe, a, c))

    # Segunda passagem: pela camada de baixo, com uma via junto a cada pad
    def via_junto(pad, rede, w, proib):
        px, py = loc(pad.GetPosition())
        bx = caixa(pad)
        hx, hy = (bx[2] - bx[0]) / 2, (bx[3] - bx[1]) / 2
        cx, cy = loc(pad.GetParent().GetPosition())
        base = math.atan2(py - cy, px - cx) if abs(px - cx) + abs(py - cy) > 1e-3 else 0.0
        angs = sorted((k * math.pi / 4 for k in range(8)), key=lambda a: abs(math.remainder(a - base, 2 * math.pi)))
        for ang in angs:
            ux, uy = math.cos(ang), math.sin(ang)
            t = min(hx / abs(ux) if abs(ux) > 1e-6 else 1e9, hy / abs(uy) if abs(uy) > 1e-6 else 1e9)
            for extra in (0.3, 0.6, 1.0):
                d = t + extra + 0.3
                vx, vy = px + ux * d, py + uy * d
                if any(math.dist((vx, vy), q) < 0.95 for q in vias):
                    continue
                if not (livre(obs, vx, vy, vx, vy, 0.6, rede, proib) and livre(obs_b, vx, vy, vx, vy, 0.6, rede, proib)):
                    continue
                if not livre(obs, px, py, vx, vy, w, rede, proib):
                    continue
                return vx, vy
        return None

    feitas_b = 0
    novas_vias = []
    for d, rede, classe, a, c in sorted(falhadas, key=lambda r: r[0]):
        if d > 45:
            continue
        w = LARGURA.get(classe, 0.2)
        proib = proibidas + [r for n, r in pot.items() if n != rede]
        va = via_junto(a, rede, w, proib)
        if va is None:
            continue
        # reservar provisoriamente a via A para a escolha da via B
        vias.append(va)
        vb = via_junto(c, rede, w, proib)
        vias.pop()
        if vb is None or math.dist(va, vb) < 0.95:
            continue
        opcoes = [[va, (vb[0], va[1]), vb], [va, (va[0], vb[1]), vb]]
        if min(abs(va[0] - vb[0]), abs(va[1] - vb[1])) < 0.05:
            opcoes.insert(0, [va, vb])
        for pts in opcoes:
            if all(livre(obs_b, *p, *q, w, rede, proib) for p, q in zip(pts, pts[1:])):
                pa, pc = loc(a.GetPosition()), loc(c.GetPosition())
                marcar(obs, [pa, va], w, rede)
                marcar(obs, [vb, pc], w, rede)
                marcar(obs_b, pts, w, rede)
                for v in (va, vb):
                    vias.append(v)
                    obs.add((v[0] - 0.3, v[1] - 0.3, v[0] + 0.3, v[1] + 0.3), rede)
                    obs_b.add((v[0] - 0.3, v[1] - 0.3, v[0] + 0.3, v[1] + 0.3), rede)
                novas.append(([pa, va], w, a.GetNet()))
                novas.append(([vb, pc], w, a.GetNet()))
                novas.append((pts, w, a.GetNet(), pcbnew.B_Cu))
                novas_vias += [(va, a.GetNet()), (vb, a.GetNet())]
                feitas_b += 1
                break
    print(f'{feitas_b} ligações pela camada de baixo')

    for (v, net) in novas_vias:
        via = pcbnew.PCB_VIA(b)
        via.SetPosition(pcbnew.VECTOR2I(mm(OX + v[0]), mm(OY + v[1])))
        via.SetViaType(pcbnew.VIATYPE_THROUGH)
        via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        via.SetWidth(mm(0.6))
        via.SetDrill(mm(0.3))
        via.SetNet(net)
        b.Add(via)
    for item in novas:
        pts, w, net = item[:3]
        camada = item[3] if len(item) > 3 else pcbnew.F_Cu
        for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
            if math.dist((x0, y0), (x1, y1)) < 1e-3:
                continue
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(pcbnew.VECTOR2I(mm(OX + x0), mm(OY + y0)))
            t.SetEnd(pcbnew.VECTOR2I(mm(OX + x1), mm(OY + y1)))
            t.SetWidth(mm(w))
            t.SetLayer(camada)
            t.SetNet(net)
            b.Add(t)
    pcbnew.SaveBoard(PCB, b)
    print(f'{feitas} ligações curtas desenhadas em F.Cu')

    # DRC: retirar as pistas destas ligações que causem violações
    for volta in range(6):
        b = pcbnew.LoadBoard(PCB)
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
        with tempfile.TemporaryDirectory() as dd:
            rpt = os.path.join(dd, 'drc.rpt')
            pcbnew.WriteDRCReport(b, rpt, pcbnew.EDA_UNITS_MILLIMETRES, False)
            t = open(rpt, encoding='utf-8').read()
        maus = []
        for bloco in re.split(r'\n(?=\[)', t):
            if re.match(r'\[(clearance|shorting_items|tracks_crossing|copper_edge_clearance|solder_mask_bridge|'
                        r'via_dangling|track_dangling|hole_clearance|hole_near_hole)\]', bloco):
                maus += [(float(x), float(y)) for x, y in re.findall(r'@\(([\d.]+) mm, ([\d.]+) mm\): (?:Track|Via)', bloco)]
        if not maus:
            break
        n = 0
        for it in list(b.GetTracks()):
            if it.GetClass() == 'PCB_VIA':
                q = it.GetPosition()
                if any(math.hypot(pcbnew.FromMM(x) - q.x, pcbnew.FromMM(y) - q.y) < pcbnew.FromMM(0.05) for x, y in maus):
                    b.Remove(it)
                    n += 1
                continue
            s, e = it.GetStart(), it.GetEnd()
            for x, y in maus:
                # o DRC indica um ponto da pista; retirar a pista que passa por ele
                px, py = pcbnew.FromMM(x), pcbnew.FromMM(y)
                dx, dy = e.x - s.x, e.y - s.y
                L2 = dx * dx + dy * dy
                u = 0 if L2 == 0 else max(0, min(1, ((px - s.x) * dx + (py - s.y) * dy) / L2))
                qx, qy = s.x + u * dx, s.y + u * dy
                if math.hypot(px - qx, py - qy) < pcbnew.FromMM(0.05) + it.GetWidth() / 2:
                    b.Remove(it)
                    n += 1
                    break
        pcbnew.SaveBoard(PCB, b)
        print(f'volta {volta + 1}: retiradas {n} pistas com violações')
    b = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(PCB, b)


if __name__ == '__main__':
    main()
