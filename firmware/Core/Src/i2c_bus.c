/* Operações I2C pedidas pelo PC (RF01). Escrita: tipo DADOS, endereço de 7 bits no
 * cabeçalho, bytes nos dados. Leitura: tipo PEDIDO, dados[0] = número de bytes a ler e,
 * se existirem, dados[1..] são escritos antes (por exemplo o registo a ler). */
#include <string.h>
#include "placa.h"
#include "app.h"

int i2c_executar(uint8_t canal, const mensagem_t *m)
{
    I2C_HandleTypeDef *h = canal == 0 ? &hi2c1 : &hi2c2;
    uint16_t end = (uint16_t)((m->c.endereco & 0x7F) << 1);
    mensagem_t r = *m;
    HAL_StatusTypeDef st;
    r.origem_if = IF_I2C;
    r.origem_canal = canal;
    if (TIPO(m) == MSG_PEDIDO && m->c.comprimento >= 1) {
        uint8_t n = m->dados[0] > MSG_DADOS_MAX ? MSG_DADOS_MAX : m->dados[0];
        st = HAL_OK;
        if (m->c.comprimento > 1)
            st = HAL_I2C_Master_Transmit(h, end, (uint8_t *)&m->dados[1], m->c.comprimento - 1, 10);
        if (st == HAL_OK) st = HAL_I2C_Master_Receive(h, end, r.dados, n, 10);
        r.c.tipo = st == HAL_OK ? MSG_DADOS : MSG_ERRO;
        r.c.comprimento = st == HAL_OK ? n : 0;
    } else {
        st = HAL_I2C_Master_Transmit(h, end, (uint8_t *)m->dados, m->c.comprimento, 10);
        r.c.tipo = st == HAL_OK ? MSG_CONFIRMACAO : MSG_ERRO;
        r.c.comprimento = 0;
    }
    r.c.marca_us = sincronizacao_agora_us();
    encaminhamento_entrada(&r, 0);                    /* a resposta segue para o PC */
    return st == HAL_OK ? 0 : -1;
}
