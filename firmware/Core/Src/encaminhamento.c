/* Encaminhamento (Figura 5.2): as rotinas de receção colocam mensagens na fila de
 * entrada; a tarefa de encaminhamento aplica a tabela e coloca cada mensagem na fila
 * urgente ou normal da saída de destino; cada saída tem uma tarefa de transmissão que
 * esvazia as suas filas ao ritmo do respetivo barramento (RF12). */
#include <string.h>
#include "placa.h"
#include "app.h"
#include "config.h"
#include "queue.h"
#include "task.h"

#define ENTRADA_N      32
#define SAIDA_N        16      /* por classe; dimensionar com B = (Rin - Rout) T (RF13) */
#define MAX_URGENTES   4       /* depois de 4 urgentes seguidas passa uma normal (RF14) */
#define PILHA_TX       512

typedef int (*enviar_fn)(const mensagem_t *m);

typedef struct {
    const char *nome;
    enviar_fn enviar;
    QueueHandle_t urg, norm;
    StaticQueue_t urg_q, norm_q;
    uint8_t urg_buf[SAIDA_N * sizeof(mensagem_t)], norm_buf[SAIDA_N * sizeof(mensagem_t)];
    TaskHandle_t tarefa;
    StaticTask_t tarefa_tcb;
    StackType_t pilha[PILHA_TX];
    uint8_t seguidas;
    volatile uint32_t enviadas, descartadas, erros;
} saida_ctx_t;

tabela_t tabela;   /* cópia de config_atual.tabela, só alterada por esta tarefa */

static QueueHandle_t entrada;
static StaticQueue_t entrada_q;
static uint8_t entrada_buf[ENTRADA_N * sizeof(mensagem_t)];
static volatile uint32_t entrada_descartadas, sem_destino;
static StaticTask_t enc_tcb;
static StackType_t enc_pilha[768];

/* funções de envio de cada saída */
static int env_can1(const mensagem_t *m)  { return m->para_pc ? can_pc_enviar(0, m) : can_enviar(0, m); }
static int env_can2(const mensagem_t *m)  { return m->para_pc ? can_pc_enviar(1, m) : can_enviar(1, m); }
static int env_i2c1(const mensagem_t *m)  { return i2c_executar(0, m); }
static int env_i2c2(const mensagem_t *m)  { return i2c_executar(1, m); }
static int env_rs232(const mensagem_t *m)
{
    return m->para_pc ? pc_serie_enviar(m) : rs232_enviar_bruto(m);
}

static saida_ctx_t saidas[S_N] = {
    [S_CAN1]  = { .nome = "CAN FD 1", .enviar = env_can1 },
    [S_CAN2]  = { .nome = "CAN FD 2", .enviar = env_can2 },
    [S_RS232] = { .nome = "RS232",    .enviar = env_rs232 },
    [S_RS485] = { .nome = "RS485",    .enviar = rs485_enviar },
    [S_I2C1]  = { .nome = "I2C1",     .enviar = env_i2c1 },
    [S_I2C2]  = { .nome = "I2C2",     .enviar = env_i2c2 },
    [S_PWM]   = { .nome = "PWM",      .enviar = pwm_comando },
    [S_ETH]   = { .nome = "Ethernet", .enviar = eth_enviar },
};

static void tarefa_saida(void *arg)
{
    saida_ctx_t *s = arg;
    mensagem_t m;
    for (;;) {
        ulTaskNotifyTake(pdFALSE, portMAX_DELAY);          /* uma notificação por mensagem */
        int f = escolher_fila(uxQueueMessagesWaiting(s->urg) > 0, uxQueueMessagesWaiting(s->norm) > 0,
                              &s->seguidas, MAX_URGENTES);
        if (f < 0) continue;
        if (xQueueReceive(f ? s->urg : s->norm, &m, 0) != pdTRUE) continue;
        if (s->enviar(&m) == 0) s->enviadas++; else s->erros++;
    }
}

static void enfileirar(saida_t s, const mensagem_t *m, uint8_t urg)
{
    saida_ctx_t *c = &saidas[s];
    if (xQueueSend(urg ? c->urg : c->norm, m, 0) == pdTRUE) xTaskNotifyGive(c->tarefa);
    else c->descartadas++;                               /* fila cheia: conta e descarta (RF13) */
}

/* Mensagens para a própria unidade (interface IF_SISTEMA): versão e configuração.
 * A resposta volta por onde o pedido entrou. */
