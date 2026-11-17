# Hardware do gateway LASET

Projeto KiCad do gateway multiprotocolo. O esquema é **gerado por código** a partir de
`gerador/`: cada folha é um ficheiro Python com os componentes, os valores e a rede de
cada pino. Assim cada alteração fica revista em PR, como o relatório.

## Abrir o projeto

1. Abrir `laset_gateway.kicad_pro` no KiCad (8 ou 9). Se perguntar se quer atualizar o
   formato dos ficheiros, aceitar: o gerador escreve no formato do KiCad 6/7.
2. No editor de esquemas, a folha raiz mostra uma caixa por folha. Duplo clique entra
   na folha.
3. As ligações são feitas por **etiquetas** (texto junto a cada pino) e por símbolos de
   alimentação (GND, +5V, +3V3). Dois pinos com a mesma etiqueta estão ligados.
   Etiquetas com forma de seta são globais e ligam entre folhas.

## Verificar (ERC)

`Inspecionar > Verificador de regras elétricas > Executar ERC`.
Os únicos pinos sem ligação devem ser os NC do LM5177 e os HO1_LL/HO2_LL, que estão
marcados com cruz. Qualquer outro erro deve ser reportado.

## Regenerar depois de mudar o código

```sh
cd hardware/gerador
python3 -I gerar.py
```

Não editar à mão os `.kicad_sch` gerados: as alterações perdem-se na próxima geração.
Arrumar a posição dos componentes na interface é seguro só depois de congelarmos o
gerador (fase de layout).

## Folha 1: Alimentação (`alimentacao.kicad_sch`)

Percurso: J1 (entrada 5 a 60 V) → F1 (polyfuse) → D1 (TVS) → D2 (Schottky contra
inversão) → **U1 LM5177** (buck-boost, 5 V) → **U2 TPS62162** (3,3 V).

| Bloco | Componentes | Como se chegou ao valor |
|---|---|---|
| UVLO | R1 53,6k, R2 20,5k | Liga a 1,25 V × (1 + 53,6/20,5) = 4,52 V |
| Tensão de saída | R7 40,2k, R8 10k | 1,0 V × (1 + 40,2/10) = 5,02 V |
| Frequência | R5 78,7k | 400 kHz (exemplo da folha de características) |
| Sensor de corrente | R10 10 mΩ, R11/R12 10 Ω, C9 180 pF | Limite 50 mV / 10 mΩ = 5 A típico (3,85 A mínimo) |
| Rampa | R4 75k | L / R_CS × 50×10⁶ = 15 µH / 10 mΩ × 50×10⁶ |
| Bobina | L1 15 µH, Isat ≥ 6 A | Ondulação ≈ 0,76 A no pior caso (60 V → 5 V) |
| Andar de entrada | Q1, Q2 NMOS 100 V | Têm de aguentar os 60 V com margem |
| Andar de saída | Q3, Q4 NMOS 40 V | Só veem os 5 V |
| Pinos de modo | MODE e SYNC a VCC, DTRK e BIAS a GND | MODE alto = PWM forçado (frequência fixa, menos ruído) |

**Alteração face ao relatório:** o LM74700-Q1 saiu. Aguenta no máximo 65 V e, com
entrada nominal de 60 V, o TVS de proteção limita acima disso. Passou a ser um
Schottky de 100 V (D2): mais simples e robusto, à custa de ~0,5 V de queda.

**Ainda por fechar nesta folha (marcado no esquema):**
- Rede de compensação R6/C5/C6: valores do exemplo da TI, recalcular no WEBENCH para
  15 µH e 5 V.
- Referências exatas dos MOSFET e da bobina.
- Footprint do LM5177: o KiCad não tem o HTSSOP-38 de 4,4 mm com pad exposto; está
  provisoriamente o TSSOP-38 sem pad. É preciso criar o footprint.
- Pino FB do TPS62162 (versão fixa de 3,3 V) a GND: confirmar na folha de características.

## Próximas folhas

2. Microcontrolador (STM32H743ZIT6): alimentação, cristais, reset, SWD, atribuição de pinos.
3. Ethernet (LAN8742A + RJ45).
4. CAN FD ×2 (ADM3057E).
5. RS485 (ADM2582E) e RS232 (MAX3227E).
6. I2C ×2 (PCA9306) e GPS (PPS + UART).
7. PWM ×3 (ADuM6401).
