#!/usr/bin/env python3
"""Cliente do PC para o gateway LASET.

Ligações:
  --porta COM5        série (RS232 ou conversor USB-série): tramas COBS(cabeçalho de
                      20 bytes + dados + CRC-16/CCITT-FALSE LE) terminadas por 0x00
  --udp 192.168.1.50  Ethernet, UDP 5000: um datagrama por mensagem, sem COBS nem CRC
  --tcp 192.168.1.50  Ethernet, TCP 5001 (configuração): tramas COBS, como na série

Exemplos (a série precisa de pyserial: pip install pyserial):
  python3 laset_pc.py --porta COM5 versao
  python3 laset_pc.py --udp 192.168.1.50 can --canal 1 --id 0x123 --fd --brs 01 02 03
  python3 laset_pc.py --porta COM5 pwm --canal 0 --us 1500
  python3 laset_pc.py --porta COM5 i2c-ler --canal 0 --end 0x48 --n 2 --reg 0x00
  python3 laset_pc.py --tcp 192.168.1.50 cfg-ler
  python3 laset_pc.py --tcp 192.168.1.50 cfg-regra --de canfd:1 --para rs485:0 --ids 0x100-0x1ff --urgente
  python3 laset_pc.py --tcp 192.168.1.50 cfg-ligacao eth:0
  python3 laset_pc.py --tcp 192.168.1.50 cfg-gravar
  python3 laset_pc.py --porta COM5 ouvir
  python3 laset_pc.py autoteste          # não precisa da placa
"""
import argparse
import socket
import struct
import sys
import time

IF = {'i2c': 0, 'rs232': 1, 'rs485': 2, 'canfd': 3, 'eth': 4, 'pwm': 5, 'sistema': 6}
IF_NOME = {v: k for k, v in IF.items()}
PEDIDO, DADOS, CONFIRMACAO, ERRO, CONFIG = range(5)
URGENTE = 0x80
CAN_EXT, CAN_FD, CAN_BRS = 1 << 31, 1 << 30, 1 << 29
CFG = dict(ler=1, ler_regra=2, adicionar_regra=3, apagar_regras=4, ligacao_pc=5, rede=6, serie=7,
           gravar=8, omissao=9)
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


def bruto(tipo, interface, canal=0, endereco=0, dados=b'', seq=0, marca=0) -> bytes:
    return CAB.pack(1, tipo, interface, canal, endereco, seq, marca, len(dados)) + bytes(dados)


def trama(*a, **k) -> bytes:
    b = bruto(*a, **k)
    return cobs_cod(b + struct.pack('<H', crc16(b))) + b'\x00'


def ler_bruto(d: bytes):
    v, tipo, itf, canal, end, seq, marca, n = CAB.unpack(d[:CAB.size])
    return dict(tipo=tipo & 0x7F, urgente=bool(tipo & URGENTE), interface=IF_NOME.get(itf, itf),
                canal=canal, endereco=end, sequencia=seq, marca_us=marca, dados=d[CAB.size:CAB.size + n])


def ler_trama(raw: bytes):
    d = cobs_desc(raw)
    if len(d) < CAB.size + 2 or crc16(d[:-2]) != struct.unpack('<H', d[-2:])[0]:
        raise ValueError('CRC ou tamanho inválido')
    return ler_bruto(d[:-2])


def destino(txt):
    """'canfd:1' -> (3, 1)"""
    nome, _, canal = txt.partition(':')
    return IF[nome], int(canal or 0)


def regra(de, para, ids, urgente):
    oi, oc = destino(de) if de != '*' else (0xFF, 0xFF)
    di, dc = destino(para)
    a, _, b = ids.partition('-')
    return struct.pack('<BBBBBII', oi, oc, di, dc, int(urgente), int(a, 0), int(b or a, 0))


