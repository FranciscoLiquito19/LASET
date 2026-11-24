"""Encaminhador em grelha (A*) para as ligações que o curtas.py não fez. Rascunho.

Uso:  python3 encaminhar.py      (depois de pcb.py, fanout.py e curtas.py)

Lê as ligações em falta no DRC do KiCad e encaminha cada uma numa grelha de 0,1 mm
em F.Cu e B.Cu, com vias quando é preciso mudar de camada. A grelha marca como ocupado
todo o ponto a menos de (meia largura + afastamento) de cobre de outra rede, as áreas
de isolamento, as zonas de potência em F.Cu e a margem ao bordo. O caminho é procurado
com A* e penalização das mudanças de direção (pistas a 0, 45 e 90 graus). No fim corre
o DRC e retira as pistas e vias que causem violações.

Não substitui a revisão: os pares Ethernet, o comando das portas dos MOSFET e tudo o
que é sensível a ruído deve ser revisto ou refeito à mão no KiCad.
"""
import heapq
import math
import os
import re
import sys
import tempfile
import time

import numpy as np
import pcbnew
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcb import PCB, OX, OY, W, H, BARREIRA, ISO, POTENCIA  # noqa: E402
from fanout import plano, PLANO_IN1  # noqa: E402

RES = 0.1                      # mm por célula
NX, NY = int(W / RES), int(H / RES)
BASE = 0.1 + 0.15 + 0.05       # meia pista de 0,2 mm + afastamento + margem de quantização
LARG = {'Default': 0.2, 'ETH': 0.25, 'BUS': 0.4, 'HV': 0.4, 'P5V': 0.4}
AFAST = {'Default': 0.15, 'ETH': 0.15, 'BUS': 0.3, 'HV': 0.6, 'P5V': 0.2}
VIA_D, VIA_F = 0.6, 0.3
CUSTO_VIA = 30.0               # em células (3 mm)
CUSTO_CURVA = 4.0
JANELA = float(os.environ.get('JANELA', 12.0))                 # mm à volta da caixa das duas pontas
LIMITE = [400000]
DIRS = [(1, 0), (1, 1), (0, 1), (-1, 1), (-1, 0), (-1, -1), (0, -1), (1, -1)]


def mm(v):
    return pcbnew.FromMM(float(v))


def loc(p):
    return pcbnew.ToMM(p.x) - OX, pcbnew.ToMM(p.y) - OY


