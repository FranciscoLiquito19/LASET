"""Encaminha ligações em falta por F.Cu e pela camada interior In2 (plano de 3,3 V).

Uso:  VIA=0.5 python3 interior.py [REDE ...]                  (depois de melhorar.py)
      VIA=0.5 BASE=<placa_base> python3 interior.py [REDE ...]  (com arranque, como o melhorar.py)
      arrancar_e_ordenar(base, redes, ordem)                    (arranca e encaminha por ordem)

VIA=0.5: vias de saída de 0,5/0,25 mm (cabem nas bolsas junto aos pinos de passo fino).
FB_PRIMEIRO=1: tenta primeiro só F.Cu e B.Cu (encaminhar.py) e usa In2 só se falhar.
ALVO=n: só aceita se ficarem menos de n ligações em falta. DEBUG=1: mostra cada procura.
O afastamento da classe vale em todo o caminho, menos a 0,8 mm das pontas (PERTO).
Se uma pista em In2 deixar uma ilha do plano de 3,3 V solta, o que ficou solto é religado
antes de contar.

Para as ligações que já não cabem em F.Cu e B.Cu. Uma pista em In2 corta o plano de
3,3 V à volta dela (o preenchimento da zona afasta-se), e tem o plano de massa (In1) logo
ao lado como referência. Só para sinais lentos ou de baixa corrente: UART, MDIO, RMII,
reset, PWM, alimentação dos circuitos integrados.

Na grelha de In2 só são obstáculos as vias, os furos e as pistas que já estejam em In2;
as zonas de In2 não, porque se recortam. As vias têm de caber também em B.Cu. Cada rota
só fica se o DRC do KiCad não acusar violações novas e o número de ligações em falta
baixar; senão volta atrás.
"""
import inspect
import math
import os
import shutil
import sys

import numpy as np
import pcbnew
from scipy import ndimage

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import encaminhar as E  # noqa: E402

COPIA = E.PCB + '.interior'
# Área do chassis do RJ45 em In2 (afastamento de 2 mm à massa): fica de fora
CHASSIS = (71.0, 0.0, 93.0, 16.0)
VIOLACOES = ('clearance', 'shorting_items', 'tracks_crossing', 'copper_edge_clearance', 'hole_clearance',
             'hole_near_hole', 'items_not_allowed', 'via_dangling', 'track_dangling', 'solder_mask_bridge')

# desenhar() do encaminhar.py, com In2 no lugar de B.Cu
_src = inspect.getsource(E.desenhar).replace('def desenhar(', 'def desenhar_in2(').replace(
    'pcbnew.F_Cu, pcbnew.B_Cu)\n    # ligar', 'pcbnew.F_Cu, pcbnew.In2_Cu)\n    # ligar')
exec(_src, E.__dict__)

# procurar() com o afastamento da classe relaxado perto das pontas (máscara RELAXA)
RELAXA = [None]
_src2 = inspect.getsource(E.procurar).replace('def procurar(', 'def procurar_rel(').replace(
    '''            livre &= ~ndimage.binary_dilation(~livre, structure=ndimage.generate_binary_structure(2, 2), iterations=extra)''',
    '''            base_l = livre.copy()
            livre &= ~ndimage.binary_dilation(~livre, structure=ndimage.generate_binary_structure(2, 2), iterations=extra)
            if RELAXA[0] is not None:
                livre |= base_l & RELAXA[0][j0:j1, i0:i1]''')
_src2 = _src2.replace("rv = int(round((VIA_D / 2 - LARG['Default'] / 2) / RES))", "rv = RV[0]")
assert 'RELAXA[0][j0' in _src2 and 'RV[0]' in _src2
exec(_src2, E.__dict__)
E.RELAXA = RELAXA

# Área do LM5177 (pcb.LM5177_AREA): lá dentro a classe HV usa 0,15 mm (.kicad_dru), por isso
# os obstáculos HV e a própria rede HV usam esse afastamento na grelha
from pcb import LM5177_AREA  # noqa: E402


def _na_area(x, y):
    x0, y0, x1, y1 = LM5177_AREA
    return x0 <= x <= x1 and y0 <= y <= y1


def _afast_t(t):
    a = E.AFAST.get(t.GetNetClassName(), 0.15)
    if t.GetNetClassName() == 'HV':
        pts = [E.loc(t.GetPosition())] if t.GetClass() == 'PCB_VIA' else [E.loc(t.GetStart()), E.loc(t.GetEnd())]
        if all(_na_area(*q) for q in pts):
            return 0.15
    return a


