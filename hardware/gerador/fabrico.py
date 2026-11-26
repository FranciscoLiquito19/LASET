"""Ficheiros de fabrico para a JLCPCB (Gerbers, furação e posições para montagem).

Uso:  python3 -I fabrico.py      (precisa do kicad-cli, KiCad 7 ou mais recente)

Escreve em hardware/fabrico/ (fora do repositório):
  - laset_gateway_gerbers.zip: Gerbers das 4 camadas de cobre, máscaras, serigrafia,
    pasta e contorno, mais a furação Excellon; é este o ficheiro que se envia à JLCPCB;
  - laset_gateway_posicoes.csv: posição e rotação de cada componente (CPL), no formato
    que a JLCPCB pede para a montagem.

Só faz sentido depois de a placa estar encaminhada e com o DRC limpo no KiCad.
"""
import csv
import os
import subprocess
import sys
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
HW = os.path.normpath(os.path.join(AQUI, '..'))
PCB = os.path.join(HW, 'laset_gateway.kicad_pcb')
SAIDA = os.path.join(HW, 'fabrico')
CAMADAS = ['F.Cu', 'In1.Cu', 'In2.Cu', 'B.Cu', 'F.Mask', 'B.Mask', 'F.Silkscreen', 'B.Silkscreen',
           'F.Paste', 'B.Paste', 'Edge.Cuts']


def correr(*args):
    r = subprocess.run(['kicad-cli', *args], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(r.stderr or r.stdout)


def main():
    g = os.path.join(SAIDA, 'gerbers')
    os.makedirs(g, exist_ok=True)
    for f in os.listdir(g):
        os.remove(os.path.join(g, f))
    correr('pcb', 'export', 'gerbers', '--layers', ','.join(CAMADAS), '--subtract-soldermask',
           '--no-x2', '-o', g + os.sep, PCB)
    correr('pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th',
           '--generate-map', '--map-format', 'gerberx2', '-o', g + os.sep, PCB)
    z = os.path.join(SAIDA, 'laset_gateway_gerbers.zip')
    with zipfile.ZipFile(z, 'w', zipfile.ZIP_DEFLATED) as fh:
        for f in sorted(os.listdir(g)):
            fh.write(os.path.join(g, f), f)

    pos = os.path.join(SAIDA, 'posicoes_kicad.csv')
    correr('pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'both', '--use-drill-file-origin',
           '-o', pos, PCB)
    cpl = os.path.join(SAIDA, 'laset_gateway_posicoes.csv')
    with open(pos, encoding='utf-8') as fi, open(cpl, 'w', newline='', encoding='utf-8') as fo:
        w = csv.writer(fo)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        for row in csv.DictReader(fi):
            if row['Ref'].startswith(('H', 'TP')):
                continue
            w.writerow([row['Ref'], row['PosX'] + 'mm', row['PosY'] + 'mm',
                        'Top' if row['Side'] == 'top' else 'Bottom', row['Rot']])
    os.remove(pos)
    print('ok:', os.path.relpath(z, HW), os.path.relpath(cpl, HW))


if __name__ == '__main__':
    main()
