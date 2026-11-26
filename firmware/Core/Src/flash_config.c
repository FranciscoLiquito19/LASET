/* Configuração na flash (RF18): setores 0 e 1 do banco 2 (128 KB cada), alternados.
 * O código corre do banco 1, por isso apagar e escrever no banco 2 não pára o CPU.
 * A gravação corre numa tarefa de baixa prioridade, porque apagar um setor demora
 * até ~2 s e não pode atrasar o encaminhamento. */
#include <string.h>
#include "placa.h"
#include "app.h"
#include "config.h"
#include "task.h"

#define SETOR_A_END  0x08100000UL
#define SETOR_B_END  0x08120000UL
#define PALAVRA      32                        /* a flash do H7 escreve 256 bits de cada vez */
#define TAM_GRAVADO  ((sizeof(config_t) + PALAVRA - 1) / PALAVRA * PALAVRA)

static uint32_t ultimo_setor;
static uint8_t consola_erro_flash;     /* uma das cópias tinha a ECC estragada */                  /* onde está a cópia mais recente (0 = nenhuma) */
static uint8_t copia[TAM_GRAVADO] __attribute__((aligned(32)));
static TaskHandle_t tarefa;
static StaticTask_t tcb;
static StackType_t pilha[512];

/* Leitura protegida. Se faltar a alimentação a meio de uma gravação, a palavra de 256
 * bits que estava a ser escrita fica com o ECC errado, e ler essa palavra dá uma falha de
 * barramento. Sem proteção, a unidade bloqueava em cada arranque ao ler a cópia
 * estragada. Enquanto flash_lendo está ativo, o BusFault_Handler (stm32h7xx_it.c) salta
 * a instrução que falhou e marca flash_erro; a cópia é então dada como inválida e fica a
 * outra. A região está sem cache (MPU, sistema.c) para a falha ser precisa. */
volatile uint8_t flash_lendo, flash_erro;

static int ler_copia(uint32_t end, config_t *dst)
{
    const volatile uint8_t *s = (const volatile uint8_t *)end;
    uint8_t *d = (uint8_t *)dst;
    flash_erro = 0;
    flash_lendo = 1;
    __DSB();
    __ISB();
    for (size_t i = 0; i < sizeof *dst; i++) d[i] = s[i];
    __DSB();
    flash_lendo = 0;
    if (flash_erro) {
        __HAL_FLASH_CLEAR_FLAG_BANK2(FLASH_FLAG_DBECCERR_BANK2 | FLASH_FLAG_SNECCERR_BANK2);
        memset(dst, 0, sizeof *dst);             /* CRC errado: config_valida recusa */
        return -1;
    }
    return 0;
}

void config_carregar(void)
{
    static config_t a, b;
    int ea = ler_copia(SETOR_A_END, &a), eb = ler_copia(SETOR_B_END, &b);
    if (ea || eb) consola_erro_flash = 1;
    const config_t *c = config_escolher(&a, &b);
    if (c) {
        config_atual = *c;
        ultimo_setor = (c == &a) ? SETOR_A_END : SETOR_B_END;
    } else {
        config_atual.sequencia = 0;
        config_omissao(&config_atual);
        ultimo_setor = 0;
    }
}

int config_carregada_da_flash(void) { return ultimo_setor != 0; }
int config_houve_erro_flash(void) { return consola_erro_flash; }

static int gravar(const config_t *c)
{
    uint32_t end = (ultimo_setor == SETOR_A_END) ? SETOR_B_END : SETOR_A_END;
    FLASH_EraseInitTypeDef e = {
        .TypeErase = FLASH_TYPEERASE_SECTORS, .Banks = FLASH_BANK_2,
        .Sector = (end == SETOR_A_END) ? FLASH_SECTOR_0 : FLASH_SECTOR_1,
        .NbSectors = 1, .VoltageRange = FLASH_VOLTAGE_RANGE_3 };
    uint32_t erro = 0;
    int r = 0;
    memset(copia, 0xFF, sizeof copia);
    memcpy(copia, c, sizeof *c);
    HAL_FLASH_Unlock();
    if (HAL_FLASHEx_Erase(&e, &erro) != HAL_OK) r = -1;
    for (uint32_t i = 0; r == 0 && i < TAM_GRAVADO; i += PALAVRA)
        if (HAL_FLASH_Program(FLASH_TYPEPROGRAM_FLASHWORD, end + i, (uint32_t)(copia + i)) != HAL_OK) r = -2;
    HAL_FLASH_Lock();
    SCB_InvalidateDCache_by_Addr((void *)end, TAM_GRAVADO);
    static config_t lida;
    if (r == 0 && (ler_copia(end, &lida) != 0 || !config_valida(&lida))) r = -3;   /* relê e confirma */
    if (r == 0) ultimo_setor = end;
    return r;
}

static void tarefa_gravar(void *arg)
{
    (void)arg;
    static config_t c;
    for (;;) {
        ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
        vTaskSuspendAll();                     /* cópia coerente (só o encaminhamento a altera) */
        config_atual.sequencia++;
        config_selar(&config_atual);
        c = config_atual;
        xTaskResumeAll();
        int r = gravar(&c);
        consola_printf("configuração gravada na flash (sequência %lu): %s (%d)\r\n",
                       (unsigned long)c.sequencia, r ? "FALHOU" : "ok", r);
    }
}

void config_iniciar(void)
{
    tarefa = xTaskCreateStatic(tarefa_gravar, "config", 512, NULL, 1, pilha, &tcb);
}

void config_pedir_gravacao(void) { if (tarefa) xTaskNotifyGive(tarefa); }
