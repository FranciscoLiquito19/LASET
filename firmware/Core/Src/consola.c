/* Consola de depuração no USART3 (VCP da NUCLEO, 115200 baud). Na PCB os pinos PD8/PD9
 * ficam livres, por isso a consola só tem efeito na NUCLEO. */
#include <stdarg.h>
#include <stdio.h>
#include "placa.h"
#include "app.h"
#include "semphr.h"

static SemaphoreHandle_t mutex;
static StaticSemaphore_t mutex_mem;

void consola_iniciar(void)
{
    mutex = xSemaphoreCreateMutexStatic(&mutex_mem);
}

void consola_printf(const char *fmt, ...)
{
    static char buf[256];
    int com_rtos = xTaskGetSchedulerState() == taskSCHEDULER_RUNNING;
    if (com_rtos) xSemaphoreTake(mutex, portMAX_DELAY);
    va_list ap;
    va_start(ap, fmt);
    int n = vsnprintf(buf, sizeof buf, fmt, ap);
    va_end(ap);
    if (n > (int)sizeof buf - 1) n = sizeof buf - 1;
    if (n > 0) HAL_UART_Transmit(&huart3, (uint8_t *)buf, (uint16_t)n, 100);
    if (com_rtos) xSemaphoreGive(mutex);
}
