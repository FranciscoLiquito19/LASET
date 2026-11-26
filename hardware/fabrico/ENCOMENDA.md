# Encomendar a placa na JLCPCB

Ficheiros desta pasta (gerados a partir do desenho; ver o fim):

| Ficheiro | Para quê |
|---|---|
| `laset_gateway_gerbers.zip` | fazer a placa nua (cobre, máscara, serigrafia, furos) |
| `laset_gateway_bom_jlcpcb.csv` | lista de material com o código LCSC de cada peça, para a montagem |
| `laset_gateway_posicoes.csv` | posição, face e rotação de cada peça, para a montagem |

## 1. Placa

Em jlcpcb.com, "Order now", carregar `laset_gateway_gerbers.zip`. O site lê o tamanho
(100 × 100 mm) e as 4 camadas. Escolher:

| Opção | Valor | Porquê |
|---|---|---|
| Layers | 4 | |
| PCB Thickness | 1,6 mm | |
| Specify Stackup | JLC04161H-7628 | é a pilha para que a placa foi desenhada |
| Surface Finish | ENIG | pads planos, melhor para o LQFP-144 e os QFN de passo 0,5 mm |
| Via Covering | Epoxy Filled & Capped | 8 vias tocam em pads; cheias e tapadas não puxam a solda (tem custo extra em 4 camadas) |
| Outer / Inner Copper | 1 oz / 0,5 oz | valores normais da pilha |
| Quantidade | 5 (mínimo) | |

## 2. Montagem (PCBA)

Ativar "PCB Assembly":

- **PCBA Type: Standard.** Há 5 condensadores na face de baixo (C34, C35, C61, C62, C63) e
  a montagem Economic só faz uma face. Alternativa mais barata: Economic só na face de cima
  e soldar esses 5 à mão (0603 e 0805).
- **Assembly Side: Both sides** (com Standard).
- **Quantidade montada: 2** chega para os ensaios.
- Carregar `laset_gateway_bom_jlcpcb.csv` como BOM e `laset_gateway_posicoes.csv` como CPL.

Na página seguinte o site mostra cada peça com o código LCSC. Confirmar que nenhuma ficou
"out of stock" (o stock muda; foi visto a 26/11/2026). A peça com menos margem é o
MAX3227EEAE+ (U8, 9 unidades em stock).

Depois aparece a pré-visualização da placa com as peças: **verificar a rotação de cada peça
polarizada** (circuitos integrados, díodos, LED, condensadores eletrolíticos, MOSFET). O
ponto ou chanfro do pino 1 da peça tem de coincidir com a marca na placa. As bibliotecas
do KiCad e da JLCPCB nem sempre usam a mesma rotação de referência; quando não coincide,
roda-se a peça ali mesmo, na pré-visualização.

As peças de furo passante (bornes, fichas JST, barras de pinos, RJ45) também estão na
lista. Se o preço da montagem passante for alto, podem tirar-se da lista e soldar à mão.

## 3. Peças que não estão na JLCPCB

| Ref. | Peça | Onde |
|---|---|---|
| U14 | ADuM6401ARWZ (isolador do PWM) | DigiKey ou Mouser; soldar à mão (SOIC-16 largo, fácil) ou usar "Global Sourcing" da JLCPCB, que a compra e monta |
| J7 | DE-9 fêmea a 90° para circuito impresso | qualquer distribuidor; soldar à mão |

Substituições feitas por falta de stock (mesmo footprint e valores equivalentes):

- L2: Sunlord SWPA6045S2R2MT (2,2 µH, 6 × 6 mm) no lugar do Bourns SRN6045TA-2R2M.
  Confirmar que os pads do footprint servem (os dois são 6 × 6 mm).
- Y1, Y2: Yangxing X322525MMB4SI (25 MHz, 10 pF, 3225) no lugar do CTS 425F22A025M0000.
- R41 a R44: 62 Ω 1 % no lugar de 60,4 Ω (124 Ω no total por barramento CAN, dentro
  dos 100 a 130 Ω da norma). Já está assim no esquema.

## Gerar outra vez

Se a placa ou o esquema mudarem, a partir de `hardware/`:

```sh
python3 -I gerador/fabrico.py   # Gerbers e posições
python3 -I gerador/jlcpcb.py    # lista de material com os códigos LCSC
```

Os códigos estão em `hardware/bom/lcsc.csv`; para trocar uma peça basta mudar a linha.
