#include "nmea.h"
#include <string.h>

static int hex(char c) { return c >= '0' && c <= '9' ? c - '0' : c >= 'A' && c <= 'F' ? c - 'A' + 10 : -1; }

int nmea_checksum_ok(const char *f)
{
    if (f[0] != '$') return 0;
    uint8_t x = 0;
    const char *p = f + 1;
    while (*p && *p != '*') x ^= (uint8_t)*p++;
    if (*p != '*' || hex(p[1]) < 0 || hex(p[2]) < 0) return 0;
    return x == (uint8_t)(hex(p[1]) * 16 + hex(p[2]));
}

/* dias desde 1970-01-01 (algoritmo de Howard Hinnant, calendário gregoriano) */
static int64_t dias_civis(int y, unsigned m, unsigned d)
{
    y -= m <= 2;
    const int64_t era = (y >= 0 ? y : y - 399) / 400;
    const unsigned yoe = (unsigned)(y - era * 400);
    const unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
    const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return era * 146097 + (int64_t)doe - 719468;
}

static int campo(const char *f, int n, char *out, int tam)
{
    /* copia o campo n (0 = identificador) separado por vírgulas */
    int i = 0;
    while (n > 0 && *f) { if (*f == ',') n--; f++; }
    if (n) return 0;
    while (*f && *f != ',' && *f != '*' && i < tam - 1) out[i++] = *f++;
    out[i] = 0;
    return 1;
}

static int dois(const char *s) { return (s[0] - '0') * 10 + (s[1] - '0'); }

int nmea_rmc(const char *f, int64_t *utc_s)
{
    char id[8], hora[16], estado[4], data[8];
    if (!nmea_checksum_ok(f)) return 0;
    if (!campo(f, 0, id, sizeof id) || strlen(id) != 6 || strcmp(id + 3, "RMC") != 0) return 0;
    if (!campo(f, 1, hora, sizeof hora) || strlen(hora) < 6) return 0;
    if (!campo(f, 2, estado, sizeof estado) || estado[0] != 'A') return 0;
    if (!campo(f, 9, data, sizeof data) || strlen(data) != 6) return 0;
    for (int i = 0; i < 6; i++)
        if (hora[i] < '0' || hora[i] > '9' || data[i] < '0' || data[i] > '9') return 0;
    int h = dois(hora), mi = dois(hora + 2), s = dois(hora + 4);
    int d = dois(data), me = dois(data + 2), aa = dois(data + 4);
    int a = aa < 80 ? 2000 + aa : 1900 + aa;          /* o RMC só traz o ano com dois dígitos */
    if (h > 23 || mi > 59 || s > 60 || d < 1 || d > 31 || me < 1 || me > 12) return 0;
    *utc_s = dias_civis(a, (unsigned)me, (unsigned)d) * 86400 + h * 3600 + mi * 60 + s;
    return 1;
}

uint64_t tempo_us(int64_t utc_s, uint64_t cap, uint64_t agora, uint32_t freq_hz)
{
    uint64_t dt = agora - cap;                         /* contagens desde o PPS */
    uint64_t seg = dt / freq_hz, resto = dt % freq_hz;
    return (uint64_t)(utc_s + (int64_t)seg) * 1000000ULL + resto * 1000000ULL / freq_hz;
}

int freq_plausivel(uint32_t medida, uint32_t nominal)
{
    uint32_t tol = nominal / 1000;                     /* 1000 ppm */
    return medida + tol >= nominal && medida <= nominal + tol;
}
