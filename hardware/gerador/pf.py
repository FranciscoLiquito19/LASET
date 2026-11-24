"""Encaminhamento por congestionamento negociado (PathFinder, McMurchie e Ebeling, 1995).

Uso:  python3 pf.py      (depois de pcb.py e fanout.py; substitui curtas.py e encaminhar.py)

Todas as ligações em falta são encaminhadas na grelha do encaminhar.py, mas o cobre
das outras rotas não bloqueia: só custa. Cada célula tem um custo de ocupação (quantas
outras redes a usam agora) e um custo histórico (quantas vezes esteve em conflito).
Em cada iteração as redes em conflito são arrancadas e refeitas, com o custo de
ocupação a subir; as redes acabam por se afastar das zonas disputadas e os conflitos
desaparecem. No fim a placa é escrita e o DRC do KiCad retira o que sobrar de
violações.

Variáveis: ITERACOES (30), JANELA, LIMITE, PESO_H (ver encaminhar.py).
"""
import heapq
import math
import os
import sys
import time

import numpy as np
import pcbnew
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import encaminhar as E  # noqa: E402

ITER = int(os.environ.get('ITERACOES', 30))
EST8 = ndimage.generate_binary_structure(2, 2)


class Rota:
    def __init__(self, rede, k, a, c):
        self.rede, self.k, self.a, self.c = rede, k, a, c
        self.cam = None
        self.mask = None
        self.plano = False


def disco(r):
    n = int(math.ceil(r / E.RES))
    yy, xx = np.mgrid[-n:n + 1, -n:n + 1]
    return (np.hypot(xx, yy) * E.RES <= r + 1e-9)


def mascara(rota, w, gd):
    """Zona de exclusão da rota para os eixos das outras: meia largura própria +
    afastamento + meia largura de uma pista normal (0,1 mm). Devolve também o eixo
    (as células por onde a rota passa, e um disco nas vias) para medir conflitos."""
    r = w / 2 + 0.15 + 0.1
    rv = E.VIA_D / 2 + 0.15 + 0.1
    pts = {0: [], 1: []}
    vias = []
    cam = rota.cam
    for n, (c, j, i) in enumerate(cam):
        # dentro do cobre da própria rede (o pad de partida ou de chegada) não ocupa
        if gd.nucleo[c][j, i] != rota.k:
            pts[c].append((j, i))
        if n and cam[n - 1][0] != c:
            vias.append((j, i))
    if rota.plano:
        vias.append(cam[-1][1:])
    out = {}
    for c in (0, 1):
        sel = pts[c] + vias
        if not sel:
            continue
        js = [p[0] for p in sel]
        is_ = [p[1] for p in sel]
        m = int(math.ceil(rv / E.RES)) + 1
        j0, i0 = max(0, min(js) - m), max(0, min(is_) - m)
        j1, i1 = min(E.NY, max(js) + m + 1), min(E.NX, max(is_) + m + 1)
        a = np.zeros((j1 - j0, i1 - i0), bool)
        for j, i in pts[c]:
            a[j - j0, i - i0] = True
        eixo = a.copy()
        a = ndimage.binary_dilation(a, structure=disco(r)) if a.any() else a
        if vias:
            b = np.zeros_like(a)
            for j, i in vias:
                b[j - j0, i - i0] = True
            a |= ndimage.binary_dilation(b, structure=disco(rv))
            eixo |= ndimage.binary_dilation(b, structure=disco(E.VIA_D / 2 - 0.1))
        out[c] = (j0, i0, a)
        EIXOS[(id(rota), c)] = (j0, i0, eixo)
    return out


EIXOS = {}


class Ocupacao:
    def __init__(self):
        self.occ = [np.zeros((E.NY, E.NX), np.int16) for _ in range(2)]
        self.hist = [np.zeros((E.NY, E.NX), np.float32) for _ in range(2)]

    def aplicar(self, mask, sinal):
        for c, (j0, i0, a) in mask.items():
            self.occ[c][j0:j0 + a.shape[0], i0:i0 + a.shape[1]] += sinal * a.astype(np.int16)


