"""Gera o projeto KiCad em hardware/. Uso: python3 -I gerar.py"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from hw import raiz
import folha_alimentacao
import folha_mcu
import folhas_interfaces as fi

PASTA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
folhas = [folha_alimentacao.folha(), folha_mcu.folha(), fi.ethernet(), fi.can(), fi.serie(), fi.i2c_gps(), fi.pwm()]
raiz(PASTA, 'laset_gateway', folhas, 'Gateway multiprotocolo LASET')
print('ok:', [f.ficheiro for f in folhas])
