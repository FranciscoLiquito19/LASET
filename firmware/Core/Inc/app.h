/* Interfaces entre os módulos da aplicação. */
#ifndef APP_H
#define APP_H
#include <stdint.h>
#include "FreeRTOS.h"
#include "mensagem.h"
#include "encaminhamento_regras.h"

#define FIRMWARE_VERSAO "0.2.0"
/* O bit 7 do campo "tipo" marca a mensagem como urgente (RF14); os bits 0-6 são o tipo. */
#define TIPO_URGENTE 0x80
#define TIPO(m)      ((m)->c.tipo & 0x7F)

/* consola.c */
void consola_iniciar(void);
void consola_printf(const char *fmt, ...) __attribute__((format(printf, 1, 2)));

/* encaminhamento.c */
void encaminhamento_iniciar(void);
BaseType_t encaminhamento_entrada(const mensagem_t *m, TickType_t espera);
BaseType_t encaminhamento_entrada_isr(const mensagem_t *m, BaseType_t *acordar);
void encaminhamento_estado(void);
extern tabela_t tabela;
extern volatile uint32_t can_bus_off[2];   /* recuperações de bus-off por controlador */

/* can.c */
int  can_autoteste(void);                 /* 0 = os dois FDCAN passaram em loopback */
void can_arrancar(void);
int  can_enviar(uint8_t canal, const mensagem_t *m);
int  can_pc_enviar(uint8_t canal, const mensagem_t *m);   /* ISO-TP, quando o PC está no CAN */
#define ISOTP_ID_PC_PARA_GW  0x7E0                         /* identificadores do ISO-TP (11 bits) */
#define ISOTP_ID_GW_PARA_PC  0x7E8
uint8_t len_valida_canfd(uint16_t n);      /* arredonda para um comprimento CAN FD válido */

/* serie.c */
void serie_iniciar(void);
int  pc_serie_enviar(const mensagem_t *m);
int  rs485_enviar(const mensagem_t *m);
int  rs232_enviar_bruto(const mensagem_t *m);

/* sincronizacao.c */
void sincronizacao_iniciar(void);
uint64_t sincronizacao_agora_us(void);
int  sincronizacao_estado(uint32_t *freq_hz, int64_t *utc_s);  /* 1 = sincronizado */

/* pwm.c */
void pwm_iniciar(void);
int  pwm_comando(const mensagem_t *m);

/* eth.c */
void eth_iniciar(void);
int  eth_enviar(const mensagem_t *m);
void eth_estado(void);

/* flash_config.c */
void config_carregar(void);            /* antes de iniciar os periféricos */
int  config_carregada_da_flash(void);
void config_iniciar(void);
void config_pedir_gravacao(void);

/* i2c_bus.c */
int  i2c_executar(uint8_t canal, const mensagem_t *m);

#endif
