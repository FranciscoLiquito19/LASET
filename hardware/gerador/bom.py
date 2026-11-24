"""Lista de material a partir do esquema.

Uso (depois de gerar.py):  python3 -I bom.py
Precisa do kicad-cli. Lê os componentes da netlist, agrupa por valor e footprint e
junta o preço de hardware/bom/precos.csv. Escreve hardware/bom/bom.csv e mostra os totais.
Para atualizar um preço basta editar precos.csv; para um componente novo, acrescentar
uma linha e, se for preciso, uma regra em chave().
"""
import collections
import csv
import os
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

AQUI = os.path.dirname(os.path.abspath(__file__))
HW = os.path.join(AQUI, '..')
SCH = os.path.join(HW, 'laset_gateway.kicad_sch')
PRECOS = os.path.join(HW, 'bom', 'precos.csv')
SAIDA = os.path.join(HW, 'bom', 'bom.csv')
EXTRAS = os.path.join(HW, 'bom', 'extras.csv')

DIRETOS = ['STM32H743ZIT6', 'LAN8742A-CZ', 'ADM3057EBRWZ', 'ADM2582EBRWZ', 'MAX3227EEAE',
           'ADuM6401ARWZ', 'TCA9406DCUR', 'TPS62162', '74AHCT1G125', 'BSC160N10NS3 G',
           'SRP1245A-180M', 'SMCJ60CA', 'MB510', 'NUP2105L', 'SM712', 'PRTR5V0U2X',
           'ESDA6V1-5SC6', 'HR911105A', '25 MHz']


def chave(ref, valor, fp):
    """Liga um componente do esquema a uma linha de precos.csv."""
    if valor == 'LM5177':
        return 'LM5177'
    for d in DIRETOS:
        if valor.startswith(d):
            return d
    if ref.startswith('TP'):
        return 'Ponto de teste'
    if ref.startswith('L') and 'SRN6045' in fp:
        return 'SRN6045TA'
    if ref.startswith('FB'):
        return 'Ferrite 0603'
    if ref.startswith('F'):
        return 'Polyfuse 1812'
    if ref.startswith('D') and 'LED' in fp:
        return 'LED 0603'
    if ref.startswith('R'):
        if '2512' in fp:
            return 'R 2512 shunt'
        return 'R 1206' if '1206' in fp else 'R 0603'
    if ref.startswith('C'):
        if 'CP_Elec_8x10' in fp:
            return 'CP 47 uF 100 V'
        if 'CP_Elec' in fp:
            return 'CP 100 uF polímero'
        if '1210' in fp:
            return 'C 1210 100 V'
        if '1206' in fp:
            return 'C 1206 2 kV' if '2 kV' in valor else 'C 1206'
        if '0805' in fp:
            return 'C 0805'
        grande = any(valor.startswith(v) for v in ('4,7 uF', '10 uF'))
        return 'C 0603 grande' if grande else 'C 0603 pequeno'
    if ref.startswith('J') or ref.startswith('JP'):
        if 'TerminalBlock' in fp:
            return 'Borne 3 vias' if '1x03' in fp else 'Borne 2 vias'
        if 'JST_PH' in fp:
            return 'JST PH ' + fp.split('_1x0')[1][0]
        if 'DSUB' in fp:
            return 'DE-9 fêmea'
        if 'RJ45' in fp:
            return 'HR911105A'
        for n in ('02', '03', '06'):
            if f'1x{n}' in fp:
                return f'Barra 1x{n}'
    raise KeyError(f'{ref} ({valor}, {fp}) sem linha em precos.csv')


