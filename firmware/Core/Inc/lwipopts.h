/* LwIP sem sistema operativo (NO_SYS = 1, API "raw"): toda a pilha corre numa só
 * tarefa (eth.c), que também envia o que as outras tarefas lhe põem na fila. Assim não
 * é preciso alocação dinâmica do FreeRTOS nem proteger a pilha com mutexes. */
#ifndef LWIPOPTS_H
#define LWIPOPTS_H

#define NO_SYS                    1
#define SYS_LIGHTWEIGHT_PROT      0
#define LWIP_NETCONN              0
#define LWIP_SOCKET               0
#define LWIP_IPV4                 1
#define LWIP_IPV6                 0
#define LWIP_ARP                  1
#define LWIP_ETHERNET             1
#define LWIP_ICMP                 1
#define LWIP_UDP                  1
#define LWIP_TCP                  1
#define LWIP_DHCP                 0           /* endereço fixo, da configuração (RF18) */
#define LWIP_DNS                  0
#define LWIP_IGMP                 0
#define LWIP_STATS                0
#define LWIP_NETIF_HOSTNAME       0

#define MEM_ALIGNMENT             4
#define MEM_SIZE                  (16 * 1024)
#define MEMP_NUM_PBUF             16
#define MEMP_NUM_UDP_PCB          4
#define MEMP_NUM_TCP_PCB          4
#define MEMP_NUM_TCP_PCB_LISTEN   2
#define MEMP_NUM_TCP_SEG          16
#define PBUF_POOL_SIZE            16
#define PBUF_POOL_BUFSIZE         1536

#define TCP_MSS                   1460
#define TCP_SND_BUF               (4 * TCP_MSS)
#define TCP_WND                   (4 * TCP_MSS)
#define TCP_SND_QUEUELEN          16

#endif
