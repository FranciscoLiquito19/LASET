/* CAN FD: autoteste em loopback, receção por interrupção e transmissão. */
#include <string.h>
#include "placa.h"
#include "app.h"
#include "task.h"

static const uint8_t COMPRIMENTOS[16] = { 0, 1, 2, 3, 4, 5, 6, 7, 8, 12, 16, 20, 24, 32, 48, 64 };
static const uint32_t DLC[16] = {
    FDCAN_DLC_BYTES_0, FDCAN_DLC_BYTES_1, FDCAN_DLC_BYTES_2, FDCAN_DLC_BYTES_3,
    FDCAN_DLC_BYTES_4, FDCAN_DLC_BYTES_5, FDCAN_DLC_BYTES_6, FDCAN_DLC_BYTES_7,
    FDCAN_DLC_BYTES_8, FDCAN_DLC_BYTES_12, FDCAN_DLC_BYTES_16, FDCAN_DLC_BYTES_20,
    FDCAN_DLC_BYTES_24, FDCAN_DLC_BYTES_32, FDCAN_DLC_BYTES_48, FDCAN_DLC_BYTES_64 };

static int indice_dlc(uint16_t n)
{
    for (int i = 0; i < 16; i++) if (COMPRIMENTOS[i] >= n) return i;
    return 15;
}

uint8_t len_valida_canfd(uint16_t n) { return COMPRIMENTOS[indice_dlc(n)]; }

static uint16_t dlc_para_len(uint32_t dlc)
{
    for (int i = 0; i < 16; i++) if (DLC[i] == dlc) return COMPRIMENTOS[i];
    return 0;
}

static FDCAN_HandleTypeDef *handle(uint8_t canal) { return canal == 0 ? &hfdcan1 : &hfdcan2; }

static void cabecalho_tx(FDCAN_TxHeaderTypeDef *t, uint32_t endereco, uint16_t n)
{
    memset(t, 0, sizeof *t);
    t->Identifier = endereco & CAN_ID_MASCARA;
    t->IdType = (endereco & CAN_ID_ESTENDIDO) ? FDCAN_EXTENDED_ID : FDCAN_STANDARD_ID;
    if (t->IdType == FDCAN_STANDARD_ID) t->Identifier &= 0x7FF;
    t->TxFrameType = FDCAN_DATA_FRAME;
    int fd = (endereco & CAN_FD) || n > 8;
    t->DataLength = DLC[fd ? indice_dlc(n) : (n > 8 ? 8 : n)];
    t->ErrorStateIndicator = FDCAN_ESI_ACTIVE;
    t->BitRateSwitch = (fd && (endereco & CAN_BRS)) ? FDCAN_BRS_ON : FDCAN_BRS_OFF;
    t->FDFormat = fd ? FDCAN_FD_CAN : FDCAN_CLASSIC_CAN;
    t->TxEventFifoControl = FDCAN_NO_TX_EVENTS;
    t->MessageMarker = 0;
}

/* Autoteste (antes do escalonador): cada FDCAN em loopback interno envia uma trama
 * CAN FD de 64 bytes com comutação de taxa (1 -> 8 Mbit/s) e tem de a receber igual. */
static int autoteste_um(FDCAN_HandleTypeDef *h, uint32_t id)
{
    FDCAN_TxHeaderTypeDef tx;
    FDCAN_RxHeaderTypeDef rx;
    uint8_t d[64], r[64];
    for (int i = 0; i < 64; i++) d[i] = (uint8_t)(i * 7 + id);
    cabecalho_tx(&tx, id | CAN_FD | CAN_BRS, 64);
    if (HAL_FDCAN_Start(h) != HAL_OK) return -1;
    if (HAL_FDCAN_AddMessageToTxFifoQ(h, &tx, d) != HAL_OK) return -2;
    uint32_t t0 = HAL_GetTick();
    while (HAL_FDCAN_GetRxFifoFillLevel(h, FDCAN_RX_FIFO0) == 0)
        if (HAL_GetTick() - t0 > 20) return -3;
    if (HAL_FDCAN_GetRxMessage(h, FDCAN_RX_FIFO0, &rx, r) != HAL_OK) return -4;
    HAL_FDCAN_Stop(h);
    if (rx.Identifier != id || dlc_para_len(rx.DataLength) != 64 || rx.BitRateSwitch != FDCAN_BRS_ON) return -5;
    return memcmp(d, r, 64) == 0 ? 0 : -6;
}

