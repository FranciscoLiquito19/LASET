"""Pesquisa local para as últimas ligações em falta (depois do encaminhar.py).

Uso:  python3 melhorar.py <placa_base.kicad_pcb>

<placa_base> é a placa depois de pcb.py e fanout.py: o cobre que lá não está foi posto
pelos encaminhadores e pode ser arrancado.

Para cada ligação em falta:
  1. procura o caminho como se o cobre dos encaminhadores não existisse;
  2. arranca as redes desse cobre que o caminho atravessa (só essas);
  3. encaminha a ligação e depois as redes arrancadas;
  4. conta as ligações em falta (DRC do KiCad): se baixou, fica; senão, volta atrás.
"""
import math
import re
import os
import shutil
import sys
import time

import numpy as np
import pcbnew
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import encaminhar as E  # noqa: E402

COPIA = E.PCB + '.melhor'
BASE_K = set()


def chave(it):
    if it.GetClass() == 'PCB_VIA':
        p = it.GetPosition()
        return ('V', it.GetNetname(), round(p.x, -3), round(p.y, -3))
    s, e = it.GetStart(), it.GetEnd()
    return ('T', it.GetNetname(), it.GetLayer(), round(s.x, -3), round(s.y, -3), round(e.x, -3), round(e.y, -3))


def linhas_cobre(caminho):
    """(nome da rede, chave geométrica, linha) de cada pista e via do ficheiro."""
    t = open(caminho, encoding='utf-8').read()
    nomes = dict(re.findall(r'^  \(net (\d+) "([^"]*)"\)$', t, re.M))
    out = []
    for linha in t.splitlines():
        m = re.match(r'^  \((segment|via) (.*) \(net (\d+)\) \(tstamp [^)]*\)\)$', linha)
        if m:
            out.append((nomes.get(m.group(3), ''), (m.group(1), m.group(2)), linha))
    return out


def arrancar_texto(nomes):
    """Retira do ficheiro da placa as pistas e vias dos encaminhadores destas redes
    (editar o texto evita o Remove do pcbnew, que no KiCad 7 corrompe a memória)."""
    t = open(E.PCB, encoding='utf-8').read()
    tirar = {linha for rede, k, linha in linhas_cobre(E.PCB) if rede in nomes and (rede, k) not in BASE_K}
    novo = '\n'.join(l for l in t.split('\n') if l not in tirar)
    open(E.PCB, 'w', encoding='utf-8').write(novo)
    return len(tirar)


def contar():
    b = pcbnew.LoadBoard(E.PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    return b, E.faltas(b)


def redes_no_caminho(b, base_k, cam, k):
    """Redes com cobre dos encaminhadores a menos de ~0,5 mm do caminho."""
    gm = E.Grelha()
    for t in b.GetTracks():
        if chave(t) in base_k or t.GetNetCode() == k:
            continue
        if t.GetClass() == 'PCB_VIA':
            x, y = E.loc(t.GetPosition())
            gm.segmento(None, t.GetNetCode(), x, y, x, y, E.VIA_D, 0)
        else:
            (xa, ya), (xb, yb) = E.loc(t.GetStart()), E.loc(t.GetEnd())
            gm.segmento(0 if t.GetLayer() == pcbnew.F_Cu else 1, t.GetNetCode(), xa, ya, xb, yb,
                        pcbnew.ToMM(t.GetWidth()), 0)
    est = ndimage.generate_binary_structure(2, 2)
    out = set()
    for c in (0, 1):
        m = np.zeros((E.NY, E.NX), bool)
        for cc, j, i in cam:
            if cc == c:
                m[j, i] = True
        vias = np.zeros((E.NY, E.NX), bool)
        for n, (cc, j, i) in enumerate(cam):
            if n and cam[n - 1][0] != cc:
                vias[j, i] = True
        m = ndimage.binary_dilation(m, structure=est, iterations=5) | ndimage.binary_dilation(vias, structure=est, iterations=7)
        out |= {int(r) for r in np.unique(gm.nucleo[c][m]) if r > 0 and r != k}
    return out


def main():
    base = sys.argv[1]
    inicio = time.time()
    b0 = pcbnew.LoadBoard(base)
    base_k = {chave(t) for t in b0.GetTracks()}
    del b0
    BASE_K.update((rede, k) for rede, k, _ in linhas_cobre(base))
    b, lista = contar()
    melhor = len(lista)
    print(f'{melhor} ligações em falta')
    tentadas = set()
    E.LIMITE[0] = int(os.environ.get('LIMITE', 2000000))
    progresso = True
    while progresso:
        progresso = False
        for rede, a, c in list(lista):
            alvo = (rede, round(a[0], 1), round(a[1], 1), round(c[0], 1), round(c[1], 1))
            if alvo in tentadas:
                continue
            tentadas.add(alvo)
            shutil.copy(E.PCB, COPIA)
            b, _ = contar()
            net = b.FindNet(rede)
            k = net.GetNetCode()
            # 1. caminho ideal sem o cobre dos encaminhadores
            g_ideal = E.carregar(b, ignorar=lambda t: chave(t) not in base_k)
            aa, cc_ = (c, a) if a[2] == 'Zone' else (a, c)
            orig, pa = E.celulas_item(b, g_ideal, k, aa)
            dest, pb = E.celulas_item(b, g_ideal, k, cc_, outro=aa)
            if not orig or not dest:
                continue
            classe = net.GetNetClassName()
            w = E.LARG.get(classe, 0.2)
            af = 0.15 if classe in ('HV', 'P5V') else E.AFAST.get(classe, 0.15)
            extra = int(math.ceil(round(max(0.0, (w / 2 + af) - (E.BASE - 0.04)) / E.RES, 6)))
            cam = E.procurar(g_ideal, k, orig, dest, extra, True)
            if cam is None:
                print(f'  {rede.split("/")[-1]}: sem caminho mesmo sem as outras rotas')
                continue
            arrancar = redes_no_caminho(b, base_k, cam, k)
            nomes = {b.FindNet(r).GetNetname() for r in arrancar}
            # 2. arrancar
            del b, g_ideal
            arrancar_texto(nomes)
            # 3. encaminhar a ligação e depois as redes arrancadas
            b, falta = contar()
            g = E.carregar(b)
            primeiro = [x for x in falta if x[0] == rede]
            resto = sorted([x for x in falta if x[0] in nomes], key=lambda r: math.dist(r[1][:2], r[2][:2]))
            for x in primeiro + resto:
                E.rotear_uma(b, g, *x)
            pcbnew.SaveBoard(E.PCB, b)
            E.limpar()
            b, lista2 = contar()
            if len(lista2) < melhor:
                print(f'  {rede.split("/")[-1]}: {melhor} -> {len(lista2)} (arrancadas {len(nomes)})'
                      f' ({time.time() - inicio:.0f} s)', flush=True)
                melhor = len(lista2)
                lista = lista2
                progresso = True
                break
            shutil.copy(COPIA, E.PCB)
            print(f'  {rede.split("/")[-1]}: sem ganho ({len(lista2)})', flush=True)
    os.remove(COPIA) if os.path.exists(COPIA) else None
    # preencher as zonas com as vias novas (senão os planos ficam com a folga antiga)
    b = pcbnew.LoadBoard(E.PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(E.PCB, b)
    print(f'em falta: {melhor}')


if __name__ == '__main__':
    main()
