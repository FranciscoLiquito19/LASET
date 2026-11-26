# Testes no PC (compilador nativo): cmake -B build && cmake --build build && ./build/teste_modulos
cmake_minimum_required(VERSION 3.22)
project(testes_firmware C)
add_executable(teste_modulos teste_modulos.c
  ../Core/Src/encaminhamento_regras.c ../Core/Src/cobs.c ../Core/Src/nmea.c
  ../Core/Src/isotp.c ../Core/Src/config.c ../Core/Src/trama_pc.c)
target_include_directories(teste_modulos PRIVATE ../Core/Inc)
target_compile_options(teste_modulos PRIVATE -Wall -Wextra -Werror -std=gnu11)

# Robustez: entradas aleatórias, com AddressSanitizer e UndefinedBehaviorSanitizer
add_executable(teste_robustez teste_robustez.c
  ../Core/Src/cobs.c ../Core/Src/nmea.c ../Core/Src/isotp.c ../Core/Src/config.c
  ../Core/Src/trama_pc.c ../Core/Src/encaminhamento_regras.c)
target_include_directories(teste_robustez PRIVATE ../Core/Inc)
target_compile_options(teste_robustez PRIVATE -Wall -Wextra -Werror -std=gnu11 -O1 -g
  -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer)
target_link_options(teste_robustez PRIVATE -fsanitize=address,undefined)