def mostrar(r):
    d = r['dados']
    if r['interface'] == 'sistema' and r['tipo'] in (CONFIRMACAO, ERRO) and d:
        nome = {v: k for k, v in CFG.items()}.get(d[0], d[0])
        print('config', nome, 'ok' if r['tipo'] == CONFIRMACAO else 'ERRO', end='')
        if r['tipo'] == CONFIRMACAO and d[0] == CFG['ler'] and len(d) >= 28:
            pc_if, pc_c, n = d[1:4]
            print(f": PC em {IF_NOME.get(pc_if)}:{pc_c}, {n} regras, IP {'.'.join(map(str, d[4:8]))}/"
                  f"{'.'.join(map(str, d[8:12]))} gw {'.'.join(map(str, d[12:16]))}, UDP {d[16] | d[17] << 8}, "
                  f"TCP {d[18] | d[19] << 8}, RS232 {struct.unpack('<I', d[20:24])[0]}, RS485 {struct.unpack('<I', d[24:28])[0]}")
        else:
            print('', d[1:].hex())
    else:
        print(r)


class Serie:
    """Fluxo de tramas COBS: série ou TCP."""
    def __init__(self, ler, escrever):
        self.ler, self.escrever, self.buf = ler, escrever, bytearray()

    def enviar(self, b):
        self.escrever(cobs_cod(b + struct.pack('<H', crc16(b))) + b'\x00')

    def receber(self):
        self.buf += self.ler()
        out = []
        while b'\x00' in self.buf:
            raw, _, resto = bytes(self.buf).partition(b'\x00')
            self.buf = bytearray(resto)
            try:
                out.append(ler_trama(raw))
            except ValueError as e:
                print('trama inválida:', e)
        return out


def ligar_serie(porta, baud):
    import serial  # pyserial
    s = serial.Serial(porta, baud, timeout=0.1)
    return Serie(lambda: s.read(256), s.write)


def ligar_tcp(ip, porta):
    s = socket.create_connection((ip, porta), timeout=2)
    s.settimeout(0.1)

    def ler():
        try:
            return s.recv(256)
        except socket.timeout:
            return b''
    return Serie(ler, s.sendall)


class Udp:
    def __init__(self, ip, porta):
        self.dest = (ip, porta)
        self.s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.s.settimeout(0.1)

    def enviar(self, b):
        self.s.sendto(b, self.dest)

    def receber(self):
        try:
            return [ler_bruto(self.s.recv(2048))]
        except socket.timeout:
            return []


