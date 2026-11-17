"""Gerador de esquemas KiCad para o projeto LASET.

Cada folha é descrita em Python: componentes, posição e a rede de cada pino.
As ligações são feitas por etiquetas (labels) e símbolos de alimentação, o que
mantém o esquema legível sem desenhar fios longos.
"""
import copy
import os
import uuid

from kiutils.items.common import Effects, Font, Justify, PageSettings, Position, Property, TitleBlock
from kiutils.items.schitems import (Connection, GlobalLabel, HierarchicalSheet, HierarchicalSheetInstance,
                                    LocalLabel, NoConnect, SchematicSymbol, SymbolInstance, Text)
from kiutils.schematic import Schematic
from kiutils.symbol import SymbolLib

KICAD_LIBS = '/usr/share/kicad/symbols'
AQUI = os.path.dirname(os.path.abspath(__file__))
LIB_PROJETO = os.path.join(AQUI, '..', 'lib', 'laset.kicad_sym')

# Redes desenhadas com símbolo de alimentação; as restantes usam etiquetas.
REDES_ALIMENTACAO = {'GND': 'GND', '+5V': '+5V', '+3V3': '+3V3'}
STUB = 2.54

_libs = {}
_contador = [0]  # numeração única de #PWR/#FLG em todas as folhas


def _lib(nick):
    if nick not in _libs:
        path = LIB_PROJETO if nick == 'laset' else os.path.join(KICAD_LIBS, nick + '.kicad_sym')
        _libs[nick] = {s.entryName: s for s in SymbolLib.from_file(path).symbols}
    return _libs[nick]


def simbolo(lib_id):
    """Devolve o símbolo da biblioteca já 'achatado' (sem extends)."""
    nick, name = lib_id.split(':')
    lib = _lib(nick)
    s = lib[name]
    if s.extends:
        base = copy.deepcopy(lib[s.extends])
        base.entryName = name
        for u in base.units:
            u.entryName = name
        props = {p.key: p for p in s.properties}
        for p in base.properties:
            if p.key in props:
                p.value = props[p.key].value
        base.extends = None
    else:
        base = copy.deepcopy(s)
    base.libraryNickname = nick
    return base


def pinos(sym):
    out = []
    for u in sym.units:
        if u.unitId in (0, 1, None):
            out.extend(u.pins)
    return out


def grelha(v, passo=2.54):
    """Arredonda à grelha de ligação do KiCad (100 mil)."""
    return round(round(v / passo) * passo, 2)


def _u():
    return str(uuid.uuid4())


def _fx(size=1.27, hide=False, just=None):
    e = Effects(font=Font(height=size, width=size), hide=hide)
    if just:
        e.justify = Justify(horizontally=just)
    return e


