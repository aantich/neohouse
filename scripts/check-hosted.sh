#!/bin/sh
# SPDX-License-Identifier: MIT
set -eu

mkdir -p build/hosted
ghc --numeric-version > build/hosted/ghc-version.txt
ghc --info > build/hosted/ghc-info.txt
ghc-pkg list --simple-output > build/hosted/ghc-packages.txt
cp /opt/house-toolchain/debian-packages.tsv build/hosted/
gcc --version > build/hosted/gcc-version.txt
ld --version > build/hosted/ld-version.txt
ghc -fasm -O1 -Wall -Werror -rtsopts -with-rtsopts=-T -fforce-recomp \
    -outputdir build/hosted bootstrap/hosted/Main.hs -o build/hosted/gc-check
file build/hosted/gc-check | tee build/hosted/executable-format.txt
readelf -h build/hosted/gc-check > build/hosted/elf-header.txt
ldd build/hosted/gc-check > build/hosted/native-libraries.txt
build/hosted/gc-check +RTS -s -RTS > build/hosted/stdout.txt 2> build/hosted/rts-stats.txt
cat build/hosted/stdout.txt