int can_autoteste(void)
{
    can_configurar(FDCAN_MODE_INTERNAL_LOOPBACK);
    int r1 = autoteste_um(&hfdcan1, 0x123);
    int r2 = autoteste_um(&hfdcan2, 0x321);
    consola_printf("autoteste CAN FD (64 bytes, 1/8 Mbit/s, loopback): FDCAN1 %s (%d), FDCAN2 %s (%d)\r\n",
                   r1 ? "FALHOU" : "ok", r1, r2 ? "FALHOU" : "ok", r2);
    return (r1 || r2) ? -1 : 0;
}

void can_arrancar(void)
{
#if defined(LASET_CAN_LOOPBACK)
    can_configurar(FDCAN_MODE_INTERNAL_LOOPBACK);   /* NUCLEO sem transceivers */
#else
    can_configurar(FDCAN_MODE_NORMAL);
#endif
    FDCAN_HandleTypeDef *hs[2] = { &hfdcan1, &hfdcan2 };
    for (int i = 0; i < 2; i++) {
        if (HAL_FDCAN_ActivateNotification(hs[i], FDCAN_IT_RX_FIFO0_NEW_MESSAGE, 0) != HAL_OK) Error_Handler();
        if (HAL_FDCAN_Start(hs[i]) != HAL_OK) Error_Handler();
    }
}

void HAL_FDCAN_RxFifo0Callback(FDCAN_HandleTypeDef *h, uint32_t its)
{
    BaseType_t acordar = pdFALSE;
    FDCAN_RxHeaderTypeDef rx;
    mensagem_t m;
    if (!(its & FDCAN_IT_RX_FIFO0_NEW_MESSAGE)) return;
    while (HAL_FDCAN_GetRxFifoFillLevel(h, FDCAN_RX_FIFO0) > 0) {
        if (HAL_FDCAN_GetRxMessage(h, FDCAN_RX_FIFO0, &rx, m.dados) != HAL_OK) break;
        memset(&m.c, 0, sizeof m.c);
        m.c.versao = MSG_VERSAO;
        m.c.tipo = MSG_DADOS;
        m.c.interface = IF_CANFD;
        m.c.canal = (h == &hfdcan1) ? 0 : 1;
        m.c.endereco = rx.Identifier
                     | (rx.IdType == FDCAN_EXTENDED_ID ? CAN_ID_ESTENDIDO : 0)
                     | (rx.FDFormat == FDCAN_FD_CAN ? CAN_FD : 0)
                     | (rx.BitRateSwitch == FDCAN_BRS_ON ? CAN_BRS : 0);
        m.c.comprimento = dlc_para_len(rx.DataLength);
        m.c.marca_us = sincronizacao_agora_us();
        m.origem_if = IF_CANFD;
        m.origem_canal = m.c.canal;
        m.urgente = 0;
        encaminhamento_entrada_isr(&m, &acordar);
    }
    portYIELD_FROM_ISR(acordar);
}

int can_enviar(uint8_t canal, const mensagem_t *m)
{
    FDCAN_HandleTypeDef *h = handle(canal);
    FDCAN_TxHeaderTypeDef tx;
    uint16_t n = m->c.comprimento > 64 ? 64 : m->c.comprimento;
    cabecalho_tx(&tx, m->c.endereco, n);
    /* espera por espaço na fila de transmissão do controlador (até 10 ms) */
    for (int i = 0; HAL_FDCAN_GetTxFifoFreeLevel(h) == 0; i++) {
        if (i >= 10) return -1;
        vTaskDelay(pdMS_TO_TICKS(1));
    }
    uint8_t d[64] = {0};
    memcpy(d, m->dados, n);                            /* bytes de enchimento a zero */
    return HAL_FDCAN_AddMessageToTxFifoQ(h, &tx, d) == HAL_OK ? 0 : -2;
}
