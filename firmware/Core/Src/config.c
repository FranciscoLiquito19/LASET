#include <string.h>
#include "config.h"

config_t config_atual;

uint32_t crc32(const void *d, size_t n)
{
    const uint8_t *p = d;
    uint32_t c = 0xFFFFFFFFUL;
    while (n--) {
        c ^= *p++;
        for (int i = 0; i < 8; i++) c = (c >> 1) ^ (0xEDB88320UL & (0U - (c & 1)));
    }
    return ~c;
}

void config_omissao(config_t *c)
{
    uint32_t seq = c->sequencia;
    memset(c, 0, sizeof *c);
    c->magia = CONFIG_MAGIA;
    c->versao = CONFIG_VERSAO;
    c->tamanho = sizeof *c;
    c->sequencia = seq;
    c->tabela.pc_if = IF_RS232;
    c->tabela.pc_canal = 0;
    memcpy(c->ip, (uint8_t[]){ 192, 168, 1, 50 }, 4);
    memcpy(c->mascara, (uint8_t[]){ 255, 255, 255, 0 }, 4);
    memcpy(c->gateway, (uint8_t[]){ 192, 168, 1, 1 }, 4);
    c->porta_udp = 5000;
    c->porta_tcp = 5001;
    c->baud_rs232 = 1000000;
    c->baud_rs485 = 1000000;
}

void config_selar(config_t *c) { c->crc = crc32(c, offsetof(config_t, crc)); }

int config_valida(const config_t *c)
{
    return c->magia == CONFIG_MAGIA && c->versao == CONFIG_VERSAO && c->tamanho == sizeof *c
        && c->tabela.n_regras <= REGRAS_MAX && c->crc == crc32(c, offsetof(config_t, crc));
}

const config_t *config_escolher(const config_t *a, const config_t *b)
{
    int va = config_valida(a), vb = config_valida(b);
    if (va && vb) return (int32_t)(a->sequencia - b->sequencia) >= 0 ? a : b;
    return va ? a : vb ? b : NULL;
}

int config_ligacao_valida(uint8_t i, uint8_t canal)
{
    return (i == IF_RS232 && canal == 0) || (i == IF_CANFD && canal <= 1) || (i == IF_ETH && canal <= 1);
}

static uint32_t le32(const uint8_t *p) { return p[0] | p[1] << 8 | p[2] << 16 | (uint32_t)p[3] << 24; }
static uint16_t le16(const uint8_t *p) { return (uint16_t)(p[0] | p[1] << 8); }
static uint8_t *es32(uint8_t *p, uint32_t v) { for (int i = 0; i < 4; i++) *p++ = (uint8_t)(v >> 8 * i); return p; }
static uint8_t *es16(uint8_t *p, uint16_t v) { *p++ = (uint8_t)v; *p++ = (uint8_t)(v >> 8); return p; }

int config_comando(config_t *c, const uint8_t *cmd, uint16_t n, uint8_t *resp, uint16_t *nresp)
{
    tabela_t *t = &c->tabela;
    uint8_t *r = resp;
    if (n < 1) return -1;
    *r++ = cmd[0];
    int res = 0;
    switch (cmd[0]) {
    case CFG_LER:
        *r++ = t->pc_if; *r++ = t->pc_canal; *r++ = t->n_regras;
        memcpy(r, c->ip, 4); r += 4;
        memcpy(r, c->mascara, 4); r += 4;
        memcpy(r, c->gateway, 4); r += 4;
        r = es16(r, c->porta_udp); r = es16(r, c->porta_tcp);
        r = es32(r, c->baud_rs232); r = es32(r, c->baud_rs485);
        break;
    case CFG_LER_REGRA: {
        if (n < 2 || cmd[1] >= t->n_regras) return -1;
        const regra_t *g = &t->regras[cmd[1]];
        *r++ = t->n_regras;
        *r++ = g->origem_if; *r++ = g->origem_canal; *r++ = g->destino_if; *r++ = g->destino_canal;
        *r++ = g->urgente;
        r = es32(r, g->id_min); r = es32(r, g->id_max);
        break;
    }
    case CFG_ADICIONAR_REGRA: {
        if (n < 1 + REGRA_BYTES || t->n_regras >= REGRAS_MAX) return -1;
        const uint8_t *p = cmd + 1;
        regra_t g = { .origem_if = p[0], .origem_canal = p[1], .destino_if = p[2], .destino_canal = p[3],
                      .urgente = p[4] ? 1 : 0, .id_min = le32(p + 5), .id_max = le32(p + 9) };
        if (saida_de(g.destino_if, g.destino_canal) == S_NENHUMA || g.id_min > g.id_max) return -1;
        t->regras[t->n_regras++] = g;
        *r++ = t->n_regras;
        break;
    }
    case CFG_APAGAR_REGRAS:
        t->n_regras = 0;
        break;
    case CFG_LIGACAO_PC:
        if (n < 3 || !config_ligacao_valida(cmd[1], cmd[2])) return -1;
        t->pc_if = cmd[1];
        t->pc_canal = cmd[2];
        break;
    case CFG_REDE:
        if (n < 17) return -1;
        memcpy(c->ip, cmd + 1, 4);
        memcpy(c->mascara, cmd + 5, 4);
        memcpy(c->gateway, cmd + 9, 4);
        c->porta_udp = le16(cmd + 13);
        c->porta_tcp = le16(cmd + 15);
        break;
    case CFG_SERIE: {
        if (n < 9) return -1;
        uint32_t a = le32(cmd + 1), b = le32(cmd + 5);
        if (a < 1200 || a > 10000000 || b < 1200 || b > 10000000) return -1;
        c->baud_rs232 = a;
        c->baud_rs485 = b;
        break;
    }
    case CFG_GRAVAR:
        res = 1;
        break;
    case CFG_OMISSAO:
        config_omissao(c);
        break;
    default:
        return -1;
    }
    *nresp = (uint16_t)(r - resp);
    return res;
}
