"""Gera o projeto KiCad em hardware/. Uso: python3 -I gerar.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hw import raiz
import folha_alimentacao, folha_mcu, folha_ethernet, folha_can, folha_serie, folha_i2c_gps, folha_pwm

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
folhas = [m.folha() for m in (folha_alimentacao, folha_mcu, folha_ethernet, folha_can,
                                folha_serie, folha_i2c_gps, folha_pwm)]
refs = [r for f in folhas for r, _ in f.refs if not r.startswith('#')]
dup = sorted({r for r in refs if refs.count(r) > 1})
if dup:
    raise SystemExit('referências repetidas: ' + ', '.join(dup))
raiz(PASTA, 'laset_gateway', folhas, 'Gateway multiprotocolo LASET')

# Ligações pretendidas, pino a pino, para o verificar.py comparar com a netlist do KiCad.
# Apanha redes fundidas por fios ou etiquetas que se tocam no desenho.
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ligacoes.csv'), 'w', encoding='utf-8') as fh:
    fh.write('ref;pino;rede\n')
    for f in folhas:
        for ref, pino, rede in f.ligacoes:
            nome = '/%s/%s' % (f.titulo, rede[1:]) if rede.startswith('/') else rede
            fh.write('%s;%s;%s\n' % (ref, pino, nome))
print('ok:', [f.ficheiro for f in folhas], len(refs), 'componentes')
