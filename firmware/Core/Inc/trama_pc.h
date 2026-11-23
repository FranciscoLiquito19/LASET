/* Mensagens do PC em bytes: cabeçalho de 20 bytes + dados. Na série e no TCP vão
 * dentro de uma trama COBS(bytes + CRC-16 LE) terminada por 0x00; no UDP e no ISO-TP
 * vão sem COBS nem CRC (esses meios já detetam erros). */
#ifndef TRAMA_PC_H
#define TRAMA_PC_H
#include <stddef.h>
#include <stdint.h>
#include "mensagem.h"

#define PC_BRUTO_MAX   (sizeof(cabecalho_t) + MSG_DADOS_MAX)
#define PC_TRAMA_MAX   (PC_BRUTO_MAX + 2 + (PC_BRUTO_MAX + 2) / 254 + 2)

/* Bytes -> mensagem (preenche só c e dados). 0 = válida. */
int    pc_de_bytes(const uint8_t *d, size_t n, mensagem_t *m);
size_t pc_para_bytes(const mensagem_t *m, uint8_t *out);             /* out >= PC_BRUTO_MAX */
/* Trama COBS sem o 0x00 final -> mensagem. 0 = válida (COBS, CRC e comprimentos). */
int    pc_de_trama(const uint8_t *cobs, size_t n, mensagem_t *m);
size_t pc_para_trama(const mensagem_t *m, uint8_t *out);             /* inclui o 0x00 final */

/* Acumula bytes de um fluxo (série, TCP) e entrega cada trama completa. */
typedef struct { uint8_t buf[PC_TRAMA_MAX]; size_t n; uint8_t excedeu; } pc_fluxo_t;
/* Devolve 1 quando m tem uma mensagem válida (a trama terminou neste byte). */
int    pc_fluxo_byte(pc_fluxo_t *f, uint8_t b, mensagem_t *m);

#endif
