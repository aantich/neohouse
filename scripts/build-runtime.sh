#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu
mkdir -p build/runtime
python3 scripts/rebuild-rts.py
rts_include=$(ghc-pkg field rts include-dirs --simple-output)
source=.cache/ghc-9.14.1
gcc -m32 -ffreestanding -fno-pie -DHOUSE_RUNTIME -c bootstrap/serial/start.S -o build/runtime/start.o
gcc -m32 -c bootstrap/runtime/faults.S -o build/runtime/fault_vectors.o
for unit in entry startup iface memory clock features minic faults support_check; do
    gcc -m32 -O2 -Wall -Wextra -Werror -ffreestanding -fno-pie -fno-stack-protector \
        -ffunction-sections -fdata-sections -DCOMPILING_RTS \
        -I"$rts_include" -I"$source/rts" \
        -I"$source/libraries/ghc-internal/include" -I"$source/libraries/ghc-internal/cbits" \
        -c "bootstrap/runtime/$unit.c" -o "build/runtime/$unit.o"
done
ghc -fasm -O1 -Wall -Werror -fforce-recomp -static -no-hs-main \
    -pgml /work/scripts/link-runtime.py -outputdir build/runtime \
    -ibootstrap/runtime bootstrap/runtime/HouseKernel.hs build/runtime/start.o \
    build/runtime/entry.o build/runtime/startup.o build/runtime/iface.o \
    build/runtime/memory.o build/runtime/clock.o build/runtime/features.o \
    build/runtime/minic.o build/runtime/faults.o build/runtime/fault_vectors.o build/runtime/support_check.o \
    -o build/runtime/kernel.elf
python3 scripts/audit-runtime.py
