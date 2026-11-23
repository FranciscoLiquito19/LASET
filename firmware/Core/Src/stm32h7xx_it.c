/* Rotinas de interrupção. O SysTick é partilhado entre a HAL e o FreeRTOS. */
#include "placa.h"
#include "FreeRTOS.h"
#include "task.h"

extern void xPortSysTickHandler(void);
void sincronizacao_tim2_irq(void);

void NMI_Handler(void)        { for (;;) {} }
void HardFault_Handler(void)  { Error_Handler(); }
void MemManage_Handler(void)  { Error_Handler(); }
void BusFault_Handler(void)   { Error_Handler(); }
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
