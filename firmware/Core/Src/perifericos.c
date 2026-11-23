/* Iniciação dos periféricos (o equivalente ao que o CubeMX gera em main.c). */
#include "placa.h"

FDCAN_HandleTypeDef hfdcan1, hfdcan2;
TIM_HandleTypeDef   htim1, htim2;
UART_HandleTypeDef  huart2, huart3, huart6, huart7;
I2C_HandleTypeDef   hi2c1, hi2c2;

static void gpio_iniciar(void)
{
    GPIO_InitTypeDef g = {0};
    __HAL_RCC_GPIOA_CLK_ENABLE(); __HAL_RCC_GPIOB_CLK_ENABLE(); __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE(); __HAL_RCC_GPIOE_CLK_ENABLE(); __HAL_RCC_GPIOF_CLK_ENABLE();
    __HAL_RCC_GPIOG_CLK_ENABLE(); __HAL_RCC_GPIOH_CLK_ENABLE();

    HAL_GPIO_WritePin(LED_PORTA, LED_PINO, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(CAN1_SILENT_PORTA, CAN1_SILENT_PINO, GPIO_PIN_RESET);
    HAL_GPIO_WritePin(CAN2_SILENT_PORTA, CAN2_SILENT_PINO, GPIO_PIN_RESET);
    g.Mode = GPIO_MODE_OUTPUT_PP; g.Pull = GPIO_NOPULL; g.Speed = GPIO_SPEED_FREQ_LOW;
    g.Pin = LED_PINO;                 HAL_GPIO_Init(LED_PORTA, &g);
    g.Pin = CAN1_SILENT_PINO | CAN2_SILENT_PINO; HAL_GPIO_Init(GPIOG, &g);

    g.Mode = GPIO_MODE_INPUT; g.Pull = GPIO_PULLUP;      /* na PCB há pull-up externo */
    g.Pin = PG_5V_PINO | PG_3V3_PINO; HAL_GPIO_Init(PG_PORTA, &g);
}

/* FDCAN: núcleo a 80 MHz. Arbitragem 1 Mbit/s = 80 tq (63 + 16 + 1), ponto de
 * amostragem a 80 %. Dados 8 Mbit/s = 10 tq (7 + 2 + 1), amostragem a 80 %, com
 * compensação do atraso do transceiver (TDC). A RAM de mensagens (10 kB) é partilhada:
 * cada controlador usa 8 elementos de 64 bytes na receção e 8 na transmissão. */
static void fdcan_iniciar(FDCAN_HandleTypeDef *h, FDCAN_GlobalTypeDef *inst, uint32_t offset, uint32_t modo)
{
    h->Instance = inst;
    h->Init.FrameFormat = FDCAN_FRAME_FD_BRS;
    h->Init.Mode = modo;
    h->Init.AutoRetransmission = ENABLE;
    h->Init.TransmitPause = DISABLE;
    h->Init.ProtocolException = ENABLE;
    h->Init.NominalPrescaler = 1;
    h->Init.NominalSyncJumpWidth = 16;
    h->Init.NominalTimeSeg1 = 63;
    h->Init.NominalTimeSeg2 = 16;
    h->Init.DataPrescaler = 1;
    h->Init.DataSyncJumpWidth = 2;
    h->Init.DataTimeSeg1 = 7;
    h->Init.DataTimeSeg2 = 2;
    h->Init.MessageRAMOffset = offset;
    h->Init.StdFiltersNbr = 0;
    h->Init.ExtFiltersNbr = 0;
    h->Init.RxFifo0ElmtsNbr = 8;
    h->Init.RxFifo0ElmtSize = FDCAN_DATA_BYTES_64;
    h->Init.RxFifo1ElmtsNbr = 0;
    h->Init.RxFifo1ElmtSize = FDCAN_DATA_BYTES_64;
    h->Init.RxBuffersNbr = 0;
    h->Init.RxBufferSize = FDCAN_DATA_BYTES_64;
    h->Init.TxEventsNbr = 0;
    h->Init.TxBuffersNbr = 0;
    h->Init.TxFifoQueueElmtsNbr = 8;
    h->Init.TxFifoQueueMode = FDCAN_TX_FIFO_OPERATION;
    h->Init.TxElmtSize = FDCAN_DATA_BYTES_64;
    if (HAL_FDCAN_Init(h) != HAL_OK) Error_Handler();
    /* aceita todas as tramas na FIFO 0; o encaminhamento decide o destino */
    if (HAL_FDCAN_ConfigGlobalFilter(h, FDCAN_ACCEPT_IN_RX_FIFO0, FDCAN_ACCEPT_IN_RX_FIFO0,
                                     FDCAN_REJECT_REMOTE, FDCAN_REJECT_REMOTE) != HAL_OK) Error_Handler();
    if (HAL_FDCAN_ConfigTxDelayCompensation(h, h->Init.DataPrescaler * h->Init.DataTimeSeg1, 0) != HAL_OK) Error_Handler();
    if (HAL_FDCAN_EnableTxDelayCompensation(h) != HAL_OK) Error_Handler();
}

void can_configurar(uint32_t modo)
{
    if (hfdcan1.Instance) HAL_FDCAN_DeInit(&hfdcan1);
    if (hfdcan2.Instance) HAL_FDCAN_DeInit(&hfdcan2);
    fdcan_iniciar(&hfdcan1, FDCAN1, 0, modo);
    fdcan_iniciar(&hfdcan2, FDCAN2, 320, modo);   /* palavras de 32 bits; FDCAN1 usa 288 */
}

/* TIM1: PWM a 50 Hz com resolução de 0,5 us (240 MHz / 120 = 2 MHz; período 40000).
 * Entrada de paragem BKIN (PE15) ativa a nível baixo: a falha da carga ou a falta de
 * alimentação do isolador desligam as saídas por hardware. */
static void tim1_iniciar(void)
{
    TIM_OC_InitTypeDef oc = {0};
    TIM_BreakDeadTimeConfigTypeDef br = {0};
    htim1.Instance = TIM1;
    htim1.Init.Prescaler = 119;
    htim1.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim1.Init.Period = 39999;
    htim1.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim1.Init.RepetitionCounter = 0;
    htim1.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_ENABLE;
    if (HAL_TIM_PWM_Init(&htim1) != HAL_OK) Error_Handler();
    oc.OCMode = TIM_OCMODE_PWM1;
    oc.Pulse = 0;                                  /* nível baixo até haver comando válido */
    oc.OCPolarity = TIM_OCPOLARITY_HIGH;
    oc.OCNPolarity = TIM_OCNPOLARITY_HIGH;
    oc.OCFastMode = TIM_OCFAST_DISABLE;
    oc.OCIdleState = TIM_OCIDLESTATE_RESET;
    oc.OCNIdleState = TIM_OCNIDLESTATE_RESET;
    if (HAL_TIM_PWM_ConfigChannel(&htim1, &oc, TIM_CHANNEL_1) != HAL_OK) Error_Handler();
    if (HAL_TIM_PWM_ConfigChannel(&htim1, &oc, TIM_CHANNEL_2) != HAL_OK) Error_Handler();
    if (HAL_TIM_PWM_ConfigChannel(&htim1, &oc, TIM_CHANNEL_3) != HAL_OK) Error_Handler();
    br.OffStateRunMode = TIM_OSSR_ENABLE;
    br.OffStateIDLEMode = TIM_OSSI_ENABLE;
    br.LockLevel = TIM_LOCKLEVEL_OFF;
    br.DeadTime = 0;
    br.BreakState = TIM_BREAK_ENABLE;
    br.BreakPolarity = TIM_BREAKPOLARITY_LOW;
    br.BreakFilter = 15;                           /* ignora picos curtos */
    br.Break2State = TIM_BREAK2_DISABLE;
    br.AutomaticOutput = TIM_AUTOMATICOUTPUT_DISABLE;  /* rearme por software */
    if (HAL_TIMEx_ConfigBreakDeadTime(&htim1, &br) != HAL_OK) Error_Handler();
}

/* TIM2 (32 bits a 240 MHz): captura do flanco ascendente do PPS em PA0 (TIM2_CH1). */
static void tim2_iniciar(void)
{
    TIM_IC_InitTypeDef ic = {0};
    htim2.Instance = TIM2;
    htim2.Init.Prescaler = 0;
    htim2.Init.CounterMode = TIM_COUNTERMODE_UP;
    htim2.Init.Period = 0xFFFFFFFF;
    htim2.Init.ClockDivision = TIM_CLOCKDIVISION_DIV1;
    htim2.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
    if (HAL_TIM_IC_Init(&htim2) != HAL_OK) Error_Handler();
    ic.ICPolarity = TIM_INPUTCHANNELPOLARITY_RISING;
    ic.ICSelection = TIM_ICSELECTION_DIRECTTI;
    ic.ICPrescaler = TIM_ICPSC_DIV1;
    ic.ICFilter = 4;
    if (HAL_TIM_IC_ConfigChannel(&htim2, &ic, TIM_CHANNEL_1) != HAL_OK) Error_Handler();
}

static void uart_iniciar(UART_HandleTypeDef *h, USART_TypeDef *inst, uint32_t baud)
{
    h->Instance = inst;
    h->Init.BaudRate = baud;
    h->Init.WordLength = UART_WORDLENGTH_8B;
    h->Init.StopBits = UART_STOPBITS_1;
    h->Init.Parity = UART_PARITY_NONE;
    h->Init.Mode = UART_MODE_TX_RX;
    h->Init.HwFlowCtl = UART_HWCONTROL_NONE;
    h->Init.OverSampling = UART_OVERSAMPLING_8;   /* permite 1 Mbit/s e mais com 120 MHz */
    h->Init.OneBitSampling = UART_ONE_BIT_SAMPLE_DISABLE;
    h->Init.ClockPrescaler = UART_PRESCALER_DIV1;
    h->AdvancedInit.AdvFeatureInit = UART_ADVFEATURE_NO_INIT;
}

static void uarts_iniciar(void)
{
    uart_iniciar(&huart2, USART2, 1000000);        /* RS232 (RF02: 500 kbit/s e 1 Mbit/s) */
    if (HAL_UART_Init(&huart2) != HAL_OK) Error_Handler();
    uart_iniciar(&huart6, USART6, 1000000);        /* RS485, DE controlado pelo periférico */
    if (HAL_RS485Ex_Init(&huart6, UART_DE_POLARITY_HIGH, 8, 8) != HAL_OK) Error_Handler();
    uart_iniciar(&huart7, UART7, 9600);            /* GPS (NMEA a 9600 baud por omissão) */
    if (HAL_UART_Init(&huart7) != HAL_OK) Error_Handler();
    uart_iniciar(&huart3, USART3, 115200);         /* consola (VCP da NUCLEO) */
    if (HAL_UART_Init(&huart3) != HAL_OK) Error_Handler();
}

/* I2C em Standard mode (RF01), núcleo a 120 MHz: PRESC 11 (100 ns), SCLL 5 us, SCLH 4 us,
 * SDADEL 200 ns, SCLDEL 500 ns -> ~100 kHz. */
static void i2c_iniciar(I2C_HandleTypeDef *h, I2C_TypeDef *inst)
{
    h->Instance = inst;
    h->Init.Timing = 0xB0422731;
    h->Init.OwnAddress1 = 0;
    h->Init.AddressingMode = I2C_ADDRESSINGMODE_7BIT;
    h->Init.DualAddressMode = I2C_DUALADDRESS_DISABLE;
    h->Init.OwnAddress2 = 0;
    h->Init.OwnAddress2Masks = I2C_OA2_NOMASK;
    h->Init.GeneralCallMode = I2C_GENERALCALL_DISABLE;
    h->Init.NoStretchMode = I2C_NOSTRETCH_DISABLE;
    if (HAL_I2C_Init(h) != HAL_OK) Error_Handler();
    HAL_I2CEx_ConfigAnalogFilter(h, I2C_ANALOGFILTER_ENABLE);
}

void perifericos_iniciar(void)
{
    gpio_iniciar();
#if defined(LASET_CAN_LOOPBACK)
    can_configurar(FDCAN_MODE_INTERNAL_LOOPBACK);
#else
    can_configurar(FDCAN_MODE_NORMAL);
#endif
    tim1_iniciar();
    tim2_iniciar();
    uarts_iniciar();
    i2c_iniciar(&hi2c1, I2C1);
    i2c_iniciar(&hi2c2, I2C2);
}
