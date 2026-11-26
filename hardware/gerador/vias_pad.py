"""Tira as vias de dentro dos pads SMD.

Uso:  python3 vias_pad.py          (lista e corrige)
      LISTAR=1 python3 vias_pad.py (só lista)

Uma via não tapada dentro de um pad (ou encostada a ele) puxa a solda para o furo na
refusão: a junta fica fraca e os passivos pequenos levantam de um lado. Cada via assim
passa para o sítio livre mais perto, fora de todos os pads (0,1 mm de folga), e liga ao
ponto antigo por uma pista curta em cada camada onde havia pistas ligadas a ela. Ficam
como estão as vias dos pads grandes (pads térmicos, mais de 3 mm²), que são de
propósito. A via é movida (não apagada e criada de novo) e as pistas são acrescentadas.
"""
import math
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcb import PCB, OX, OY, W, H, LM5177_AREA  # noqa: E402

CAMADAS = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)
FOLGA_PAD = 0.1
AFAST = {'Default': 0.15, 'BUS': 0.3, 'ETH': 0.15, 'HV': 0.6, 'P5V': 0.2}


def mm(v):
    return pcbnew.FromMM(float(v))


def P(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def loc(p):
    return pcbnew.ToMM(p.x) - OX, pcbnew.ToMM(p.y) - OY


def area_pad(p):
    s = p.GetSize()
    return pcbnew.ToMM(s.x) * pcbnew.ToMM(s.y)


def na_area_lm(x, y):
    a = LM5177_AREA
    return a[0] <= x <= a[2] and a[1] <= y <= a[3]


def em_pad(b, v, pads):
    c = pcbnew.SHAPE_CIRCLE(v.GetPosition(), v.GetWidth() // 2)
    for p in pads:
        for L in (pcbnew.F_Cu, pcbnew.B_Cu):
            if p.IsOnLayer(L) and p.GetEffectiveShape(L).Collide(c, mm(FOLGA_PAD) - 1):
                return p
    return None


def main():
    b = pcbnew.LoadBoard(PCB)
    classe = {}
    for n in b.GetNetsByNetcode().values():
        classe[n.GetNetCode()] = n.GetNetClassName()
    pads = [p for f in b.GetFootprints() for p in f.Pads() if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD]
    vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
    maus, termicos = [], []
    for v in vias:
        p = em_pad(b, v, pads)
        if p is None:
            continue
        (termicos if area_pad(p) > 3.0 else maus).append((v, p))
    print(f'{len(maus)} vias dentro ou encostadas a pads, {len(termicos)} em pads térmicos (ficam)')
    if os.environ.get('LISTAR'):
        for v, p in maus:
            x, y = loc(v.GetPosition())
            print(f'  {p.GetParent().GetReference()}.{p.GetNumber()} {p.GetNetname()} ({x:.2f}; {y:.2f})')
        return

    proibidas = [z for z in b.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
    sem_pistas = [z for z in b.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowTracks()]
    feitos, falhados = 0, []
    for v, pad in maus:
        rede = v.GetNetCode()
        hv = classe.get(rede) == 'HV'
        ox, oy = loc(v.GetPosition())
        vd = pcbnew.ToMM(v.GetWidth())
        fr = pcbnew.ToMM(v.GetDrill()) / 2
        # pistas ligadas ao ponto antigo, por camada
        ligadas = {}
        pontas = {}   # camada -> pontos das pistas dentro da via
        raio = v.GetWidth() / 2
        for t in b.GetTracks():
            if t.GetClass() == 'PCB_VIA' or t.GetNetCode() != rede:
                continue
            for e in (t.GetStart(), t.GetEnd()):
                if math.hypot(e.x - v.GetPosition().x, e.y - v.GetPosition().y) <= raio:
                    ligadas.setdefault(t.GetLayer(), []).append(t)
                    pontas.setdefault(t.GetLayer(), set()).add(loc(e))
        L_pad = pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
        pontas.setdefault(L_pad, set()).add((ox, oy))
        camadas_pista = set(pontas)
        # obstáculos (sem esta via)
        itens = []
        furos = []
        for t in b.GetTracks():
            if t is v or t.m_Uuid.AsString() == v.m_Uuid.AsString():
                continue
            if t.GetClass() == 'PCB_VIA':
                for L in CAMADAS:
                    itens.append((L, t.GetEffectiveShape(L), t.GetNetCode()))
                x, y = loc(t.GetPosition())
                furos.append((x, y, pcbnew.ToMM(t.GetDrill()) / 2, t.GetNetCode()))
            else:
                itens.append((t.GetLayer(), t.GetEffectiveShape(t.GetLayer()), t.GetNetCode()))
        for f in b.GetFootprints():
            for p in f.Pads():
                for L in CAMADAS:
                    if p.IsOnLayer(L):
                        itens.append((L, p.GetEffectiveShape(L), p.GetNetCode()))
                if p.GetDrillSize().x > 0:
                    x, y = loc(p.GetPosition())
                    furos.append((x, y, pcbnew.ToMM(p.GetDrillSize().x) / 2, p.GetNetCode()))

        caixa = pcbnew.BOX2I(P(ox - 4, oy - 4), pcbnew.VECTOR2I(mm(8), mm(8)))
        itens = [i for i in itens if i[1].BBox().Intersects(caixa)]
        perto = [p for p in pads if p.GetBoundingBox().Intersects(caixa)]

        def afast(r2, x, y):
            if r2 == rede:
                return None
            if hv or classe.get(r2) == 'HV':
                return 0.16 if na_area_lm(x, y) else 0.62
            return max(AFAST.get(classe.get(rede), 0.15), AFAST.get(classe.get(r2), 0.15)) + 0.03

        def livre(L, forma, x, y):
            for L2, f2, r2 in itens:
                if L2 != L:
                    continue
                a = afast(r2, x, y)
                if a is None:
                    continue
                if f2.Collide(forma, mm(a)):
                    return False
            return True

        sucesso = None
        cands = []
        for ix in range(-40, 41):
            for iy in range(-40, 41):
                d = math.hypot(ix, iy) * 0.1
                if 0.3 <= d <= 4.0:
                    cands.append((d, ox + ix * 0.1, oy + iy * 0.1))
        cands.sort()
        tamanhos = [(vd, fr)] + ([(0.5, 0.1)] if vd > 0.5 and os.environ.get('REDUZIR') else [])
        for d, nx, ny, (vd, fr) in [(d, x, y, s) for s in tamanhos for d, x, y in cands]:
            if not (1.0 < nx < W - 1.0 and 1.0 < ny < H - 1.0):
                continue
            c = pcbnew.SHAPE_CIRCLE(P(nx, ny), mm(vd / 2))
            if any(p.IsOnLayer(L) and p.GetEffectiveShape(L).Collide(c, mm(FOLGA_PAD))
                   for p in perto for L in (pcbnew.F_Cu, pcbnew.B_Cu)):
                continue
            if any(z.Outline().Contains(P(nx, ny)) for z in proibidas):
                continue
            if not all(livre(L, c, nx, ny) for L in CAMADAS):
                continue
            if any(math.hypot(fx - nx, fy - ny) - ffr - fr < (0.5 if fn != rede else 0.3) for fx, fy, ffr, fn in furos):
                continue
            ok = True
            pistas = []
            mover = []
            for L in camadas_pista:
                w = min([pcbnew.ToMM(t.GetWidth()) for t in ligadas.get(L, [])] or [0.6 if hv else 0.25])
                if L != L_pad:
                    # primeiro tenta levar a ponta da pista até à via nova (sem cunhas)
                    ok_m = True
                    for tr in ligadas.get(L, []):
                        a, c_ = tr.GetStart(), tr.GetEnd()
                        da = math.hypot(a.x - v.GetPosition().x, a.y - v.GetPosition().y)
                        dc = math.hypot(c_.x - v.GetPosition().x, c_.y - v.GetPosition().y)
                        fixo = loc(c_) if da < dc else loc(a)
                        s = pcbnew.SHAPE_SEGMENT(P(*fixo), P(nx, ny), tr.GetWidth())
                        if not livre(L, s, nx, ny):
                            ok_m = False
                            break
                        mover.append((tr, da < dc))
                    if ok_m:
                        continue
                    mover = [m for m in mover if m[0].GetLayer() != L]
                for ex, ey in pontas[L]:
                    s = pcbnew.SHAPE_SEGMENT(P(ex, ey), P(nx, ny), mm(w))
                    if not livre(L, s, nx, ny) or any(z.Outline().Collide(s) for z in sem_pistas):
                        ok = False
                        break
                    pistas.append((L, w, ex, ey))
                if not ok:
                    break
            if not ok:
                continue
            sucesso = (nx, ny, pistas, vd, fr, mover)
            break
        ref = f'{pad.GetParent().GetReference()}.{pad.GetNumber()}'
        if not sucesso:
            falhados.append((ref, pad.GetNetname(), ox, oy))
            continue
        nx, ny, pistas, vd, fr, mover = sucesso
        for tr, inicio in mover:
            (tr.SetStart if inicio else tr.SetEnd)(P(nx, ny))
        v.SetPosition(P(nx, ny))
        v.SetWidth(mm(vd))
        v.SetDrill(mm(2 * fr))
        for L, w, ex, ey in pistas:
            t = pcbnew.PCB_TRACK(b)
            t.SetStart(P(ex, ey))
            t.SetEnd(P(nx, ny))
            t.SetWidth(mm(w))
            t.SetLayer(L)
            t.SetNet(v.GetNet())
            b.Add(t)
        feitos += 1
        print(f'  {ref:8s} {pad.GetNetname().split("/")[-1]:12s} ({ox:.2f}; {oy:.2f}) -> ({nx:.2f}; {ny:.2f}), '
              f'{math.hypot(nx - ox, ny - oy):.2f} mm, pistas em {len(pistas)} camada(s)')
    print(f'{feitos} vias tiradas dos pads; ficaram {len(falhados)}:')
    for f in falhados:
        print('  ', f)
    pcbnew.SaveBoard(PCB, b)


if __name__ == '__main__':
    main()
