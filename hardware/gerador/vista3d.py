"""Visualização 3D da placa: texturas das duas faces e lista de componentes.

Uso:  python3 vista3d.py            (precisa do pcbnew e do kicad-cli; rsvg-convert e Pillow)

Escreve em hardware/3d/ as texturas top.jpg e bottom.jpg (máscara, cobre sob a máscara,
pads expostos, serigrafia e furos, a 24 px/mm) e parts.json (caixa, altura e cor de cada
componente, pelos footprints). O index.html dessa pasta mostra a placa em 3D (three.js);
abre-se com um servidor local (python3 -m http.server na pasta 3d) ou publica-se tal e qual.
Os modelos 3D reais estão nos footprints: no KiCad, Ver > Visualizador 3D (Alt+3).
"""
import sys, os, json, subprocess, re, math
import numpy as np
from PIL import Image, ImageDraw
import pcbnew
AQUI = os.path.dirname(os.path.abspath(__file__))
PCB = sys.argv[1] if len(sys.argv) > 1 else os.path.join(AQUI, '..', 'laset_gateway.kicad_pcb')
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(AQUI, '..', '3d')
PX = 24  # px por mm
W = H = 100.0; OX, OY = 100.0, 50.0
N = int(W * PX)

b = pcbnew.LoadBoard(PCB)
_bb = b.ComputeBoundingBox(False)
BBX, BBY = pcbnew.ToMM(_bb.GetX()), pcbnew.ToMM(_bb.GetY())
def camada(layers):
    svg = os.path.join(OUT, 'tmp.svg'); png = os.path.join(OUT, 'tmp.png')
    subprocess.run(['kicad-cli', 'pcb', 'export', 'svg', '--layers', layers + ',Edge.Cuts', '--black-and-white',
                    '--page-size-mode', '2', '--exclude-drawing-sheet', '--drill-shape-opt', '0', '-o', svg, PCB],
                   check=True, capture_output=True)
    t = open(svg).read()
    vb = [float(v) for v in re.search(r'viewBox="([-\d. ]+)"', t).group(1).split()]
    wmm = float(re.search(r'width="([\d.]+)mm"', t).group(1))
    esc = vb[2] / wmm                      # unidades do viewBox por mm
    lw, lh = int(round(vb[2] / esc * PX)), int(round(vb[3] / esc * PX))
    subprocess.run(['rsvg-convert', '-w', str(lw), '-h', str(lh), '-b', 'white', '-o', png, svg], check=True)
    full = np.asarray(Image.open(png).convert('L')) < 128
    x0 = int(round((OX - BBX) * PX)); y0 = int(round((OY - BBY) * PX))
    a = np.zeros((N, N), bool)
    sub = full[max(0, y0):y0 + N, max(0, x0):x0 + N]
    a[max(0, -y0):max(0, -y0) + sub.shape[0], max(0, -x0):max(0, -x0) + sub.shape[1]] = sub
    return a

def mm(v): return pcbnew.ToMM(v)
furos = []
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        p = t.GetPosition(); furos.append((mm(p.x) - OX, mm(p.y) - OY, mm(t.GetDrill()) / 2))
for f in b.GetFootprints():
    for p in f.Pads():
        if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH):
            q = p.GetPosition(); d = p.GetDrillSize()
            furos.append((mm(q.x) - OX, mm(q.y) - OY, mm(min(d.x, d.y)) / 2))

MASK = np.array([22, 84, 52]); COBRE = np.array([48, 122, 74]); OURO = np.array([214, 175, 96])
FR4 = np.array([170, 152, 100]); SILK = np.array([245, 245, 240]); BORDA = np.array([30, 60, 40])
for lado, (cu, msk, slk) in {'top': ('F.Cu', 'F.Mask', 'F.Silkscreen'), 'bottom': ('B.Cu', 'B.Mask', 'B.Silkscreen')}.items():
    c, mk, s = camada(cu), camada(msk), camada(slk)
    img = np.empty((N, N, 3), np.uint8); img[:] = MASK
    img[c] = COBRE
    img[mk & ~c] = FR4
    img[mk & c] = OURO
    img[s & ~mk] = SILK
    im = Image.fromarray(img); d = ImageDraw.Draw(im)
    for x, y, r in furos:
        d.ellipse([(x - r) * PX, (y - r) * PX, (x + r) * PX, (y + r) * PX], fill=(18, 18, 18))
    # contorno: 2 px escuros
    d.rectangle([0, 0, N - 1, N - 1], outline=tuple(BORDA), width=3)
    im.convert('RGB').save(os.path.join(OUT, f'{lado}.jpg'), quality=86)

