/* Três saídas PWM a 50 Hz (RF15). Comando: canal 0-2 no cabeçalho, largura do impulso
 * em microssegundos nos dados (uint16, little-endian); 0 desliga a saída. Sem comandos
 * durante TIMEOUT_MS, as saídas passam ao valor seguro (Capítulo 5). */
#include "placa.h"
#include "app.h"
#include "task.h"
#include "timers.h"

#define TIMEOUT_MS   1000
#define MIN_US       500
#define MAX_US       2500

static const uint32_t CANAIS[3] = { TIM_CHANNEL_1, TIM_CHANNEL_2, TIM_CHANNEL_3 };
static uint16_t seguro_us[3] = { 0, 0, 0 };        /* sem impulso; configurável */
static volatile TickType_t ultimo;
static volatile uint8_t em_seguro = 1;
static TimerHandle_t vigia;
static StaticTimer_t vigia_mem;

static void aplicar(int canal, uint16_t us)
{
    __HAL_TIM_SET_COMPARE(&htim1, CANAIS[canal], (uint32_t)us * 2);   /* 0,5 us por contagem */
}

static void cb_vigia(TimerHandle_t t)
{
    (void)t;
    if (!em_seguro && (xTaskGetTickCount() - ultimo) > pdMS_TO_TICKS(TIMEOUT_MS)) {
        for (int i = 0; i < 3; i++) aplicar(i, seguro_us[i]);
        em_seguro = 1;
    }
}

int pwm_comando(const mensagem_t *m)
{
    if (m->c.canal > 2 || m->c.comprimento < 2) return -1;
    uint16_t us = (uint16_t)(m->dados[0] | m->dados[1] << 8);
    if (us != 0 && (us < MIN_US || us > MAX_US)) return -2;
    aplicar(m->c.canal, us);
    ultimo = xTaskGetTickCount();
    em_seguro = 0;
    if (__HAL_TIM_GET_FLAG(&htim1, TIM_FLAG_BREAK)) return -3;   /* falha ativa: saídas desligadas */
    return 0;
}

void pwm_iniciar(void)
{
    for (int i = 0; i < 3; i++) {
        aplicar(i, 0);
        HAL_TIM_PWM_Start(&htim1, CANAIS[i]);
    }
    vigia = xTimerCreateStatic("vigia_pwm", pdMS_TO_TICKS(100), pdTRUE, NULL, cb_vigia, &vigia_mem);
    xTimerStart(vigia, 0);
}
