/* Ethernet (RF05): LAN8742A em RMII + LwIP (NO_SYS, API raw), tudo numa tarefa.
 *  - UDP (porta 5000 por omissão): operações. Cada datagrama leva uma mensagem
 *    (cabeçalho de 20 bytes + dados, sem COBS nem CRC). As respostas vão para o
 *    endereço e porta de onde veio o último datagrama do PC.
 *  - TCP (porta 5001): configuração. Fluxo de tramas COBS + CRC, como na série;
 *    um cliente de cada vez.
 * Os descritores e os buffers do DMA estão na SRAM do domínio D2, sem cache (MPU em
 * sistema.c); os dados copiam-se de e para os pbufs do LwIP. */
#include <string.h>
#include "placa.h"
#include "app.h"
#include "config.h"
#include "trama_pc.h"
#include "task.h"
#include "queue.h"
#include "lwip/init.h"
#include "lwip/netif.h"
#include "lwip/etharp.h"
#include "lwip/timeouts.h"
#include "lwip/udp.h"
#include "lwip/tcp.h"
#include "netif/ethernet.h"

#define PHY_END   0          /* PHYAD0 = 0 (esquema, folha 3; também na NUCLEO) */
#define PHY_BCR   0
#define PHY_BSR   1
#define PHY_SCSR  31
#define BUF_ETH   1536
#define RX_N      (ETH_RX_DESC_CNT + 2)
#define TX_N      8

ETH_HandleTypeDef heth;
static ETH_DMADescTypeDef desc_rx[ETH_RX_DESC_CNT] __attribute__((section(".eth_desc"), aligned(32)));
static ETH_DMADescTypeDef desc_tx[ETH_TX_DESC_CNT] __attribute__((section(".eth_desc"), aligned(32)));
static uint8_t buf_rx[RX_N][BUF_ETH] __attribute__((section(".eth_buf"), aligned(32)));
static uint8_t buf_tx[BUF_ETH] __attribute__((section(".eth_buf"), aligned(32)));
static uint8_t *livres[RX_N];
static int n_livres;

static struct netif nif;
static uint8_t mac[6];
static struct udp_pcb *udp;
static struct tcp_pcb *tcp_cliente;
static ip_addr_t pc_ip;
static uint16_t pc_porta;
static int pc_conhecido, ligado, hw_ok;
static pc_fluxo_t fluxo_tcp;
static volatile uint32_t rx_n, tx_n, tx_erros;

static QueueHandle_t fila_tx;
static StaticQueue_t fila_tx_q;
static uint8_t fila_tx_buf[TX_N * sizeof(mensagem_t)];
static TaskHandle_t tarefa;
static StaticTask_t tcb;
static StackType_t pilha[1024];

uint32_t sys_now(void) { return HAL_GetTick(); }

void lwip_falhou(const char *msg)
{
    consola_printf("LwIP: %s\r\n", msg);
    Error_Handler();
}

/* ---- HAL ETH: buffers de receção e interrupções ---- */
void HAL_ETH_RxAllocateCallback(uint8_t **buff) { *buff = n_livres ? livres[--n_livres] : NULL; }

void HAL_ETH_RxLinkCallback(void **ini, void **fim, uint8_t *buff, uint16_t n)
{
    struct pbuf *p = pbuf_alloc(PBUF_RAW, n, PBUF_POOL);
    if (p) pbuf_take(p, buff, n);
    livres[n_livres++] = buff;                   /* já copiado: o buffer volta ao DMA */
    if (!p) return;
    if (*ini == NULL) *ini = p; else pbuf_cat(*ini, p);
    *fim = p;
}

void HAL_ETH_RxCpltCallback(ETH_HandleTypeDef *h)
{
    BaseType_t acordar = pdFALSE;
    vTaskNotifyGiveFromISR(tarefa, &acordar);
    portYIELD_FROM_ISR(acordar);
}

/* ---- interface de rede do LwIP ---- */
static err_t saida_eth(struct netif *n, struct pbuf *p)
{
    if (p->tot_len > BUF_ETH) return ERR_BUF;
    pbuf_copy_partial(p, buf_tx, p->tot_len, 0);
    ETH_BufferTypeDef b = { .buffer = buf_tx, .len = p->tot_len, .next = NULL };
    ETH_TxPacketConfigTypeDef cfg = {0};
    cfg.Attributes = ETH_TX_PACKETS_FEATURES_CRCPAD;
    cfg.CRCPadCtrl = ETH_CRC_PAD_INSERT;
    cfg.Length = p->tot_len;
    cfg.TxBuffer = &b;
    HAL_StatusTypeDef r = HAL_ETH_Transmit(&heth, &cfg, 5);
    HAL_ETH_ReleaseTxPacket(&heth);
    if (r != HAL_OK) { tx_erros++; return ERR_IF; }
    return ERR_OK;
}

