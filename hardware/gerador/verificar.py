"""Verifica as ligações do esquema a partir da netlist do KiCad.

Uso (depois de gerar.py):  python3 -I verificar.py
Precisa do kicad-cli (KiCad 7 ou mais recente) no PATH.

Assinala:
  - pinos cuja rede na netlist não é a pretendida no gerador (ligacoes.csv): apanha
    redes fundidas porque dois fios ou etiquetas se tocam no desenho;
  - redes com um só pino (etiqueta mal escrita ou pino esquecido), exceto pinos NC;
  - sinais globais que não saem da folha onde nascem (exceto os da lista LOCAIS_OK).
Não substitui o ERC do KiCad (Inspecionar > Verificador de regras elétricas),
que também confirma tipos de pino e alimentações.
"""
import os
import re
import subprocess
import sys
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
SCH = os.path.join(AQUI, '..', 'laset_gateway.kicad_sch')
ALIM = {'GND', '+3V3', '+5V'}
LOCAIS_OK = {'VIN'}  # rede global usada só na folha de alimentação


def main():
    with tempfile.TemporaryDirectory() as d:
        net = os.path.join(d, 'n.net')
        subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', net, SCH],
                       check=True, capture_output=True)
        t = open(net, encoding='utf-8').read()
    folha_de = dict(re.findall(r'\(comp \(ref "([^"]+)"\).*?\(sheetpath \(names "([^"]*)"', t, re.S))
    erros = []
    blocos = t.split('(net (code')[1:]
    for b in blocos:
        nome = re.search(r'\(name "([^"]*)"\)', b).group(1)
        refs = re.findall(r'\(node \(ref "([^"]+)"\)', b)
        if len(refs) < 2 and 'no_connect' not in b:
            erros.append(f'rede com um só pino: {nome} {refs}')
        global_ = not (nome.startswith('/') or nome.startswith('unconnected') or nome.startswith('Net-'))
        if global_ and nome not in ALIM | LOCAIS_OK and len({folha_de.get(r) for r in refs}) < 2:
            erros.append(f'sinal global numa só folha: {nome}')
    rede_de = {}
    for b in blocos:
        nome = re.search(r'\(name "([^"]*)"\)', b).group(1)
        for r, p in re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', b):
            rede_de[(r, p)] = nome
    lig = os.path.join(AQUI, 'ligacoes.csv')
    if os.path.exists(lig):
        for linha in open(lig, encoding='utf-8').read().splitlines()[1:]:
            r, p, pretendida = linha.split(';')
            real = rede_de.get((r, p))
            if real != pretendida:
                erros.append(f'{r}.{p}: pretendida {pretendida}, na netlist {real}')
    print(f'{len(blocos)} redes, {len(folha_de)} componentes')
    for e in erros:
        print('ERRO:', e)
    sys.exit(1 if erros else 0)


if __name__ == '__main__':
    main()
