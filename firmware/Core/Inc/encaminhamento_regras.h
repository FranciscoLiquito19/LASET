/* Regras de encaminhamento e política de atendimento, sem dependências de hardware
 * (compilam também no PC, para os testes em firmware/testes). */
#ifndef ENCAMINHAMENTO_REGRAS_H
#define ENCAMINHAMENTO_REGRAS_H
#include <stdint.h>
#include "mensagem.h"

/* Saídas da unidade: cada uma tem duas filas (urgente e normal) e uma tarefa. */
typedef enum { S_CAN1 = 0, S_CAN2, S_RS232, S_RS485, S_I2C1, S_I2C2, S_PWM, S_ETH, S_N, S_NENHUMA = 0xFF } saida_t;

typedef struct {
    uint8_t  origem_if, origem_canal;  /* 0xFF = qualquer */
    uint32_t id_min, id_max;           /* gama de endereços/identificadores */
    uint8_t  destino_if, destino_canal;
    uint8_t  urgente;
} regra_t;

#define REGRAS_MAX 32
#define QUALQUER   0xFF

typedef struct {
    uint8_t pc_if, pc_canal;           /* ligação ao PC em uso (RF09) */
    regra_t regras[REGRAS_MAX];
    uint8_t n_regras;
} tabela_t;

saida_t saida_de(uint8_t interface, uint8_t canal);
/* Decide a saída de uma mensagem. Vinda do PC: o cabeçalho indica o destino.
 * Vinda de um dispositivo: procura-se a primeira regra que coincide; sem regra, vai
 * para o PC. Devolve S_NENHUMA se o destino não existir. *urgente recebe a classe. */
saida_t encaminhar(const tabela_t *t, const mensagem_t *m, uint8_t *urgente);
/* Política de atendimento de uma saída (RF14, DP08): as urgentes passam primeiro, mas
 * depois de max_seguidas urgentes passa uma normal, se houver.
 * Devolve 1 = tirar da fila urgente, 0 = da normal, -1 = nada a fazer. */
int escolher_fila(int tem_urgente, int tem_normal, uint8_t *seguidas, uint8_t max_seguidas);

#endif