def tipo(ref, fp, val):
    n = fp.lower()
    if ref.startswith('H'): return None
    if ref.startswith('TP'): return None
    if 'cp_elec' in n:
        dia = float(re.search(r'cp_elec_([\d.]+)x([\d.]+)', n).group(1)); alt = float(re.search(r'cp_elec_[\d.]+x([\d.]+)', n).group(1))
        return dict(k='cyl', h=alt, c='#c9ccd1', top='#2b2f36', d=dia)
    if ref.startswith('J') or ref.startswith('JP'):
        if 'terminalblock' in n: return dict(k='box', h=8.5, c='#1f7a45')
        if 'rj45' in n: return dict(k='box', h=13.3, c='#b9bdc2')
        if 'dsub' in n: return dict(k='box', h=12.5, c='#a9adb3')
        if 'jst' in n: return dict(k='box', h=6.0, c='#efe8d6')
        if 'pinheader' in n: return dict(k='hdr', h=2.5, c='#202124')
        return dict(k='box', h=3, c='#303236')
    if ref.startswith('L'): return dict(k='box', h=4.5 if '1245' in n else 4.5, c='#3a3d42')
    if ref.startswith('Q'): return dict(k='box', h=1.0, c='#1b1c1e')
    if ref.startswith('U'):
        h = 1.4 if 'qfp' in n else 2.4 if 'soic' in n and '7.5' in n else 0.9 if ('qfn' in n or 'dfn' in n or 'son' in n) else 1.1
        return dict(k='box', h=h, c='#1d1f22')
    if ref.startswith('F'): return dict(k='box', h=2.7, c='#e8e1cf')
    if ref.startswith('Y'): return dict(k='box', h=0.8, c='#cfd3d8')
    if ref.startswith('D'):
        if 'led' in n: return dict(k='box', h=0.6, c='#e94b3c' if 'erm' in val.lower() or 'red' in val.lower() else '#46c35a')
        return dict(k='box', h=2.3 if 'smc' in n else 1.1, c='#1d1f22')
    if ref.startswith('R'): return dict(k='box', h=0.55 if '2512' not in n else 0.65, c='#1e1f21')
    if ref.startswith('FB'): return dict(k='box', h=0.8, c='#2a2b2e')
    if ref.startswith('C'):
        h = 1.6 if ('1206' in n or '1210' in n) else 1.25 if '0805' in n else 0.8
        return dict(k='box', h=h, c='#b88a52')
    return dict(k='box', h=1, c='#444')

partes = []
for f in b.GetFootprints():
    ref = f.GetReference(); fp = str(f.GetFPID().GetUniStringLibItemName()); val = f.GetValue()
    tp = tipo(ref, fp, val)
    if tp is None: continue
    # caixa do corpo: camada Fab, se houver; senão o courtyard encolhido
    xs, ys = [], []
    baixo = f.IsFlipped()
    fab, crt = (pcbnew.B_Fab, pcbnew.B_CrtYd) if baixo else (pcbnew.F_Fab, pcbnew.F_CrtYd)
    for g in f.GraphicalItems():
        if g.GetLayer() == fab and g.GetClass() != 'MTEXT' and not isinstance(g, pcbnew.FP_TEXT):
            bb = g.GetBoundingBox(); xs += [mm(bb.GetX()), mm(bb.GetRight())]; ys += [mm(bb.GetY()), mm(bb.GetBottom())]
    if not xs:
        f.BuildCourtyardCaches()
        bb = f.GetCourtyard(crt).BBox(); m = 0.25
        xs = [mm(bb.GetX()) + m, mm(bb.GetRight()) - m]; ys = [mm(bb.GetY()) + m, mm(bb.GetBottom()) - m]
    x0, x1, y0, y1 = min(xs) - OX, max(xs) - OX, min(ys) - OY, max(ys) - OY
    pinos = []
    for p in f.Pads():
        if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
            q = p.GetPosition(); pinos.append([round(mm(q.x) - OX, 2), round(mm(q.y) - OY, 2)])
    partes.append(dict(r=ref, v=val, f=fp, x0=round(x0, 2), x1=round(x1, 2), y0=round(y0, 2), y1=round(y1, 2), p=pinos,
                       **({'b': 1} if baixo else {}), **tp))
json.dump(partes, open(os.path.join(OUT, 'parts.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
for f in ('tmp.svg', 'tmp.png'):
    if os.path.exists(os.path.join(OUT, f)):
        os.remove(os.path.join(OUT, f))
print(len(partes), 'componentes', os.path.getsize(os.path.join(OUT, 'top.jpg')) // 1024, 'KB')
