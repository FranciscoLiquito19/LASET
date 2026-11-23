# Testes no PC (compilador nativo): cmake -B build && cmake --build build && ./build/teste_modulos
cmake_minimum_required(VERSION 3.22)
project(testes_firmware C)
add_executable(teste_modulos teste_modulos.c
  ../Core/Src/encaminhamento_regras.c ../Core/Src/cobs.c ../Core/Src/nmea.c)
target_include_directories(teste_modulos PRIVATE ../Core/Inc)
target_compile_options(teste_modulos PRIVATE -Wall -Wextra -Werror -std=gnu11)
