#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu

mkdir -p build/serial
gcc -m32 -ffreestanding -fno-pie -c bootstrap/serial/start.S -o build/serial/start.o
ld -m elf_i386 -nostdlib -T bootstrap/serial/link.ld \
    -Map=build/serial/kernel.map build/serial/start.o -o build/serial/kernel.elf
readelf -h -l build/serial/kernel.elf > build/serial/elf-layout.txt
nm -u build/serial/kernel.elf > build/serial/undefined-symbols.txt
test ! -s build/serial/undefined-symbols.txt
