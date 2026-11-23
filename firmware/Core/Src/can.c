/* CAN FD: autoteste em loopback, receção por interrupção e transmissão. Quando a
 * ligação ao PC é um dos CAN FD (RF09), as tramas com os identificadores do ISO-TP
 * vão para a tarefa isotp, que junta as mensagens do PC e responde com Flow Control. */
#include <string.h>
#include "placa.h"
#include "app.h"
#include "isotp.h"
#include "trama_pc.h"
#include "task.h"
#include "queue.h"

#define ISOTP_N_BS_MS  1000     /* tempo máximo à espera de um Flow Control (N_Bs) */

typedef struct { uint8_t canal, n; uint8_t d[64]; } trama_t;
static QueueHandle_t fila_isotp, fila_fc[2];
static StaticQueue_t fila_isotp_q, fila_fc_q[2];
static uint8_t fila_isotp_buf[8 * sizeof(trama_t)], fila_fc_buf[2][sizeof(trama_t)];
static StaticTask_t isotp_tcb;
static StackType_t isotp_pilha[768];
static void tarefa_isotp(void *arg);

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
    fila_isotp = xQueueCreateStatic(8, sizeof(trama_t), fila_isotp_buf, &fila_isotp_q);
    for (int i = 0; i < 2; i++) fila_fc[i] = xQueueCreateStatic(1, sizeof(trama_t), fila_fc_buf[i], &fila_fc_q[i]);
    xTaskCreateStatic(tarefa_isotp, "isotp", 768, NULL, 4, isotp_pilha, &isotp_tcb);
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
        if (tabela.pc_if == IF_CANFD && tabela.pc_canal == m.c.canal && rx.IdType == FDCAN_STANDARD_ID
            && rx.Identifier == ISOTP_ID_PC_PARA_GW) {
            trama_t t = { .canal = m.c.canal, .n = (uint8_t)m.c.comprimento };
            memcpy(t.d, m.dados, t.n);
            xQueueSendFromISR(fila_isotp, &t, &acordar);
            continue;
        }
        encaminhamento_entrada_isr(&m, &acordar);
    }
    portYIELD_FROM_ISR(acordar);
}

static int can_trama(uint8_t canal, uint32_t endereco, const uint8_t *dados, uint16_t n)
{
    FDCAN_HandleTypeDef *h = handle(canal);
    FDCAN_TxHeaderTypeDef tx;
    if (n > 64) n = 64;
    cabecalho_tx(&tx, endereco, n);
    /* espera por espaço na fila de transmissão do controlador (até 10 ms) */
    for (int i = 0; HAL_FDCAN_GetTxFifoFreeLevel(h) == 0; i++) {
        if (i >= 10) return -1;
        vTaskDelay(pdMS_TO_TICKS(1));
    }
    uint8_t d[64] = {0};
    memcpy(d, dados, n);                               /* bytes de enchimento a zero */
    return HAL_FDCAN_AddMessageToTxFifoQ(h, &tx, d) == HAL_OK ? 0 : -2;
}

int can_enviar(uint8_t canal, const mensagem_t *m)
{
    return can_trama(canal, m->c.endereco, m->dados, m->c.comprimento);
}

/* Mensagem para o PC por ISO-TP: cabeçalho + dados, segmentados em tramas de 64 bytes. */
int can_pc_enviar(uint8_t canal, const mensagem_t *m)
{
    uint8_t b[PC_BRUTO_MAX], t[64];
    trama_t fc;
    isotp_tx_t tx;
    isotp_tx_iniciar(&tx, b, (uint16_t)pc_para_bytes(m, b));
    xQueueReset(fila_fc[canal]);
    for (;;) {
        int k = isotp_tx_proxima(&tx, t);
        if (k < 0) return 0;
        if (k == 0) {                                  /* espera pelo Flow Control do PC */
            if (xQueueReceive(fila_fc[canal], &fc, pdMS_TO_TICKS(ISOTP_N_BS_MS)) != pdTRUE) return -1;
            if (isotp_tx_fc(&tx, fc.d, fc.n) < 0) return -2;
            continue;
        }
        if (can_trama(canal, ISOTP_ID_GW_PARA_PC | CAN_FD | CAN_BRS, t, (uint16_t)k) != 0) return -3;
        uint32_t st = isotp_stmin_us(tx.stmin);
        if (st) vTaskDelay(pdMS_TO_TICKS((st + 999) / 1000));
    }
}

static void tarefa_isotp(void *arg)
{
    (void)arg;
    static isotp_rx_t rx[2];
    trama_t t;
    uint8_t fc[3], fc_n;
    mensagem_t m;
    for (;;) {
        if (xQueueReceive(fila_isotp, &t, portMAX_DELAY) != pdTRUE || t.canal > 1) continue;
        switch (isotp_rx_trama(&rx[t.canal], t.d, t.n, fc, &fc_n)) {
        case ISOTP_RX_ENVIAR_FC:
            can_trama(t.canal, ISOTP_ID_GW_PARA_PC | CAN_FD | CAN_BRS, fc, fc_n);
            break;
        case ISOTP_RX_FC_RECEBIDO:
            xQueueOverwrite(fila_fc[t.canal], &t);
            break;
        case ISOTP_RX_COMPLETA:
            if (pc_de_bytes(rx[t.canal].buf, rx[t.canal].total, &m) != 0) break;
            m.origem_if = IF_CANFD;
            m.origem_canal = t.canal;
            m.urgente = (m.c.tipo & TIPO_URGENTE) != 0;
            encaminhamento_entrada(&m, pdMS_TO_TICKS(10));
            break;
        default:
            break;
        }
    }
}
