/* Configuração persistente (RF18): tabela de encaminhamento, ligação ao PC, rede e
 * velocidades série. Guardada no banco 2 da flash em dois setores alternados (A/B):
 * cada gravação vai para o setor que não tem a cópia mais recente, por isso uma falha
 * de energia a meio deixa sempre uma cópia válida. Esta parte não depende do hardware
 * (testes no PC); a escrita na flash está em flash_config.c. */
#ifndef CONFIG_H
#define CONFIG_H
#include <stddef.h>
#include <stdint.h>
#include "encaminhamento_regras.h"

#define CONFIG_MAGIA   0x4C534554UL   /* "LSET" */
#define CONFIG_VERSAO  1

typedef struct {
    uint32_t magia;
    uint16_t versao, tamanho;
    uint32_t sequencia;               /* aumenta em cada gravação; a maior é a atual */
    tabela_t tabela;
    uint8_t  ip[4], mascara[4], gateway[4];
    uint16_t porta_udp, porta_tcp;
    uint32_t baud_rs232, baud_rs485;
    uint32_t crc;                     /* CRC-32 de todos os campos anteriores */
} config_t;

extern config_t config_atual;

uint32_t crc32(const void *d, size_t n);
void config_omissao(config_t *c);
void config_selar(config_t *c);
int  config_valida(const config_t *c);
/* Entre as duas cópias da flash, a válida com maior sequência (NULL se nenhuma). */
const config_t *config_escolher(const config_t *a, const config_t *b);

/* Comandos de configuração: mensagem MSG_CONFIG para a interface IF_SISTEMA.
 * dados[0] = comando; a resposta começa pelo mesmo comando. */
enum {
    CFG_LER = 1,             /* -> pc_if, pc_canal, n_regras, ip, mascara, gateway, udp, tcp, baud232, baud485 */
    CFG_LER_REGRA,           /* [i] -> n_regras, regra (13 bytes) */
    CFG_ADICIONAR_REGRA,     /* [regra: origem_if, origem_canal, destino_if, destino_canal, urgente, id_min, id_max] */
    CFG_APAGAR_REGRAS,
    CFG_LIGACAO_PC,          /* [interface, canal] */
    CFG_REDE,                /* [ip(4), mascara(4), gateway(4), porta_udp(2), porta_tcp(2)] (no próximo arranque) */
    CFG_SERIE,               /* [baud232(4), baud485(4)] (no próximo arranque) */
    CFG_GRAVAR,              /* grava na flash */
    CFG_OMISSAO,             /* repõe os valores de fábrica (sem gravar) */
};
#define REGRA_BYTES 13

/* Executa um comando sobre c. Devolve <0 se inválido, 0 se aplicado, 1 se for preciso
 * gravar na flash (CFG_GRAVAR). resp recebe a resposta (até MSG_DADOS_MAX bytes). */
int config_comando(config_t *c, const uint8_t *cmd, uint16_t n, uint8_t *resp, uint16_t *nresp);
/* Ligação ao PC aceite? (RS232, CAN FD 1 ou 2 com ISO-TP, Ethernet UDP ou TCP) */
int config_ligacao_valida(uint8_t interface, uint8_t canal);

#endif