def autoteste():
    assert crc16(b'123456789') == 0x29B1
    for n in (0, 1, 253, 254, 255, 600):
        d = bytes((i * 37) % 5 and i % 256 for i in range(n))
        assert cobs_desc(cobs_cod(d)) == d
    t = trama(DADOS, IF['canfd'], 1, 0x123 | CAN_FD | CAN_BRS, b'\x01\x00\x02', seq=7, marca=1_000_000)
    assert ler_trama(t[:-1])['dados'] == b'\x01\x00\x02'
    # regra com o mesmo formato que o teste do firmware (t_config em teste_modulos.c)
    assert regra('canfd:1', 'rs485:0', '0x100-0x1ff', True).hex() == '030102000100010000ff010000'
    print('vetor de teste:', t.hex())
    print('autoteste ok')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--porta', help='porta série (COM5, /dev/ttyUSB0)')
    ap.add_argument('--baud', type=int, default=1_000_000)
    ap.add_argument('--udp', metavar='IP')
    ap.add_argument('--tcp', metavar='IP')
    ap.add_argument('--porta-udp', type=int, default=5000)
    ap.add_argument('--porta-tcp', type=int, default=5001)
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
    sub.add_parser('cfg-ler')
    r = sub.add_parser('cfg-ler-regra'); r.add_argument('i', type=int)
    r = sub.add_parser('cfg-regra', help='acrescenta uma regra de encaminhamento')
    r.add_argument('--de', default='*', help="origem, p. ex. canfd:1 ('*' = qualquer)")
    r.add_argument('--para', required=True, help='destino, p. ex. rs485:0')
    r.add_argument('--ids', default='0-0x1fffffff', help='gama de identificadores/endereços, p. ex. 0x100-0x1ff')
    r.add_argument('--urgente', action='store_true')
    sub.add_parser('cfg-apagar-regras')
    r = sub.add_parser('cfg-ligacao', help='ligação ao PC: rs232:0, canfd:0, canfd:1, eth:0 (UDP), eth:1 (TCP)'); r.add_argument('ligacao')
    r = sub.add_parser('cfg-rede'); r.add_argument('ip'); r.add_argument('mascara'); r.add_argument('gateway')
    r.add_argument('--udp', type=int, default=5000); r.add_argument('--tcp', type=int, default=5001)
    r = sub.add_parser('cfg-serie'); r.add_argument('rs232', type=int); r.add_argument('rs485', type=int)
    sub.add_parser('cfg-gravar')
    sub.add_parser('cfg-omissao')
    a = ap.parse_args()
    if a.cmd == 'autoteste':
        return autoteste()
    if a.udp:
        lig = Udp(a.udp, a.porta_udp)
    elif a.tcp:
        lig = ligar_tcp(a.tcp, a.porta_tcp)
    elif a.porta:
        lig = ligar_serie(a.porta, a.baud)
    else:
        ap.error('indicar --porta, --udp ou --tcp')

    def cfg(*b):
        lig.enviar(bruto(CONFIG, IF['sistema'], dados=bytes(b[0]) if len(b) == 1 else bytes(b)))

    ip4 = lambda t: bytes(int(x) for x in t.split('.'))
    if a.cmd == 'versao':
        lig.enviar(bruto(PEDIDO, IF['sistema']))
    elif a.cmd == 'can':
        end = a.id | (CAN_EXT if a.ext else 0) | (CAN_FD if a.fd else 0) | (CAN_BRS if a.brs else 0)
        lig.enviar(bruto(DADOS | (URGENTE if a.urgente else 0), IF['canfd'], a.canal, end, bytes(int(x, 16) for x in a.dados)))
    elif a.cmd == 'pwm':
        lig.enviar(bruto(DADOS, IF['pwm'], a.canal, 0, struct.pack('<H', a.us)))
    elif a.cmd == 'i2c-ler':
        lig.enviar(bruto(PEDIDO, IF['i2c'], a.canal, a.end, bytes([a.n]) + (bytes([a.reg]) if a.reg is not None else b'')))
    elif a.cmd == 'cfg-ler':
        cfg([CFG['ler']])
    elif a.cmd == 'cfg-ler-regra':
        cfg([CFG['ler_regra'], a.i])
    elif a.cmd == 'cfg-regra':
        cfg(bytes([CFG['adicionar_regra']]) + regra(a.de, a.para, a.ids, a.urgente))
    elif a.cmd == 'cfg-apagar-regras':
        cfg([CFG['apagar_regras']])
    elif a.cmd == 'cfg-ligacao':
        cfg([CFG['ligacao_pc'], *destino(a.ligacao)])
    elif a.cmd == 'cfg-rede':
        cfg(bytes([CFG['rede']]) + ip4(a.ip) + ip4(a.mascara) + ip4(a.gateway) + struct.pack('<HH', a.udp, a.tcp))
    elif a.cmd == 'cfg-serie':
        cfg(bytes([CFG['serie']]) + struct.pack('<II', a.rs232, a.rs485))
    elif a.cmd == 'cfg-gravar':
        cfg([CFG['gravar']])
    elif a.cmd == 'cfg-omissao':
        cfg([CFG['omissao']])
    fim = time.time() + (1e9 if a.cmd == 'ouvir' else 1.0)
    while time.time() < fim:
        for r in lig.receber():
            mostrar(r)


if __name__ == '__main__':
    sys.exit(main())
