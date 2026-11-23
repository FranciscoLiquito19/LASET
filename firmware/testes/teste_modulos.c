/* Testes no PC dos módulos sem hardware: encaminhamento, política de filas, COBS,
 * CRC-16, NMEA e cálculo do tempo. Corre na CI: cmake -B b && cmake --build b && ./b/teste_modulos */
#include <stdio.h>
#include <string.h>
#include "encaminhamento_regras.h"
#include "cobs.h"
#include "nmea.h"
#include "isotp.h"
#include "config.h"
#include "trama_pc.h"

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

/* ISO-TP: envia mensagens de vários tamanhos de um emissor para um recetor, trama a
 * trama, com Flow Control, e compara. */
static int isotp_ida_volta(uint16_t n, uint8_t bs)
{
    uint8_t d[ISOTP_MAX], t[64], fc[3], fc_n;
    for (int i = 0; i < n; i++) d[i] = (uint8_t)(i * 13 + 1);
    isotp_tx_t tx;
    isotp_rx_t rx = {0};
    isotp_tx_iniciar(&tx, d, n);
    int tramas = 0, esperas = 0;
    for (;;) {
        int k = isotp_tx_proxima(&tx, t);
        if (k < 0) return -1;                       /* terminou sem o recetor completar */
        if (k == 0) {                               /* BS > 0: novo FC a cada BS tramas */
            uint8_t f2[3] = { 0x30, bs, 0 };
            if (!bs || ++esperas > 100 || isotp_tx_fc(&tx, f2, 3) != 0) return -2;
            continue;
        }
        if (k != isotp_len_canfd((uint8_t)k)) return -3;
        tramas++;
        int r = isotp_rx_trama(&rx, t, (uint8_t)k, fc, &fc_n);
        if (r == ISOTP_RX_COMPLETA) break;
        if (r == ISOTP_RX_ENVIAR_FC) { fc[1] = bs; if (isotp_tx_fc(&tx, fc, fc_n) != 0) return -4; }
        else if (r != ISOTP_RX_NADA) return -5;
    }
    if (rx.total != n || memcmp(rx.buf, d, n)) return -6;
    return tramas;
}

static void t_isotp(void)
{
    VERIFICA(isotp_ida_volta(1, 0) == 1);           /* SF clássica */
    VERIFICA(isotp_ida_volta(7, 0) == 1);
    VERIFICA(isotp_ida_volta(8, 0) == 1);           /* SF com comprimento no byte 1 */
    VERIFICA(isotp_ida_volta(62, 0) == 1);
    VERIFICA(isotp_ida_volta(63, 0) == 2);          /* FF + 1 CF */
    VERIFICA(isotp_ida_volta(84, 0) == 2);          /* maior mensagem do PC: 20 + 64 */
    VERIFICA(isotp_ida_volta(62 + 63, 0) == 2);
    VERIFICA(isotp_ida_volta(62 + 64, 0) == 3);
    VERIFICA(isotp_ida_volta(256, 0) == 5);
    VERIFICA(isotp_ida_volta(256, 2) == 5);         /* com blocos de 2 CF */
    /* CF fora de ordem aborta a receção */
    isotp_rx_t rx = {0};
    uint8_t fc[3], fc_n, ff[64] = { 0x10, 100 }, cf[64] = { 0x22 };
    VERIFICA(isotp_rx_trama(&rx, ff, 64, fc, &fc_n) == ISOTP_RX_ENVIAR_FC && fc[0] == 0x30);
    VERIFICA(isotp_rx_trama(&rx, cf, 64, fc, &fc_n) == ISOTP_RX_ERRO && !rx.ativo);
    /* mensagem demasiado grande: FC de excesso */
    uint8_t ff2[64] = { 0x1F, 0xFF };
    VERIFICA(isotp_rx_trama(&rx, ff2, 64, fc, &fc_n) == ISOTP_RX_ENVIAR_FC && fc[0] == 0x32);
    VERIFICA(isotp_stmin_us(10) == 10000 && isotp_stmin_us(0xF5) == 500);
}

