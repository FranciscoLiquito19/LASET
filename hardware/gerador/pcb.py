"""Gera o PCB (laset_gateway.kicad_pcb) a partir do esquema.

Uso:  python3 pcb.py          (precisa do módulo pcbnew do KiCad 7 ou mais recente)

O que faz:
  1. Exporta a netlist do esquema com o kicad-cli.
  2. Cria a placa: 4 camadas (sinal, GND, PWR, sinal), contorno 100 x 100 mm,
     furos de fixação, regras mínimas e classes de redes (no .kicad_pro).
  3. Coloca cada footprint com o caminho folha/símbolo do esquema, para o
     "Atualizar PCB a partir do esquema" (F8) do KiCad reconhecer as peças.
  4. Disposição: as peças principais (conectores, circuitos integrados, andar de
     potência) têm posição fixa em ANCORAS; as restantes são postas o mais perto
     possível do pino a que ligam, sem sobreposição e dentro do seu domínio
     (lado lógico ou um dos quatro lados isolados).
  5. Faixa de isolamento sem cobre por baixo dos isoladores e planos interiores.

Só deve ser corrido enquanto não houver pistas: refaz a placa de raiz. Depois de
começar o encaminhamento, as alterações ao esquema passam para a placa com o F8.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np
import pcbnew

AQUI = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(AQUI, '..'))
SCH = os.path.join(HW, 'laset_gateway.kicad_sch')
PCB = os.path.join(HW, 'laset_gateway.kicad_pcb')
PRO = os.path.join(HW, 'laset_gateway.kicad_pro')
LIBS = os.environ.get('KICAD_FOOTPRINTS', '/usr/share/kicad/footprints')

W, H = 100.0, 100.0          # placa (mm)
OX, OY = 100.0, 50.0         # canto superior esquerdo na folha
RES = 0.25                   # resolução da grelha de ocupação (mm)
FOLGA = 0.15                 # folga entre courtyards (mm)

# Faixa de isolamento (lado lógico em cima, lados isolados em baixo)
BARREIRA = (74.6, 81.4)
# Domínios isolados: x mínimo, x máximo (abaixo da barreira)
ISO = {
    'CAN1': (0.0, 24.0),
    'CAN2': (26.5, 50.5),
    '485': (53.0, 74.5),
    'PWM': (77.0, 100.0),
}
REDES_ISO = {
    'CAN1': {'CANH1', 'CANL1', 'GNDISO_CAN1', 'GND_CAN1', 'MID1', 'TL1', 'VISOOUT1', 'VISO_CAN1'},
    'CAN2': {'CANH2', 'CANL2', 'GNDISO_CAN2', 'GND_CAN2', 'MID2', 'TL2', 'VISOOUT2', 'VISO_CAN2'},
    '485': {'GNDISO_485', 'GND_485', 'RS485_A', 'RS485_B', 'T485', 'VISO_485'},
    'PWM': {'GND_PWM', 'PWM1_ISO', 'PWM2_ISO', 'PWM3_ISO', 'PWM1_OUT', 'PWM2_OUT', 'PWM3_OUT',
            'VISO_PWM', 'FALHA_ISO'},
}
ALIM = {'GND', '+3V3', '+5V', 'VIN'}

# Peças com posição fixa. Formatos:
#   ('c', x, y, rot)            centro do courtyard em (x, y)
#   ('borda', lado, pos, rot)   corpo (camada Fab) encostado ao bordo; pos ao longo do bordo
# rot em graus (sentido anti-horário). Conectores: abertura para fora da placa.
Y_ISO = (BARREIRA[0] + BARREIRA[1]) / 2
ANCORAS = {
    # Furos M3 nos cantos
    'H1': ('c', 4, 4, 0), 'H2': ('c', 96, 4, 0), 'H3': ('c', 4, 96, 0), 'H4': ('c', 96, 96, 0),
    # Alimentação: entrada em cima à esquerda, andar de potência em linha
    'J1': ('borda', 'cima', 16, 180),
    'F1': ('c', 28.5, 5.5, 0),
    'D1': ('c', 39.5, 6.0, 0),
    'D2': ('c', 50.5, 6.0, 180),
    # Andar de potência da esquerda para a direita no sentido inverso da corrente:
    # entrada (D2) -> condensadores de entrada -> perna buck (Q1/Q2) -> R_CS -> L1 ->
    # perna boost (Q3/Q4) -> condensadores de saída -> R_ISNS -> +5 V.
    # Q1 e Q3 com a patilha (dreno) virada para os condensadores; Q2 e Q4 com o
    # dreno virado para o nó de comutação.
    'C3': ('c', 63.5, 8.0, 0),
    'C1': ('c', 58.5, 15.0, 90), 'C2': ('c', 62.0, 15.0, 90),
    'Q1': ('c', 58.5, 21.5, 90), 'Q2': ('c', 58.5, 29.3, 90),
    'R10': ('c', 51.5, 25.5, 90),
    'L1': ('c', 40.0, 23.0, 180),
    'Q3': ('c', 26.5, 16.5, 90), 'Q4': ('c', 26.5, 24.3, 90),
    'C11': ('c', 21.5, 15.5, 270),
    'R13': ('c', 17.0, 16.0, 270),
    'C12': ('c', 12.5, 25.5, 270), 'C13': ('c', 12.5, 20.0, 90),
    'U1': ('c', 40.0, 35.0, 90),
    'TP1': ('c', 70.0, 14.5, 0),
    # 3,3 V
    'C14': ('c', 5.5, 15.5, 90), 'L2': ('c', 5.5, 25.0, 0), 'U2': ('c', 10.0, 31.0, 0),
    # Microcontrolador
    'U3': ('c', 46.0, 52.0, 0),
    'Y1': ('c', 31.5, 49.0, 90),
    'J2': ('c', 61.5, 37.5, 90),
    'JP6': ('c', 27.0, 61.0, 90),
    # Ethernet: RJ45 em cima à direita, a abrir para cima
    'J3': ('borda', 'cima', 82.0, 180),
    'U4': ('c', 82.0, 30.0, 0),
    'Y2': ('c', 75.0, 32.0, 0),
    # RS232: DE-9 no bordo esquerdo
    'J7': ('borda', 'esq', 54.0, 270),
    # I2C e GPS: conectores JST no bordo direito
    'J8': ('borda', 'dir', 40.0, 90), 'J9': ('borda', 'dir', 53.0, 90), 'J10': ('borda', 'dir', 66.0, 90),
    'U9': ('c', 84.0, 40.5, 0), 'U10': ('c', 84.0, 53.5, 0),
    # Isoladores sobre a barreira (pinos 1.. do lado lógico, em cima)
    'U5': ('c', 12.0, Y_ISO, 270), 'U6': ('c', 38.5, Y_ISO, 270),
    'U7': ('c', 63.5, Y_ISO, 270), 'U14': ('c', 88.5, Y_ISO, 270),
    # Conectores dos barramentos isolados no bordo de baixo
    'J4': ('borda', 'baixo', 16.0, 0), 'J5': ('borda', 'baixo', 38.5, 0),
    'J6': ('borda', 'baixo', 63.5, 0), 'J11': ('borda', 'baixo', 84.0, 0),
}
# Andar de potência: zonas de cobre em F.Cu (x0, y0, x1, y1) por rede. Fazem as ligações de
# corrente alta com o mínimo de indutância; as peças automáticas não entram nestas áreas.
POTENCIA = [
    ('/Alimentação/VIN_RAW', [(16.8, 2.0, 27.3, 7.6)]),
    ('/Alimentação/VIN_F', [(29.7, 3.0, 38.0, 10.5), (29.7, 8.4, 48.7, 10.5), (45.4, 3.0, 48.7, 10.5)]),
    ('VIN', [(52.3, 4.0, 63.7, 23.0)]),
    ('/Alimentação/SW1', [(49.4, 23.6, 60.0, 30.9)]),
    ('/Alimentação/LA', [(43.6, 20.1, 53.6, 24.0)]),
    ('/Alimentação/SW2', [(24.0, 18.6, 36.4, 26.0)]),
    ('/Alimentação/5V_PRE', [(14.8, 11.9, 29.2, 16.0)]),
    ('+5V', [(4.0, 16.9, 19.2, 21.9), (9.5, 16.9, 19.2, 25.8)]),
]

# Rotações permitidas para as peças colocadas automaticamente
ROTS = (0, 90, 180, 270)


# ---------------------------------------------------------------- netlist
def netlist():
    with tempfile.TemporaryDirectory() as d:
        f = os.path.join(d, 'n.net')
        subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '-o', f, SCH], check=True, capture_output=True)
        t = open(f, encoding='utf-8').read()
    comps = {}
    for b in t.split('(comp (ref ')[1:]:
        ref = re.match(r'"([^"]+)"', b).group(1)
        comps[ref] = {
            'valor': re.search(r'\(value "([^"]*)"\)', b).group(1),
            'fp': re.search(r'\(footprint "([^"]*)"\)', b).group(1),
            'folha': re.search(r'\(sheetpath \(names "([^"]*)"\)', b).group(1),
            'caminho': re.search(r'\(sheetpath \(names "[^"]*"\) \(tstamps "([^"]*)"\)', b).group(1)
                       + re.search(r'\)\s*\(tstamps "([^"]*)"\)\s*\)', b).group(1),
        }
    redes = {}
    for b in t.split('(net (code')[1:]:
        nome = re.search(r'\(name "([^"]*)"\)', b).group(1)
        redes[nome] = re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', b)
    return comps, redes


def curto(nome):
    return nome.rsplit('/', 1)[-1]


# ---------------------------------------------------------------- geometria
def mm(v):
    return pcbnew.FromMM(float(v))


def pt(x, y):
    return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))


def caixa(fp, camada):
    """Caixa (x0, y0, x1, y1) em mm, coordenadas locais da placa."""
    if camada == 'crt':
        fp.BuildCourtyardCaches()
        c = fp.GetCourtyard(pcbnew.F_CrtYd)
        if c.OutlineCount():
            b = c.BBox()
            return (pcbnew.ToMM(b.GetX()) - OX, pcbnew.ToMM(b.GetY()) - OY,
                    pcbnew.ToMM(b.GetRight()) - OX, pcbnew.ToMM(b.GetBottom()) - OY)
        b = fp.GetBoundingBox(False, False)
    else:
        b = None
        for g in fp.GraphicalItems():
            if g.GetLayer() == pcbnew.F_Fab and g.GetClass() in ('MGRAPHIC', 'FP_SHAPE', 'PCB_SHAPE'):
                bb = g.GetBoundingBox()
                if b is None:
                    b = bb
                else:
                    b.Merge(bb)
        if b is None:
            return caixa(fp, 'crt')
    return (pcbnew.ToMM(b.GetX()) - OX, pcbnew.ToMM(b.GetY()) - OY,
            pcbnew.ToMM(b.GetRight()) - OX, pcbnew.ToMM(b.GetBottom()) - OY)


def por(fp, x, y, rot):
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(pt(x, y))


def por_centro(fp, cx, cy, rot, camada='crt'):
    por(fp, 0, 0, rot)
    x0, y0, x1, y1 = caixa(fp, camada)
    por(fp, cx - (x0 + x1) / 2, cy - (y0 + y1) / 2, rot)


def por_borda(fp, lado, pos, rot):
    por(fp, 0, 0, rot)
    x0, y0, x1, y1 = caixa(fp, 'fab')
    if lado == 'cima':
        por(fp, pos - (x0 + x1) / 2, -y0, rot)
    elif lado == 'baixo':
        por(fp, pos - (x0 + x1) / 2, H - y1, rot)
    elif lado == 'esq':
        por(fp, -x0, pos - (y0 + y1) / 2, rot)
    elif lado == 'dir':
        por(fp, W - x1, pos - (y0 + y1) / 2, rot)


# ---------------------------------------------------------------- grelha
N = int(W / RES), int(H / RES)


def idx(v):
    return int(round(v / RES))


class Grelha:
    def __init__(self):
        self.ocup = np.zeros((N[1], N[0]), dtype=bool)
        self.dominio = {}
        lado_logico = np.zeros_like(self.ocup)
        lado_logico[:idx(BARREIRA[0]), :] = True
        self.dominio['logico'] = lado_logico
        for d, (x0, x1) in ISO.items():
            m = np.zeros_like(self.ocup)
            m[idx(BARREIRA[1]):, idx(x0):idx(x1)] = True
            self.dominio[d] = m
        # margem de 0,5 mm ao bordo
        borda = np.zeros_like(self.ocup)
        k = idx(0.5)
        borda[:k, :] = borda[-k:, :] = borda[:, :k] = borda[:, -k:] = True
        self.borda = borda

    def marcar(self, c):
        x0, y0, x1, y1 = c
        self.ocup[max(0, idx(y0 - FOLGA)):max(0, idx(y1 + FOLGA)), max(0, idx(x0 - FOLGA)):max(0, idx(x1 + FOLGA))] = True

    def livres(self, dominio, w, h):
        """Mapa booleano: True onde um retângulo w x h (mm) cabe com o canto sup. esq. na célula."""
        bloq = self.ocup | ~self.dominio[dominio] | self.borda
        a = np.pad(bloq.astype(np.int32), ((1, 0), (1, 0))).cumsum(0).cumsum(1)
        kw, kh = int(np.ceil((w + 2 * FOLGA) / RES)), int(np.ceil((h + 2 * FOLGA) / RES))
        if kh >= a.shape[0] or kw >= a.shape[1]:
            return None, kw, kh
        s = a[kh:, kw:] - a[:-kh, kw:] - a[kh:, :-kw] + a[:-kh, :-kw]
        return s == 0, kw, kh


# ---------------------------------------------------------------- placa
def criar_placa(comps, redes):
    b = pcbnew.BOARD()
    b.SetCopperLayerCount(4)
    b.SetLayerName(pcbnew.In1_Cu, 'GND')
    b.SetLayerName(pcbnew.In2_Cu, 'PWR')
    b.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
    b.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_POWER)

    # Contorno
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_RECT)
    s.SetStart(pt(0, 0))
    s.SetEnd(pt(W, H))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(mm(0.1))
    b.Add(s)

    # Redes
    netinfo = {}
    for nome in redes:
        n = pcbnew.NETINFO_ITEM(b, nome)
        b.Add(n)
        netinfo[nome] = n
    pino_rede = {(r, p): nome for nome, nos in redes.items() for r, p in nos}

    fps = {}
    for ref, c in sorted(comps.items()):
        lib, nome = c['fp'].split(':')
        pasta = os.path.join(HW, 'lib', 'laset.pretty') if lib == 'laset' else os.path.join(LIBS, lib + '.pretty')
        fp = pcbnew.FootprintLoad(pasta, nome)
        if fp is None:
            sys.exit(f'footprint não encontrado: {c["fp"]} ({ref})')
        fp.SetFPID(pcbnew.LIB_ID(lib, nome))
        fp.SetReference(ref)
        fp.SetValue(c['valor'])
        fp.SetPath(pcbnew.KIID_PATH(c['caminho']))
        fp.SetProperty('Sheetname', c['folha'].strip('/'))
        b.Add(fp)
        for pad in fp.Pads():
            nome_rede = pino_rede.get((ref, pad.GetNumber()))
            if nome_rede:
                pad.SetNet(netinfo[nome_rede])
        fps[ref] = fp
    return b, fps, netinfo


def dominio_de(ref, comps, redes_de):
    ds = {d for d, rs in REDES_ISO.items() for n in redes_de.get(ref, ()) if curto(n) in rs}
    if len(ds) > 1:
        return None
    return ds.pop() if ds else 'logico'


def dispor(b, fps, comps, redes):
    g = Grelha()
    redes_de = {}
    for nome, nos in redes.items():
        for r, _ in nos:
            redes_de.setdefault(r, set()).add(nome)

    colocados = set()
    for ref, a in ANCORAS.items():
        fp = fps[ref]
        if a[0] == 'c':
            por_centro(fp, a[1], a[2], a[3])
        else:
            por_borda(fp, a[1], a[2], a[3])
        g.marcar(caixa(fp, 'crt'))
        colocados.add(ref)
    for _, rs in POTENCIA:
        for r in rs:
            g.marcar(r)
    # As âncoras não se podem sobrepor
    cx = {r: caixa(fps[r], 'crt') for r in ANCORAS}
    for i, r1 in enumerate(ANCORAS):
        for r2 in list(ANCORAS)[i + 1:]:
            a, c = cx[r1], cx[r2]
            if a[0] < c[2] and c[0] < a[2] and a[1] < c[3] and c[1] < a[3]:
                sys.exit(f'âncoras sobrepostas: {r1} e {r2}')

    # Pinos de alimentação dos circuitos integrados, para os condensadores de desacoplamento
    pinos_alim = []
    for ref, fp in fps.items():
        if ref[0] == 'U':
            for pad in fp.Pads():
                if pad.GetNetname() in ('+3V3', '+5V') or curto(pad.GetNetname()).startswith(('VISO', 'VCC', 'VDD', 'VCAP')):
                    pinos_alim.append([ref, pad.GetNetname(), pad, 0])

    def posicao(pad):
        p = pad.GetPosition()
        return pcbnew.ToMM(p.x) - OX, pcbnew.ToMM(p.y) - OY

    def alvos(ref):
        """Pinos já colocados a que esta peça liga por redes de sinal."""
        out = []
        for pad in fps[ref].Pads():
            n = pad.GetNetname()
            if not n or n in ALIM or curto(n).startswith(('GND', 'VISO')):
                continue
            for r, p in redes.get(n, ()):
                if r in colocados and r != ref:
                    for q in fps[r].Pads():
                        if q.GetNumber() == p:
                            out.append((pad.GetNumber(), posicao(q)))
        return out

    pendentes = [r for r in fps if r not in colocados]
    while pendentes:
        # próxima peça: a que tem mais ligações a peças já colocadas
        pendentes.sort(key=lambda r: (-len(alvos(r)), r))
        ref = pendentes.pop(0)
        fp = fps[ref]
        dom = dominio_de(ref, comps, redes_de) or 'logico'
        alv = alvos(ref)
        if not alv:
            # desacoplamento: pino de alimentação mais perto que ainda tenha menos condensadores
            rs = redes_de.get(ref, set())
            cand = [p for p in pinos_alim if p[1] in rs and comps[p[0]]['folha'] == comps[ref]['folha']] or \
                   [p for p in pinos_alim if p[1] in rs]
            if cand:
                cand.sort(key=lambda p: p[3])
                p = cand[0]
                p[3] += 1
                alv = [(None, posicao(p[2]))]
            else:
                xs = [posicao(q)[0] for r in colocados if comps.get(r, {}).get('folha') == comps[ref]['folha'] for q in fps[r].Pads()][:1]
                alv = [(None, (W / 2, H / 2))] if not xs else [(None, (xs[0], H / 2))]
        tx = sum(p[1][0] for p in alv) / len(alv)
        ty = sum(p[1][1] for p in alv) / len(alv)

        melhor = None
        for rot in ROTS:
            por(fp, 0, 0, rot)
            x0, y0, x1, y1 = caixa(fp, 'crt')
            w, h = x1 - x0, y1 - y0
            livre, kw, kh = g.livres(dom, w, h)
            if livre is None or not livre.any():
                continue
            ys, xs = np.nonzero(livre)
            cx = xs * RES + FOLGA + w / 2
            cy = ys * RES + FOLGA + h / 2
            d2 = (cx - tx) ** 2 + (cy - ty) ** 2
            for i in np.argsort(d2)[:8]:
                px, py = cx[i] - (x0 + x1) / 2, cy[i] - (y0 + y1) / 2
                por(fp, px, py, rot)
                custo = 0.0
                for num, (qx, qy) in alv:
                    pads = [pd for pd in fp.Pads() if num is None or pd.GetNumber() == num]
                    if pads:
                        custo += min(np.hypot(posicao(pd)[0] - qx, posicao(pd)[1] - qy) for pd in pads)
                if melhor is None or custo < melhor[0] - 1e-6:
                    melhor = (custo, px, py, rot)
        if melhor is None:
            sys.exit(f'não há espaço para {ref} no domínio {dom}')
        _, px, py, rot = melhor
        por(fp, px, py, rot)
        g.marcar(caixa(fp, 'crt'))
        colocados.add(ref)


# ---------------------------------------------------------------- zonas
def retangulo(z, x0, y0, x1, y1):
    o = z.Outline()
    o.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        o.Append(mm(OX + x), mm(OY + y))


def zona(b, camada, rede, x0, y0, x1, y1, prioridade=0, solida=False):
    z = pcbnew.ZONE(b)
    z.SetLayer(camada)
    z.SetNet(rede)
    z.SetAssignedPriority(prioridade)
    z.SetMinThickness(mm(0.2))
    z.SetLocalClearance(mm(0.3))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if solida else pcbnew.ZONE_CONNECTION_THERMAL)
    retangulo(z, x0, y0, x1, y1)
    b.Add(z)
    return z


def proibida(b, x0, y0, x1, y1, nome):
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    z.SetZoneName(nome)
    ls = pcbnew.LSET()
    for l in (pcbnew.F_Cu, pcbnew.In1_Cu, pcbnew.In2_Cu, pcbnew.B_Cu):
        ls.AddLayer(l)
    z.SetLayerSet(ls)
    z.SetDoNotAllowTracks(True)
    z.SetDoNotAllowVias(True)
    z.SetDoNotAllowCopperPour(True)
    z.SetDoNotAllowPads(False)
    z.SetDoNotAllowFootprints(False)
    retangulo(z, x0, y0, x1, y1)
    b.Add(z)


def zonas(b, netinfo):
    m = 0.5
    # Faixa de isolamento e intervalos entre domínios isolados
    proibida(b, 0, BARREIRA[0], W, BARREIRA[1], 'isolamento')
    xs = sorted(ISO.values())
    for (a0, a1), (b0, b1) in zip(xs, xs[1:]):
        proibida(b, a1, BARREIRA[1], b0, H, 'isolamento')
    # Lado lógico: GND em In1, 3,3 V em In2 (5 V na faixa dos isoladores e na fonte)
    zona(b, pcbnew.In1_Cu, netinfo['GND'], m, m, W - m, BARREIRA[0], 0)
    zona(b, pcbnew.In2_Cu, netinfo['+3V3'], m, m, W - m, BARREIRA[0], 0)
    zona(b, pcbnew.In2_Cu, netinfo['+5V'], m, 63.5, W - m, BARREIRA[0], 1)
    zona(b, pcbnew.In2_Cu, netinfo['+5V'], 0.5, 10.0, 32.0, 36.0, 1)
    # Andar de potência em F.Cu
    for rede, rs in POTENCIA:
        for r in rs:
            zona(b, pcbnew.F_Cu, netinfo[rede], *r, 3, solida=True)
    # Blindagem do RJ45: chassis nas camadas interiores à frente dos pinos, a 2 mm da
    # massa (a ligação à massa é só por C50 1 nF 2 kV e R38 1 MΩ)
    for camada in (pcbnew.In1_Cu, pcbnew.In2_Cu):
        z = zona(b, camada, netinfo['/Ethernet/CHASSIS'], 71.5, m, 92.5, 15.5, 2)
        z.SetLocalClearance(mm(2.0))
    # Lados isolados: massa de cada barramento em In1
    massa = {'CAN1': '/CAN FD/GND_CAN1', 'CAN2': '/CAN FD/GND_CAN2', '485': '/RS485 e RS232/GND_485',
             'PWM': '/PWM isolado/GND_PWM'}
    for d, (x0, x1) in ISO.items():
        zona(b, pcbnew.In1_Cu, netinfo[massa[d]], max(x0, m), BARREIRA[1], min(x1, W - m), H - m, 0)


# ---------------------------------------------------------------- projeto
def projeto():
    def classe(nome, pista, afast, via, furo):
        return {'name': nome, 'clearance': afast, 'track_width': pista, 'via_diameter': via, 'via_drill': furo,
                'diff_pair_gap': 0.25, 'diff_pair_via_gap': 0.25, 'diff_pair_width': 0.2,
                'microvia_diameter': 0.3, 'microvia_drill': 0.1, 'bus_width': 12, 'wire_width': 6, 'line_style': 0,
                'pcb_color': 'rgba(0, 0, 0, 0.000)', 'schematic_color': 'rgba(0, 0, 0, 0.000)'}
    padroes = [('VIN', 'HV'), ('/Alimenta*/VIN_*', 'HV'), ('/Alimenta*/SW1', 'HV'), ('/Alimenta*/SW2', 'HV'),
               ('/Alimenta*/LA', 'HV'), ('+5V', 'P5V'), ('/Alimenta*/5V_PRE', 'P5V'), ('/Alimenta*/SW3', 'P5V'),
               ('/Ethernet/T*', 'ETH'), ('/Ethernet/R?', 'ETH'), ('/Ethernet/RX?', 'ETH'),
               ('/CAN FD/CAN*', 'BUS'), ('/RS485*/RS485_*', 'BUS')]
    d = json.load(open(PRO)) if os.path.exists(PRO) else {}
    d.setdefault('meta', {'filename': 'laset_gateway.kicad_pro', 'version': 1})
    d.setdefault('board', {})['design_settings'] = {
        'meta': {'version': 2},
        'rules': {'min_clearance': 0.15, 'min_track_width': 0.15, 'min_via_diameter': 0.5,
                  'min_via_annular_width': 0.1, 'min_through_hole_diameter': 0.2, 'min_hole_to_hole': 0.25,
                  'min_hole_clearance': 0.25, 'min_copper_edge_clearance': 0.5, 'min_connection': 0.0,
                  'min_silk_clearance': 0.0, 'min_text_height': 0.8, 'min_text_thickness': 0.08}}
    d['net_settings'] = {
        'meta': {'version': 3},
        'classes': [classe('Default', 0.2, 0.15, 0.6, 0.3), classe('HV', 1.5, 0.6, 0.8, 0.4),
                    classe('P5V', 1.0, 0.2, 0.8, 0.4), classe('ETH', 0.25, 0.15, 0.6, 0.3),
                    classe('BUS', 0.4, 0.3, 0.6, 0.3)],
        'net_colors': None, 'netclass_assignments': None,
        'netclass_patterns': [{'pattern': p, 'netclass': c} for p, c in padroes]}
    json.dump(d, open(PRO, 'w'), indent=2, ensure_ascii=False)
    with open(os.path.join(HW, 'laset_gateway.kicad_dru'), 'w') as fh:
        fh.write(DRU)


# Regras próprias. A classe HV pede 0,6 mm (IPC-2221B, 60 V, cobre exterior sem verniz),
# mas os pinos do LM5177 (passo de 0,5 mm) e dos MOSFET não o permitem: dentro desses
# footprints vale o afastamento do fabricante do circuito integrado.
DRU = '''(version 1)

(rule "HV dentro dos componentes de potência"
  (constraint clearance (min 0.15mm))
  (condition "A.NetClass == 'HV' && (A.intersectsCourtyard('U1') || A.intersectsCourtyard('Q1') || A.intersectsCourtyard('Q2') || A.intersectsCourtyard('Q3') || A.intersectsCourtyard('Q4') || A.intersectsCourtyard('D1') || A.intersectsCourtyard('D2') || A.intersectsCourtyard('F1') || A.intersectsCourtyard('J1'))"))

(rule "Faixa de isolamento"
  (constraint clearance (min 0.2mm))
  (condition "A.insideArea('isolamento')"))
'''


def textos(b):
    for i, (t, h) in enumerate((('LASET', 1.5), ('Gateway', 1.0), ('multiprotocolo', 1.0), ('v1.0  2026', 1.0))):
        x = pcbnew.PCB_TEXT(b)
        x.SetText(t)
        x.SetLayer(pcbnew.F_SilkS)
        x.SetTextSize(pcbnew.VECTOR2I(mm(h), mm(h)))
        x.SetTextThickness(mm(0.15 * h / 1.0))
        x.SetPosition(pt(70.5, 45.5 + 2.4 * i))
        b.Add(x)


def main():
    comps, redes = netlist()
    b, fps, netinfo = criar_placa(comps, redes)
    dispor(b, fps, comps, redes)
    textos(b)
    zonas(b, netinfo)
    pcbnew.SaveBoard(PCB, b)
    projeto()
    # Encher as zonas numa placa carregada do disco (na placa criada em memória o
    # preenchimento falha no KiCad 7)
    b = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(PCB, b)
    print(f'ok: {len(fps)} footprints, {len(redes)} redes -> {os.path.relpath(PCB)}')


if __name__ == '__main__':
    main()
