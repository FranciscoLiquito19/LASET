/* Pinos e periféricos, iguais ao esquema (hardware/gerador/folha_mcu.py).
 * A NUCLEO-H753ZI e a PCB usam os mesmos pinos; só mudam o relógio (8 MHz do ST-LINK
 * em bypass / cristal de 25 MHz) e a consola, que só existe na NUCLEO (USART3/VCP). */
#ifndef PLACA_H
#define PLACA_H
#include "stm32h7xx_hal.h"

#define PRIO_IRQ_PERIFERICOS   6   /* >= configLIBRARY_MAX_SYSCALL_INTERRUPT_PRIORITY */

/* LED de estado (na NUCLEO é o LD1 verde) */
#define LED_PORTA   GPIOB
#define LED_PINO    GPIO_PIN_0
/* SILENT dos transceivers CAN FD (alto = só escuta) */
#define CAN1_SILENT_PORTA GPIOG
#define CAN1_SILENT_PINO  GPIO_PIN_2
#define CAN2_SILENT_PORTA GPIOG
#define CAN2_SILENT_PINO  GPIO_PIN_3
/* Power-good das fontes */
#define PG_PORTA    GPIOF
#define PG_5V_PINO  GPIO_PIN_2
#define PG_3V3_PINO GPIO_PIN_3

extern FDCAN_HandleTypeDef hfdcan1, hfdcan2;
extern TIM_HandleTypeDef   htim1, htim2;
extern UART_HandleTypeDef  huart2, huart3, huart6, huart7;
extern I2C_HandleTypeDef   hi2c1, hi2c2;
extern ETH_HandleTypeDef   heth;

void sistema_relogios(void);
void sistema_cache(void);          /* configura também a MPU (Ethernet) */
void perifericos_iniciar(void);
void can_configurar(uint32_t modo);   /* FDCAN_MODE_NORMAL, _INTERNAL_LOOPBACK, ... */
void Error_Handler(void);

#endif
