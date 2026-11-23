#include <string.h>
#include "isotp.h"

enum { TX_SF, TX_FF, TX_ESPERA_FC, TX_CF, TX_FIM };

uint8_t isotp_len_canfd(uint8_t n)
{
    static const uint8_t L[] = { 12, 16, 20, 24, 32, 48, 64 };
    if (n <= 8) return n;
    for (unsigned i = 0; i < sizeof L; i++) if (L[i] >= n) return L[i];
    return 64;
}

static int fechar(uint8_t *out, uint8_t n)
{
    uint8_t k = isotp_len_canfd(n);
    memset(out + n, ISOTP_PAD, k - n);
    return k;
}

int isotp_rx_trama(isotp_rx_t *r, const uint8_t *t, uint8_t n, uint8_t *fc, uint8_t *fc_n)
{
    if (n == 0) return ISOTP_RX_ERRO;
    switch (t[0] >> 4) {
    case ISOTP_SF: {
        uint8_t len = t[0] & 0x0F, ini = 1;
        if (len == 0) {                       /* formato CAN FD: comprimento no byte 1 */
            if (n < 2) return ISOTP_RX_ERRO;
            len = t[1]; ini = 2;
        }
        if (len == 0 || len > n - ini) return ISOTP_RX_ERRO;
        memcpy(r->buf, t + ini, len);
        r->total = r->recebidos = len;
        r->ativo = 0;
        return ISOTP_RX_COMPLETA;
    }
    case ISOTP_FF: {
        uint32_t total = (uint32_t)(t[0] & 0x0F) << 8 | t[1];
        uint8_t ini = 2;
        if (total == 0) {                     /* comprimento de 32 bits */
            if (n < 6) return ISOTP_RX_ERRO;
            total = (uint32_t)t[2] << 24 | (uint32_t)t[3] << 16 | (uint32_t)t[4] << 8 | t[5];
            ini = 6;
        }
        fc[1] = 0; fc[2] = 0; *fc_n = 3;      /* BS = 0 (sem limite), STmin = 0 */
        if (total > ISOTP_MAX || total < (uint32_t)(n - ini)) {
            fc[0] = 0x30 | ISOTP_FC_EXCESSO;
            r->ativo = 0;
            return ISOTP_RX_ENVIAR_FC;
        }
        r->total = (uint16_t)total;
        r->recebidos = n - ini;
        memcpy(r->buf, t + ini, r->recebidos);
        r->sn = 1;
        r->ativo = 1;
        fc[0] = 0x30 | ISOTP_FC_CTS;
        return ISOTP_RX_ENVIAR_FC;
    }
    case ISOTP_CF: {
        if (!r->ativo) return ISOTP_RX_NADA;
        if ((t[0] & 0x0F) != r->sn) { r->ativo = 0; return ISOTP_RX_ERRO; }
        uint16_t k = r->total - r->recebidos;
        if (k > n - 1) k = n - 1;
        memcpy(r->buf + r->recebidos, t + 1, k);
        r->recebidos += k;
        r->sn = (r->sn + 1) & 0x0F;
        if (r->recebidos < r->total) return ISOTP_RX_NADA;
        r->ativo = 0;
        return ISOTP_RX_COMPLETA;
    }
    case ISOTP_FC:
        return ISOTP_RX_FC_RECEBIDO;
    default:
        return ISOTP_RX_ERRO;
    }
}

void isotp_tx_iniciar(isotp_tx_t *t, const uint8_t *d, uint16_t n)
{
    memset(t, 0, sizeof *t);
    t->d = d;
    t->total = n;
    t->estado = (n <= ISOTP_TX_DL - 2) ? TX_SF : TX_FF;
}

int isotp_tx_proxima(isotp_tx_t *t, uint8_t *out)
{
    switch (t->estado) {
    case TX_SF:
        t->estado = TX_FIM;
        t->enviados = t->total;
        if (t->total <= 7) {                  /* cabe numa trama clássica */
            out[0] = (uint8_t)t->total;
            memcpy(out + 1, t->d, t->total);
            return fechar(out, (uint8_t)(1 + t->total));
        }
        out[0] = 0x00;
        out[1] = (uint8_t)t->total;
        memcpy(out + 2, t->d, t->total);
        return fechar(out, (uint8_t)(2 + t->total));
    case TX_FF:
        out[0] = 0x10 | (uint8_t)(t->total >> 8 & 0x0F);
        out[1] = (uint8_t)t->total;
        memcpy(out + 2, t->d, ISOTP_TX_DL - 2);
        t->enviados = ISOTP_TX_DL - 2;
        t->sn = 1;
        t->estado = TX_ESPERA_FC;
        return ISOTP_TX_DL;
    case TX_CF: {
        uint16_t k = t->total - t->enviados;
        if (k > ISOTP_TX_DL - 1) k = ISOTP_TX_DL - 1;
        out[0] = 0x20 | t->sn;
        memcpy(out + 1, t->d + t->enviados, k);
        t->enviados += k;
        t->sn = (t->sn + 1) & 0x0F;
        if (t->enviados >= t->total) t->estado = TX_FIM;
        else if (t->bs && --t->bs_restante == 0) t->estado = TX_ESPERA_FC;
        return fechar(out, (uint8_t)(1 + k));
    }
    case TX_ESPERA_FC:
        return 0;
    default:
        return -1;
    }
}

int isotp_tx_fc(isotp_tx_t *t, const uint8_t *fc, uint8_t n)
{
    if (t->estado != TX_ESPERA_FC || n < 3 || (fc[0] >> 4) != ISOTP_FC) return 1;
    switch (fc[0] & 0x0F) {
    case ISOTP_FC_CTS:
        t->bs = t->bs_restante = fc[1];
        t->stmin = fc[2];
        t->estado = TX_CF;
        return 0;
    case ISOTP_FC_ESPERA:
        return 1;
    default:
        t->estado = TX_FIM;
        return -1;
    }
}

uint32_t isotp_stmin_us(uint8_t s)
{
    if (s <= 0x7F) return (uint32_t)s * 1000;
    if (s >= 0xF1 && s <= 0xF9) return (uint32_t)(s - 0xF0) * 100;
    return 127000;                            /* valores reservados: o máximo */
}