class Grelha:
    def __init__(self):
        self.dono = [np.zeros((NY, NX), np.int32) for _ in range(2)]   # 0 livre, -1 bloqueado, k rede
        self.nucleo = [np.zeros((NY, NX), np.int32) for _ in range(2)]
        self.netcode_classe = {}

    def _janela(self, x0, y0, x1, y1, r):
        i0, i1 = max(0, int((x0 - r) / RES) - 1), min(NX, int((x1 + r) / RES) + 2)
        j0, j1 = max(0, int((y0 - r) / RES) - 1), min(NY, int((y1 + r) / RES) + 2)
        xs = (np.arange(i0, i1) + 0.5) * RES
        ys = (np.arange(j0, j1) + 0.5) * RES
        return i0, i1, j0, j1, xs, ys

    def retangulo(self, camada, rede, x0, y0, x1, y1, r):
        """Cobre retangular da rede (k > 0) com raio de influência r."""
        i0, i1, j0, j1, xs, ys = self._janela(x0, y0, x1, y1, r)
        if i0 >= i1 or j0 >= j1:
            return
        dx = np.maximum(np.maximum(x0 - xs, xs - x1), 0)[None, :]
        dy = np.maximum(np.maximum(y0 - ys, ys - y1), 0)[:, None]
        d = np.hypot(dx, dy)
        self._marcar(camada, rede, i0, i1, j0, j1, d <= r, d <= 0)

    def segmento(self, camada, rede, xa, ya, xb, yb, w, r):
        i0, i1, j0, j1, xs, ys = self._janela(min(xa, xb), min(ya, yb), max(xa, xb), max(ya, yb), r + w / 2)
        if i0 >= i1 or j0 >= j1:
            return
        X, Y = np.meshgrid(xs, ys)
        vx, vy = xb - xa, yb - ya
        L2 = vx * vx + vy * vy
        u = np.zeros_like(X) if L2 == 0 else np.clip(((X - xa) * vx + (Y - ya) * vy) / L2, 0, 1)
        d = np.hypot(X - (xa + u * vx), Y - (ya + u * vy)) - w / 2
        self._marcar(camada, rede, i0, i1, j0, j1, d <= r, d <= 0)

    def _marcar(self, camada, rede, i0, i1, j0, j1, zona, nucleo):
        for c in ((0, 1) if camada is None else (camada,)):
            dono = self.dono[c][j0:j1, i0:i1]
            if rede < 0:
                dono[zona] = -1
                continue
            livre = zona & (dono == 0)
            outro = zona & (dono != 0) & (dono != rede)
            dono[livre] = rede
            dono[outro] = -1
            if nucleo is not None:
                self.nucleo[c][j0:j1, i0:i1][nucleo] = rede

    def poligono(self, camada, rede, pts, r):
        xs_, ys_ = [p[0] for p in pts], [p[1] for p in pts]
        i0, i1, j0, j1, xs, ys = self._janela(min(xs_), min(ys_), max(xs_), max(ys_), r)
        X, Y = np.meshgrid(xs, ys)
        dentro = np.zeros(X.shape, bool)
        n = len(pts)
        for k in range(n):
            (xa, ya), (xb, yb) = pts[k], pts[(k + 1) % n]
            cruza = ((ya > Y) != (yb > Y)) & (X < (xb - xa) * (Y - ya) / (yb - ya + 1e-12) + xa)
            dentro ^= cruza
        d = ndimage.distance_transform_edt(~dentro) * RES
        self._marcar(camada, rede, i0, i1, j0, j1, d <= r, dentro)


def carregar(b):
    g = Grelha()
    for f in b.GetFootprints():
        for p in f.Pads():
            k = p.GetNetCode()
            bb = p.GetBoundingBox()
            x0, y0 = pcbnew.ToMM(bb.GetX()) - OX, pcbnew.ToMM(bb.GetY()) - OY
            x1, y1 = pcbnew.ToMM(bb.GetRight()) - OX, pcbnew.ToMM(bb.GetBottom()) - OY
            r = BASE + AFAST.get(p.GetNetClassName(), 0.15) - 0.15
            for c, cam in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)):
                if p.IsOnLayer(cam):
                    g.retangulo(c, k if k > 0 else -1, x0, y0, x1, y1, r)
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                g.retangulo(None, -1, x0, y0, x1, y1, BASE + 0.1)
    for t in b.GetTracks():
        k = t.GetNetCode()
        if t.GetClass() == 'PCB_VIA':
            x, y = loc(t.GetPosition())
            rr = pcbnew.ToMM(t.GetWidth()) / 2
            g.segmento(None, k, x, y, x, y, 2 * rr, BASE + AFAST.get(t.GetNetClassName(), 0.15) - 0.15)
        else:
            (xa, ya), (xb, yb) = loc(t.GetStart()), loc(t.GetEnd())
            c = 0 if t.GetLayer() == pcbnew.F_Cu else 1
            g.segmento(c, k, xa, ya, xb, yb, pcbnew.ToMM(t.GetWidth()), BASE + AFAST.get(t.GetNetClassName(), 0.15) - 0.15)
    # zonas de potência em F.Cu (contorno inteiro, conservador)
    for rede, pts in POTENCIA:
        net = b.FindNet(rede)
        g.poligono(0, net.GetNetCode(), pts, BASE + 0.45)
    # áreas de isolamento e margem ao bordo
    g.retangulo(None, -1, 0, BARREIRA[0], W, BARREIRA[1], 0.3)
    xs = sorted(ISO.values())
    for (a0, a1), (b0, b1) in zip(xs, xs[1:]):
        g.retangulo(None, -1, a1, BARREIRA[1], b0, H, 0.3)
    for c in (0, 1):
        m = int(0.7 / RES)
        g.dono[c][:m, :] = g.dono[c][-m:, :] = g.dono[c][:, :m] = g.dono[c][:, -m:] = -1
    return g