static void t_config(void)
{
    VERIFICA(crc32("123456789", 9) == 0xCBF43926UL);
    static config_t a, b;
    memset(&a, 0xFF, sizeof a);                     /* flash apagada */
    memset(&b, 0xFF, sizeof b);
    VERIFICA(config_escolher(&a, &b) == NULL);
    a.sequencia = 0;
    config_omissao(&a);
    config_selar(&a);
    VERIFICA(config_valida(&a) && config_escolher(&a, &b) == &a);
    b = a; b.sequencia = 1; config_selar(&b);
    VERIFICA(config_escolher(&a, &b) == &b);
    b.tabela.pc_canal ^= 1;                         /* corrompida: fica a outra */
    VERIFICA(config_escolher(&a, &b) == &a);
    b = a; b.sequencia = 0; a.sequencia = 0xFFFFFFFFUL; config_selar(&a); config_selar(&b);
    VERIFICA(config_escolher(&a, &b) == &b);        /* a sequência dá a volta */

    uint8_t r[64];
    uint16_t nr;
    config_t c = {0};
    config_omissao(&c);
    uint8_t regra[] = { CFG_ADICIONAR_REGRA, IF_CANFD, 1, IF_RS485, 0, 1, 0x00,0x01,0,0, 0xFF,0x01,0,0 };
    VERIFICA(config_comando(&c, regra, sizeof regra, r, &nr) == 0 && c.tabela.n_regras == 1 && r[1] == 1);
    VERIFICA(c.tabela.regras[0].id_min == 0x100 && c.tabela.regras[0].id_max == 0x1FF && c.tabela.regras[0].urgente);
    uint8_t ler[] = { CFG_LER_REGRA, 0 };
    VERIFICA(config_comando(&c, ler, 2, r, &nr) == 0 && nr == 2 + REGRA_BYTES && !memcmp(r + 2, regra + 1, REGRA_BYTES));
    uint8_t mau[] = { CFG_ADICIONAR_REGRA, IF_CANFD, 1, IF_CANFD, 9, 0, 0,0,0,0, 0,0,0,0 };
    VERIFICA(config_comando(&c, mau, sizeof mau, r, &nr) < 0);    /* destino inexistente */
    uint8_t pc[] = { CFG_LIGACAO_PC, IF_ETH, 0 }, pc_mau[] = { CFG_LIGACAO_PC, IF_I2C, 0 };
    VERIFICA(config_comando(&c, pc, 3, r, &nr) == 0 && c.tabela.pc_if == IF_ETH);
    VERIFICA(config_comando(&c, pc_mau, 3, r, &nr) < 0 && c.tabela.pc_if == IF_ETH);
    uint8_t le[] = { CFG_LER };
    VERIFICA(config_comando(&c, le, 1, r, &nr) == 0 && nr == 28 && r[1] == IF_ETH && r[4] == 192);
    uint8_t g[] = { CFG_GRAVAR };
    VERIFICA(config_comando(&c, g, 1, r, &nr) == 1);
    uint8_t ap[] = { CFG_APAGAR_REGRAS };
    VERIFICA(config_comando(&c, ap, 1, r, &nr) == 0 && c.tabela.n_regras == 0);
}

static void t_trama_pc_modulo(void)
{
    mensagem_t m = {0}, o;
    m.c.versao = MSG_VERSAO; m.c.tipo = MSG_DADOS; m.c.interface = IF_I2C; m.c.endereco = 0x48;
    m.c.comprimento = MSG_DADOS_MAX;
    for (int i = 0; i < MSG_DADOS_MAX; i++) m.dados[i] = (uint8_t)i;   /* inclui zeros */
    uint8_t t[PC_TRAMA_MAX];
    size_t k = pc_para_trama(&m, t);
    VERIFICA(k <= PC_TRAMA_MAX && t[k - 1] == 0 && memchr(t, 0, k - 1) == NULL);
    pc_fluxo_t f = {0};
    int ok = 0;
    for (size_t i = 0; i < k; i++) ok += pc_fluxo_byte(&f, t[i], &o);
    VERIFICA(ok == 1 && o.c.endereco == 0x48 && !memcmp(o.dados, m.dados, MSG_DADOS_MAX));
    t[5] ^= 1;                                      /* um bit errado: rejeitada */
    ok = 0;
    for (size_t i = 0; i < k; i++) ok += pc_fluxo_byte(&f, t[i], &o);
    VERIFICA(ok == 0);
    uint8_t b[PC_BRUTO_MAX];
    size_t n = pc_para_bytes(&m, b);
    VERIFICA(n == PC_BRUTO_MAX && pc_de_bytes(b, n, &o) == 0 && pc_de_bytes(b, n - 1, &o) != 0);
}

int main(void)
{
    t_encaminhamento();
    t_politica();
    t_cobs();
    t_nmea();
    t_trama_pc();
    t_isotp();
    t_config();
    t_trama_pc_modulo();
    printf("%d verificações, %d falhas\n", total, falhas);
    return falhas != 0;
}
