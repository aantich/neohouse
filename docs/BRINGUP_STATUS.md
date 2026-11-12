# Terminal-first bring-up status

Verified 2026-11-11–12 on an Apple Silicon Mac. These results establish two
foundations, a standalone modern GHC allocation/GC checkpoint, a basic
interactive Haskell terminal, and a source-built library/native-module
checkpoint. The terminal is still a command shell; live native loading and
REPL sessions are next. The historical House kernel modules are not yet ported.

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

## Initial standalone native Haskell and terminal: passed

This section records the original primitive-only checkpoint. The later
library/native-module checkpoint below supersedes its library limitations.

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

## Ordinary Haskell and native modules: passed

Verified 2026-11-12 with GHC 9.14.1 native code executing in the standalone
QEMU guest. The new library build compiles the current graph of **203 Haskell
objects** from the matching source with `BIGNUM_NATIVE`. It uses a private
guest package database; the hosted compiler and its Linux/GMP dependencies are
unchanged. The full new-target compiler/RTS configuration is still future work.

The guest now checks functions, list processing, signed/derived `Show`,
multiword `Integer` multiplication/division, `100!` rendering and integer
retention across major GC. Opaque inputs prevent compile-time evaluation of
the arithmetic checks. Standard evaluation exceptions are caught and followed
by successful evaluation of `42`. Additional checks exercise typed arithmetic
exceptions, allocator failure/errno, Haskell UTF-8 conversion, and explicit
rejection of unavailable codecs, file hashing and IPE configuration. Rejection
of IPE configuration leaves normal exception handling intact.

An ordinary source module exporting `HouseSubmission.submission :: OS ()`
is compiled on the host and linked into a fresh kernel. Inside House, the
example prints `42`, `[2,4,6,8,10]`, `2^200`, a live memory snapshot and a
division-by-zero recovery message, then completes with QEMU exit status 33.
This is a rebuilt/rebooted static image, not live code loading or a REPL.
See [the source/module contract and checks](NATIVE_SUBMISSIONS.md).

The final default image and all 14 terminal cases pass; QEMU exits with 33.
The assembly-only boot hash remains unchanged. The submission test also
verifies that GHC rejects an ill-typed module before boot, preserving the
previous runtime image. Recorded kernel SHA-256 values:

- Default library/terminal image:
  `9ec2694965b72864dcbfca349565f3d64248c8a8b6f94e8a09a329f4435f6165`.
- Successful native submission:
  `efeedccf122581ee42d84388064de83f74305626f40b44e22c16992e02bb6a33`.

The initial chain check still measures 24 collections and 16,802,376 allocated
bytes. Two additional explicit collections test the library/retained integers.
The terminal initially acquires 6 MiB from the 245 MiB physical pool; its
configured RTS heap limit remains 128 MiB.

### Non-Haskell code in the expanded guest

The GHC RTS C/Cmm/assembly, original bootstrap C/assembly and three libgcc
helpers remain as above. The expanded guest additionally uses GHC's
public-domain **`cbits/md5.c`** for type fingerprints: `__hsbase_MD5Init`,
`__hsbase_MD5Update`, `__hsbase_MD5Final`, `__hsbase_MD5Transform`. Its notice
and source hash are recorded. There is no added external crypto library.
No GMP, libffi, host libc/libm, pthread or Linux syscall dependency is linked.

Source/configuration/interface hashes, exact native imports and ELF layout
are recorded in `build/runtime/dependencies.json`. The ELF syscall scan now
recognizes verified GHC info-table offset data that linear disassembly treats
as instructions. A regression check injects real `int 0x80`, `sysenter`,
`syscall` and prefixed syscall instructions into unexecuted copies and verifies
rejection; corrupting a recognized table must also remove its exemption.
The scan is dependency evidence, not a security or control-flow proof.

### Remaining limits

The ordinary Haskell/OS surface is deliberately small. The full Unix `base`
API, RTS Haskell-finalizer callback, general floating-point math, live native
loader, persistent bindings and GHC self-hosting remain unavailable. The OS
API is trusted code in a shared address space. UART output/input is still
ASCII/polled, with no hardware IRQs, preemption, paging or application
isolation. Ctrl-C edits a line; it does not interrupt native evaluation.

## Next gate

Add a compiler transport and native loader so newly entered Haskell can run
in the same guest without rebuilding/rebooting. Then add session bindings and
timer-driven cancellation. Continue toward a fully configured freestanding
RTS/library source build, porting historical House modules as practical needs
arise. Memory protection precedes protected applications. [The RTS work
map](RTS_PORT.md) records the implementation and remaining interfaces; GUI and
publication research stay deferred.

The local Docker disk limit was increased to 128 GiB for build capacity;
the filesystem then reported approximately 64 GiB available. The existing
services were restored after the Docker restart. This host configuration is
not part of the guest OS.
