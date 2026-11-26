/* Operações I2C pedidas pelo PC (RF01). Escrita: tipo DADOS, endereço de 7 bits no
 * cabeçalho, bytes nos dados. Leitura: tipo PEDIDO, dados[0] = número de bytes a ler e,
 * se existirem, dados[1..] são escritos antes (por exemplo o registo a ler; com 1 ou 2
 * bytes usa-se o início repetido). Tempo máximo de 20 ms por operação (64 bytes a
 * 100 kHz levam cerca de 6 ms). */
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
        uint16_t pre = m->c.comprimento - 1;          /* bytes a escrever antes da leitura */
        if (pre == 1 || pre == 2) {
            /* registo de 8 ou 16 bits: escrita e leitura com início repetido, sem STOP no
             * meio, como pedem muitos sensores */
            uint16_t reg = pre == 1 ? m->dados[1] : (uint16_t)(m->dados[1] << 8 | m->dados[2]);
            st = HAL_I2C_Mem_Read(h, end, reg, pre == 1 ? I2C_MEMADD_SIZE_8BIT : I2C_MEMADD_SIZE_16BIT,
                                  r.dados, n, 20);
        } else {
            st = HAL_OK;
            if (pre > 0) st = HAL_I2C_Master_Transmit(h, end, (uint8_t *)&m->dados[1], pre, 20);
            if (st == HAL_OK) st = HAL_I2C_Master_Receive(h, end, r.dados, n, 20);
        }
        r.c.tipo = st == HAL_OK ? MSG_DADOS : MSG_ERRO;
        r.c.comprimento = st == HAL_OK ? n : 0;
    } else {
        st = HAL_I2C_Master_Transmit(h, end, (uint8_t *)m->dados, m->c.comprimento, 20);
        r.c.tipo = st == HAL_OK ? MSG_CONFIRMACAO : MSG_ERRO;
        r.c.comprimento = 0;
    }
    if (st == HAL_TIMEOUT || st == HAL_BUSY) {
        /* barramento preso (por exemplo um escravo a segurar SDA): reinicia o periférico
         * para a operação seguinte não ficar também presa */
        HAL_I2C_DeInit(h);
        HAL_I2C_Init(h);
        HAL_I2CEx_ConfigAnalogFilter(h, I2C_ANALOGFILTER_ENABLE);
    }
    r.c.marca_us = sincronizacao_agora_us();
    encaminhamento_entrada(&r, 0);                    /* a resposta segue para o PC */
    return st == HAL_OK ? 0 : -1;
}
