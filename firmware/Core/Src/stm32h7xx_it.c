/* Rotinas de interrupção. O SysTick é partilhado entre a HAL e o FreeRTOS. */
#include "placa.h"
#include "FreeRTOS.h"
#include "task.h"

extern void xPortSysTickHandler(void);
void sincronizacao_tim2_irq(void);

void NMI_Handler(void)
{
    /* erro duplo de ECC na leitura protegida da configuração: marca e continua */
    extern volatile uint8_t flash_lendo, flash_erro;
    if (flash_lendo && (FLASH->SR2 & FLASH_FLAG_DBECCERR_BANK2 & 0x7FFFFFFFU)) {
        flash_erro = 1;
        __HAL_FLASH_CLEAR_FLAG_BANK2(FLASH_FLAG_DBECCERR_BANK2);
        return;
    }
    for (;;) {}
}
void HardFault_Handler(void)  { Error_Handler(); }
void MemManage_Handler(void)  { Error_Handler(); }
/* Falha de barramento: se vier da leitura protegida da configuração (flash_config.c),
 * salta a instrução que falhou (16 ou 32 bits) e marca o erro; caso contrário, pára. */
extern volatile uint8_t flash_lendo, flash_erro;

void BusFault_C(uint32_t *quadro)
{
    if (flash_lendo && (SCB->CFSR & SCB_CFSR_PRECISERR_Msk)) {
        uint16_t ins = *(const uint16_t *)quadro[6];          /* PC empilhado */
        quadro[6] += ((ins >> 11) >= 0x1D) ? 4u : 2u;        /* instrução Thumb-2 de 32 bits? */
        flash_erro = 1;
        SCB->CFSR = SCB_CFSR_PRECISERR_Msk | SCB_CFSR_BFARVALID_Msk;   /* limpa (escrever 1) */
        return;
    }
    Error_Handler();
}

__attribute__((naked)) void BusFault_Handler(void)
{
    __asm volatile(
        "tst lr, #4      \n"
        "ite eq          \n"
        "mrseq r0, msp   \n"
        "mrsne r0, psp   \n"
        "b BusFault_C    \n");
}
void UsageFault_Handler(void) { Error_Handler(); }
void DebugMon_Handler(void)   {}

void SysTick_Handler(void)
{
    HAL_IncTick();
    if (xTaskGetSchedulerState() != taskSCHEDULER_NOT_STARTED)
        xPortSysTickHandler();
}

void FDCAN1_IT0_IRQHandler(void) { HAL_FDCAN_IRQHandler(&hfdcan1); }
void FDCAN2_IT0_IRQHandler(void) { HAL_FDCAN_IRQHandler(&hfdcan2); }
void TIM2_IRQHandler(void)       { sincronizacao_tim2_irq(); }
void USART2_IRQHandler(void)     { HAL_UART_IRQHandler(&huart2); }
void USART6_IRQHandler(void)     { HAL_UART_IRQHandler(&huart6); }
void UART7_IRQHandler(void)      { HAL_UART_IRQHandler(&huart7); }
void ETH_IRQHandler(void)        { HAL_ETH_IRQHandler(&heth); }