def procurar(gd, oc, k, origem, destino, extra, pres, rede_plano=None, proprias=()):
    if rede_plano:
        c0, j, i = origem[0]
        destino = [(0, j + dj, i + di) for dj in range(-40, 41, 2) for di in range(-40, 41, 2)
                   if 0 <= j + dj < E.NY and 0 <= i + di < E.NX
                   and E.plano(rede_plano, (i + di + 0.5) * E.RES, (j + dj + 0.5) * E.RES) is not None]
    todas = origem + destino
    if not destino:
        return None
    js = [c[1] for c in todas]
    is_ = [c[2] for c in todas]
    m = int(E.JANELA / E.RES)
    j0, j1 = max(0, min(js) - m), min(E.NY, max(js) + m + 1)
    i0, i1 = max(0, min(is_) - m), min(E.NX, max(is_) + m + 1)
    passa, custo = [], []
    for c in (0, 1):
        d = gd.dono[c][j0:j1, i0:i1]
        livre = (d == 0) | (d == k)
        if extra > 0:
            livre &= ~ndimage.binary_dilation(~livre, structure=EST8, iterations=extra)
        passa.append(livre)
        occ = oc.occ[c][j0:j1, i0:i1].astype(np.float32)
        for (pc, (pj0, pi0, a)) in proprias:      # as rotas da própria rede não contam
            if pc != c:
                continue
            jj0, ii0 = max(pj0, j0), max(pi0, i0)
            jj1, ii1 = min(pj0 + a.shape[0], j1), min(pi0 + a.shape[1], i1)
            if jj0 < jj1 and ii0 < ii1:
                occ[jj0 - j0:jj1 - j0, ii0 - i0:ii1 - i0] -= a[jj0 - pj0:jj1 - pj0, ii0 - pi0:ii1 - pi0]
        custo.append((1.0 + oc.hist[c][j0:j1, i0:i1]) * (1.0 + pres * np.maximum(occ, 0)) - 1.0)
    rv = int(round((E.VIA_D / 2 - 0.1) / E.RES))
    vias = ndimage.binary_erosion(passa[0] & passa[1], structure=EST8, iterations=rv) & ~gd.sem_via[j0:j1, i0:i1]
    alvo = {(c, j - j0, i - i0) for c, j, i in destino if j0 <= j < j1 and i0 <= i < i1 and passa[c][j - j0, i - i0]
            and (not rede_plano or vias[j - j0, i - i0])}
    if not alvo:
        return None
    tjm = sum(a[1] for a in alvo) / len(alvo)
    tim = sum(a[2] for a in alvo) / len(alvo)
    ph = E.PESO_H

    def h(j, i):
        dj, di = abs(j - tjm), abs(i - tim)
        return ph * (max(dj, di) + 0.414 * min(dj, di))

    abertos, melhor, pai = [], {}, {}
    for c, j, i in origem:
        jj, ii = j - j0, i - i0
        if 0 <= jj < j1 - j0 and 0 <= ii < i1 - i0 and passa[c][jj, ii]:
            s = (c, jj, ii, 8)
            melhor[s] = 0.0
            heapq.heappush(abertos, (h(jj, ii), 0.0, s))
    nj, ni = j1 - j0, i1 - i0
    vis = 0
    cv = E.CUSTO_VIA
    while abertos:
        f, gc, s = heapq.heappop(abertos)
        if gc > melhor.get(s, 1e18):
            continue
        c, j, i, dr = s
        if (c, j, i) in alvo:
            cam = [(c, j + j0, i + i0)]
            while s in pai:
                s = pai[s]
                cam.append((s[0], s[1] + j0, s[2] + i0))
            return cam[::-1]
        vis += 1
        if vis > E.LIMITE[0]:
            return None
        cc = custo[c]
        pc = passa[c]
        for nd, (di, dj) in enumerate(E.DIRS):
            jj, ii = j + dj, i + di
            if not (0 <= jj < nj and 0 <= ii < ni) or not pc[jj, ii]:
                continue
            passo = 1.414 if di and dj else 1.0
            cst = gc + passo * (1.0 + cc[jj, ii]) + (E.CUSTO_CURVA if dr != 8 and nd != dr else 0)
            t = (c, jj, ii, nd)
            if cst < melhor.get(t, 1e18):
                melhor[t] = cst
                pai[t] = s
                heapq.heappush(abertos, (cst + h(jj, ii), cst, t))
        if vias[j, i]:
            t = (1 - c, j, i, 8)
            cst = gc + cv * (1.0 + custo[0][j, i] + custo[1][j, i])
            if cst < melhor.get(t, 1e18):
                melhor[t] = cst
                pai[t] = s
                heapq.heappush(abertos, (cst + h(j, i), cst, t))
    return None


