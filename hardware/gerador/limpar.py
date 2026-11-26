"""Retira cobre morto: pistas com uma ponta solta (track_dangling do DRC) e as vias que
ficam sem pistas nessa ponta. Edita o texto do ficheiro (no KiCad 7 apagar objetos pela
API e voltar a usá-los corrompe a memória) e repete até não haver pontas soltas.

Uso:  python3 limpar.py
"""
import os
import re
import sys
import tempfile

import pcbnew

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pcb import PCB  # noqa: E402


def soltas(b):
    with tempfile.TemporaryDirectory() as d:
        r = os.path.join(d, 'drc.rpt')
        pcbnew.WriteDRCReport(b, r, pcbnew.EDA_UNITS_MILLIMETRES, False)
        t = open(r, encoding='utf-8').read()
    pts = []
    for bloco in re.split(r'\n(?=\[)', t):
        if bloco.startswith('[track_dangling]'):
            m = re.search(r'@\(([\d.]+) mm, ([\d.]+) mm\): Track', bloco)
            pts.append((float(m.group(1)), float(m.group(2))))
    return pts


def apagar(uuids):
    L = open(PCB, encoding='utf-8').read().split('\n')
    out, i, n = [], 0, 0
    while i < len(L):
        s = L[i].lstrip()
        if s.startswith('(segment') or s.startswith('(via') or s.startswith('(arc'):
            j, d, blk = i, 0, []
            while True:
                d += L[j].count('(') - L[j].count(')')
                blk.append(L[j])
                if d == 0:
                    break
                j += 1
            if any(u in ''.join(blk) for u in uuids):
                n += 1
            else:
                out.extend(blk)
            i = j + 1
            continue
        out.append(L[i])
        i += 1
    open(PCB, 'w', encoding='utf-8').write('\n'.join(out))
    return n


def main():
    total = 0
    for volta in range(30):
        b = pcbnew.LoadBoard(PCB)
        pts = soltas(b)
        if not pts:
            break
        uu = set()
        tol = pcbnew.FromMM(0.01)
        for x, y in pts:
            P = pcbnew.VECTOR2I(pcbnew.FromMM(x), pcbnew.FromMM(y))
            for t in b.GetTracks():
                if t.GetClass() == 'PCB_VIA':
                    continue
                # o DRC dá o meio da pista ou uma ponta: aceita as duas
                meio = (t.GetStart() + t.GetEnd()) / 2 if hasattr(t.GetStart(), '__add__') else None
                for q in (t.GetStart(), t.GetEnd(), meio):
                    if q is not None and abs(q.x - P.x) <= tol and abs(q.y - P.y) <= tol:
                        uu.add(t.m_Uuid.AsString())
                        for e in (t.GetStart(), t.GetEnd()):
                            for v in b.GetTracks():
                                if v.GetClass() == 'PCB_VIA' and v.GetPosition() == e:
                                    k = sum(1 for o in b.GetTracks() if o.GetClass() != 'PCB_VIA'
                                            and (o.GetStart() == e or o.GetEnd() == e))
                                    if k == 1:
                                        uu.add(v.m_Uuid.AsString())
                        break
        if not uu:
            print('pontas soltas sem pista encontrada:', pts)
            break
        n = apagar(uu)
        total += n
        print(f'volta {volta + 1}: {len(pts)} pontas soltas, {n} objetos retirados')
    b = pcbnew.LoadBoard(PCB)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    pcbnew.SaveBoard(PCB, b)
    print(f'{total} objetos retirados')


if __name__ == '__main__':
    main()