static err_t netif_iniciar(struct netif *n)
{
    n->name[0] = 'e'; n->name[1] = '0';
    n->output = etharp_output;
    n->linkoutput = saida_eth;
    n->mtu = 1500;
    n->hwaddr_len = 6;
    memcpy(n->hwaddr, mac, 6);
    n->flags = NETIF_FLAG_BROADCAST | NETIF_FLAG_ETHARP | NETIF_FLAG_ETHERNET;
    return ERR_OK;
}

static int hw_iniciar(void)
{
    uint32_t u = HAL_GetUIDw0() ^ HAL_GetUIDw1() ^ HAL_GetUIDw2();
    /* endereço administrado localmente, derivado do identificador único do MCU */
    uint8_t m[6] = { 0x02, 0x4C, (uint8_t)(u >> 24), (uint8_t)(u >> 16), (uint8_t)(u >> 8), (uint8_t)u };
    memcpy(mac, m, 6);
    for (unsigned i = 0; i < RX_N; i++) livres[n_livres++] = buf_rx[i];
    heth.Instance = ETH;
    heth.Init.MACAddr = mac;
    heth.Init.MediaInterface = HAL_ETH_RMII_MODE;
    heth.Init.TxDesc = desc_tx;
    heth.Init.RxDesc = desc_rx;
    heth.Init.RxBuffLen = BUF_ETH;
    if (HAL_ETH_Init(&heth) != HAL_OK) return -1;   /* p. ex. sem os 50 MHz do PHY */
    HAL_ETH_SetMDIOClockRange(&heth);
    /* autonegociação (o PHY já arranca assim pelos pinos MODE, mas fica explícito) */
    HAL_ETH_WritePHYRegister(&heth, PHY_END, PHY_BCR, 0x1000 | 0x0200);
    return 0;
}

static void verificar_ligacao(void)
{
    uint32_t bsr = 0, scsr = 0;
    HAL_ETH_ReadPHYRegister(&heth, PHY_END, PHY_BSR, &bsr);     /* o bit de ligação é "latch low" */
    if (HAL_ETH_ReadPHYRegister(&heth, PHY_END, PHY_BSR, &bsr) != HAL_OK) return;
    int up = (bsr & 0x0004) && (bsr & 0x0020);                   /* ligação + autonegociação feita */
    if (up && !ligado) {
        HAL_ETH_ReadPHYRegister(&heth, PHY_END, PHY_SCSR, &scsr);
        uint32_t v = (scsr >> 2) & 7;                             /* 001 10H, 101 10F, 010 100H, 110 100F */
        ETH_MACConfigTypeDef mc;
        HAL_ETH_GetMACConfig(&heth, &mc);
        mc.Speed = (v & 2) ? ETH_SPEED_100M : ETH_SPEED_10M;
        mc.DuplexMode = (v & 4) ? ETH_FULLDUPLEX_MODE : ETH_HALFDUPLEX_MODE;
        HAL_ETH_SetMACConfig(&heth, &mc);
        HAL_ETH_Start_IT(&heth);
        netif_set_link_up(&nif);
        ligado = 1;
        consola_printf("Ethernet: ligação a %s Mbit/s, %s duplex\r\n", (v & 2) ? "100" : "10", (v & 4) ? "full" : "half");
    } else if (!up && ligado) {
        HAL_ETH_Stop_IT(&heth);
        netif_set_link_down(&nif);
        ligado = 0;
        consola_printf("Ethernet: sem ligação\r\n");
    }
}

/* ---- aplicação: UDP e TCP ---- */
static void entrar(mensagem_t *m, uint8_t canal)
{
    m->origem_if = IF_ETH;
    m->origem_canal = canal;
    m->urgente = (m->c.tipo & TIPO_URGENTE) != 0;
    rx_n++;
    encaminhamento_entrada(m, 0);
}

static void udp_recebido(void *arg, struct udp_pcb *pcb, struct pbuf *p, const ip_addr_t *ip, u16_t porta)
{
    uint8_t b[PC_BRUTO_MAX];
    mensagem_t m;
    if (p->tot_len <= sizeof b) {
        pbuf_copy_partial(p, b, p->tot_len, 0);
        if (pc_de_bytes(b, p->tot_len, &m) == 0) {
            ip_addr_copy(pc_ip, *ip);
            pc_porta = porta;
            pc_conhecido = 1;
            entrar(&m, 0);
        }
    }
    pbuf_free(p);
}

static err_t tcp_recebido(void *arg, struct tcp_pcb *pcb, struct pbuf *p, err_t err)
{
    if (p == NULL) {                              /* o cliente fechou */
        if (pcb == tcp_cliente) tcp_cliente = NULL;
        if (tcp_close(pcb) != ERR_OK) { tcp_abort(pcb); return ERR_ABRT; }   /* sem memória para o FIN */
        return ERR_OK;
    }
    mensagem_t m;
    for (struct pbuf *q = p; q; q = q->next)
        for (u16_t i = 0; i < q->len; i++)
            if (pc_fluxo_byte(&fluxo_tcp, ((const uint8_t *)q->payload)[i], &m)) entrar(&m, 1);
    tcp_recved(pcb, p->tot_len);
    pbuf_free(p);
    return ERR_OK;
}

