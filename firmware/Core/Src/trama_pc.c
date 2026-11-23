#include <string.h>
#include "trama_pc.h"
#include "cobs.h"

int pc_de_bytes(const uint8_t *d, size_t n, mensagem_t *m)
{
    if (n < sizeof(cabecalho_t)) return -1;
    memcpy(&m->c, d, sizeof(cabecalho_t));
    if (m->c.versao != MSG_VERSAO || m->c.comprimento > MSG_DADOS_MAX
        || m->c.comprimento != n - sizeof(cabecalho_t)) return -1;
    memcpy(m->dados, d + sizeof(cabecalho_t), m->c.comprimento);
    return 0;
}

size_t pc_para_bytes(const mensagem_t *m, uint8_t *out)
{
    cabecalho_t c = m->c;
    uint16_t n = c.comprimento > MSG_DADOS_MAX ? MSG_DADOS_MAX : c.comprimento;
    c.versao = MSG_VERSAO;
    c.comprimento = n;
    memcpy(out, &c, sizeof c);
    memcpy(out + sizeof c, m->dados, n);
    return sizeof c + n;
}

int pc_de_trama(const uint8_t *cobs, size_t n, mensagem_t *m)
{
    uint8_t d[PC_TRAMA_MAX];
    if (n == 0 || n > PC_TRAMA_MAX) return -1;
    size_t k = cobs_descodificar(cobs, n, d);
    if (k < sizeof(cabecalho_t) + 2 || k > PC_BRUTO_MAX + 2) return -1;
    if (crc16_ccitt(d, k - 2) != (uint16_t)(d[k - 2] | d[k - 1] << 8)) return -1;
    return pc_de_bytes(d, k - 2, m);
}

size_t pc_para_trama(const mensagem_t *m, uint8_t *out)
{
    uint8_t d[PC_BRUTO_MAX + 2];
    size_t n = pc_para_bytes(m, d);
    uint16_t crc = crc16_ccitt(d, n);
    d[n++] = (uint8_t)crc;
    d[n++] = (uint8_t)(crc >> 8);
    size_t k = cobs_codificar(d, n, out);
    out[k++] = 0;
    return k;
}

int pc_fluxo_byte(pc_fluxo_t *f, uint8_t b, mensagem_t *m)
{
    if (b != 0) {
        if (f->n < sizeof f->buf) f->buf[f->n++] = b; else f->excedeu = 1;
        return 0;
    }
    int ok = !f->excedeu && pc_de_trama(f->buf, f->n, m) == 0;
    f->n = 0;
    f->excedeu = 0;
    return ok;
}