class Folha:
    def __init__(self, titulo, ficheiro, notas=()):
        self.titulo = titulo
        self.ficheiro = ficheiro
        self.sch = Schematic.create_new()
        self.sch.version = '20211123'
        self.sch.generator = 'eeschema'
        self.sch.uuid = _u()
        self.sch.paper = PageSettings(paperSize='A3')
        self.sch.titleBlock = TitleBlock(title=titulo, company='LASET 2026/2027', comments={1: 'Francisco Liquito, Pedro Ribeiro', 2: 'Gerado por hardware/gerador'})
        self.libs = {}
        self.refs = []
        self.npwr = 0
        y = 20
        for n in notas:
            self.texto(n, 20, y)
            y += 5

    def texto(self, t, x, y, size=1.5):
        self.sch.texts.append(Text(text=t, position=Position(x, y, 0), effects=_fx(size, just='left'), uuid=_u()))

    def _add_lib(self, sym):
        key = sym.libId
        if key not in self.libs:
            self.libs[key] = sym
            self.sch.libSymbols.append(sym)

    def _instancia(self, sym, ref, valor, x, y, footprint='', rot=0, extra=None):
        self._add_lib(sym)
        s = SchematicSymbol()
        s.libraryNickname = sym.libraryNickname
        s.entryName = sym.entryName
        s.position = Position(x, y, rot)
        s.unit = 1
        s.inBom = not ref.startswith('#')
        s.onBoard = not ref.startswith('#')
        s.uuid = _u()
        base = {p.key: p.value for p in sym.properties}
        fp = footprint or base.get('Footprint', '')
        hide_ref = ref.startswith('#')
        s.properties = [
            Property(key='Reference', value=ref, id=0, position=Position(x, y - 3, 0), effects=_fx(hide=hide_ref)),
            Property(key='Value', value=valor, id=1, position=Position(x, y + 3, 0), effects=_fx()),
            Property(key='Footprint', value=fp, id=2, position=Position(x, y, 0), effects=_fx(hide=True)),
            Property(key='Datasheet', value=base.get('Datasheet', ''), id=3, position=Position(x, y, 0), effects=_fx(hide=True)),
        ]
        for i, (k, v) in enumerate((extra or {}).items()):
            s.properties.append(Property(key=k, value=v, id=4 + i, position=Position(x, y, 0), effects=_fx(hide=True)))
        s.pins = {p.number: _u() for p in pinos(sym)}
        self.sch.schematicSymbols.append(s)
        self.refs.append((ref, s))
        return s

    def _pwr(self, rede, x, y, d):
        """Símbolo de alimentação na ponta do stub, orientado no sentido d."""
        _contador[0] += 1
        self.npwr = _contador[0]
        sym = simbolo('power:' + REDES_ALIMENTACAO[rede])
        if rede == 'GND':
            rot = {(0, 1): 0, (0, -1): 180, (1, 0): 90, (-1, 0): 270}[d]
        else:
            rot = {(0, -1): 0, (0, 1): 180, (1, 0): 270, (-1, 0): 90}[d]
        self._instancia(sym, '#PWR%03d' % self.npwr, rede, x, y, rot=rot)

    def flag(self, rede, x, y):
        """PWR_FLAG: indica ao ERC que a rede é alimentada (ex.: saída de um conversor)."""
        x, y = grelha(x), grelha(y)
        _contador[0] += 1
        self.npwr = _contador[0]
        sym = simbolo('power:PWR_FLAG')
        self._instancia(sym, '#FLG%03d' % self.npwr, 'PWR_FLAG', x, y)
        self._ligar(rede, x, y, (0, 1))

    def _ligar(self, rede, x, y, d):
        ex, ey = x + d[0] * STUB, y + d[1] * STUB
        self.sch.graphicalItems.append(Connection(type='wire', points=[Position(x, y), Position(ex, ey)], uuid=_u()))
        if rede in REDES_ALIMENTACAO:
            self._pwr(rede, ex, ey, d)
            return
        ang = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[d]
        just = 'right' if ang in (180, 270) else 'left'
        if rede.startswith('/'):
            # rede local à folha
            self.sch.labels.append(LocalLabel(text=rede[1:], position=Position(ex, ey, ang), effects=_fx(just=just), uuid=_u()))
        else:
            self.sch.globalLabels.append(GlobalLabel(text=rede, shape='bidirectional', position=Position(ex, ey, ang), effects=_fx(just=just), uuid=_u()))

    def comp(self, ref, lib_id, valor, x, y, ligacoes, footprint='', nc=(), extra=None, resto_nc=False):
        """Coloca um componente. ligacoes: {numero_ou_nome_do_pino: rede}.

        Redes começadas por '/' são locais à folha; as outras são globais
        (ligam entre folhas). GND, +5V e +3V3 usam símbolos de alimentação.
        """
        x, y = grelha(x), grelha(y)
        sym = simbolo(lib_id)
        self._instancia(sym, ref, valor, x, y, footprint, extra=extra)
        ps = pinos(sym)
        por_nome = {}
        for p in ps:
            por_nome.setdefault(p.name, []).append(p)
        feitos = set()
        for chave, rede in ligacoes.items():
            alvo = [p for p in ps if p.number == str(chave)] or por_nome.get(str(chave), [])
            if not alvo:
                raise KeyError(f'{ref}: pino {chave} não existe em {lib_id}')
            for p in alvo:
                self._pino(p, x, y, rede)
                feitos.add(p.number)
        for p in ps:
            if p.number in feitos:
                continue
            if resto_nc or p.electricalType == 'no_connect' or p.number in [str(n) for n in nc] or p.name in nc:
                px, py = x + p.position.X, y - p.position.Y
                self.sch.noConnects.append(NoConnect(position=Position(px, py), uuid=_u()))
            else:
                raise ValueError(f'{ref}: pino {p.number} ({p.name}) sem ligação')

    def _pino(self, p, x, y, rede):
        px, py = x + p.position.X, y - p.position.Y
        a = int(p.position.angle or 0) % 360
        d = {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[a]
        self._ligar(rede, px, py, d)

    def guardar(self, pasta):
        self.sch.filePath = os.path.join(pasta, self.ficheiro)
        self.sch.to_file()


def raiz(pasta, nome, folhas, titulo):
    """Cria o esquema raiz com uma caixa de folha por cada sub-folha."""
    r = Schematic.create_new()
    r.version = '20211123'
    r.generator = 'eeschema'
    r.uuid = _u()
    r.paper = PageSettings(paperSize='A3')
    r.titleBlock = TitleBlock(title=titulo, company='LASET 2026/2027', comments={1: 'Francisco Liquito, Pedro Ribeiro'})
    r.sheetInstances.append(HierarchicalSheetInstance(instancePath='/', page='1'))
    for i, f in enumerate(folhas):
        x = 30 + (i % 4) * 90
        y = 40 + (i // 4) * 60
        hs = HierarchicalSheet(position=Position(x, y), width=70, height=40, uuid=_u())
        hs.sheetName = Property(key='Sheet name', value=f.titulo, id=0, position=Position(x, y - 0.7, 0), effects=_fx(just='left'))
        hs.fileName = Property(key='Sheet file', value=f.ficheiro, id=1, position=Position(x, y + 40.7, 0), effects=_fx(just='left'))
        r.sheets.append(hs)
        r.sheetInstances.append(HierarchicalSheetInstance(instancePath='/' + hs.uuid, page=str(i + 2)))
        for ref, s in f.refs:
            r.symbolInstances.append(SymbolInstance(path='/' + hs.uuid + '/' + s.uuid, reference=ref, unit=1,
                                                    value=[p.value for p in s.properties if p.key == 'Value'][0],
                                                    footprint=[p.value for p in s.properties if p.key == 'Footprint'][0]))
        f.guardar(pasta)
    r.filePath = os.path.join(pasta, nome + '.kicad_sch')
    r.to_file()
    pro = os.path.join(pasta, nome + '.kicad_pro')
    if not os.path.exists(pro):
        with open(pro, 'w') as fh:
            fh.write('{\n  "meta": {"filename": "%s.kicad_pro", "version": 1}\n}\n' % nome)
    with open(os.path.join(pasta, 'sym-lib-table'), 'w') as fh:
        fh.write('(sym_lib_table\n  (lib (name "laset")(type "KiCad")(uri "${KIPRJMOD}/lib/laset.kicad_sym")(options "")(descr "Símbolos do projeto LASET"))\n)\n')
