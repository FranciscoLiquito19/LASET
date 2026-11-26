/* Robustez dos módulos que recebem dados de fora (PC, GPS, barramentos): milhões de
 * entradas aleatórias ou corrompidas, que não podem fazer escrever fora dos buffers nem
 * dar resultados incoerentes. Na CI corre compilado com -fsanitize=address,undefined,
 * que para o programa ao primeiro acesso inválido.
 *   cmake -B build && cmake --build build && ./build/teste_robustez */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "cobs.h"
#include "nmea.h"
#include "isotp.h"
#include "trama_pc.h"
#include "config.h"

static uint32_t semente = 12345u;
static uint32_t aleat(void) { semente = semente * 1664525u + 1013904223u; return semente >> 8; }
static int falhas = 0;
static long esperadas = 0, corrompidas_aceites = 0, completas = 0, aceites = 0, rmc_ok = 0, cfg_ok = 0;
#define VERIFICA(c, ...) do { if (!(c)) { falhas++; printf("falha: " __VA_ARGS__); printf("\n"); } } while (0)

static void r_cobs(void)
{
    uint8_t in[600], out[600], volta[600];
    for (int it = 0; it < 200000; it++) {
        size_t n = aleat() % 300;
        for (size_t i = 0; i < n; i++) in[i] = (uint8_t)((aleat() % 4) ? aleat() : 0);
        /* descodificar lixo: nunca escreve mais do que n bytes */
        memset(out, 0xA5, sizeof out);
        size_t k = cobs_descodificar(in, n, out);
        VERIFICA(k <= n, "cobs: %zu bytes a partir de %zu", k, n);
        VERIFICA(out[n] == 0xA5 || n == 0, "cobs: escreveu depois de n");
        /* ida e volta */
        size_t c = cobs_codificar(in, n, out);
        VERIFICA(c <= n + n / 254 + 1, "cobs: codificado grande demais");
        VERIFICA(memchr(out, 0, c) == NULL, "cobs: zero no codificado");
        if (n > 0) {
            size_t d = cobs_descodificar(out, c, volta);
            VERIFICA(d == n && memcmp(volta, in, n) == 0, "cobs: ida e volta (%zu)", n);
        }
    }
}

static void r_nmea(void)
{
    static const char base[] = "$GPRMC,123519.00,A,4807.038,N,01131.000,E,022.4,084.4,230394,003.1,W*6A";
    char s[128];
    int64_t t;
    for (int it = 0; it < 300000; it++) {
        size_t n = strlen(base);
        memcpy(s, base, n + 1);
        int mexidas = 1 + aleat() % 4;
        for (int j = 0; j < mexidas; j++) {
            size_t p = aleat() % n;
            switch (aleat() % 3) {
            case 0: s[p] = (char)(aleat() % 256); break;          /* troca um byte */
            case 1: s[p] = '\0'; n = p; break;                    /* corta */
            default: s[p] = ",*$0"[aleat() % 4]; break;           /* separadores fora do sítio */
            }
            if (n == 0) break;
        }
        s[sizeof s - 1] = '\0';
        (void)nmea_checksum_ok(s);
        if (nmea_rmc(s, &t) == 1) rmc_ok++;
    }
}

static void r_isotp(void)
{
    isotp_rx_t r;
    memset(&r, 0, sizeof r);
    uint8_t t[64], fc[64], fcn;
    for (int it = 0; it < 500000; it++) {
        uint8_t n = (uint8_t)(aleat() % 65);
        for (int i = 0; i < n; i++) t[i] = (uint8_t)aleat();
        if (n && aleat() % 2) t[0] = (uint8_t)((t[0] & 0x0F) | ((aleat() % 4) << 4));  /* tipos válidos */
        int e = isotp_rx_trama(&r, t, n, fc, &fcn);
        VERIFICA(r.total <= ISOTP_MAX && r.recebidos <= ISOTP_MAX, "isotp: total %u recebidos %u", r.total, r.recebidos);
        if (e == ISOTP_RX_COMPLETA) completas++;
        if (e == ISOTP_RX_ENVIAR_FC) VERIFICA(fcn <= 64, "isotp: fc com %u bytes", fcn);
    }
    /* emissão com Flow Control aleatório */
    uint8_t dados[ISOTP_MAX], out[64];
    for (int it = 0; it < 20000; it++) {
        isotp_tx_t tx;
        uint16_t n = (uint16_t)(aleat() % ISOTP_MAX + 1);
        for (int i = 0; i < n; i++) dados[i] = (uint8_t)aleat();
        isotp_tx_iniciar(&tx, dados, n);
        for (int k = 0; k < 64; k++) {
            int c = isotp_tx_proxima(&tx, out);
            VERIFICA(c <= 64, "isotp tx: trama de %d", c);
            if (c < 0) break;
            if (c == 0) {
                uint8_t f[8];
                for (int i = 0; i < 8; i++) f[i] = (uint8_t)aleat();
                f[0] = (uint8_t)(0x30 | (aleat() % 3));
                if (isotp_tx_fc(&tx, f, (uint8_t)(aleat() % 9)) < 0) break;
            }
            VERIFICA(tx.enviados <= tx.total, "isotp tx: enviados %u > total %u", tx.enviados, tx.total);
        }
    }
}

