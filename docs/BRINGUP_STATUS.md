# Terminal-first bring-up status

Verified 2026-11-11–12 on an Apple Silicon Mac. These results establish two
foundations, plus a standalone modern GHC allocation/GC checkpoint and a basic
interactive Haskell terminal. The historical House kernel modules and broader
standard-library surface have not yet been ported.

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

## Standalone native Haskell and terminal: passed

```sh
python3 scripts/check_runtime.py
python3 scripts/check_terminal.py
python3 scripts/terminal.py --no-build  # interactive, in a normal host terminal
```

The new Multiboot kernel enters GHC 9.14.1 native Haskell without Linux or
another guest OS. It uses one non-threaded capability and the two-generation
copying collector. Each of twelve 50,000-node chains is forced, retained in a
mutable root, checked after major GC, dropped and collected again. The initial
checkpoint records **24 collections** and **16,802,376 allocated bytes**.
The tested kernel SHA-256 is
`db400ef95cf7ee8e6e44477a870e7af36b029578948506d14aeefdef70a7abf7`.

Bootstrap checks run inside the guest before RTS initialization: metadata
allocation/reallocation preserves payloads across 2048 mixed operations; free
blocks coalesce; overflow allocation is rejected; sorting, bounded formatting,
x87 collector math and megablock isolation/reuse are checked. The HPET must
advance. CPU exceptions report their vector, error code and instruction address
and exit the test VM with failure.

The terminal test drives UART input after each prompt and checks `help`, `mem`,
`gc`, `echo`, `clear`, unknown commands and `selftest`, plus backspace, Delete,
Ctrl-U, Ctrl-C, ignored arrow escapes, CR/LF/CRLF and the 256-character line
limit. Its second allocation check completes another 24 collections. `halt`
returns through Haskell to the runtime entry; QEMU exits with status 33.

The final ELF audit checks for no undefined symbols, dynamic interpreter,
dynamic/TLS segments, Linux syscall instructions, GMP/libffi/pthread symbols
or listed Unix services. Evidence is in `build/runtime/` and `build/terminal/`:
serial logs, run JSON, link map, disassembly, input hashes, notices and exact
dependency manifests. No historical House/Gadgets source or assets enter the
new target. Test VMs exit; the interactive launcher is separate.

### Non-Haskell code in this guest

| Component | Exact current scope |
| --- | --- |
| GHC runtime | Selected GHC 9.14.1 C/Cmm/assembly; 138 C objects rebuilt from matching source with section GC, nine platform/unsupported objects replaced, 22 native objects retained from the pinned bindist before final link selection |
| Original bootstrap support | Boot/fault assembly and C for CPU instruction bridges, RTS initialization, physical megablocks, HPET, diagnostics and a small metadata allocator; source under `bootstrap/` |
| GCC compiler support | Debian `libgcc-12-dev` 12.2.0-14+deb12u1: only `__divdi3`, `__udivdi3`, `__udivmoddi4` remain in the final ELF |

No host libc/libm, GMP, libffi, pthread, GRUB or other external native runtime
library is linked. GCC, binutils, Docker and QEMU are build/emulation tools,
not guest libraries. Haskell implements serial polling, text editing, command
dispatch and the retained-data test.

### Deliberate limits

This is a restricted first-boot ABI, with primitive Haskell types/operations,
not the full Linux `base` library. `Integer`, standard exception/finalizer
behavior, Unix handles, dynamic loading and bytecode execution are unavailable.
GMP's absence does **not** establish that native Haskell bignums were built.
The Cmm/assembly runtime objects are still from the matching compiler bindist;
the complete RTS/library source build remains work to do.

The console is ASCII serial, busy-polling on one CPU. Paging, hardware IRQs,
preemption, protected applications, filesystem and networking are absent. The
physical allocator conservatively excludes everything below the highest kernel
or boot-data/module end, and uses only whole usable megablocks. C metadata has
an 8 MiB arena; the RTS heap limit is 128 MiB. On the 256 MiB test VM the admitted
physical pool is 245 MiB and the terminal initially acquires 5 MiB for the heap.
These are bring-up choices, not a general hardware or production OS claim.

## Next gate

Build the full freestanding RTS/library configuration from source, enable
native Haskell bignums and standard library semantics, then port historical
House modules onto the new platform boundary. Add interrupts/event-driven
input and memory protection before protected applications. [The RTS work
map](RTS_PORT.md) records the implementation and remaining interfaces. GUI work
is deferred.

The local Docker disk limit was increased to 128 GiB for build capacity;
the filesystem then reported approximately 64 GiB available. The existing
services were restored after the Docker restart. This host configuration is
not part of the guest OS.
