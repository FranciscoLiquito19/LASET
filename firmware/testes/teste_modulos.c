/* Testes no PC dos módulos sem hardware: encaminhamento, política de filas, COBS,
 * CRC-16, NMEA e cálculo do tempo. Corre na CI: cmake -B b && cmake --build b && ./b/teste_modulos */
#include <stdio.h>
#include <string.h>
#include "encaminhamento_regras.h"
#include "cobs.h"
#include "nmea.h"

static int falhas = 0, total = 0;
#define VERIFICA(c) do { total++; if (!(c)) { falhas++; printf("FALHOU %s:%d: %s\n", __FILE__, __LINE__, #c); } } while (0)

static void t_encaminhamento(void)
{
    tabela_t t = { .pc_if = IF_RS232, .pc_canal = 0 };
    t.regras[t.n_regras++] = (regra_t){ IF_CANFD, 1, 0x100, 0x1FF, IF_RS485, 0, 1 };
    mensagem_t m = {0};
    uint8_t urg;

    /* do PC para o CAN FD 2 */
    m.origem_if = IF_RS232; m.origem_canal = 0; m.c.interface = IF_CANFD; m.c.canal = 1;
    VERIFICA(encaminhar(&t, &m, &urg) == S_CAN2);
    /* do PC para um destino que não existe */
    m.c.interface = IF_CANFD; m.c.canal = 7;
    VERIFICA(encaminhar(&t, &m, &urg) == S_NENHUMA);
    /* do CAN FD 2 com id na gama da regra: vai para RS485, urgente */
    m.origem_if = IF_CANFD; m.origem_canal = 1; m.c.endereco = 0x150 | CAN_FD;
    VERIFICA(encaminhar(&t, &m, &urg) == S_RS485 && urg == 1);
    /* do CAN FD 2 fora da gama: por omissão vai para o PC */
    m.c.endereco = 0x050;
    VERIFICA(encaminhar(&t, &m, &urg) == S_RS232);
    /* PWM: três canais numa saída */
    VERIFICA(saida_de(IF_PWM, 2) == S_PWM && saida_de(IF_PWM, 3) == S_NENHUMA);
}

static void t_politica(void)
{
    uint8_t s = 0;
    int n_urg = 0, n_norm = 0;
    /* ambas as filas sempre com mensagens: de 3 em 3 urgentes passa uma normal */
    for (int i = 0; i < 40; i++) {
        int f = escolher_fila(1, 1, &s, 3);
        if (f == 1) n_urg++; else if (f == 0) n_norm++;
    }
    VERIFICA(n_urg == 30 && n_norm == 10);
    s = 0;
    VERIFICA(escolher_fila(0, 1, &s, 3) == 0);
    VERIFICA(escolher_fila(1, 0, &s, 3) == 1);
    VERIFICA(escolher_fila(0, 0, &s, 3) == -1);
    /* sem normais, as urgentes continuam a passar mesmo acima do limite */
    s = 10;
    VERIFICA(escolher_fila(1, 0, &s, 3) == 1);
}

static void t_cobs(void)
{
    uint8_t in[300], enc[310], dec[300];
    for (int n = 0; n <= 300; n += 7) {
        for (int i = 0; i < n; i++) in[i] = (uint8_t)((i * 37) % 5 == 0 ? 0 : i);
        size_t m = cobs_codificar(in, n, enc);
        int sem_zeros = 1;
        for (size_t i = 0; i < m; i++) if (enc[i] == 0) sem_zeros = 0;
        size_t k = cobs_descodificar(enc, m, dec);
        VERIFICA(sem_zeros && k == (size_t)n && memcmp(in, dec, n) == 0);
    }
    /* 254 bytes sem zeros: bloco máximo */
    memset(in, 0x55, 254);
    size_t m = cobs_codificar(in, 254, enc);
    VERIFICA(m == 255 && cobs_descodificar(enc, m, dec) == 254);
    /* trama inválida: zero no meio */
    uint8_t mau[] = { 3, 1, 0, 2 };
    VERIFICA(cobs_descodificar(mau, sizeof mau, dec) == 0);
    /* CRC-16/CCITT-FALSE de "123456789" = 0x29B1 */
    VERIFICA(crc16_ccitt((const uint8_t *)"123456789", 9) == 0x29B1);
}

/* Trama gerada pela ferramenta do PC (ferramentas/laset_pc.py autoteste): o firmware
 * tem de a ler da mesma forma (CAN FD 2, id 0x123 com FD e BRS, 3 bytes). */
static void t_trama_pc(void)
{
    static const uint8_t t[] = { 0x07,0x01,0x01,0x03,0x01,0x23,0x01,0x03,0x60,0x07,0x04,0x40,0x42,0x0f,
                                 0x01,0x01,0x01,0x01,0x02,0x03,0x02,0x01,0x04,0x02,0xc4,0x36 };
    uint8_t d[64];
    size_t k = cobs_descodificar(t, sizeof t, d);
    cabecalho_t c;
    VERIFICA(k == sizeof(cabecalho_t) + 3 + 2);
    memcpy(&c, d, sizeof c);
    VERIFICA(crc16_ccitt(d, k - 2) == (uint16_t)(d[k - 2] | d[k - 1] << 8));
    VERIFICA(c.versao == 1 && c.tipo == MSG_DADOS && c.interface == IF_CANFD && c.canal == 1);
    VERIFICA(c.endereco == (0x123 | CAN_FD | CAN_BRS) && c.sequencia == 7 && c.marca_us == 1000000);
    VERIFICA(c.comprimento == 3 && d[20] == 1 && d[21] == 0 && d[22] == 2);
}

static void t_nmea(void)
{
    int64_t s;
    /* exemplo clássico: 23/03/1994 12:35:19 UTC = 764426119 */
    VERIFICA(nmea_rmc("$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A", &s) && s == 764426119);
    VERIFICA(!nmea_rmc("$GPRMC,123519,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6B", &s)); /* checksum */
    VERIFICA(!nmea_rmc("$GPRMC,123519,V,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*7D", &s)); /* sem fix */
    VERIFICA(!nmea_rmc("$GPGGA,123519,4807.038,N,01131.000,E,1,08,0.9,545.4,M,46.9,M,,*47", &s));
    /* tempo: 1,5 s depois do PPS a 240 MHz */
    VERIFICA(tempo_us(1000, 0, 360000000ULL, 240000000) == 1001500000ULL);
    VERIFICA(tempo_us(1000, 100, 100 + 240, 240000000) == 1000000001ULL);
    VERIFICA(freq_plausivel(240000100, 240000000) && !freq_plausivel(241000000, 240000000));
}

int main(void)
{
    t_encaminhamento();
    t_politica();
    t_cobs();
    t_nmea();
    t_trama_pc();
    printf("%d verificações, %d falhas\n", total, falhas);
    return falhas != 0;
}
