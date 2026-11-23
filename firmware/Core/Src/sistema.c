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

    per.PeriphClockSelection = RCC_PERIPHCLK_FDCAN;
    per.FdcanClockSelection = RCC_FDCANCLKSOURCE_PLL;
    if (HAL_RCCEx_PeriphCLKConfig(&per) != HAL_OK) Error_Handler();
}

void sistema_cache(void)
{
    SCB_EnableICache();
    SCB_EnableDCache();   /* sem DMA nesta fase; a Ethernet usará a SRAM2 sem cache (MPU) */
}

void Error_Handler(void)
{
    __disable_irq();
    for (;;) {
        HAL_GPIO_TogglePin(LED_PORTA, LED_PINO);
        for (volatile uint32_t i = 0; i < 20000000; i++) {}
    }
}
