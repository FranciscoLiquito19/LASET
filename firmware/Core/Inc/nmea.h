/* Leitura das frases NMEA RMC do recetor GPS e cálculo da marca temporal (RF16, DP14). */
#ifndef NMEA_H
#define NMEA_H
#include <stdint.h>

/* Lê uma frase $xxRMC terminada (com ou sem \r\n). Se for válida e com estado 'A',
 * escreve em *utc_s os segundos desde 1970-01-01 e devolve 1; caso contrário 0. */
int nmea_rmc(const char *frase, int64_t *utc_s);
/* Verifica o checksum "*hh" de uma frase NMEA. */
int nmea_checksum_ok(const char *frase);
/* Tempo em microssegundos a partir do último PPS: utc_s é o segundo UTC desse PPS,
 * cap e agora são contagens do temporizador (64 bits) e freq_hz a frequência medida. */
uint64_t tempo_us(int64_t utc_s, uint64_t cap, uint64_t agora, uint32_t freq_hz);
/* Aceita uma nova medida de frequência só se estiver a menos de 1000 ppm da nominal. */
int freq_plausivel(uint32_t medida, uint32_t nominal);

#endif
