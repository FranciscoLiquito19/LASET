/* Chamadas de sistema mínimas para a newlib (sem sistema de ficheiros). */
#include <errno.h>
#include <sys/stat.h>
#include "placa.h"

int _write(int fd, char *p, int n)
{
    (void)fd;
    HAL_UART_Transmit(&huart3, (uint8_t *)p, (uint16_t)n, 100);   /* consola */
    return n;
}
int _read(int fd, char *p, int n)        { (void)fd; (void)p; (void)n; errno = ENOSYS; return -1; }
int _close(int fd)                       { (void)fd; return -1; }
int _lseek(int fd, int o, int w)         { (void)fd; (void)o; (void)w; return 0; }
int _fstat(int fd, struct stat *st)      { (void)fd; st->st_mode = S_IFCHR; return 0; }
int _isatty(int fd)                      { (void)fd; return 1; }
