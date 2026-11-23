/* ISO 15765-2 (ISO-TP) sobre CAN FD, para usar o CAN FD 1 como ligação ao PC (RF09).
 * Uma mensagem do PC (cabeçalho de 20 bytes + até 64 bytes de dados) não cabe numa
 * trama, por isso segmenta-se: Single Frame até 62 bytes, ou First Frame + Consecutive
 * Frames, com Flow Control do recetor. Tramas de 64 bytes (TX_DL = 64).
 * Sem dependências de hardware: compila também no PC (firmware/testes). */
#ifndef ISOTP_H
#define ISOTP_H
#include <stdint.h>

#define ISOTP_TX_DL  64
#define ISOTP_MAX    256          /* maior mensagem aceite */
#define ISOTP_PAD    0xCC         /* enchimento até um comprimento CAN FD válido */

enum { ISOTP_SF = 0, ISOTP_FF = 1, ISOTP_CF = 2, ISOTP_FC = 3 };
enum { ISOTP_FC_CTS = 0, ISOTP_FC_ESPERA = 1, ISOTP_FC_EXCESSO = 2 };

typedef struct {
    uint8_t  buf[ISOTP_MAX];
    uint16_t total, recebidos;
    uint8_t  sn, ativo;
} isotp_rx_t;

/* Resultado de isotp_rx_trama */
enum { ISOTP_RX_NADA = 0, ISOTP_RX_COMPLETA, ISOTP_RX_ENVIAR_FC, ISOTP_RX_FC_RECEBIDO, ISOTP_RX_ERRO = -1 };

/* Trata uma trama recebida. ISOTP_RX_COMPLETA: a mensagem está em r->buf (r->total
 * bytes). ISOTP_RX_ENVIAR_FC: enviar as fc_n bytes de fc (Flow Control). */
int isotp_rx_trama(isotp_rx_t *r, const uint8_t *t, uint8_t n, uint8_t *fc, uint8_t *fc_n);

typedef struct {
    const uint8_t *d;
    uint16_t total, enviados;
    uint8_t  sn, estado, bs, bs_restante, stmin;
} isotp_tx_t;

void isotp_tx_iniciar(isotp_tx_t *t, const uint8_t *d, uint16_t n);
/* Escreve a próxima trama em out (64 bytes) e devolve o seu comprimento (já um
 * comprimento CAN FD válido); 0 = esperar pelo Flow Control; -1 = terminou. */
int isotp_tx_proxima(isotp_tx_t *t, uint8_t *out);
/* Aplica um Flow Control recebido. 0 = continuar, 1 = esperar, -1 = abortado. */
int isotp_tx_fc(isotp_tx_t *t, const uint8_t *fc, uint8_t n);
/* Tempo mínimo entre Consecutive Frames pedido pelo recetor, em microssegundos */
uint32_t isotp_stmin_us(uint8_t stmin);
uint8_t isotp_len_canfd(uint8_t n);   /* arredonda para 0-8, 12, 16, 20, 24, 32, 48, 64 */

#endif
