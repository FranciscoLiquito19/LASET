"""Passa condensadores de desacoplamento para a face de baixo, por baixo do pino.

Uso:  python3 baixo.py C34:57.95,50.75 C35:54.55,64.85 ...

Cada argumento é a referência do condensador e o ponto de ancoragem (uma via da rede de
alimentação do pino, em mm relativos à origem da placa). O condensador é virado para B.Cu
e posto no sítio livre mais perto da via: o pad da rede liga à via por uma pista curta em
B.Cu e o pad de massa recebe uma via nova para o plano de massa (In1). Não há vias dentro
de pads, nem cobre de outras redes a menos de 0,25 mm.

A ligação antiga em F.Cu não é apagada aqui (no KiCad 7 apagar e reutilizar objetos
corrompe a memória): o script grava a placa e escreve em baixo.lista os uuid das pistas e
vias que ficaram penduradas, que se retiram depois editando o texto do ficheiro.
"""
import math
import tempfile
import os
import sys

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcb import PCB, OX, OY, W, H  # noqa: E402

AF = 0.25          # afastamento a cobre de outras redes
AF_VIA_PAD = 0.15  # via afastada de qualquer pad SMD (nada de vias dentro de pads)
VIA, FURO = 0.6, 0.3
PISTA = 0.3
CAMADAS = (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu)


def mm(v):
    return pcbnew.FromMM(float(v))


