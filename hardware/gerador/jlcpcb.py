"""Lista de material no formato da montagem da JLCPCB (com o código LCSC de cada peça).

Uso (depois de gerar.py):  python3 -I jlcpcb.py

Lê os componentes do esquema, liga cada um a uma linha de hardware/bom/lcsc.csv e
escreve hardware/fabrico/laset_gateway_bom_jlcpcb.csv (Comment, Designator, Footprint,
LCSC Part #), que se carrega na JLCPCB junto com as posições. As peças marcadas FORA em
lcsc.csv (sem stock na JLCPCB) ficam de fora desta lista e aparecem no fim, para se
comprarem noutro sítio e soldarem à mão. Os pontos de teste não se montam.

Códigos e stock consultados no catálogo da JLCPCB a 26/11/2026; o stock muda, por isso
convém ver na encomenda se alguma peça ficou sem stock.
"""
import collections
import csv
import os
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

AQUI = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(AQUI, '..'))
SCH = os.path.join(HW, 'laset_gateway.kicad_sch')
TABELA = os.path.join(HW, 'bom', 'lcsc.csv')
SAIDA = os.path.join(HW, 'fabrico', 'laset_gateway_bom_jlcpcb.csv')

DIRETOS = ['LM5177', 'TPS62162', 'STM32H743ZIT6', 'LAN8742A-CZ', 'ADM3057EBRWZ', 'ADM2582EBRWZ',
           'MAX3227EEAE', 'ADuM6401ARWZ', 'TCA9406DCUR', '74AHCT1G125', 'BSC070N10LS5', 'SRP1245A-180M',
           'SMCJ60CA', 'MB510', 'NUP2105L', 'SM712', 'PRTR5V0U2X', 'ESDA6V1-5SC6', 'HR911105A', '25 MHz']


def chave(ref, valor, fp):
    for d in DIRETOS:
        if valor.startswith(d):
            return d
    letras = re.match(r'[A-Z]+', ref).group(0)
    if letras == 'TP':
        return None
    if letras == 'F':
        return 'Fusível'
    if letras == 'FB':
        return 'Ferrite'
    if letras == 'D':
        return 'LED'
    if letras == 'L':
        return 'SRN6045TA'
    if letras == 'R':
        if '2512' in fp:
            return 'R_CS'
        return 'R ' + valor.split(' ')[0]
    if letras == 'C':
        num = re.match(r'([\d,]+ [unp]F)', valor).group(1)
        tam = re.search(r'_(\d{4})_', fp)
        tam = tam.group(1) if tam else ''
        if 'CP_Elec_8x10' in fp:
            return 'C 47 uF 100V'
        if 'CP_Elec' in fp:
            return 'C 100 uF polimero'
        if '2 kV' in valor:
            return 'C 1 nF 2 kV 1206'
        if '100 V' in valor:
            return f'C {num} 100V {tam}'.replace(' 0603', ' 0603').strip()
        if '22 uF' in num and 'X7R' in valor:
            return 'C 22 uF 10V 1206 X7R'
        return f'C {num} {tam}'
    if letras in ('J', 'JP'):
        if 'TerminalBlock' in fp:
            return 'J borne ' + re.search(r'1x0(\d)', fp).group(1)
        if 'JST_PH' in fp:
            return 'J JST ' + re.search(r'1x0(\d)', fp).group(1)
        if 'PinHeader' in fp:
            return 'J barra ' + str(int(re.search(r'1x(\d\d)', fp).group(1)))
        if 'DSUB' in fp:
            return 'J DE-9'
    raise KeyError(f'{ref} ({valor}, {fp}) sem regra em chave()')


def ordem(r):
    return ''.join(ch for ch in r if ch.isalpha()), int(''.join(ch for ch in r if ch.isdigit()) or 0)


def main():
    with tempfile.TemporaryDirectory() as d:
        net = os.path.join(d, 'n.xml')
        subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', net, SCH],
                       check=True, capture_output=True)
        raiz = ET.parse(net).getroot()
    tabela = {l['chave']: l for l in csv.DictReader(open(TABELA, encoding='utf-8'), delimiter=';')}
    grupos = collections.OrderedDict()
    for c in raiz.iter('comp'):
        ref, valor = c.get('ref'), c.findtext('value')
        fp = (c.findtext('footprint') or '').split(':')[-1]
        if ref.startswith('#') or ref.startswith('H'):
            continue
        k = chave(ref, valor, fp)
        if k is None:
            continue
        if k not in tabela:
            sys.exit(f'{ref}: chave {k!r} não existe em lcsc.csv')
        grupos.setdefault(k, []).append((ref, valor, fp))
    os.makedirs(os.path.dirname(SAIDA), exist_ok=True)
    fora, n = [], 0
    with open(SAIDA, 'w', encoding='utf-8', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
        for k, comps in sorted(grupos.items(), key=lambda g: ordem(sorted(c[0] for c in g[1])[0])):
            t = tabela[k]
            refs = ','.join(sorted((c[0] for c in comps), key=ordem))
            if t['lcsc'] == 'FORA':
                fora.append((refs, t['mpn'], t['nota']))
                continue
            w.writerow([t['mpn'], refs, comps[0][2], t['lcsc']])
            n += len(comps)
    print(f'{os.path.relpath(SAIDA, HW)}: {n} peças, {len(grupos) - len(fora)} códigos LCSC')
    for refs, mpn, nota in fora:
        print(f'  fora da JLCPCB: {refs} {mpn} ({nota})')
    notas = [(k, t['nota']) for k, t in tabela.items() if t['nota'] and t['lcsc'] != 'FORA' and k in grupos]
    for k, nota in notas:
        print(f'  nota: {k}: {nota}')


if __name__ == '__main__':
    main()
