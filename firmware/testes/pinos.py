"""Confirma que os pinos usados no firmware são os do esquema.

Uso:  python3 -I firmware/testes/pinos.py      (corre na CI)

Lê as chamadas af(...) de Core/Src/stm32h7xx_hal_msp.c e os #define de pinos de
Core/Inc/placa.h, e compara com a tabela PINOS de hardware/gerador/folha_mcu.py. Cada
função alternativa tem de cair num pino ligado à rede certa (por exemplo FDCAN1 nas redes
CAN1_*). O USART3 é a consola da NUCLEO e não existe na PCB, por isso fica de fora.
Também avisa dos pinos de sinal do esquema que o firmware não configura.
"""
import ast
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.normpath(os.path.join(AQUI, '..', '..'))
MSP = os.path.join(RAIZ, 'firmware', 'Core', 'Src', 'stm32h7xx_hal_msp.c')
PLACA = os.path.join(RAIZ, 'firmware', 'Core', 'Inc', 'placa.h')
FOLHA = os.path.join(RAIZ, 'hardware', 'gerador', 'folha_mcu.py')

# função alternativa -> redes aceites (prefixo do nome curto) e pinos esperados por função
ESPERADO = {
    'FDCAN1': ('CAN1_RX', 'CAN1_TX'),
    'FDCAN2': ('CAN2_RX', 'CAN2_TX'),
    'TIM1': ('PWM1', 'PWM2', 'PWM3', 'PWM_FALHA'),
    'TIM2': ('GPS_PPS',),
    'USART2': ('RS232_TX', 'RS232_RX'),
    'USART6': ('RS485_TX', 'RS485_RX', 'RS485_DE'),
    'UART7': ('GPS_TX', 'GPS_RX'),
    'I2C1': ('I2C1_SCL', 'I2C1_SDA'),
    'I2C2': ('I2C2_SCL', 'I2C2_SDA'),
    'ETH': ('ETH_',),
}
SO_NUCLEO = {'USART3'}
# pinos que o firmware não precisa de configurar (depuração, relógio, alimentação)
SEM_FIRMWARE = {'/SWDIO', '/SWCLK', '/SWO', '/OSC_IN', '/OSC_OUT', 'NRST', '/BOOT0', '/VCAP', '/VDDA'}


def pinos_esquema():
    arv = ast.parse(open(FOLHA, encoding='utf-8').read())
    for no in arv.body:
        if isinstance(no, ast.Assign) and getattr(no.targets[0], 'id', '') == 'PINOS':
            return {k: v for k, v in ast.literal_eval(no.value).items() if re.match(r'P[A-K]\d+$', k)}
    sys.exit('PINOS não encontrado em folha_mcu.py')


def main():
    esq = pinos_esquema()
    msp = open(MSP, encoding='utf-8').read()
    erros, usados = [], set()
    for porta, pinos, alt in re.findall(r'af\(GPIO([A-K]),\s*([^,]+),\s*GPIO_AF\d+_(\w+)', msp):
        if alt in SO_NUCLEO:
            continue
        if alt not in ESPERADO:
            erros.append(f'função {alt} sem regra em ESPERADO')
            continue
        for n in re.findall(r'GPIO_PIN_(\d+)', pinos):
            p = f'P{porta}{n}'
            usados.add(p)
            rede = esq.get(p)
            if rede is None:
                erros.append(f'{p} ({alt}) não está ligado a nada no esquema')
            elif not rede.lstrip('/').startswith(ESPERADO[alt]):
                erros.append(f'{p} ({alt}) liga a {rede} no esquema')
    placa = open(PLACA, encoding='utf-8').read()
    portas = dict(re.findall(r'#define\s+(\w+)_PORTA\s+GPIO([A-K])', placa))
    for nome, n in re.findall(r'#define\s+(\w+)_PINO\s+GPIO_PIN_(\d+)', placa):
        base = nome if nome in portas else nome.split('_')[0]
        porta = portas.get(nome) or portas.get(base) or portas.get(nome.rsplit('_', 1)[0])
        if porta is None:
            erros.append(f'{nome}_PINO sem {nome}_PORTA em placa.h')
            continue
        p = f'P{porta}{n}'
        usados.add(p)
        rede = esq.get(p, '')
        if nome.replace('_', '').upper() not in rede.lstrip('/').replace('_', '').upper():
            erros.append(f'{nome} em {p}, que no esquema liga a {rede or "nada"}')
    avisos = [f'{p} ({r}) não é configurado no firmware' for p, r in sorted(esq.items())
              if p not in usados and r not in SEM_FIRMWARE]
    for a in avisos:
        print('aviso:', a)
    for e in erros:
        print('ERRO:', e)
    print(f'{len(usados)} pinos do firmware conferidos com o esquema, {len(erros)} erros')
    sys.exit(1 if erros else 0)


if __name__ == '__main__':
    main()
