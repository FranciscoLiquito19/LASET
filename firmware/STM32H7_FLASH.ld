/* Linker script para o STM32H743ZI / STM32H753ZI (2 MB de flash, 1 MB de RAM).
 * O código corre do banco 1 da flash; o banco 2 (a partir de 0x08100000) fica
 * reservado para a configuração persistente (RF18), por isso FLASH tem só 1 MB.
 * Dados, pilha e heap ficam na AXI SRAM (D1). O início da SRAM do domínio D2 fica para
 * os descritores e buffers da Ethernet (secção .eth), acessíveis pelo DMA.
 */
ENTRY(Reset_Handler)
_estack = ORIGIN(RAM_D1) + LENGTH(RAM_D1);
_Min_Heap_Size = 0x400;
_Min_Stack_Size = 0x1000;

MEMORY
{
  ITCMRAM (xrw) : ORIGIN = 0x00000000, LENGTH = 64K
  DTCMRAM (xrw) : ORIGIN = 0x20000000, LENGTH = 128K
  FLASH   (rx)  : ORIGIN = 0x08000000, LENGTH = 1024K
  CONFIG  (r)   : ORIGIN = 0x08100000, LENGTH = 1024K   /* setores 0 e 1: configuração A/B */
  RAM_D1  (xrw) : ORIGIN = 0x24000000, LENGTH = 512K
  RAM_D2  (xrw) : ORIGIN = 0x30000000, LENGTH = 288K
  RAM_D3  (xrw) : ORIGIN = 0x38000000, LENGTH = 64K
}

SECTIONS
{
  .isr_vector : { . = ALIGN(4); KEEP(*(.isr_vector)) . = ALIGN(4); } >FLASH
  .text : { . = ALIGN(4); *(.text) *(.text*) *(.glue_7) *(.glue_7t) *(.eh_frame)
            KEEP (*(.init)) KEEP (*(.fini)) . = ALIGN(4); _etext = .; } >FLASH
  .rodata : { . = ALIGN(4); *(.rodata) *(.rodata*) . = ALIGN(4); } >FLASH
  .ARM.extab : { *(.ARM.extab* .gnu.linkonce.armextab.*) } >FLASH
  .ARM : { __exidx_start = .; *(.ARM.exidx*) __exidx_end = .; } >FLASH
  .preinit_array : { PROVIDE_HIDDEN (__preinit_array_start = .); KEEP (*(.preinit_array*)) PROVIDE_HIDDEN (__preinit_array_end = .); } >FLASH
  .init_array : { PROVIDE_HIDDEN (__init_array_start = .); KEEP (*(SORT(.init_array.*))) KEEP (*(.init_array*)) PROVIDE_HIDDEN (__init_array_end = .); } >FLASH
  .fini_array : { PROVIDE_HIDDEN (__fini_array_start = .); KEEP (*(SORT(.fini_array.*))) KEEP (*(.fini_array*)) PROVIDE_HIDDEN (__fini_array_end = .); } >FLASH

  _sidata = LOADADDR(.data);
  .data : { . = ALIGN(4); _sdata = .; *(.data) *(.data*) . = ALIGN(4); _edata = .; } >RAM_D1 AT> FLASH

  .bss : { . = ALIGN(4); _sbss = .; __bss_start__ = _sbss; *(.bss) *(.bss*) *(COMMON)
           . = ALIGN(4); _ebss = .; __bss_end__ = _ebss; } >RAM_D1

  ._user_heap_stack : { . = ALIGN(8); PROVIDE ( end = . ); PROVIDE ( _end = . );
           . = . + _Min_Heap_Size; . = . + _Min_Stack_Size; . = ALIGN(8); } >RAM_D1

  /* tem de começar em 0x30000000: a MPU (sistema.c) tira a cache aos primeiros 32 KB
   * e marca os primeiros 256 bytes (descritores) como memória de dispositivo */
  .eth (NOLOAD) : { . = ALIGN(32); __eth_ini = .; *(.eth_desc) __eth_desc_fim = .;
                    . = __eth_ini + 256; *(.eth_buf) __eth_fim = .; } >RAM_D2
  ASSERT(__eth_ini == 0x30000000, "a seccao .eth tem de comecar no inicio da SRAM D2")
  ASSERT(__eth_desc_fim - __eth_ini <= 256, "descritores da Ethernet fora da regiao de 256 bytes da MPU")
  ASSERT(__eth_fim - __eth_ini <= 32K, "buffers da Ethernet fora da regiao de 32 KB sem cache")

  .ARM.attributes 0 : { *(.ARM.attributes) }
}
