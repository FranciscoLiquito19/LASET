/* Sincronização (RF16, DP14): o TIM2 (32 bits, 240 MHz) captura o flanco do PPS; a
 * frequência real do temporizador é medida entre PPS sucessivos, o que compensa a
 * deriva do cristal; a frase RMC dá o segundo UTC do último PPS. Sem PPS, mantém-se
 * a última frequência medida e a unidade indica que não está sincronizada.
 * O contador é estendido para 64 bits com a interrupção de transbordo (a cada 17,9 s). */
#include <string.h>
#include "placa.h"
#include "app.h"
#include "nmea.h"
#include "task.h"
#include "stream_buffer.h"

#define F_NOMINAL 240000000UL

extern StreamBufferHandle_t sb_gps;
static volatile uint32_t alto;                /* 32 bits superiores do contador */
static volatile uint64_t cap_ult;             /* contagem no último PPS */
static volatile uint32_t freq = F_NOMINAL;
static volatile uint32_t n_pps;
static volatile int64_t utc_ult = -1;         /* segundo UTC do último PPS (-1 = desconhecido) */
static volatile TickType_t tick_pps;
static StaticTask_t gps_tcb;
static StackType_t gps_pilha[512];

static uint64_t contador64(void)
{
    uint32_t pm = __get_PRIMASK();
    __disable_irq();
    uint32_t a = alto, c = TIM2->CNT;
    if ((TIM2->SR & TIM_SR_UIF) && c < 0x80000000UL) a++;   /* transbordo ainda por tratar */
    __set_PRIMASK(pm);
    return ((uint64_t)a << 32) | c;
}

void sincronizacao_tim2_irq(void)
{
    uint32_t sr = TIM2->SR;
    uint32_t a = alto;
    if (sr & TIM_SR_UIF) {
        TIM2->SR = ~TIM_SR_UIF;
        alto = ++a;
    }
    if (sr & TIM_SR_CC1IF) {
        uint32_t cap = TIM2->CCR1;                           /* a leitura limpa CC1IF */
        uint32_t a_cap = ((sr & TIM_SR_UIF) && cap > 0x80000000UL) ? a - 1 : a;
        uint64_t c64 = ((uint64_t)a_cap << 32) | cap;
        if (n_pps > 0) {
            uint64_t d = c64 - cap_ult;
            if (d < 0xFFFFFFFFULL && freq_plausivel((uint32_t)d, F_NOMINAL)) freq = (uint32_t)d;
        }
        if (utc_ult >= 0) utc_ult++;                         /* cada PPS avança um segundo */
        cap_ult = c64;
        n_pps++;
        tick_pps = xTaskGetTickCountFromISR();
    }
}

uint64_t sincronizacao_agora_us(void)
{
    /* lê o estado de forma atómica: o PPS pode chegar a meio */
    uint32_t pm = __get_PRIMASK();
    __disable_irq();
    uint64_t agora = contador64(), cap = cap_ult;
    int64_t utc = utc_ult;
    uint32_t f = freq, n = n_pps;
    __set_PRIMASK(pm);
    if (utc < 0 || n == 0)
        return tempo_us(0, 0, agora, f);                     /* tempo desde o arranque */
    return tempo_us(utc, cap, agora, f);
}

int sincronizacao_estado(uint32_t *freq_hz, int64_t *utc_s)
{
    *freq_hz = freq;
    *utc_s = utc_ult;
    return utc_ult >= 0 && (xTaskGetTickCount() - tick_pps) < pdMS_TO_TICKS(1500);
}

/* Junta os caracteres do GPS em frases e usa as RMC válidas. Assume-se, como nos
 * recetores u-blox e MediaTek, que a frase se refere ao PPS que a precede; confirmar
 * com o recetor escolhido. */
static void tarefa_gps(void *arg)
{
    (void)arg;
    char linha[96];
    size_t n = 0;
    char c;
    for (;;) {
        if (xStreamBufferReceive(sb_gps, &c, 1, portMAX_DELAY) != 1) continue;
        if (c == '$') n = 0;
        if (c == '\r' || c == '\n') {
            linha[n] = 0;
            int64_t s;
            if (n > 0 && nmea_rmc(linha, &s)) {
                taskENTER_CRITICAL();
                utc_ult = s;
                taskEXIT_CRITICAL();
            }
            n = 0;
        } else if (n < sizeof linha - 1) {
            linha[n++] = c;
        }
    }
}

void sincronizacao_iniciar(void)
{
    __HAL_TIM_CLEAR_FLAG(&htim2, TIM_FLAG_UPDATE | TIM_FLAG_CC1);
    __HAL_TIM_ENABLE_IT(&htim2, TIM_IT_UPDATE | TIM_IT_CC1);
    TIM_CCxChannelCmd(TIM2, TIM_CHANNEL_1, TIM_CCx_ENABLE);
    __HAL_TIM_ENABLE(&htim2);
    xTaskCreateStatic(tarefa_gps, "gps", 512, NULL, 2, gps_pilha, &gps_tcb);
}
