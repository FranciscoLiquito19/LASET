"""Gera o projeto KiCad em hardware/. Uso: python3 -I gerar.py"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hw import raiz
import folha_alimentacao

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
folhas = [folha_alimentacao.folha()]
raiz(PASTA, 'laset_gateway', folhas, 'Gateway multiprotocolo LASET')
print('ok:', [f.ficheiro for f in folhas])