def _afast_p(p, ref=None):
    if p.GetNetClassName() == 'HV' and _na_area(*E.loc(p.GetPosition())):
        return 0.15
    return E.afast(p, ref)


E.afast_t, E.afast_p = _afast_t, _afast_p
_src3 = inspect.getsource(E.carregar).replace('def carregar(', 'def carregar_lm(').replace(
    'AFAST.get(t.GetNetClassName(), 0.15)', 'afast_t(t)').replace('afast(p, f.GetReference())', 'afast_p(p, f.GetReference())')
assert 'afast_t(t)' in _src3 and 'afast_p(p' in _src3
exec(_src3, E.__dict__)
_RES = E.RES
MASCARA_LM = np.zeros((E.NY, E.NX), bool)
MASCARA_LM[int(LM5177_AREA[1] / _RES):int(LM5177_AREA[3] / _RES), int(LM5177_AREA[0] / _RES):int(LM5177_AREA[2] / _RES)] = True
# vias de saída mais pequenas (VIA=0.5): 0,5/0,25 mm, dentro das regras do projeto
if os.environ.get('VIA'):
    E.VIA_D, E.VIA_F = float(os.environ['VIA']), 0.2      # anel de 0,15 mm (JLCPCB pede 0,13)
E.RV = [1 if E.VIA_D <= 0.5 else 2]
E.LIMITE[0] = int(os.environ.get('LIMITE', 3000000))


def grelha(b, k, ignorar=None):
    """Grelha de duas camadas: 0 = F.Cu (como no encaminhar.py), 1 = In2."""
    g = E.carregar_lm(b, ignorar=ignorar)
    gi = E.Grelha()
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) or p.IsOnLayer(pcbnew.In2_Cu):
                bb = p.GetBoundingBox()
                x0, y0 = pcbnew.ToMM(bb.GetX()) - E.OX, pcbnew.ToMM(bb.GetY()) - E.OY
                x1, y1 = pcbnew.ToMM(bb.GetRight()) - E.OX, pcbnew.ToMM(bb.GetBottom()) - E.OY
                k = p.GetNetCode()
                gi.retangulo(0, k if k > 0 else -1, x0, y0, x1, y1, E.BASE + E.afast(p, f.GetReference()) - 0.15)
    for t in b.GetTracks():
        k = t.GetNetCode()
        r = E.BASE + E.AFAST.get(t.GetNetClassName(), 0.15) - 0.15
        if t.GetClass() == 'PCB_VIA':
            x, y = E.loc(t.GetPosition())
            gi.segmento(0, k, x, y, x, y, pcbnew.ToMM(t.GetWidth()), r)
        elif t.GetLayer() == pcbnew.In2_Cu:
            (xa, ya), (xb, yb) = E.loc(t.GetStart()), E.loc(t.GetEnd())
            gi.segmento(0, k, xa, ya, xb, yb, pcbnew.ToMM(t.GetWidth()), r)
    gi.retangulo(0, -1, 0, E.BARREIRA[0], E.W, E.BARREIRA[1], 0.3)
    xs = sorted(E.ISO.values())
    for (a0, a1), (b0, b1) in zip(xs, xs[1:]):
        gi.retangulo(0, -1, a1, E.BARREIRA[1], b0, E.H, 0.3)
    gi.retangulo(0, -1, *CHASSIS, 0.3)
    m = int(1.0 / E.RES)
    gi.dono[0][:m, :] = gi.dono[0][-m:, :] = gi.dono[0][:, :m] = gi.dono[0][:, -m:] = -1
    # via: também tem de caber em B.Cu (qualquer cobre de B.Cu a menos de meia via + afastamento)
    rv = int(math.ceil((E.VIA_D / 2 + 0.15) / E.RES))
    est = ndimage.generate_binary_structure(2, 2)
    ocupado_b = ndimage.binary_dilation((g.nucleo[1] != 0) & (g.nucleo[1] != k), structure=est, iterations=rv)
    # furos: 0,8 mm entre centros (0,6 mm de via + 0,15 mm de afastamento, arredondado)
    furos = np.zeros_like(g.sem_via)
    for t in b.GetTracks():
        if t.GetClass() == 'PCB_VIA':
            x, y = E.loc(t.GetPosition())
            furos[min(E.NY - 1, int(y / E.RES)), min(E.NX - 1, int(x / E.RES))] = True
    for f in b.GetFootprints():
        for p in f.Pads():
            if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
                x, y = E.loc(p.GetPosition())
                rr = int(math.ceil((max(pcbnew.ToMM(p.GetSize().x), pcbnew.ToMM(p.GetSize().y)) / 2 + 0.5) / E.RES))
                j, i = int(y / E.RES), int(x / E.RES)
                furos[max(0, j - rr):j + rr + 1, max(0, i - rr):i + rr + 1] = True
    # 0,8 mm entre centros: com furos de 0,2 a 0,3 mm ficam pelo menos 0,5 mm entre furos (JLCPCB)
    sem_via = ndimage.binary_dilation(furos, structure=est, iterations=int(0.8 / E.RES))
    g3 = E.Grelha()
    g3.dono = [g.dono[0], gi.dono[0]]
    g3.nucleo = [g.nucleo[0], gi.nucleo[0]]
    g3.sem_via = sem_via | ocupado_b
    return g3


