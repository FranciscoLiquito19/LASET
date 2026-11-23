/* Relógios, pinos (funções alternativas) e interrupções de cada periférico. */
#include "placa.h"

static void af(GPIO_TypeDef *porta, uint32_t pinos, uint32_t alt, uint32_t pull, uint32_t modo)
{
    GPIO_InitTypeDef g = {0};
    g.Pin = pinos; g.Mode = modo; g.Pull = pull; g.Speed = GPIO_SPEED_FREQ_VERY_HIGH; g.Alternate = alt;
    HAL_GPIO_Init(porta, &g);
}

static void irq(IRQn_Type n)
{
    HAL_NVIC_SetPriority(n, PRIO_IRQ_PERIFERICOS, 0);
    HAL_NVIC_EnableIRQ(n);
}

void HAL_MspInit(void)
{
    __HAL_RCC_SYSCFG_CLK_ENABLE();
}

void HAL_FDCAN_MspInit(FDCAN_HandleTypeDef *h)
{
    __HAL_RCC_FDCAN_CLK_ENABLE();
    if (h->Instance == FDCAN1) {                      /* PD0 RX, PD1 TX */
        __HAL_RCC_GPIOD_CLK_ENABLE();
        af(GPIOD, GPIO_PIN_0 | GPIO_PIN_1, GPIO_AF9_FDCAN1, GPIO_NOPULL, GPIO_MODE_AF_PP);
        irq(FDCAN1_IT0_IRQn);
    } else {                                          /* PB5 RX, PB6 TX */
        __HAL_RCC_GPIOB_CLK_ENABLE();
        af(GPIOB, GPIO_PIN_5 | GPIO_PIN_6, GPIO_AF9_FDCAN2, GPIO_NOPULL, GPIO_MODE_AF_PP);
        irq(FDCAN2_IT0_IRQn);
    }
}

void HAL_FDCAN_MspDeInit(FDCAN_HandleTypeDef *h)
{
    HAL_NVIC_DisableIRQ(h->Instance == FDCAN1 ? FDCAN1_IT0_IRQn : FDCAN2_IT0_IRQn);
}

void HAL_TIM_PWM_MspInit(TIM_HandleTypeDef *h)
{
    if (h->Instance == TIM1) {                        /* PE9, PE11, PE13 = CH1-3; PE15 = BKIN */
        __HAL_RCC_TIM1_CLK_ENABLE();
        __HAL_RCC_GPIOE_CLK_ENABLE();
        af(GPIOE, GPIO_PIN_9 | GPIO_PIN_11 | GPIO_PIN_13, GPIO_AF1_TIM1, GPIO_PULLDOWN, GPIO_MODE_AF_PP);
        af(GPIOE, GPIO_PIN_15, GPIO_AF1_TIM1, GPIO_PULLUP, GPIO_MODE_AF_PP);
    }
}

void HAL_TIM_IC_MspInit(TIM_HandleTypeDef *h)
{
    if (h->Instance == TIM2) {                        /* PA0 = TIM2_CH1 (PPS) */
        __HAL_RCC_TIM2_CLK_ENABLE();
        __HAL_RCC_GPIOA_CLK_ENABLE();
        af(GPIOA, GPIO_PIN_0, GPIO_AF1_TIM2, GPIO_PULLDOWN, GPIO_MODE_AF_PP);
        irq(TIM2_IRQn);
    }
}

void HAL_UART_MspInit(UART_HandleTypeDef *h)
{
    if (h->Instance == USART2) {                      /* RS232: PD5 TX, PD6 RX */
        __HAL_RCC_USART2_CLK_ENABLE(); __HAL_RCC_GPIOD_CLK_ENABLE();
        af(GPIOD, GPIO_PIN_5 | GPIO_PIN_6, GPIO_AF7_USART2, GPIO_PULLUP, GPIO_MODE_AF_PP);
        irq(USART2_IRQn);
    } else if (h->Instance == USART3) {               /* consola: PD8 TX, PD9 RX */
        __HAL_RCC_USART3_CLK_ENABLE(); __HAL_RCC_GPIOD_CLK_ENABLE();
        af(GPIOD, GPIO_PIN_8 | GPIO_PIN_9, GPIO_AF7_USART3, GPIO_PULLUP, GPIO_MODE_AF_PP);
    } else if (h->Instance == USART6) {               /* RS485: PC6 TX, PC7 RX, PG8 DE */
        __HAL_RCC_USART6_CLK_ENABLE(); __HAL_RCC_GPIOC_CLK_ENABLE(); __HAL_RCC_GPIOG_CLK_ENABLE();
        af(GPIOC, GPIO_PIN_6 | GPIO_PIN_7, GPIO_AF7_USART6, GPIO_PULLUP, GPIO_MODE_AF_PP);
        af(GPIOG, GPIO_PIN_8, GPIO_AF7_USART6, GPIO_PULLDOWN, GPIO_MODE_AF_PP);
        irq(USART6_IRQn);
    } else if (h->Instance == UART7) {                /* GPS: PE8 TX, PE7 RX */
        __HAL_RCC_UART7_CLK_ENABLE(); __HAL_RCC_GPIOE_CLK_ENABLE();
        af(GPIOE, GPIO_PIN_7 | GPIO_PIN_8, GPIO_AF7_UART7, GPIO_PULLUP, GPIO_MODE_AF_PP);
        irq(UART7_IRQn);
    }
}

void HAL_I2C_MspInit(I2C_HandleTypeDef *h)
{
    if (h->Instance == I2C1) {                        /* PB8 SCL, PB9 SDA */
        __HAL_RCC_GPIOB_CLK_ENABLE();
        af(GPIOB, GPIO_PIN_8 | GPIO_PIN_9, GPIO_AF4_I2C1, GPIO_NOPULL, GPIO_MODE_AF_OD);
        __HAL_RCC_I2C1_CLK_ENABLE();
    } else if (h->Instance == I2C2) {                 /* PF1 SCL, PF0 SDA */
        __HAL_RCC_GPIOF_CLK_ENABLE();
        af(GPIOF, GPIO_PIN_0 | GPIO_PIN_1, GPIO_AF4_I2C2, GPIO_NOPULL, GPIO_MODE_AF_OD);
        __HAL_RCC_I2C2_CLK_ENABLE();
    }
}

void HAL_ETH_MspInit(ETH_HandleTypeDef *h)
{
    __HAL_RCC_ETH1MAC_CLK_ENABLE();
    __HAL_RCC_ETH1TX_CLK_ENABLE();
    __HAL_RCC_ETH1RX_CLK_ENABLE();
    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOB_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOG_CLK_ENABLE();
    /* RMII: PA1 REF_CLK, PA2 MDIO, PA7 CRS_DV, PC1 MDC, PC4 RXD0, PC5 RXD1,
     * PG11 TX_EN, PG13 TXD0, PB13 TXD1 */
    af(GPIOA, GPIO_PIN_1 | GPIO_PIN_2 | GPIO_PIN_7, GPIO_AF11_ETH, GPIO_NOPULL, GPIO_MODE_AF_PP);
    af(GPIOC, GPIO_PIN_1 | GPIO_PIN_4 | GPIO_PIN_5, GPIO_AF11_ETH, GPIO_NOPULL, GPIO_MODE_AF_PP);
    af(GPIOG, GPIO_PIN_11 | GPIO_PIN_13, GPIO_AF11_ETH, GPIO_NOPULL, GPIO_MODE_AF_PP);
    af(GPIOB, GPIO_PIN_13, GPIO_AF11_ETH, GPIO_NOPULL, GPIO_MODE_AF_PP);
    irq(ETH_IRQn);
}
