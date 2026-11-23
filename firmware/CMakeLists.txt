# Firmware do gateway multiprotocolo LASET (STM32H743/H753 + FreeRTOS).
#
#   cmake -B build -DPLACA=NUCLEO -DCMAKE_TOOLCHAIN_FILE=cmake/gcc-arm-none-eabi.cmake
#   cmake --build build
#
# PLACA=NUCLEO  -> NUCLEO-H753ZI (HSE de 8 MHz do ST-LINK, consola no USART3/VCP)
# PLACA=LASET   -> PCB do projeto (STM32H743ZIT6, cristal de 25 MHz)
# As bibliotecas da ST, o FreeRTOS e o LwIP são descarregadas na configuração (FetchContent),
# nas versões fixadas abaixo.
cmake_minimum_required(VERSION 3.22)
project(laset_gateway C ASM)

set(PLACA "NUCLEO" CACHE STRING "NUCLEO ou LASET")
set_property(CACHE PLACA PROPERTY STRINGS NUCLEO LASET)
# Na NUCLEO não há transceivers CAN: os dois FDCAN ficam em loopback interno, o que
# permite ensaiar o encaminhamento de ponta a ponta sem hardware extra.
if(PLACA STREQUAL "NUCLEO")
  option(CAN_LOOPBACK "FDCAN em loopback interno" ON)
else()
  option(CAN_LOOPBACK "FDCAN em loopback interno" OFF)
endif()

include(FetchContent)
set(FETCHCONTENT_QUIET OFF)
FetchContent_Declare(hal_h7   GIT_REPOSITORY https://github.com/STMicroelectronics/stm32h7xx-hal-driver.git GIT_TAG v1.11.5 GIT_SHALLOW TRUE)
FetchContent_Declare(cmsis_h7 GIT_REPOSITORY https://github.com/STMicroelectronics/cmsis-device-h7.git     GIT_TAG v1.10.6 GIT_SHALLOW TRUE)
FetchContent_Declare(cmsis6   GIT_REPOSITORY https://github.com/ARM-software/CMSIS_6.git                  GIT_TAG v6.1.0  GIT_SHALLOW TRUE)
FetchContent_Declare(freertos GIT_REPOSITORY https://github.com/FreeRTOS/FreeRTOS-Kernel.git              GIT_TAG V11.1.0 GIT_SHALLOW TRUE)
FetchContent_Declare(lwip     GIT_REPOSITORY https://github.com/lwip-tcpip/lwip.git                       GIT_TAG STABLE-2_2_0_RELEASE GIT_SHALLOW TRUE)
foreach(dep hal_h7 cmsis_h7 cmsis6 freertos lwip)
  FetchContent_GetProperties(${dep})
  if(NOT ${dep}_POPULATED)
    FetchContent_Populate(${dep})
  endif()
endforeach()

if(PLACA STREQUAL "NUCLEO")
  set(DEV STM32H753xx)
  set(HSE 8000000)
  set(STARTUP ${cmsis_h7_SOURCE_DIR}/Source/Templates/gcc/startup_stm32h753xx.s)
elseif(PLACA STREQUAL "LASET")
  set(DEV STM32H743xx)
  set(HSE 25000000)
  set(STARTUP ${cmsis_h7_SOURCE_DIR}/Source/Templates/gcc/startup_stm32h743xx.s)
else()
  message(FATAL_ERROR "PLACA tem de ser NUCLEO ou LASET")
endif()

set(HAL_MODULOS cortex dma mdma exti eth eth_ex fdcan flash flash_ex gpio i2c i2c_ex pwr pwr_ex rcc rcc_ex tim tim_ex uart uart_ex hsem)
set(HAL_SRC ${hal_h7_SOURCE_DIR}/Src/stm32h7xx_hal.c)
foreach(m ${HAL_MODULOS})
  list(APPEND HAL_SRC ${hal_h7_SOURCE_DIR}/Src/stm32h7xx_hal_${m}.c)
endforeach()

set(RTOS ${freertos_SOURCE_DIR})
set(RTOS_SRC ${RTOS}/tasks.c ${RTOS}/queue.c ${RTOS}/list.c ${RTOS}/timers.c
             ${RTOS}/event_groups.c ${RTOS}/stream_buffer.c ${RTOS}/portable/GCC/ARM_CM4F/port.c)

file(GLOB LWIP_SRC ${lwip_SOURCE_DIR}/src/core/*.c ${lwip_SOURCE_DIR}/src/core/ipv4/*.c)
list(APPEND LWIP_SRC ${lwip_SOURCE_DIR}/src/netif/ethernet.c)

file(GLOB APP_SRC CONFIGURE_DEPENDS Core/Src/*.c)

add_executable(laset_gateway ${APP_SRC} ${HAL_SRC} ${RTOS_SRC} ${LWIP_SRC}
  ${cmsis_h7_SOURCE_DIR}/Source/Templates/system_stm32h7xx.c ${STARTUP})
target_include_directories(laset_gateway PRIVATE
  Core/Inc ${hal_h7_SOURCE_DIR}/Inc ${cmsis_h7_SOURCE_DIR}/Include ${cmsis6_SOURCE_DIR}/CMSIS/Core/Include
  ${RTOS}/include ${RTOS}/portable/GCC/ARM_CM4F ${lwip_SOURCE_DIR}/src/include)
target_compile_definitions(laset_gateway PRIVATE ${DEV} USE_HAL_DRIVER HSE_VALUE=${HSE} PLACA_${PLACA}
  $<$<BOOL:${CAN_LOOPBACK}>:LASET_CAN_LOOPBACK>)
target_compile_options(laset_gateway PRIVATE -O2 -g3 -std=gnu11
  $<$<COMPILE_LANGUAGE:C>:-Wall -Wextra -Wno-unused-parameter>)
set_source_files_properties(${HAL_SRC} ${RTOS_SRC} ${LWIP_SRC} PROPERTIES COMPILE_OPTIONS "-w")
target_link_options(laset_gateway PRIVATE -T${CMAKE_CURRENT_SOURCE_DIR}/STM32H7_FLASH.ld
  -Wl,-Map=laset_gateway.map -Wl,--print-memory-usage)
set_target_properties(laset_gateway PROPERTIES SUFFIX ".elf"
  LINK_DEPENDS ${CMAKE_CURRENT_SOURCE_DIR}/STM32H7_FLASH.ld)
add_custom_command(TARGET laset_gateway POST_BUILD
  COMMAND ${CMAKE_OBJCOPY} -O ihex laset_gateway.elf laset_gateway.hex
  COMMAND ${CMAKE_OBJCOPY} -O binary laset_gateway.elf laset_gateway.bin
  COMMAND ${CMAKE_SIZE} laset_gateway.elf)
