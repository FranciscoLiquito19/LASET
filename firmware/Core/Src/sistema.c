/* Relógios: SYSCLK 480 MHz (VOS0), HCLK 240 MHz, APB 120 MHz (temporizadores a 240 MHz).
 * PLL1Q = 80 MHz para o FDCAN: 1 Mbit/s na arbitragem e 8 Mbit/s nos dados (Capítulo 5). */
#include "placa.h"

void sistema_relogios(void)
{
    RCC_OscInitTypeDef osc = {0};
    RCC_ClkInitTypeDef clk = {0};
    RCC_PeriphCLKInitTypeDef per = {0};

    HAL_PWREx_ConfigSupply(PWR_LDO_SUPPLY);
    __HAL_RCC_SYSCFG_CLK_ENABLE();
    __HAL_PWR_VOLTAGESCALING_CONFIG(PWR_REGULATOR_VOLTAGE_SCALE0);
    while (!__HAL_PWR_GET_FLAG(PWR_FLAG_VOSRDY)) {}

    osc.OscillatorType = RCC_OSCILLATORTYPE_HSE;
#if defined(PLACA_NUCLEO)
    osc.HSEState = RCC_HSE_BYPASS;          /* 8 MHz do MCO do ST-LINK */
    osc.PLL.PLLM = 1;                       /* 8 MHz na entrada do PLL */
    osc.PLL.PLLN = 120;                     /* VCO 960 MHz */
    osc.PLL.PLLRGE = RCC_PLL1VCIRANGE_3;
#else
    osc.HSEState = RCC_HSE_ON;              /* cristal de 25 MHz */
    osc.PLL.PLLM = 5;                       /* 5 MHz na entrada do PLL */
    osc.PLL.PLLN = 192;                     /* VCO 960 MHz */
    osc.PLL.PLLRGE = RCC_PLL1VCIRANGE_2;
#endif
    osc.PLL.PLLState = RCC_PLL_ON;
    osc.PLL.PLLSource = RCC_PLLSOURCE_HSE;
    osc.PLL.PLLP = 2;                       /* 480 MHz */
    osc.PLL.PLLQ = 12;                      /* 80 MHz -> FDCAN */
    osc.PLL.PLLR = 2;
    osc.PLL.PLLVCOSEL = RCC_PLL1VCOWIDE;
    osc.PLL.PLLFRACN = 0;
    if (HAL_RCC_OscConfig(&osc) != HAL_OK) Error_Handler();

    clk.ClockType = RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_PCLK1 |
                    RCC_CLOCKTYPE_PCLK2 | RCC_CLOCKTYPE_D3PCLK1 | RCC_CLOCKTYPE_D1PCLK1;
    clk.SYSCLKSource = RCC_SYSCLKSOURCE_PLLCLK;
    clk.SYSCLKDivider = RCC_SYSCLK_DIV1;
    clk.AHBCLKDivider = RCC_HCLK_DIV2;
    clk.APB3CLKDivider = RCC_APB3_DIV2;
    clk.APB1CLKDivider = RCC_APB1_DIV2;
    clk.APB2CLKDivider = RCC_APB2_DIV2;
    clk.APB4CLKDivider = RCC_APB4_DIV2;
    if (HAL_RCC_ClockConfig(&clk, FLASH_LATENCY_4) != HAL_OK) Error_Handler();

    __HAL_RCC_D2SRAM1_CLK_ENABLE();         /* SRAM do domínio D2 (descritores da Ethernet) */
    __HAL_RCC_D2SRAM2_CLK_ENABLE();
    __HAL_RCC_D2SRAM3_CLK_ENABLE();

    per.PeriphClockSelection = RCC_PERIPHCLK_FDCAN;
    per.FdcanClockSelection = RCC_FDCANCLKSOURCE_PLL;
    if (HAL_RCCEx_PeriphCLKConfig(&per) != HAL_OK) Error_Handler();
}

/* MPU: o início da SRAM do domínio D2 (secção .eth) fica sem cache, porque o DMA da
 * Ethernet lê e escreve lá. Os primeiros 256 bytes (descritores) ficam como memória
 * de dispositivo partilhada, como recomenda a ST (AN4838/AN4839). */
static void sistema_mpu(void)
{
    MPU_Region_InitTypeDef r = {0};
    HAL_MPU_Disable();
    r.Enable = MPU_REGION_ENABLE;
    r.Number = MPU_REGION_NUMBER0;
    r.BaseAddress = 0x30000000;
    r.Size = MPU_REGION_SIZE_32KB;
    r.SubRegionDisable = 0;
    r.TypeExtField = MPU_TEX_LEVEL1;              /* normal, sem cache */
    r.AccessPermission = MPU_REGION_FULL_ACCESS;
    r.DisableExec = MPU_INSTRUCTION_ACCESS_DISABLE;
    r.IsShareable = MPU_ACCESS_NOT_SHAREABLE;
    r.IsCacheable = MPU_ACCESS_NOT_CACHEABLE;
    r.IsBufferable = MPU_ACCESS_NOT_BUFFERABLE;
    HAL_MPU_ConfigRegion(&r);
    r.Number = MPU_REGION_NUMBER1;
    r.Size = MPU_REGION_SIZE_256B;
    r.TypeExtField = MPU_TEX_LEVEL0;              /* dispositivo partilhado */
    r.IsShareable = MPU_ACCESS_SHAREABLE;
    r.IsBufferable = MPU_ACCESS_BUFFERABLE;
    HAL_MPU_ConfigRegion(&r);
    /* setores da configuração (banco 2, 256 KB): sem cache, para a leitura ir sempre à
     * flash e um erro de ECC chegar ao CPU como falha de barramento precisa (ver
     * flash_config.c) */
    r.Number = MPU_REGION_NUMBER2;
    r.BaseAddress = 0x08100000;
    r.Size = MPU_REGION_SIZE_256KB;
    r.TypeExtField = MPU_TEX_LEVEL1;
    r.IsShareable = MPU_ACCESS_NOT_SHAREABLE;
    r.IsCacheable = MPU_ACCESS_NOT_CACHEABLE;
    r.IsBufferable = MPU_ACCESS_NOT_BUFFERABLE;
    HAL_MPU_ConfigRegion(&r);
    HAL_MPU_Enable(MPU_PRIVILEGED_DEFAULT);
    SCB->SHCSR |= SCB_SHCSR_BUSFAULTENA_Msk;      /* falhas de barramento no seu próprio vetor */
}

void sistema_cache(void)
{
    sistema_mpu();
    SCB_EnableICache();
    SCB_EnableDCache();
}

void Error_Handler(void)
{
    __disable_irq();
    for (;;) {
        HAL_GPIO_TogglePin(LED_PORTA, LED_PINO);
        for (volatile uint32_t i = 0; i < 20000000; i++) {}
    }
}