def faltas(b):
    """Ligações em falta, pelo relatório do DRC: [(rede, ponto A, ponto B)]."""
    with tempfile.TemporaryDirectory() as d:
        rpt = os.path.join(d, 'drc.rpt')
        pcbnew.WriteDRCReport(b, rpt, pcbnew.EDA_UNITS_MILLIMETRES, True)
        t = open(rpt, encoding='utf-8').read()
    out = []
    for bloco in re.split(r'\n(?=\[)', t):
        if not bloco.startswith('[unconnected_items]'):
            continue
        it = re.findall(r'@\(([\d.]+) mm, ([\d.]+) mm\): (\w+)[^\[]*\[([^\]]*)\]', bloco)
        if len(it) != 2 or 'Zone' in (it[0][2], it[1][2]):
            continue
        a, c = it
        out.append((a[3], (float(a[0]) - OX, float(a[1]) - OY, a[2]), (float(c[0]) - OX, float(c[1]) - OY, c[2])))
    return out


def celulas_item(b, g, rede_code, ponto):
    """Células de núcleo da rede junto ao ponto (o pad ou a pista que lá está)."""
    x, y, tipo = ponto
    i, j = int(x / RES), int(y / RES)
    out = []
    r = 1 if tipo != 'Pad' else 0
    if tipo == 'Pad':
        for f in b.GetFootprints():
            for p in f.Pads():
                if p.GetNetCode() == rede_code and math.dist(loc(p.GetPosition()), (x, y)) < 0.01:
                    bb = p.GetBoundingBox()
                    x0, y0 = pcbnew.ToMM(bb.GetX()) - OX, pcbnew.ToMM(bb.GetY()) - OY
                    x1, y1 = pcbnew.ToMM(bb.GetRight()) - OX, pcbnew.ToMM(bb.GetBottom()) - OY
                    for c, cam in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)):
                        if not p.IsOnLayer(cam):
                            continue
                        for jj in range(max(0, int(y0 / RES)), min(NY, int(y1 / RES) + 1)):
                            for ii in range(max(0, int(x0 / RES)), min(NX, int(x1 / RES) + 1)):
                                cx, cy = (ii + 0.5) * RES, (jj + 0.5) * RES
                                if x0 <= cx <= x1 and y0 <= cy <= y1:
                                    out.append((c, jj, ii))
                    return out, (x, y)
    for c in (0, 1):
        for jj in range(j - r - 1, j + r + 2):
            for ii in range(i - r - 1, i + r + 2):
                if 0 <= jj < NY and 0 <= ii < NX and g.nucleo[c][jj, ii] == rede_code:
                    out.append((c, jj, ii))
    return out, (x, y)


