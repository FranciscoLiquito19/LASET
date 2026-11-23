/* Adaptação do LwIP ao arm-none-eabi-gcc + newlib. */
#ifndef ARCH_CC_H
#define ARCH_CC_H
#include <stdint.h>
#include <stdlib.h>
#include <sys/time.h>

#define LWIP_ERRNO_STDINCLUDE     1
#define LWIP_TIMEVAL_PRIVATE      0
#define LWIP_RAND()               ((uint32_t)rand())
#define LWIP_PLATFORM_DIAG(x)     do {} while (0)
void lwip_falhou(const char *msg);
#define LWIP_PLATFORM_ASSERT(x)   lwip_falhou(x)

#endif