static void r_trama_pc(void)
{
    uint8_t lixo[PC_TRAMA_MAX + 50];
    mensagem_t m;
    pc_fluxo_t f;
    memset(&f, 0, sizeof f);
    for (int it = 0; it < 300000; it++) {
        size_t n;
        mensagem_t orig;
        int valida = aleat() % 2;
        if (valida) {                      /* trama válida, às vezes com um byte trocado */
            memset(&orig, 0, sizeof orig);
            orig.c.versao = 1; orig.c.tipo = (uint8_t)aleat(); orig.c.interface = (uint8_t)(aleat() % 7);
            orig.c.canal = (uint8_t)(aleat() % 3); orig.c.endereco = aleat(); orig.c.sequencia = (uint16_t)aleat();
            orig.c.comprimento = (uint16_t)(aleat() % (MSG_DADOS_MAX + 1));
            for (int i = 0; i < orig.c.comprimento; i++) orig.dados[i] = (uint8_t)aleat();
            n = pc_para_trama(&orig, lixo);
            VERIFICA(n <= PC_TRAMA_MAX, "pc: trama de %zu bytes", n);
            pc_fluxo_byte(&f, 0, &m);       /* fecha o que vinha de trás */
            if (aleat() % 4 == 0) {
                size_t p = aleat() % (n - 1);
                uint8_t x = (uint8_t)(1 + aleat() % 255);
                valida = (lixo[p] ^ x) == 0 ? 0 : -1;   /* -1: corrompida sem zeros a mais */
                lixo[p] ^= x;
            } else {
                esperadas++;
            }
        } else {
            n = aleat() % sizeof lixo;
            for (size_t i = 0; i < n; i++) lixo[i] = (uint8_t)((aleat() % 8) ? aleat() : 0);
        }
        (void)pc_de_trama(lixo, n, &m);
        (void)pc_de_bytes(lixo, n, &m);
        for (size_t i = 0; i < n; i++) {
            if (pc_fluxo_byte(&f, lixo[i], &m) > 0) {
                aceites++;
                VERIFICA(m.c.comprimento <= MSG_DADOS_MAX, "pc: mensagem aceite com %u bytes", m.c.comprimento);
                if (valida == -1 && i == n - 1) corrompidas_aceites++;
                if (valida == 1 && i == n - 1)
                    VERIFICA(m.c.comprimento == orig.c.comprimento && m.c.endereco == orig.c.endereco &&
                             memcmp(m.dados, orig.dados, orig.c.comprimento) == 0, "pc: ida e volta diferente");
            }
            VERIFICA(f.n <= sizeof f.buf, "pc: fluxo com %zu bytes", f.n);
        }
    }
}

static void r_config(void)
{
    config_t c;
    config_omissao(&c);
    uint8_t cmd[MSG_DADOS_MAX], resp[MSG_DADOS_MAX + 16];
    uint16_t nr;
    for (int it = 0; it < 300000; it++) {
        uint16_t n = (uint16_t)(aleat() % (MSG_DADOS_MAX + 1));
        for (int i = 0; i < n; i++) cmd[i] = (uint8_t)aleat();
        memset(resp + MSG_DADOS_MAX, 0x5A, 16);
        nr = 0;
        if (config_comando(&c, cmd, n, resp, &nr) == 0) cfg_ok++;
        VERIFICA(nr <= MSG_DADOS_MAX, "config: resposta de %u bytes", nr);
        VERIFICA(resp[MSG_DADOS_MAX] == 0x5A, "config: escreveu fora da resposta");
        if (it % 1000 == 0) {             /* uma configuração selada continua válida */
            config_selar(&c);
            VERIFICA(config_valida(&c), "config: selada mas inválida");
        }
    }
}

int main(void)
{
    r_cobs();
    r_nmea();
    r_isotp();
    r_trama_pc();
    r_config();
    VERIFICA(aceites >= esperadas, "pc: %ld tramas válidas, só %ld aceites", esperadas, aceites);
    VERIFICA(corrompidas_aceites == 0, "pc: %ld tramas corrompidas aceites", corrompidas_aceites);
    printf("robustez: %d falhas (isotp completas %ld, tramas PC aceites %ld, RMC lidas %ld, comandos aceites %ld)\n",
           falhas, completas, aceites, rmc_ok, cfg_ok);
    return falhas != 0;
}