def procurar(g, k, origem, destino, extra, via_ok, rede_plano=None):
    """A* com estado (camada, j, i, direção). Com rede_plano, o destino é qualquer
    célula de F.Cu onde caiba uma via sobre o plano dessa rede (até 4 mm da origem)."""
    if rede_plano:
        c0, j, i = origem[0]
        destino = [(0, j + dj, i + di) for dj in range(-40, 41, 2) for di in range(-40, 41, 2)
                   if 0 <= j + dj < NY and 0 <= i + di < NX
                   and plano(rede_plano, (i + di + 0.5) * RES, (j + dj + 0.5) * RES) is not None]
        if not destino:
            return None
    todas = origem + destino
    js = [c[1] for c in todas]
    is_ = [c[2] for c in todas]
    m = int(JANELA / RES)
    j0, j1 = max(0, min(js) - m), min(NY, max(js) + m + 1)
    i0, i1 = max(0, min(is_) - m), min(NX, max(is_) + m + 1)
    passa = []
    for c in (0, 1):
        d = g.dono[c][j0:j1, i0:i1]
        # o próprio cobre só conta onde também está longe do cobre das outras redes
        livre = (d == 0) | (d == k)
        if extra > 0:
            livre &= ~ndimage.binary_dilation(~livre, structure=ndimage.generate_binary_structure(2, 2), iterations=extra)
        passa.append(livre)
    # onde pode haver via: livre nas duas camadas num raio de 2 células e fora do núcleo de outros
    rv = int(round((VIA_D / 2 - LARG['Default'] / 2) / RES))
    est = ndimage.generate_binary_structure(2, 2)
    vias = ndimage.binary_erosion(passa[0] & passa[1], structure=est, iterations=rv) if via_ok or rede_plano else None
    alvo = {(c, j - j0, i - i0) for c, j, i in destino
            if j0 <= j < j1 and i0 <= i < i1 and passa[c][j - j0, i - i0]
            and (not rede_plano or vias[j - j0, i - i0])}
    if not alvo:
        return None
    tj = [a[1] for a in alvo]
    ti = [a[2] for a in alvo]
    tjm, tim = sum(tj) / len(tj), sum(ti) / len(ti)

    def h(j, i):
        dj, di = abs(j - tjm), abs(i - tim)
        return max(dj, di) + 0.414 * min(dj, di)

    abertos = []
    melhor = {}
    pai = {}
    for c, j, i in origem:
        jj, ii = j - j0, i - i0
        if 0 <= jj < j1 - j0 and 0 <= ii < i1 - i0 and passa[c][jj, ii]:
            s = (c, jj, ii, 8)
            melhor[s] = 0.0
            heapq.heappush(abertos, (h(jj, ii), 0.0, s))
    nj, ni = j1 - j0, i1 - i0
    visitados = 0
    while abertos:
        f, gc, s = heapq.heappop(abertos)
        if gc > melhor.get(s, 1e18):
            continue
        c, j, i, dr = s
        if (c, j, i) in alvo:
            caminho = [(c, j + j0, i + i0)]
            while s in pai:
                s = pai[s]
                caminho.append((s[0], s[1] + j0, s[2] + i0))
            return caminho[::-1]
        visitados += 1
        if visitados > LIMITE[0]:
            return None
        for nd, (di, dj) in enumerate(DIRS):
            jj, ii = j + dj, i + di
            if not (0 <= jj < nj and 0 <= ii < ni) or not passa[c][jj, ii]:
                continue
            custo = gc + (1.414 if di and dj else 1.0) + (CUSTO_CURVA if dr != 8 and nd != dr else 0)
            t = (c, jj, ii, nd)
            if custo < melhor.get(t, 1e18):
                melhor[t] = custo
                pai[t] = s
                heapq.heappush(abertos, (custo + h(jj, ii), custo, t))
        if vias is not None and vias[j, i]:
            t = (1 - c, j, i, 8)
            custo = gc + CUSTO_VIA
            if custo < melhor.get(t, 1e18):
                melhor[t] = custo
                pai[t] = s
                heapq.heappush(abertos, (custo + h(j, i), custo, t))
    return None


def desenhar(b, g, net, caminho, w, pa, pb):
    """Converte o caminho de células em pistas e vias; devolve o número de vias."""
    k = net.GetNetCode()
    R = BASE + AFAST.get(net.GetNetClassName(), 0.15) - 0.15
    pts = [(c, (i + 0.5) * RES, (j + 0.5) * RES) for c, j, i in caminho]
    # juntar troços colineares
    segs = []
    inicio = pts[0]
    for a, bb, cc in zip(pts, pts[1:], pts[2:]):
        if a[0] != bb[0] or bb[0] != cc[0]:
            continue
    novos = [pts[0]]
    for idx in range(1, len(pts) - 1):
        a, m_, c = novos[-1], pts[idx], pts[idx + 1]
        if m_[0] != a[0] or c[0] != m_[0]:
            novos.append(m_)
            continue
        d1 = (np.sign(round((m_[1] - a[1]) / RES)), np.sign(round((m_[2] - a[2]) / RES)))
        d2 = (np.sign(round((c[1] - m_[1]) / RES)), np.sign(round((c[2] - m_[2]) / RES)))
        if d1 != d2:
            novos.append(m_)
    novos.append(pts[-1])
    nv = 0
    itens = []
    camadas = (pcbnew.F_Cu, pcbnew.B_Cu)
    # ligar do centro do pad à primeira e última célula
    if pa:
        novos.insert(0, (novos[0][0], pa[0], pa[1]))
    if pb:
        novos.append((novos[-1][0], pb[0], pb[1]))
    for a, c in zip(novos, novos[1:]):
        if a[0] != c[0]:
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(pcbnew.VECTOR2I(mm(OX + a[1]), mm(OY + a[2])))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetWidth(mm(VIA_D))
            v.SetDrill(mm(VIA_F))
            v.SetNet(net)
            b.Add(v)
            g.segmento(None, k, a[1], a[2], a[1], a[2], VIA_D, R)
            itens.append(('V', None, (a[1], a[2]), (a[1], a[2])))
            nv += 1
            continue
        if math.dist((a[1], a[2]), (c[1], c[2])) < 1e-6:
            continue
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(pcbnew.VECTOR2I(mm(OX + a[1]), mm(OY + a[2])))
        t.SetEnd(pcbnew.VECTOR2I(mm(OX + c[1]), mm(OY + c[2])))
        t.SetWidth(mm(w))
        t.SetLayer(camadas[a[0]])
        t.SetNet(net)
        b.Add(t)
        g.segmento(a[0], k, a[1], a[2], c[1], c[2], w, R)
        itens.append(('T', a[0], (a[1], a[2]), (c[1], c[2])))
    vs = [i[2] for i in itens if i[0] == 'V']
    ok = all(math.dist(p, q) >= VIA_D + 0.3 for n_, p in enumerate(vs) for q in vs[n_ + 1:])
    return nv, itens, ok