def main():
    with tempfile.TemporaryDirectory() as d:
        net = os.path.join(d, 'n.xml')
        subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadxml', '-o', net, SCH],
                       check=True, capture_output=True)
        raiz = ET.parse(net).getroot()
    precos = {l['chave']: l for l in csv.DictReader(open(PRECOS, encoding='utf-8'), delimiter=';')}
    grupos = collections.OrderedDict()
    for c in raiz.iter('comp'):
        ref, valor = c.get('ref'), c.findtext('value')
        fp = (c.findtext('footprint') or '').split(':')[-1]
        if ref.startswith('#') or ref.startswith('H'):
            continue
        k = chave(ref, valor, fp)
        if k not in precos:
            sys.exit(f'chave {k!r} ({ref}) não existe em precos.csv')
        grupos.setdefault((k, valor, fp), []).append(ref)

    def ordem(r):
        letras = ''.join(ch for ch in r if ch.isalpha())
        return letras, int(''.join(ch for ch in r if ch.isdigit()) or 0)

    linhas, tot = [], collections.Counter()
    for (k, valor, fp), refs in sorted(grupos.items(), key=lambda g: ordem(sorted(g[1], key=ordem)[0])):
        p = precos[k]
        refs = sorted(refs, key=ordem)
        sub = len(refs) * float(p['preco_eur'])
        tot[p['tipo']] += sub
        linhas.append([', '.join(refs), len(refs), valor, fp, p['fabricante'], p['referencia'],
                       p['preco_eur'].replace('.', ','), f'{sub:.2f}'.replace('.', ','), p['tipo'], p['fonte']])
    with open(SAIDA, 'w', encoding='utf-8-sig', newline='') as fh:
        w = csv.writer(fh, delimiter=';')
        w.writerow(['Referências', 'Qtd', 'Valor', 'Footprint', 'Fabricante', 'Referência do fabricante',
                    'Preço unit. (€)', 'Subtotal (€)', 'Tipo de preço', 'Fonte'])
        w.writerows(linhas)
        w.writerow([])
        placa = sum(tot.values())
        for t in ('consultado', 'estimativa'):
            w.writerow(['', '', f'Placa: total {t}', '', '', '', '', f'{tot[t]:.2f}'.replace('.', ',')])
        w.writerow(['', '', 'Placa: total', '', '', '', '', f'{placa:.2f}'.replace('.', ',')])
        # Itens fora do esquema: NUCLEO, GPS, fabrico da PCB, fichas e cabos
        w.writerow([])
        w.writerow(['Fora do esquema', 'Qtd', 'Item', '', 'Fabricante', 'Referência do fabricante',
                    'Preço unit. (€)', 'Subtotal (€)', 'Tipo de preço', 'Fonte'])
        ext = collections.Counter()
        for e in csv.DictReader(open(EXTRAS, encoding='utf-8'), delimiter=';'):
            sub = int(e['qtd']) * float(e['preco_eur'])
            ext[e['tipo']] += sub
            w.writerow(['', e['qtd'], e['item'], '', e['fabricante'], e['referencia'],
                        e['preco_eur'].replace('.', ','), f'{sub:.2f}'.replace('.', ','), e['tipo'], e['fonte']])
        extras = sum(ext.values())
        w.writerow(['', '', 'Fora do esquema: total', '', '', '', '', f'{extras:.2f}'.replace('.', ',')])
        w.writerow([])
        w.writerow(['', '', 'Projeto (placa + fora do esquema)', '', '', '', '', f'{placa + extras:.2f}'.replace('.', ',')])
    n = sum(len(r) for r in grupos.values())
    print(f'{len(linhas)} linhas, {n} componentes')
    for t, v in tot.items():
        print(f'  {t}: {v:.2f} €')
    print(f'  placa: {sum(tot.values()):.2f} €')
    ext = collections.Counter()
    for e in csv.DictReader(open(EXTRAS, encoding='utf-8'), delimiter=';'):
        ext[e['tipo']] += int(e['qtd']) * float(e['preco_eur'])
    print(f'  fora do esquema: {sum(ext.values()):.2f} € ({dict(ext)})')
    print(f'  projeto: {sum(tot.values()) + sum(ext.values()):.2f} €')


if __name__ == '__main__':
    main()
