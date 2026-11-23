#include "cobs.h"

size_t cobs_codificar(const uint8_t *in, size_t n, uint8_t *out)
{
    size_t r = 0, w = 1, cod = 0;
    uint8_t c = 1;
    while (r < n) {
        if (in[r] == 0) {
            out[cod] = c; cod = w++; c = 1;
        } else {
            out[w++] = in[r]; c++;
            /* bloco cheio: só abre outro se ainda houver dados */
            if (c == 0xFF && r + 1 < n) { out[cod] = c; cod = w++; c = 1; }
        }
        r++;
    }
    out[cod] = c;
    return w;
}

size_t cobs_descodificar(const uint8_t *in, size_t n, uint8_t *out)
{
    size_t r = 0, w = 0;
    while (r < n) {
        uint8_t c = in[r];
        if (c == 0 || r + c > n) return 0;      /* bloco vazio ou a passar o fim */
        r++;
        for (uint8_t i = 1; i < c; i++) {
            if (in[r] == 0) return 0;
            out[w++] = in[r++];
        }
        if (c != 0xFF && r < n) out[w++] = 0;
    }
    return w;
}

uint16_t crc16_ccitt(const uint8_t *d, size_t n)
{
    uint16_t crc = 0xFFFF;
    for (size_t i = 0; i < n; i++) {
        crc ^= (uint16_t)d[i] << 8;
        for (int b = 0; b < 8; b++)
            crc = (crc & 0x8000) ? (uint16_t)((crc << 1) ^ 0x1021) : (uint16_t)(crc << 1);
    }
    return crc;
}
