#!/usr/bin/env python3
"""Cliente do PC para o gateway LASET pela ligação série (RS232 ou VCP da NUCLEO).

Cada trama é COBS(cabeçalho de 20 bytes + dados + CRC-16/CCITT-FALSE, little-endian)
seguida de 0x00, como em firmware/Core/Src/serie.c.

Exemplos (precisa de pyserial: pip install pyserial):
  python3 laset_pc.py --porta COM5 versao
  python3 laset_pc.py --porta COM5 can --canal 1 --id 0x123 --fd --brs 01 02 03
  python3 laset_pc.py --porta COM5 pwm --canal 0 --us 1500
  python3 laset_pc.py --porta COM5 i2c-ler --canal 0 --end 0x48 --n 2 --reg 0x00
  python3 laset_pc.py --porta COM5 ouvir
  python3 laset_pc.py autoteste          # não precisa da placa
"""
import argparse
import struct
import sys
import time

IF = {'i2c': 0, 'rs232': 1, 'rs485': 2, 'canfd': 3, 'eth': 4, 'pwm': 5, 'sistema': 6}
IF_NOME = {v: k for k, v in IF.items()}
PEDIDO, DADOS, CONFIRMACAO, ERRO, CONFIG = range(5)
URGENTE = 0x80
CAN_EXT, CAN_FD, CAN_BRS = 1 << 31, 1 << 30, 1 << 29
CAB = struct.Struct('<BBBBIHQH')   # versão, tipo, interface, canal, endereço, sequência, marca_us, comprimento


def crc16(d: bytes) -> int:
    crc = 0xFFFF
    for b in d:
        crc ^= b << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021) & 0xFFFF if crc & 0x8000 else (crc << 1) & 0xFFFF
    return crc


def cobs_cod(d: bytes) -> bytes:
    out, bloco = bytearray(), bytearray()
    for i, b in enumerate(d):
        if b == 0:
            out += bytes([len(bloco) + 1]) + bloco
            bloco = bytearray()
        else:
            bloco.append(b)
            if len(bloco) == 254 and i + 1 < len(d):
                out += b'\xff' + bloco
                bloco = bytearray()
    return bytes(out + bytes([len(bloco) + 1]) + bloco)


def cobs_desc(d: bytes) -> bytes:
    out, i = bytearray(), 0
    while i < len(d):
        c = d[i]
        if c == 0 or i + c > len(d):
            raise ValueError('COBS inválido')
        out += d[i + 1:i + c]
        i += c
        if c != 0xFF and i < len(d):
            out.append(0)
    return bytes(out)


def trama(tipo, interface, canal=0, endereco=0, dados=b'', seq=0, marca=0) -> bytes:
    bruto = CAB.pack(1, tipo, interface, canal, endereco, seq, marca, len(dados)) + bytes(dados)
    return cobs_cod(bruto + struct.pack('<H', crc16(bruto))) + b'\x00'


def ler_trama(raw: bytes):
    d = cobs_desc(raw)
    if len(d) < CAB.size + 2 or crc16(d[:-2]) != struct.unpack('<H', d[-2:])[0]:
        raise ValueError('CRC ou tamanho inválido')
    v, tipo, itf, canal, end, seq, marca, n = CAB.unpack(d[:CAB.size])
    return dict(tipo=tipo & 0x7F, urgente=bool(tipo & URGENTE), interface=IF_NOME.get(itf, itf),
                canal=canal, endereco=end, sequencia=seq, marca_us=marca, dados=d[CAB.size:CAB.size + n])


def autoteste():
    assert crc16(b'123456789') == 0x29B1
    for n in (0, 1, 253, 254, 255, 600):
        d = bytes((i * 37) % 5 and i % 256 for i in range(n))
        assert cobs_desc(cobs_cod(d)) == d
    t = trama(DADOS, IF['canfd'], 1, 0x123 | CAN_FD | CAN_BRS, b'\x01\x00\x02', seq=7, marca=1_000_000)
    assert ler_trama(t[:-1])['dados'] == b'\x01\x00\x02'
    print('vetor de teste:', t.hex())
    print('autoteste ok')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--porta')
    ap.add_argument('--baud', type=int, default=1_000_000)
    sub = ap.add_subparsers(dest='cmd', required=True)
    sub.add_parser('autoteste')
    sub.add_parser('versao')
    sub.add_parser('ouvir')
    c = sub.add_parser('can'); c.add_argument('--canal', type=int, default=0); c.add_argument('--id', type=lambda x: int(x, 0))
    c.add_argument('--ext', action='store_true'); c.add_argument('--fd', action='store_true'); c.add_argument('--brs', action='store_true')
    c.add_argument('--urgente', action='store_true'); c.add_argument('dados', nargs='*')
    p = sub.add_parser('pwm'); p.add_argument('--canal', type=int, default=0); p.add_argument('--us', type=int, required=True)
    i = sub.add_parser('i2c-ler'); i.add_argument('--canal', type=int, default=0); i.add_argument('--end', type=lambda x: int(x, 0))
    i.add_argument('--n', type=int, default=1); i.add_argument('--reg', type=lambda x: int(x, 0))
    a = ap.parse_args()
    if a.cmd == 'autoteste':
        return autoteste()
    import serial  # pyserial
    s = serial.Serial(a.porta, a.baud, timeout=0.1)
    if a.cmd == 'versao':
        s.write(trama(PEDIDO, IF['sistema']))
    elif a.cmd == 'can':
        end = a.id | (CAN_EXT if a.ext else 0) | (CAN_FD if a.fd else 0) | (CAN_BRS if a.brs else 0)
        s.write(trama(DADOS | (URGENTE if a.urgente else 0), IF['canfd'], a.canal, end, bytes(int(x, 16) for x in a.dados)))
    elif a.cmd == 'pwm':
        s.write(trama(DADOS, IF['pwm'], a.canal, 0, struct.pack('<H', a.us)))
    elif a.cmd == 'i2c-ler':
        s.write(trama(PEDIDO, IF['i2c'], a.canal, a.end, bytes([a.n]) + (bytes([a.reg]) if a.reg is not None else b'')))
    buf, fim = bytearray(), time.time() + (1e9 if a.cmd == 'ouvir' else 1.0)
    while time.time() < fim:
        buf += s.read(256)
        while b'\x00' in buf:
            raw, _, buf = bytes(buf).partition(b'\x00')
            buf = bytearray(buf)
            try:
                print(ler_trama(raw))
            except ValueError as e:
                print('trama inválida:', e)


if __name__ == '__main__':
    sys.exit(main())