def P(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def loc(p):
    return pcbnew.ToMM(p.x) - OX, pcbnew.ToMM(p.y) - OY


def seg(a, b, w):
    return pcbnew.SHAPE_SEGMENT(P(*a), P(*b), mm(w))


def circ(c, d):
    return pcbnew.SHAPE_CIRCLE(P(*c), mm(d / 2))


class Obst:
    def __init__(self, b, ignorar):
        self.b = b
        self.itens = []   # (camada, forma, rede, tipo)
        self.furos = []   # (x, y, r, rede)
        self.pads_smd = []
        for t in b.GetTracks():
            if t.GetClass() == 'PCB_VIA':
                x, y = loc(t.GetPosition())
                for L in CAMADAS:
                    self.itens.append((L, t.GetEffectiveShape(L), t.GetNetCode(), 'via'))
                self.furos.append((x, y, pcbnew.ToMM(t.GetDrill()) / 2, t.GetNetCode()))
            else:
                self.itens.append((t.GetLayer(), t.GetEffectiveShape(t.GetLayer()), t.GetNetCode(), 'pista'))
        for f in b.GetFootprints():
            if f.GetReference() in ignorar:
                continue
            for p in f.Pads():
                for L in CAMADAS:
                    if p.IsOnLayer(L):
                        self.itens.append((L, p.GetEffectiveShape(L), p.GetNetCode(), 'pad'))
                if p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
                    self.pads_smd.append(p)
                if p.GetDrillSize().x > 0:
                    x, y = loc(p.GetPosition())
                    self.furos.append((x, y, pcbnew.ToMM(p.GetDrillSize().x) / 2, p.GetNetCode()))
        self.proibidas = [z for z in b.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
        self.sem_cobre = [z for z in b.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowTracks()]
        self.crt_b = []
        for f in b.GetFootprints():
            if f.GetReference() in ignorar:
                continue
            f.BuildCourtyardCaches()
            c = f.GetCourtyard(pcbnew.B_CrtYd)
            if c.OutlineCount():
                self.crt_b.append(c)

    def livre(self, L, forma, rede, af=AF, sem_vias=False):
        for L2, f2, r2, tipo in self.itens:
            if L2 != L:
                continue
            if r2 == rede and not (sem_vias and tipo == 'via'):
                continue
            if f2.Collide(forma, mm(af if r2 != rede else 0.1)):
                return False
        return True

    def via_livre(self, x, y, rede):
        if not (1.0 < x < W - 1.0 and 1.0 < y < H - 1.0):
            return False
        c = circ((x, y), VIA)
        for L in CAMADAS:
            if not self.livre(L, c, rede):
                return False
        for p in self.pads_smd:   # nunca dentro nem encostada a um pad
            for L in (pcbnew.F_Cu, pcbnew.B_Cu):
                if p.IsOnLayer(L) and p.GetEffectiveShape(L).Collide(c, mm(AF_VIA_PAD)):
                    return False
        for fx, fy, fr, fn in self.furos:
            if math.hypot(fx - x, fy - y) - fr - FURO / 2 < (0.5 if fn != rede else 0.3):
                return False
        for z in self.proibidas:
            if z.Outline().Contains(P(x, y)):
                return False
        return True


def colocar(b, ref, ax, ay, ob):
    f = b.FindFootprintByReference(ref)
    if not f.IsFlipped():
        f.Flip(f.GetPosition(), False)
    pads = list(f.Pads())
    rede_v = [p for p in pads if p.GetNetname() != 'GND'][0]
    gnd = [p for p in pads if p.GetNetname() == 'GND'][0]
    rv, rg = rede_v.GetNetCode(), gnd.GetNetCode()
    melhor = None
    for ang in (0, 90, 180, 270):
        f.SetOrientationDegrees(ang)
        for k in range(0, 41):
            raio = 0.6 + k * 0.08
            for j in range(24):
                th = 2 * math.pi * j / 24
                # posição do pad da rede; o centro da peça desloca-se em conformidade
                px, py = ax + raio * math.cos(th), ay + raio * math.sin(th)
                f.SetPosition(P(0, 0))
                dx, dy = loc(rede_v.GetPosition())
                f.SetPosition(P(px - dx, py - dy))
                fx, fy = loc(f.GetPosition())
                if not (1.5 < fx < W - 1.5 and 1.5 < fy < H - 1.5):
                    continue
                ok = True
                for p in pads:
                    s = p.GetEffectiveShape(pcbnew.B_Cu)
                    if not ob.livre(pcbnew.B_Cu, s, p.GetNetCode(), sem_vias=True):
                        ok = False
                        break
                if not ok:
                    continue
                if any(z.Outline().Collide(p.GetEffectiveShape(pcbnew.B_Cu)) for z in ob.sem_cobre for p in pads):
                    continue
                f.BuildCourtyardCaches()
                cy = f.GetCourtyard(pcbnew.B_CrtYd)
                if any(cy.Collide(c) for c in ob.crt_b):
                    continue
                # pista da via ao pad da rede
                if not ob.livre(pcbnew.B_Cu, seg((ax, ay), (px, py), PISTA), rv):
                    continue
                # via de massa: para fora do pad de massa, longe do pad da rede
                gx, gy = loc(gnd.GetPosition())
                ux, uy = gx - px, gy - py
                n = math.hypot(ux, uy) or 1
                ux, uy = ux / n, uy / n
                via = None
                for d in (1.0, 1.15, 1.3, 1.5, 1.7):
                    for da in (0, 30, -30, 60, -60, 90, -90):
                        a = math.atan2(uy, ux) + math.radians(da)
                        vx, vy = gx + d * math.cos(a), gy + d * math.sin(a)
                        if math.hypot(vx - px, vy - py) < 1.2:
                            continue
                        if not ob.via_livre(vx, vy, rg):
                            continue
                        if not ob.livre(pcbnew.B_Cu, seg((gx, gy), (vx, vy), PISTA), rg):
                            continue
                        via = (vx, vy)
                        break
                    if via:
                        break
                if not via:
                    continue
                custo = raio + 0.3 * math.hypot(via[0] - gx, via[1] - gy)
                if melhor is None or custo < melhor[0]:
                    melhor = (custo, ang, (fx, fy), (px, py), via)
            if melhor and raio > melhor[0] + 0.5:
                break
    if not melhor:
        print(ref, 'sem lugar livre em B.Cu')
        return None
    _, ang, (fx, fy), (px, py), (vx, vy) = melhor
    f.SetOrientationDegrees(ang)
    f.SetPosition(P(fx, fy))
    f.Reference().SetVisible(False)
    gx, gy = loc(gnd.GetPosition())
    for a_, b_, net in (((ax, ay), (px, py), rede_v.GetNet()), ((gx, gy), (vx, vy), gnd.GetNet())):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(P(*a_))
        t.SetEnd(P(*b_))
        t.SetWidth(mm(PISTA))
        t.SetLayer(pcbnew.B_Cu)
        t.SetNet(net)
        b.Add(t)
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(P(vx, vy))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetWidth(mm(VIA))
    v.SetDrill(mm(FURO))
    v.SetNet(gnd.GetNet())
    b.Add(v)
    print(f'{ref}: B.Cu em ({fx:.2f}; {fy:.2f}) a {ang}°, pad da rede a {math.hypot(px - ax, py - ay):.2f} mm da via, '
          f'via de massa em ({vx:.2f}; {vy:.2f})')
    return f


def ancoras(b, alvo, ob):
    """Vias candidatas para o pino 'U3.106': vias da rede a menos de 1,6 mm e vias novas
    no eixo do pad, para dentro e para fora do componente, com a pista em F.Cu."""
    ref, num = alvo.split('.')
    f = b.FindFootprintByReference(ref)
    pad = [p for p in f.Pads() if p.GetNumber() == num][0]
    px, py = loc(pad.GetPosition())
    cx, cy = loc(f.GetPosition())
    rede = pad.GetNetCode()
    cands = []
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA' and t.GetNetCode() == rede:
            vx, vy = loc(t.GetPosition())
            if math.hypot(vx - px, vy - py) < 1.6 and not pad.HitTest(t.GetPosition()) and not os.environ.get('ANCORA'):
                cands.append((math.hypot(vx - px, vy - py), vx, vy, None))
    sx, sy = pad.GetSize().x, pad.GetSize().y
    eixo = (1, 0) if abs(px - cx) > abs(py - cy) else (0, 1)
    meio = max(pcbnew.ToMM(sx), pcbnew.ToMM(sy)) / 2
    dentro = -1 if (px - cx) * eixo[0] + (py - cy) * eixo[1] > 0 else 1
    sinais = {'dentro': (dentro,), 'fora': (-dentro,)}.get(os.environ.get('ANCORA', ''), (-1, 1))
    for sinal in sinais:
        for d in (0.75, 0.9, 1.05, 1.2, 1.4, 1.6, 1.8):
            vx, vy = px + sinal * eixo[0] * (meio + d - 0.45), py + sinal * eixo[1] * (meio + d - 0.45)
            if not ob.via_livre(vx, vy, rede):
                continue
            ex, ey = px + sinal * eixo[0] * (meio - 0.1), py + sinal * eixo[1] * (meio - 0.1)
            if not ob.livre(pcbnew.F_Cu, seg((ex, ey), (vx, vy), 0.2), rede, af=0.17):
                continue
            cands.append((math.hypot(vx - px, vy - py), vx, vy, ((px, py), (vx, vy))))
            break
    return sorted(cands)


def main():
    pedidos = []
    for a in sys.argv[1:]:
        ref, xy = a.split(':')
        if ',' in xy:
            x, y = map(float, xy.split(','))
            pedidos.append((ref, x, y))
        else:
            pedidos.append((ref, xy, None))
    b = pcbnew.LoadBoard(PCB)
    # posições antigas dos pads (para encontrar o cobre que fica pendurado)
    antigos = []
    for ref, _, _ in pedidos:
        for p in b.FindFootprintByReference(ref).Pads():
            antigos.append((p.GetPosition().x, p.GetPosition().y, p.GetBoundingBox()))
    for ref, x, y in pedidos:
        ob = Obst(b, {ref})
        f = b.FindFootprintByReference(ref)
        pos0, ang0 = f.GetPosition(), f.GetOrientationDegrees()
        if y is not None:
            r = colocar(b, ref, x, y, ob)
        else:
            r = None
            for d, vx, vy, pista in ancoras(b, x, ob):
                r = colocar(b, ref, vx, vy, ob)
                if r:
                    print(f'  via de ancoragem em ({vx:.2f}; {vy:.2f}), {d:.2f} mm do pino {x}')
                    if pista:
                        rede = [p for p in r.Pads() if p.GetNetname() != 'GND'][0].GetNet()
                        v = pcbnew.PCB_VIA(b)
                        v.SetPosition(P(vx, vy))
                        v.SetViaType(pcbnew.VIATYPE_THROUGH)
                        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
                        v.SetWidth(mm(VIA))
                        v.SetDrill(mm(FURO))
                        v.SetNet(rede)
                        b.Add(v)
                        t = pcbnew.PCB_TRACK(b)
                        t.SetStart(P(*pista[0]))
                        t.SetEnd(P(*pista[1]))
                        t.SetWidth(mm(0.2))
                        t.SetLayer(pcbnew.F_Cu)
                        t.SetNet(rede)
                        b.Add(t)
                    break
        if r is None:
            if f.IsFlipped():
                f.Flip(f.GetPosition(), False)
            f.SetOrientationDegrees(ang0)
            f.SetPosition(pos0)
            print(ref, 'fica onde estava')
    # cobre em F.Cu que terminava nos pads antigos
    lista = []
    pontos = {}
    for t in b.GetTracks():
        ks = [(t.GetPosition().x, t.GetPosition().y)] if t.GetClass() == 'PCB_VIA' else \
             [(t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)]
        for k in ks:
            pontos.setdefault(k, []).append(t)
    pads_pts = [p for f in b.GetFootprints() for p in f.Pads()]
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA' or t.GetLayer() != pcbnew.F_Cu:
            continue
        for e in (t.GetStart(), t.GetEnd()):
            if any(bb.Contains(e) for _, _, bb in antigos):
                outros = [o for o in pontos[(e.x, e.y)] if o is not t]
                no_pad = any(p.GetParent().GetReference() not in [r for r, _, _ in pedidos] and p.HitTest(e)
                             for p in pads_pts)
                if not outros and not no_pad:
                    o = t.GetEnd() if e == t.GetStart() else t.GetStart()
                    lista.append((t.m_Uuid.AsString(), 'pista', loc(e), loc(o)))
    with open(os.path.join(tempfile.gettempdir(), 'baixo.lista'), 'w') as fh:
        for u, tipo, e, o in lista:
            fh.write(f'{u} {tipo} {e[0]:.2f},{e[1]:.2f} {o[0]:.2f},{o[1]:.2f}\n')
    print(f'{len(lista)} pistas penduradas em baixo.lista')
    pcbnew.SaveBoard(PCB, b)


if __name__ == '__main__':
    main()
