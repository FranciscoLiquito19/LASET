/* RS232 (ligação ao PC, tramas COBS + CRC-16), RS485 (dados em bruto) e receção do GPS.
 * A receção usa ReceiveToIdle: cada bloco recebido até a linha ficar livre é tratado
 * de uma vez. */
#include <string.h>
#include "placa.h"
#include "app.h"
#include "cobs.h"
#include "task.h"
#include "stream_buffer.h"

#define BLOCO 64
static uint8_t rx232[BLOCO], rx485[BLOCO], rxgps[BLOCO];

/* bytes da ligação série ao PC, consumidos pela tarefa pc_serie */
static StreamBufferHandle_t sb_pc;
static StaticStreamBuffer_t sb_pc_mem;
static uint8_t sb_pc_buf[1024];
/* bytes do GPS, consumidos pela tarefa de sincronização */
StreamBufferHandle_t sb_gps;
static StaticStreamBuffer_t sb_gps_mem;
static uint8_t sb_gps_buf[512];

static StaticTask_t pc_tcb;
static StackType_t pc_pilha[768];

#define TRAMA_MAX (sizeof(cabecalho_t) + MSG_DADOS_MAX + 2)

static void bloco_para_mensagem(uint8_t interface, const uint8_t *d, uint16_t n, BaseType_t *acordar)
{
    mensagem_t m;
    memset(&m.c, 0, sizeof m.c);
    m.c.versao = MSG_VERSAO;
    m.c.tipo = MSG_DADOS;
    m.c.interface = interface;
    m.c.comprimento = n;
    m.c.marca_us = sincronizacao_agora_us();
    m.origem_if = interface;
    m.origem_canal = 0;
    m.urgente = 0;
    memcpy(m.dados, d, n);
    encaminhamento_entrada_isr(&m, acordar);
}

void HAL_UARTEx_RxEventCallback(UART_HandleTypeDef *h, uint16_t n)
{
    BaseType_t acordar = pdFALSE;
    if (h->Instance == USART2) {
        if (tabela.pc_if == IF_RS232) xStreamBufferSendFromISR(sb_pc, rx232, n, &acordar);
        else bloco_para_mensagem(IF_RS232, rx232, n, &acordar);
        HAL_UARTEx_ReceiveToIdle_IT(h, rx232, BLOCO);
    } else if (h->Instance == USART6) {
        bloco_para_mensagem(IF_RS485, rx485, n, &acordar);
        HAL_UARTEx_ReceiveToIdle_IT(h, rx485, BLOCO);
    } else if (h->Instance == UART7) {
        xStreamBufferSendFromISR(sb_gps, rxgps, n, &acordar);
        HAL_UARTEx_ReceiveToIdle_IT(h, rxgps, BLOCO);
    }
    portYIELD_FROM_ISR(acordar);
}

void HAL_UART_ErrorCallback(UART_HandleTypeDef *h)
{
    /* erro de trama, ruído ou sobreposição: retoma a receção */
    if (h->Instance == USART2)      HAL_UARTEx_ReceiveToIdle_IT(h, rx232, BLOCO);
    else if (h->Instance == USART6) HAL_UARTEx_ReceiveToIdle_IT(h, rx485, BLOCO);
    else if (h->Instance == UART7)  HAL_UARTEx_ReceiveToIdle_IT(h, rxgps, BLOCO);
}

/* Descodifica as tramas vindas do PC: COBS(cabeçalho + dados + CRC-16 LE), 0x00 no fim. */
static void tarefa_pc_serie(void *arg)
{
    (void)arg;
    static uint8_t trama[TRAMA_MAX + TRAMA_MAX / 254 + 2], dec[TRAMA_MAX + 2];
    size_t n = 0;
    uint8_t b;
    for (;;) {
        if (xStreamBufferReceive(sb_pc, &b, 1, portMAX_DELAY) != 1) continue;
        if (b != 0) {
            if (n < sizeof trama) trama[n++] = b; else n = sizeof trama + 1;   /* demasiado longa */
            continue;
        }
        size_t k = (n <= sizeof trama) ? cobs_descodificar(trama, n, dec) : 0;
        n = 0;
        if (k < sizeof(cabecalho_t) + 2) continue;
        uint16_t crc = (uint16_t)(dec[k - 2] | dec[k - 1] << 8);
        if (crc16_ccitt(dec, k - 2) != crc) continue;
        mensagem_t m;
        memcpy(&m.c, dec, sizeof(cabecalho_t));
        if (m.c.versao != MSG_VERSAO || m.c.comprimento != k - 2 - sizeof(cabecalho_t)
            || m.c.comprimento > MSG_DADOS_MAX) continue;
        memcpy(m.dados, dec + sizeof(cabecalho_t), m.c.comprimento);
        m.origem_if = IF_RS232;
        m.origem_canal = 0;
        m.urgente = (m.c.tipo & TIPO_URGENTE) != 0;
        encaminhamento_entrada(&m, pdMS_TO_TICKS(10));
    }
}

int pc_serie_enviar(const mensagem_t *m)
{
    static uint8_t bruto[TRAMA_MAX], enc[TRAMA_MAX + TRAMA_MAX / 254 + 2];
    uint16_t n = m->c.comprimento > MSG_DADOS_MAX ? MSG_DADOS_MAX : m->c.comprimento;
    cabecalho_t c = m->c;
    c.versao = MSG_VERSAO;
    c.comprimento = n;
    memcpy(bruto, &c, sizeof c);
    memcpy(bruto + sizeof c, m->dados, n);
    uint16_t crc = crc16_ccitt(bruto, sizeof c + n);
    bruto[sizeof c + n] = (uint8_t)crc;
    bruto[sizeof c + n + 1] = (uint8_t)(crc >> 8);
    size_t k = cobs_codificar(bruto, sizeof c + n + 2, enc);
    enc[k++] = 0;
    return HAL_UART_Transmit(&huart2, enc, (uint16_t)k, 50) == HAL_OK ? 0 : -1;
}

int rs232_enviar_bruto(const mensagem_t *m)
{
    return HAL_UART_Transmit(&huart2, (uint8_t *)m->dados, m->c.comprimento, 50) == HAL_OK ? 0 : -1;
}

int rs485_enviar(const mensagem_t *m)
{
    /* o USART6 ativa o DE durante a transmissão; o recetor fica sempre ligado (eco) */
    return HAL_UART_Transmit(&huart6, (uint8_t *)m->dados, m->c.comprimento, 50) == HAL_OK ? 0 : -1;
}

void serie_iniciar(void)
{
    sb_pc = xStreamBufferCreateStatic(sizeof sb_pc_buf, 1, sb_pc_buf, &sb_pc_mem);
    sb_gps = xStreamBufferCreateStatic(sizeof sb_gps_buf, 1, sb_gps_buf, &sb_gps_mem);
    xTaskCreateStatic(tarefa_pc_serie, "pc_serie", 768, NULL, 4, pc_pilha, &pc_tcb);
    HAL_UARTEx_ReceiveToIdle_IT(&huart2, rx232, BLOCO);
    HAL_UARTEx_ReceiveToIdle_IT(&huart6, rx485, BLOCO);
    HAL_UARTEx_ReceiveToIdle_IT(&huart7, rxgps, BLOCO);
}