def proprio(r, por_rede, c, j0, j1, i0, i1):
    """Ocupação das outras rotas da mesma rede na janela (não contam como conflito)."""
    out = np.zeros((j1 - j0, i1 - i0), np.int16)
    for o in por_rede[r.k]:
        if o is r or not o.mask or c not in o.mask:
            continue
        pj0, pi0, a = o.mask[c]
        jj0, ii0 = max(pj0, j0), max(pi0, i0)
        jj1, ii1 = min(pj0 + a.shape[0], j1), min(pi0 + a.shape[1], i1)
        if jj0 < jj1 and ii0 < ii1:
            out[jj0 - j0:jj1 - j0, ii0 - i0:ii1 - i0] += a[jj0 - pj0:jj1 - pj0, ii0 - pi0:ii1 - pi0]
    return out


def conflitos(rotas, oc, por_rede, marcar_hist=False):
    """Rotas cuja máscara toca células usadas por outra rede."""
    mau = []
    for r in rotas:
        if not r.mask:
            continue
        ruim = False
        for c, (j0, i0, a) in r.mask.items():
            j1, i1 = j0 + a.shape[0], i0 + a.shape[1]
            outras = oc.occ[c][j0:j1, i0:i1] - a - proprio(r, por_rede, c, j0, j1, i0, i1)
            m = EIXOS[(id(r), c)][2] & (outras > 0)
            if m.any():
                ruim = True
                if marcar_hist:
                    oc.hist[c][j0:j1, i0:i1] += 0.3 * m
        if ruim:
            mau.append(r)
    return mau