def dist_seg(p, a, c):
    vx, vy = c[0] - a[0], c[1] - a[1]
    L2 = vx * vx + vy * vy
    u = 0 if L2 == 0 else max(0, min(1, ((p[0] - a[0]) * vx + (p[1] - a[1]) * vy) / L2))
    return math.dist(p, (a[0] + u * vx, a[1] + u * vy))


def retirar_rotas(rotas):
    """DRC: retira inteiras as rotas desta ronda que tenham violações de cobre."""
    for volta in range(4):
        b = pcbnew.LoadBoard(PCB)
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
        with tempfile.TemporaryDirectory() as dd:
            rpt = os.path.join(dd, 'drc.rpt')
            pcbnew.WriteDRCReport(b, rpt, pcbnew.EDA_UNITS_MILLIMETRES, False)
            t = open(rpt, encoding='utf-8').read()
        maus = []
        for bloco in re.split(r'\n(?=\[)', t):
            if re.match(r'\[(clearance|shorting_items|tracks_crossing|copper_edge_clearance|solder_mask_bridge|'
                        r'via_dangling|track_dangling|hole_clearance|hole_near_hole|holes_co_located|items_not_allowed)\]', bloco):
                for x, y, rede in re.findall(r'@\(([\d.]+) mm, ([\d.]+) mm\): (?:Track|Via) \[([^\]]*)\]', bloco):
                    maus.append((float(x) - OX, float(y) - OY, rede))
        if not maus:
            return
        mas = set()
        for n, (rede, itens) in enumerate(rotas):
            for x, y, r in maus:
                if r == rede and any(dist_seg((x, y), i[2], i[3]) < 0.3 for i in itens):
                    mas.add(n)
        if not mas:
            return
        alvo = {}
        for n in mas:
            rede, itens = rotas[n]
            for i in itens:
                alvo.setdefault(rede, []).append(i)
        removidos = 0
        for it in list(b.GetTracks()):
            rede = it.GetNetname()
            if rede not in alvo:
                continue
            if it.GetClass() == 'PCB_VIA':
                p = loc(it.GetPosition())
                if any(i[0] == 'V' and math.dist(p, i[2]) < 0.01 for i in alvo[rede]):
                    b.Remove(it)
                    removidos += 1
            else:
                a_, c_ = loc(it.GetStart()), loc(it.GetEnd())
                if any(i[0] == 'T' and math.dist(a_, i[2]) < 0.01 and math.dist(c_, i[3]) < 0.01 for i in alvo[rede]):
                    b.Remove(it)
                    removidos += 1
        rotas[:] = [r for n, r in enumerate(rotas) if n not in mas]
        pcbnew.SaveBoard(PCB, b)
        print(f'  retiradas {len(mas)} rotas com violações ({removidos} pistas/vias)')