def contar():
    b = pcbnew.LoadBoard(E.PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    return b, E.faltas(b), violacoes(b)


def violacoes(b):
    import re
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        rpt = os.path.join(d, 'drc.rpt')
        pcbnew.WriteDRCReport(b, rpt, pcbnew.EDA_UNITS_MILLIMETRES, False)
        t = open(rpt, encoding='utf-8').read()
    return sum(1 for x in re.findall(r'^\[(\w+)\]', t, re.M) if x in VIOLACOES)


def cobre_perto(g, k, ponto, r=2.5):
    """Numa ponta que é pista ou via, também o cobre da mesma rede até r mm (2,5) (a via ao lado
    do pino, quando o DRC aponta para o troço curto entre o pino e a via)."""
    if ponto[2] not in ('Track', 'Via'):
        return []
    n = int(r / E.RES)
    j, i = int(ponto[1] / E.RES), int(ponto[0] / E.RES)
    j0, i0 = max(0, j - n), max(0, i - n)
    out = []
    for c in (0, 1):
        js, is_ = np.nonzero(g.nucleo[c][j0:j + n + 1, i0:i + n + 1] == k)
        out += [(c, jj + j0, ii + i0) for jj, ii in zip(js, is_)]
    return out


# Redes que não podem ir para In2: nós de comutação e potência (classes HV e P5V), pares
# Ethernet (classe ETH) e o relógio de 50 MHz do RMII (revisão independente de 25/11)
SEM_IN2_CLASSES = {'HV', 'P5V', 'ETH'}


def pode_in2(net):
    return net.GetNetClassName() not in SEM_IN2_CLASSES and 'REF_CLK' not in net.GetNetname()


def rotear(b, rede, a, c):
    """Encaminha uma ligação em F.Cu + In2; devolve o número de vias ou None."""
    net = b.FindNet(rede)
    k = net.GetNetCode()
    so_fb = not pode_in2(net)
    # redes que não podem ir para In2: mesma procura em F.Cu e B.Cu
    g = E.carregar_lm(b) if so_fb else grelha(b, k)
    if a[2] == 'Zone':
        a, c = c, a
    orig, pa = E.celulas_item(b, g, k, a)
    dest, pb = E.celulas_item(b, g, k, c, outro=a)
    orig, dest = orig + cobre_perto(g, k, a), dest + cobre_perto(g, k, c)
    if not orig or not dest:
        return None
    classe = net.GetNetClassName()
    af = E.AFAST.get(classe, 0.15)
    extra = int(math.ceil(round(max(0.0, (0.1 + af) - (E.BASE - 0.04)) / E.RES, 6)))
    rel = np.zeros((E.NY, E.NX), bool)
    for _, j, i in orig + dest:
        rel[j, i] = True
    RELAXA[0] = ndimage.binary_dilation(rel, iterations=int(float(os.environ.get('PERTO', 0.8)) / E.RES))
    if classe == 'HV':
        RELAXA[0] |= MASCARA_LM
    cam = E.procurar_rel(g, k, orig, dest, extra, True)
    if os.environ.get('DEBUG'):
        print('    rotear', rede, a, c, len(orig), len(dest), extra, cam is not None, flush=True)
    RELAXA[0] = None
    if cam is None:
        return None
    desenhar = E.desenhar if so_fb else E.desenhar_in2
    nv, itens, ok = desenhar(b, g, net, cam, 0.2, pa if a[2] == 'Pad' else None, pb if c[2] == 'Pad' else None)
    return nv


def com_arranque(base, rede, a, c):
    """Como o melhorar.py: caminho ideal sem o cobre dos encaminhadores, arranca as redes
    que o caminho atravessa, encaminha a ligação e depois as arrancadas, tudo em F.Cu + In2."""
    import melhorar as M
    b0 = pcbnew.LoadBoard(base)
    base_k = {M.chave(t) for t in b0.GetTracks()}
    del b0
    M.BASE_K.clear()
    M.BASE_K.update((r, kk) for r, kk, _ in M.linhas_cobre(base))
    b, _, _ = contar()
    net = b.FindNet(rede)
    k = net.GetNetCode()
    g = grelha(b, k, ignorar=lambda t: M.chave(t) not in base_k)
    aa, cc = (c, a) if a[2] == 'Zone' else (a, c)
    orig, _ = E.celulas_item(b, g, k, aa)
    dest, _ = E.celulas_item(b, g, k, cc, outro=aa)
    if not orig or not dest:
        return None
    cam = E.procurar(g, k, orig, dest, 0, True)
    if cam is None:
        return None
    nomes = {b.FindNet(r).GetNetname() for r in M.redes_no_caminho(b, base_k, cam, k)}
    del b, g
    M.arrancar_texto(nomes)
    b, falta, _ = contar()
    primeiro = [x for x in falta if x[0] == rede]
    resto = sorted([x for x in falta if x[0] in nomes], key=lambda r: math.dist(r[1][:2], r[2][:2]))
    for x in primeiro + resto:
        r = rotear(b, *x)
        if r is None:
            # tentar também pelo encaminhar.py normal (F.Cu e B.Cu)
            gg = E.carregar(b)
            E.rotear_uma(b, gg, *x)
    pcbnew.SaveBoard(E.PCB, b)
    return len(nomes)


def main():
    E.LIMITE[0] = int(os.environ.get('LIMITE', 3000000))
    escolha = set(sys.argv[1:])
    b, lista, v0 = contar()
    melhor = len(lista)
    print(f'{melhor} ligações em falta, {v0} violações', flush=True)
    tentadas = set()
    progresso = True
    while progresso:
        progresso = False
        for rede, a, c in list(lista):
            curto = rede.split('/')[-1]
            if escolha and curto not in escolha:
                continue
            alvo = (rede, round(a[0], 1), round(a[1], 1), round(c[0], 1), round(c[1], 1))
            if alvo in tentadas:
                continue
            tentadas.add(alvo)
            shutil.copy(E.PCB, COPIA)
            if os.environ.get('BASE'):
                n = com_arranque(os.environ['BASE'], rede, a, c)
                if n is None:
                    print(f'  {curto}: sem caminho ideal', flush=True)
                    continue
                b, lista2, v = contar()
                if len(lista2) < melhor and v <= v0:
                    print(f'  {curto}: {melhor} -> {len(lista2)} (arrancadas {n})', flush=True)
                    melhor, lista = len(lista2), lista2
                    progresso = True
                    break
                print(f'  {curto}: sem ganho ({len(lista2)} em falta, {v} violações, arrancadas {n})', flush=True)
                shutil.copy(COPIA, E.PCB)
                b, lista, _ = contar()
                continue
            nv = rotear(b, rede, a, c)
            if nv is None:
                print(f'  {curto}: sem caminho', flush=True)
                continue
            pcbnew.SaveBoard(E.PCB, b)
            b, lista2, v = contar()
            if len(lista2) < melhor and v <= v0:
                print(f'  {curto}: {melhor} -> {len(lista2)} ({nv} vias)', flush=True)
                melhor, lista = len(lista2), lista2
                progresso = True
                break
            print(f'  {curto}: sem ganho ({len(lista2)} em falta, {v} violações)', flush=True)
            shutil.copy(COPIA, E.PCB)
            b, lista, _ = contar()
    if os.path.exists(COPIA):
        os.remove(COPIA)
    b = pcbnew.LoadBoard(E.PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(E.PCB, b)
    print(f'em falta: {melhor}')




def refazer_grupo(base, ref, tentativas=6, semente=1):
    """Arranca o cobre dos encaminhadores de todas as redes de sinal de uma peça e volta a
    encaminhá-las juntas (F.Cu + In2), em várias ordens; fica a melhor sem violações."""
    import random
    import melhorar as M
    b0 = pcbnew.LoadBoard(base)
    M.BASE_K.clear()
    M.BASE_K.update((r, kk) for r, kk, _ in M.linhas_cobre(base))
    del b0
    b, lista, v0 = contar()
    melhor = len(lista)
    fp = b.FindFootprintByReference(ref)
    nomes = {p.GetNetname() for p in fp.Pads() if p.GetNetname() and p.GetNetname() not in ('GND', '+3V3', '+5V')
             and not p.GetNetname().startswith('unconnected')}
    print(f'{ref}: {len(nomes)} redes, {melhor} em falta', flush=True)
    del b
    shutil.copy(E.PCB, COPIA)
    melhor_ficheiro = E.PCB + '.melhor_grupo'
    shutil.copy(E.PCB, melhor_ficheiro)
    rnd = random.Random(semente)
    for t in range(tentativas):
        shutil.copy(COPIA, E.PCB)
        M.arrancar_texto(nomes)
        b, falta, _ = contar()
        grupo = [x for x in falta if x[0] in nomes]
        if t == 0:
            grupo.sort(key=lambda r: math.dist(r[1][:2], r[2][:2]))
        else:
            rnd.shuffle(grupo)
        for x in grupo:
            if rotear(b, *x) is None:
                gg = E.carregar(b)
                E.rotear_uma(b, gg, *x)
        pcbnew.SaveBoard(E.PCB, b)
        b, lista2, v = contar()
        print(f'  tentativa {t + 1}: {len(lista2)} em falta, {v} violações', flush=True)
        if len(lista2) < melhor and v <= v0:
            melhor = len(lista2)
            shutil.copy(E.PCB, melhor_ficheiro)
    shutil.copy(melhor_ficheiro, E.PCB)
    os.remove(melhor_ficheiro)
    os.remove(COPIA)
    print(f'{ref}: fica com {melhor} em falta', flush=True)


if __name__ == '__main__':
    if os.environ.get('GRUPO'):
        refazer_grupo(os.environ['BASE'], os.environ['GRUPO'], int(os.environ.get('TENTATIVAS', 6)))
    else:
        main()


def arrancar_e_ordenar(base, arrancar, ordem):
    """Arranca o cobre dos encaminhadores destas redes e encaminha as ligações em falta pela
    ordem dada (nomes curtos; as que não estiverem na lista vão no fim)."""
    import melhorar as M
    M.BASE_K.clear()
    M.BASE_K.update((r, kk) for r, kk, _ in M.linhas_cobre(base))
    b, lista, v0 = contar()
    antes = len(lista)
    nomes = {n.GetNetname() for n in b.GetNetsByName().values() if n.GetNetname().split('/')[-1] in arrancar}
    del b
    shutil.copy(E.PCB, COPIA)
    M.arrancar_texto(nomes)
    b, falta, _ = contar()
    pos = {n: i for i, n in enumerate(ordem)}
    falta.sort(key=lambda r: (pos.get(r[0].split('/')[-1], 99), math.dist(r[1][:2], r[2][:2])))
    for x in falta:
        if x[0].split('/')[-1] not in pos and x[0] not in nomes:
            continue
        r = None
        if os.environ.get('FB_PRIMEIRO'):
            gg = E.carregar(b)
            r = E.rotear_uma(b, gg, *x)
        if r is None:
            r = rotear(b, *x)
        print(f'  {x[0].split("/")[-1]}: {"ok" if r is not None else "falhou"}', flush=True)
    pcbnew.SaveBoard(E.PCB, b)
    b, lista2, v = contar()
    # ilhas do plano cortadas pelas pistas novas em In2: religar o que ficou solto
    planos = [x for x in lista2 if x[0] in ('+3V3', 'GND', '+5V')]
    if planos:
        for x in planos:
            gg = E.carregar(b)
            if E.rotear_uma(b, gg, *x) is None:
                rotear(b, *x)
        pcbnew.SaveBoard(E.PCB, b)
        b, lista2, v = contar()
    print(f'{antes} -> {len(lista2)} em falta, {v} violações:', ' '.join(r[0].split('/')[-1] for r in lista2), flush=True)
    if len(lista2) < int(os.environ.get('ALVO', antes)) and v <= v0:
        os.remove(COPIA)
        return True
    shutil.copy(COPIA, E.PCB)
    os.remove(COPIA)
    return False
