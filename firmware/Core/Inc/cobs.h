/* COBS (Consistent Overhead Byte Stuffing) e CRC-16/CCITT-FALSE para a ligação série
 * ao PC: cada trama é COBS(cabeçalho + dados + CRC-16) seguida de um byte 0x00. */
#ifndef COBS_H
#define COBS_H
#include <stddef.h>
#include <stdint.h>

size_t cobs_codificar(const uint8_t *in, size_t n, uint8_t *out);   /* out >= n + n/254 + 1 */
size_t cobs_descodificar(const uint8_t *in, size_t n, uint8_t *out); /* 0 se inválido */
uint16_t crc16_ccitt(const uint8_t *d, size_t n);                    /* poly 0x1021, init 0xFFFF */

#endif
