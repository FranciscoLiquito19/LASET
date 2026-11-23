/* Formato das mensagens trocadas com o PC e entre tarefas (Tabela 5.4 do relatório).
 * O cabeçalho tem 20 bytes, em little-endian, seguido de até MSG_DADOS_MAX bytes. */
#ifndef MENSAGEM_H
#define MENSAGEM_H
#include <stdint.h>

#define MSG_VERSAO      1
#define MSG_DADOS_MAX   64   /* uma trama CAN FD; mensagens maiores segmentam-se */

typedef enum {               /* campo "interface" */
    IF_I2C = 0, IF_RS232, IF_RS485, IF_CANFD, IF_ETH, IF_PWM, IF_SISTEMA, IF_N
} interface_t;

typedef enum {               /* campo "tipo" */
    MSG_PEDIDO = 0,          /* pedido de leitura (I2C) ou de estado */
    MSG_DADOS,               /* dados a enviar / dados recebidos */
    MSG_CONFIRMACAO,
    MSG_ERRO,
    MSG_CONFIG
} tipo_t;

/* Bits do campo "endereco" em CAN FD: identificador nos bits 0-28. */
#define CAN_ID_ESTENDIDO  (1UL << 31)
#define CAN_FD            (1UL << 30)
#define CAN_BRS           (1UL << 29)
#define CAN_ID_MASCARA    0x1FFFFFFFUL

typedef struct __attribute__((packed)) {
    uint8_t  versao;
    uint8_t  tipo;
    uint8_t  interface;      /* destino (vindo do PC) ou origem (para o PC) */
    uint8_t  canal;
    uint32_t endereco;       /* endereço I2C, nó RS485 ou identificador CAN */
    uint16_t sequencia;
    uint64_t marca_us;       /* microssegundos desde a época UTC (RF16) */
    uint16_t comprimento;
} cabecalho_t;

_Static_assert(sizeof(cabecalho_t) == 20, "cabeçalho tem de ter 20 bytes");

typedef struct {
    cabecalho_t c;
    uint8_t origem_if;       /* por onde a mensagem entrou na unidade */
    uint8_t origem_canal;
    uint8_t urgente;         /* classe de prioridade (RF14) */
    uint8_t dados[MSG_DADOS_MAX];
} mensagem_t;

#endif