def main():
    inicio = time.time()
    b = pcbnew.LoadBoard(E.PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    lista = E.faltas(b)
    gd = E.carregar(b)
    E.LIMITE[0] = int(os.environ.get('LIMITE', 1500000))
    rotas = []
    for rede, a, c in lista:
        net = b.FindNet(rede)
        if net is None:
            continue
        r = Rota(rede, net.GetNetCode(), a, c)
        classe = net.GetNetClassName()
        r.w = E.LARG.get(classe, 0.2)
        af = 0.15 if classe in ('HV', 'P5V') else E.AFAST.get(classe, 0.15)
        r.extra = int(math.ceil(round(max(0.0, (r.w / 2 + af) - (E.BASE - 0.04)) / E.RES, 6)))
        r.plano = False
        if rede in ('+3V3', '+5V') or rede in E.PLANO_IN1:
            p = a if a[2] == 'Pad' else c
            if p[2] == 'Pad' and E.plano(rede, p[0], p[1]) is not None:
                r.plano = True
                r.a, r.c = p, None
        if r.c is not None and r.a[2] == 'Zone':
            r.a, r.c = r.c, r.a
        r.cam = r.mask = r.pa = r.pb = None
        rotas.append(r)
    por_rede = {}
    for r in rotas:
        por_rede.setdefault(r.k, []).append(r)
    print(f'{len(rotas)} ligações ({time.time() - inicio:.0f} s)', flush=True)
    oc = Ocupacao()
    pres = 0.5
    por_fazer = sorted(rotas, key=lambda r: math.dist(r.a[:2], r.c[:2]) if r.c else 0)
    for it in range(ITER):
        sem = 0
        for r in por_fazer:
            if r.mask:
                oc.aplicar(r.mask, -1)
                r.mask = r.cam = None
            orig, r.pa = E.celulas_item(b, gd, r.k, r.a)
            dest, r.pb = ([], None) if r.plano else E.celulas_item(b, gd, r.k, r.c, outro=r.a)
            if not orig or (not dest and not r.plano):
                sem += 1
                continue
            js = [x[1] for x in orig + dest] or [orig[0][1]]
            is_ = [x[2] for x in orig + dest] or [orig[0][2]]
            m = int(E.JANELA / E.RES)
            proprias = []
            for o in por_rede[r.k]:
                if o is not r and o.mask:
                    proprias += [(c, v) for c, v in o.mask.items()]
            cam = procurar(gd, oc, r.k, orig, dest, r.extra, pres, r.rede if r.plano else None, proprias)
            if cam is None:
                sem += 1
                continue
            r.cam = cam
            r.mask = mascara(r, r.w, gd)
            oc.aplicar(r.mask, +1)
        maus = conflitos(rotas, oc, por_rede, marcar_hist=True)
        feitas = sum(1 for r in rotas if r.cam is not None)
        print(f'iteração {it + 1}: {feitas}/{len(rotas)} com caminho, {len(maus)} em conflito, '
              f'pres {pres:.1f} ({time.time() - inicio:.0f} s)', flush=True)
        if os.environ.get('DEBUG') and it % 4 == 3:
            for r in maus[:12]:
                for c, (j0, i0, a) in r.mask.items():
                    j1, i1 = j0 + a.shape[0], i0 + a.shape[1]
                    outras = oc.occ[c][j0:j1, i0:i1] - a - proprio(r, por_rede, c, j0, j1, i0, i1)
                    jj, ii = np.nonzero(a & (outras > 0))
                    if len(jj):
                        quem = set()
                        for o in rotas:
                            if o.k != r.k and o.mask and c in o.mask:
                                pj0, pi0, b_ = o.mask[c]
                                y, x = jj[0] + j0, ii[0] + i0
                                if pj0 <= y < pj0 + b_.shape[0] and pi0 <= x < pi0 + b_.shape[1] and b_[y - pj0, x - pi0]:
                                    quem.add(o.rede.split('/')[-1])
                        print(f'    {r.rede.split("/")[-1]} c{c} ({(ii[0]+i0)*E.RES:.1f},{(jj[0]+j0)*E.RES:.1f}) n={len(jj)} com {quem}')
        if not maus and it > 0:
            break
        por_fazer = maus + [r for r in rotas if r.cam is None]
        pres *= 1.6

    # escrever: as rotas sem conflito
    maus = set(id(r) for r in conflitos(rotas, oc, por_rede))
    camadas = (pcbnew.F_Cu, pcbnew.B_Cu)
    n = 0
    for r in rotas:
        if r.cam is None or id(r) in maus:
            continue
        net = b.FindNet(r.rede)
        cam = r.cam + ([(1 - r.cam[-1][0], r.cam[-1][1], r.cam[-1][2])] if r.plano else [])
        E.desenhar(b, E.Grelha(), net, cam, r.w, r.pa if r.a[2] == 'Pad' else None,
                   r.pb if (r.c and r.c[2] == 'Pad') else None)
        n += 1
    pcbnew.SaveBoard(E.PCB, b)
    print(f'escritas {n} rotas ({time.time() - inicio:.0f} s)', flush=True)
    E.limpar()
    b = pcbnew.LoadBoard(E.PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(E.PCB, b)
    print(f'em falta: {len(E.faltas(b))}')


if __name__ == '__main__':
    main()