static void tratar_sistema(const mensagem_t *m)
{
    mensagem_t r = *m;
    uint16_t n = 0;
    r.c.interface = IF_SISTEMA;
    r.c.canal = 0;
    r.c.marca_us = sincronizacao_agora_us();
    if (TIPO(m) == MSG_CONFIG) {
        int x = m->c.comprimento ? config_comando(&config_atual, m->dados, m->c.comprimento, r.dados, &n) : -1;
        if (x >= 0) tabela = config_atual.tabela;
        if (x == 1) config_pedir_gravacao();
        if (x < 0) { r.dados[0] = m->c.comprimento ? m->dados[0] : 0; n = 1; }
        r.c.tipo = x < 0 ? MSG_ERRO : MSG_CONFIRMACAO;
    } else {
        static const char v[] = "LASET " FIRMWARE_VERSAO;
        n = sizeof v - 1;
        memcpy(r.dados, v, n);
        r.c.tipo = MSG_DADOS;
    }
    r.c.comprimento = n;
    r.para_pc = 1;
    r.destino_canal = m->origem_canal;
    saida_t s = saida_de(m->origem_if, m->origem_canal);
    if (s != S_NENHUMA) enfileirar(s, &r, 0);
}

static void tarefa_encaminhamento(void *arg)
{
    (void)arg;
    mensagem_t m;
    for (;;) {
        if (xQueueReceive(entrada, &m, portMAX_DELAY) != pdTRUE) continue;
        const saida_t pc = saida_de(tabela.pc_if, tabela.pc_canal);
        int do_pc = m.origem_if == tabela.pc_if && m.origem_canal == tabela.pc_canal;
        int do_tcp = m.origem_if == IF_ETH && m.origem_canal == 1;   /* a configuração por TCP é sempre aceite */
        if ((do_pc || do_tcp) && m.c.interface == IF_SISTEMA) { tratar_sistema(&m); continue; }
        uint8_t urg;
        saida_t s = encaminhar(&tabela, &m, &urg);
        if (s == S_NENHUMA) { sem_destino++; continue; }
        m.para_pc = (s == pc && !do_pc);
        m.destino_canal = m.para_pc ? tabela.pc_canal : 0;
        if (m.para_pc) {                                  /* para o PC: o cabeçalho leva a origem */
            m.c.interface = m.origem_if;
            m.c.canal = m.origem_canal;
        }
        enfileirar(s, &m, urg);
    }
}

BaseType_t encaminhamento_entrada(const mensagem_t *m, TickType_t espera)
{
    BaseType_t r = xQueueSend(entrada, m, espera);
    if (r != pdTRUE) entrada_descartadas++;
    return r;
}

BaseType_t encaminhamento_entrada_isr(const mensagem_t *m, BaseType_t *acordar)
{
    BaseType_t r = xQueueSendFromISR(entrada, m, acordar);
    if (r != pdTRUE) entrada_descartadas++;
    return r;
}

void encaminhamento_iniciar(void)
{
    tabela = config_atual.tabela;
    entrada = xQueueCreateStatic(ENTRADA_N, sizeof(mensagem_t), entrada_buf, &entrada_q);
    for (int i = 0; i < S_N; i++) {
        saida_ctx_t *s = &saidas[i];
        s->urg = xQueueCreateStatic(SAIDA_N, sizeof(mensagem_t), s->urg_buf, &s->urg_q);
        s->norm = xQueueCreateStatic(SAIDA_N, sizeof(mensagem_t), s->norm_buf, &s->norm_q);
        s->tarefa = xTaskCreateStatic(tarefa_saida, s->nome, PILHA_TX, s, 3, s->pilha, &s->tarefa_tcb);
    }
    xTaskCreateStatic(tarefa_encaminhamento, "encaminhar", 768, NULL, 4, enc_pilha, &enc_tcb);
}

void encaminhamento_estado(void)
{
    consola_printf("entrada: %lu descartadas, %lu sem destino\r\n",
                   (unsigned long)entrada_descartadas, (unsigned long)sem_destino);
    for (int i = 0; i < S_N; i++)
        consola_printf("  %-9s enviadas %6lu  descartadas %4lu  erros %4lu\r\n", saidas[i].nome,
                       (unsigned long)saidas[i].enviadas, (unsigned long)saidas[i].descartadas,
                       (unsigned long)saidas[i].erros);
}
