# Terminal-first bring-up status

Verified 2026-11-11 on an Apple Silicon Mac. These results establish two
independent foundations. A standalone modern GHC runtime and an interactive
House terminal have not yet been implemented.

## Hosted modern compiler: passed

```sh
python3 scripts/toolchain.py build
python3 scripts/toolchain.py hosted-check
```

- GHC 9.14.1, official i386 Linux bindist with the SHA-256 in
  `toolchain/lock.json`; matching source archive also downloaded and verified.
- Debian bookworm image pinned by digest; package repositories pinned to the
  2026-11-10 snapshot, with signature verification retained.
- GCC 12.2.0 (`12.2.0-14+deb12u1`); GNU binutils 2.40.
- New Haskell program compiled with `-fasm -O1 -Wall -Werror`: ELF32, Intel
  80386, Linux executable. No old House/Gadgets module is compiled.
- Program measured **24 collections** and **16,802,724 allocated bytes** during
  its checkpoint, with **602,140 bytes maximum live data**. Each of twelve
  chains is checked before and after a major collection while held by an
  `IORef`; another collection follows dropping that root.
- The final `+RTS -s` report includes shutdown and output allocations and
  therefore reports 25 major collections and a slightly larger allocation
  total. The checkpoint counters above are sampled inside the program.

Generated evidence is in ignored `build/hosted/`: compiler and package
manifests, ELF header/format, native library list, stdout and RTS statistics.
The executed program runs under Linux. It does not establish bare-metal GC.

The executable's dynamic native dependencies are `libm.so.6`, `libgmp.so.10`,
`libc.so.6` and `/lib/ld-linux.so.2`. This is the hosted bindist configuration;
the eventual guest must replace Linux OS assumptions and evaluate the native
Haskell bignum backend. These are not an approved guest dependency list.

## Bare-metal serial platform: passed

```sh
python3 scripts/check_serial.py
```

- Newly written Multiboot entry and linker script; no inherited boot image,
  GPL-marked historical `multiboot.h`, Gadgets or font/image asset is included.
- QEMU 11.1.3, `pc-i440fx-11.1`, TCG, `qemu32`, one CPU, 256 MiB RAM; direct
  ELF kernel load with no guest network.
- Valid aligned Multiboot header in the first 8192 bytes; no undefined linker
  symbols. Kernel SHA-256:
  `ec44e15e517ea4c802fa856f0b0d4034bf4656adec762fa08449c2a31fa70f07`.
- Output: `House platform checkpoint: IA32 entry and COM1 serial OK`, followed
  by `Haskell RTS not started.` The test device returns host exit status 33.
- Only assembly is linked into this image. It verifies platform entry and UART
  output, not Haskell startup, allocation, interrupts, input or a shell.

Generated evidence is in ignored `build/serial/`: ELF layout, link map,
undefined-symbol check, serial/QEMU logs and `run.json`. The test VM exits.

## Next gate

Connect the modern non-threaded RTS to the platform entry with valid memory,
timer, scheduling and diagnostic hooks. Enter Haskell through a serial I/O
boundary, prove repeated allocation and GC in that guest, then add serial
input, line editing and the shell. [The RTS work map](RTS_PORT.md) identifies
the inspected source interfaces. GUI work is deferred.

The local Docker disk limit was increased to 128 GiB for build capacity;
the filesystem then reported approximately 64 GiB available. The existing
services were restored after the Docker restart. This host configuration is
not part of the guest OS.