def limpar():
    """DRC: retira pistas e vias com violações de cobre e as que ficarem penduradas."""
    for volta in range(8):
        b = pcbnew.LoadBoard(PCB)
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
        with tempfile.TemporaryDirectory() as dd:
            rpt = os.path.join(dd, 'drc.rpt')
            pcbnew.WriteDRCReport(b, rpt, pcbnew.EDA_UNITS_MILLIMETRES, False)
            t = open(rpt, encoding='utf-8').read()
        maus = []
        for bloco in re.split(r'\n(?=\[)', t):
            if re.match(r'\[(clearance|shorting_items|tracks_crossing|copper_edge_clearance|solder_mask_bridge|'
                        r'via_dangling|track_dangling|hole_clearance|hole_near_hole|holes_co_located|items_not_allowed)\]', bloco):
                maus += [(float(x), float(y)) for x, y in re.findall(r'@\(([\d.]+) mm, ([\d.]+) mm\): (?:Track|Via)', bloco)]
        if not maus:
            return
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
                px, py = pcbnew.FromMM(x), pcbnew.FromMM(y)
                dx, dy = e.x - s.x, e.y - s.y
                L2 = dx * dx + dy * dy
                u = 0 if L2 == 0 else max(0, min(1, ((px - s.x) * dx + (py - s.y) * dy) / L2))
                if math.hypot(px - (s.x + u * dx), py - (s.y + u * dy)) < pcbnew.FromMM(0.05) + it.GetWidth() / 2:
                    b.Remove(it)
                    n += 1
                    break
        pcbnew.SaveBoard(PCB, b)
        print(f'  limpeza {volta + 1}: retiradas {n} pistas/vias')


def main():
    inicio = time.time()
    for ronda in range(int(os.environ.get('RONDAS', 4))):
        b = pcbnew.LoadBoard(PCB)
        pcbnew.ZONE_FILLER(b).Fill(b.Zones())
        lista = faltas(b)
        print(f'ronda {ronda + 1}: {len(lista)} ligações em falta')
        LIMITE[0] = int(os.environ.get('LIMITE', 400000 if ronda == 0 else 1500000))
        if not lista:
            break
        g = carregar(b)
        feitas = vias = 0
        rotas = []
        lista.sort(key=lambda r: math.dist(r[1][:2], r[2][:2]))
        for rede, a, c in lista:
            net = b.FindNet(rede)
            if net is None:
                continue
            k = net.GetNetCode()
            classe = net.GetNetClassName()
            w = LARG.get(classe, 0.2)
            extra = int(math.ceil(max(0.0, (w / 2 + AFAST.get(classe, 0.15)) - (0.1 + 0.15)) / RES))
            if rede in ('+3V3', '+5V') or rede in PLANO_IN1:
                # pino de plano sem via: liga-o a uma via nova sobre o plano
                ponto = a if a[2] == 'Pad' else c
                if ponto[2] != 'Pad' or plano(rede, ponto[0], ponto[1]) is None:
                    continue
                orig, pa = celulas_item(b, g, k, ponto)
                if not orig:
                    continue
                cam = procurar(g, k, orig, [], 0, False, rede_plano=rede)
                if cam is None:
                    continue
                cam = cam + [(1, cam[-1][1], cam[-1][2])]   # termina numa via
                nv, itens, ok = desenhar(b, g, net, cam, 0.2, pa, None)
                rotas.append((rede, itens))
                feitas += 1
                continue
            orig, pa = celulas_item(b, g, k, a)
            dest, pb = celulas_item(b, g, k, c)
            if not orig or not dest:
                continue
            cam = procurar(g, k, orig, dest, extra, True)
            if cam is None:
                continue
            nv, itens, ok = desenhar(b, g, net, cam, w, pa if a[2] == 'Pad' else None, pb if c[2] == 'Pad' else None)
            rotas.append((rede, itens))
            vias += nv
            feitas += 1
        pcbnew.SaveBoard(PCB, b)
        print(f'  {feitas} encaminhadas, {vias} vias ({time.time() - inicio:.0f} s)')
        retirar_rotas(rotas)
        if feitas == 0:
            break
    b = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(PCB, b)
    print(f'em falta: {len(faltas(b))}')


if __name__ == '__main__':
    main()