static void tcp_erro(void *arg, err_t e) { tcp_cliente = NULL; }   /* o pcb já foi libertado */

static err_t tcp_aceite(void *arg, struct tcp_pcb *novo, err_t err)
{
    if (err != ERR_OK || novo == NULL) return ERR_VAL;
    if (tcp_cliente) tcp_abort(tcp_cliente);      /* fica só o cliente mais recente */
    tcp_cliente = novo;
    memset(&fluxo_tcp, 0, sizeof fluxo_tcp);
    tcp_recv(novo, tcp_recebido);
    tcp_err(novo, tcp_erro);
    return ERR_OK;
}

static void enviar(const mensagem_t *m)
{
    if (m->destino_canal == 1) {                  /* TCP */
        uint8_t t[PC_TRAMA_MAX];
        size_t k = pc_para_trama(m, t);
        if (!tcp_cliente || tcp_sndbuf(tcp_cliente) < k) { tx_erros++; return; }
        if (tcp_write(tcp_cliente, t, (u16_t)k, TCP_WRITE_FLAG_COPY) != ERR_OK) { tx_erros++; return; }
        tcp_output(tcp_cliente);
    } else {                                      /* UDP */
        uint8_t b[PC_BRUTO_MAX];
        size_t n = pc_para_bytes(m, b);
        struct pbuf *p = pc_conhecido ? pbuf_alloc(PBUF_TRANSPORT, (u16_t)n, PBUF_RAM) : NULL;
        if (!p) { tx_erros++; return; }
        pbuf_take(p, b, (u16_t)n);
        if (udp_sendto(udp, p, &pc_ip, pc_porta) != ERR_OK) tx_erros++;
        pbuf_free(p);
    }
    tx_n++;
}

static void tarefa_eth(void *arg)
{
    (void)arg;
    const config_t *c = &config_atual;
    hw_ok = hw_iniciar() == 0;
    if (!hw_ok) consola_printf("Ethernet: o MAC não arrancou (sem relógio de 50 MHz do PHY?)\r\n");
    lwip_init();
    ip4_addr_t ip, ms, gw;
    IP4_ADDR(&ip, c->ip[0], c->ip[1], c->ip[2], c->ip[3]);
    IP4_ADDR(&ms, c->mascara[0], c->mascara[1], c->mascara[2], c->mascara[3]);
    IP4_ADDR(&gw, c->gateway[0], c->gateway[1], c->gateway[2], c->gateway[3]);
    netif_add(&nif, &ip, &ms, &gw, NULL, netif_iniciar, ethernet_input);
    netif_set_default(&nif);
    netif_set_up(&nif);
    udp = udp_new();
    udp_bind(udp, IP_ADDR_ANY, c->porta_udp);
    udp_recv(udp, udp_recebido, NULL);
    struct tcp_pcb *t = tcp_new();
    tcp_bind(t, IP_ADDR_ANY, c->porta_tcp);
    t = tcp_listen(t);
    tcp_accept(t, tcp_aceite);
    consola_printf("Ethernet: %u.%u.%u.%u, UDP %u, TCP %u, MAC %02x:%02x:%02x:%02x:%02x:%02x\r\n",
                   c->ip[0], c->ip[1], c->ip[2], c->ip[3], c->porta_udp, c->porta_tcp,
                   mac[0], mac[1], mac[2], mac[3], mac[4], mac[5]);
    TickType_t ultima = xTaskGetTickCount();
    for (;;) {
        ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(5));
        for (;;) {
            struct pbuf *p = NULL;
            if (!ligado || HAL_ETH_ReadData(&heth, (void **)&p) != HAL_OK || p == NULL) break;
            if (nif.input(p, &nif) != ERR_OK) pbuf_free(p);
        }
        mensagem_t m;
        while (xQueueReceive(fila_tx, &m, 0) == pdTRUE) enviar(&m);
        if (hw_ok && xTaskGetTickCount() - ultima >= pdMS_TO_TICKS(500)) {
            ultima = xTaskGetTickCount();
            verificar_ligacao();
        }
        sys_check_timeouts();
    }
}

int eth_enviar(const mensagem_t *m)
{
    if (!ligado || xQueueSend(fila_tx, m, pdMS_TO_TICKS(5)) != pdTRUE) return -1;
    xTaskNotifyGive(tarefa);
    return 0;
}

void eth_iniciar(void)
{
    fila_tx = xQueueCreateStatic(TX_N, sizeof(mensagem_t), fila_tx_buf, &fila_tx_q);
    tarefa = xTaskCreateStatic(tarefa_eth, "eth", 1024, NULL, 3, pilha, &tcb);
}

void eth_estado(void)
{
    consola_printf("  Ethernet: %s, %lu recebidas, %lu enviadas, %lu erros\r\n",
                   !hw_ok ? "MAC parado" : ligado ? "ligada" : "sem ligação",
                   (unsigned long)rx_n, (unsigned long)tx_n, (unsigned long)tx_erros);
}
