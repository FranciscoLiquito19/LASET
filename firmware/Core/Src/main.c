/* Gateway multiprotocolo LASET: arranque. */
#include "placa.h"
#include "app.h"
#include "task.h"

static StaticTask_t estado_tcb;
static StackType_t estado_pilha[512];

/* LED a piscar e, a cada 5 s, o estado na consola */
static void tarefa_estado(void *arg)
{
    (void)arg;
    uint32_t n = 0;
    for (;;) {
        HAL_GPIO_TogglePin(LED_PORTA, LED_PINO);
        vTaskDelay(pdMS_TO_TICKS(250));
        if (++n % 20 == 0) {
            uint32_t f;
            int64_t utc;
            int ok = sincronizacao_estado(&f, &utc);
            consola_printf("\r\n[%lu s] sincronizado: %s, f(TIM2) = %lu Hz, UTC = %lld\r\n",
                           (unsigned long)(xTaskGetTickCount() / configTICK_RATE_HZ), ok ? "sim" : "não",
                           (unsigned long)f, (long long)utc);
            encaminhamento_estado();
        }
    }
}

int main(void)
{
    sistema_cache();
    HAL_Init();
    sistema_relogios();
    perifericos_iniciar();
    consola_printf("\r\nLASET gateway %s (%s), SYSCLK %lu Hz\r\n", FIRMWARE_VERSAO,
#if defined(PLACA_NUCLEO)
                   "NUCLEO-H753ZI",
#else
                   "PCB LASET",
#endif
                   (unsigned long)HAL_RCC_GetSysClockFreq());
    can_autoteste();

    consola_iniciar();
    encaminhamento_iniciar();      /* as filas têm de existir antes de ativar as receções */
    can_arrancar();
    serie_iniciar();
    sincronizacao_iniciar();
    pwm_iniciar();
    xTaskCreateStatic(tarefa_estado, "estado", 512, NULL, 1, estado_pilha, &estado_tcb);
    vTaskStartScheduler();
    Error_Handler();
}

void vApplicationStackOverflowHook(TaskHandle_t t, char *nome)
{
    (void)t; (void)nome;
    Error_Handler();
}
