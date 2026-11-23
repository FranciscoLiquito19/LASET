#include "encaminhamento_regras.h"

saida_t saida_de(uint8_t interface, uint8_t canal)
{
    switch (interface) {
    case IF_CANFD: return canal == 0 ? S_CAN1 : canal == 1 ? S_CAN2 : S_NENHUMA;
    case IF_RS232: return canal == 0 ? S_RS232 : S_NENHUMA;
    case IF_RS485: return canal == 0 ? S_RS485 : S_NENHUMA;
    case IF_I2C:   return canal == 0 ? S_I2C1 : canal == 1 ? S_I2C2 : S_NENHUMA;
    case IF_PWM:   return canal <= 2 ? S_PWM : S_NENHUMA;   /* um só periférico, três canais */
    case IF_ETH:   return canal <= 1 ? S_ETH : S_NENHUMA;   /* 0 = UDP, 1 = TCP */
    default:       return S_NENHUMA;
    }
}

static int coincide(const regra_t *r, const mensagem_t *m)
{
    if (r->origem_if != QUALQUER && r->origem_if != m->origem_if) return 0;
    if (r->origem_canal != QUALQUER && r->origem_canal != m->origem_canal) return 0;
    uint32_t id = m->c.endereco & CAN_ID_MASCARA;
    return id >= r->id_min && id <= r->id_max;
}

saida_t encaminhar(const tabela_t *t, const mensagem_t *m, uint8_t *urgente)
{
    *urgente = m->urgente;
    if (m->origem_if == t->pc_if && m->origem_canal == t->pc_canal)
        return saida_de(m->c.interface, m->c.canal);           /* pedido do PC */
    for (uint8_t i = 0; i < t->n_regras; i++) {
        const regra_t *r = &t->regras[i];
        if (coincide(r, m)) {
            *urgente = r->urgente;
            return saida_de(r->destino_if, r->destino_canal);
        }
    }
    return saida_de(t->pc_if, t->pc_canal);                    /* por omissão, para o PC */
}

int escolher_fila(int tem_urgente, int tem_normal, uint8_t *seguidas, uint8_t max_seguidas)
{
    if (tem_urgente && (!tem_normal || *seguidas < max_seguidas)) {
        (*seguidas)++;
        return 1;
    }
    if (tem_normal) {
        *seguidas = 0;
        return 0;
    }
    return -1;
}
