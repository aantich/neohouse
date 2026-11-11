# Standalone runtime bring-up notes

Source inspected: the verified GHC 9.14.1 source archive pinned in
`toolchain/lock.json`. It is extracted locally under ignored `.cache/ghc-9.14.1`.
This is a work map; the hooks below have not yet been ported or proven.

The character terminal removes the GUI from bring-up. It does not remove the
runtime's platform requirements. The official Linux bindist is useful as a
hosted compiler and reference; its Linux RTS cannot simply be relinked into
the kernel and expected to work.

## Relevant boundaries

| Boundary | GHC 9.14.1 source | House target work |
| --- | --- | --- |
| Startup | `rts/RtsStartup.c`, `hs_init_ghc` | Select valid initialization, supply arguments and runtime defaults, account for locale/OS setup, and enter the Haskell scheduler |
| Heap allocation | `rts/sm/OSMem.h`, `rts/sm/MBlock.c`, `rts/sm/Storage.c` | Supply aligned megablocks from boot-provided usable memory; exclude kernel, boot information/modules, stacks and device memory; implement release/accounting correctly |
| Time and ticker | `rts/GetTime.h`, `rts/posix/GetTime.c`, `rts/Timer.c`, `rts/posix/Ticker.c` | Initially disable optional periodic activity explicitly; supply monotonic time/accounting and later hardware timer delivery |
| Scheduler and waits | `rts/Schedule.c`, `rts/IOManager.c`, `rts/posix/Select.c` | Start with one capability and a non-threaded runtime; replace OS waits with supported device/event behavior |
| Signals and faults | `rts/posix/Signals.c` and scheduler interfaces | Do not install Unix signal handlers; provide controlled fault reporting first, then House-specific interrupt/fault semantics |
| Native support | `rts/rts.cabal`, generated platform configuration | Audit libc, math, compiler helpers and optional ffi/pthread/NUMA/libdw/zstd requirements against the actual selected build |
| Integer backend | Hadrian `--bignum=native` and `libraries/ghc-bignum` | Build the guest's libraries with the native backend; do not infer GMP removal from the hosted compiler configuration |

The old House patches alter startup, timers, signals, memory management and
scheduler behavior across both its own patch directory and the HaLVM archive.
Port the necessary behavior against the current source; applying old diffs
mechanically would miss major changes in GHC's initialization and libraries.

For IA32, `USE_LARGE_ADDRESS_SPACE` needs separate assessment from the modern
64-bit path. `OSMem.h` also includes physical-memory reporting and NUMA hooks;
implementing only the historical `getPageSize` function is insufficient.

## Acceptance sequence

1. Platform entry and COM1 output, with the correct boot magic and a bounded
   headless test. The new `bootstrap/serial` checkpoint establishes this layer.
2. Runtime C/platform initialization with diagnostic phase markers and an
   explicit memory map. Establish required GDT/FPU/SSE state before calling
   generated code. Unsupported OS operations must fail visibly.
3. Enter a minimal Haskell program and print through an explicit serial FFI
   boundary, initially avoiding the Unix `System.IO` handle backend.
4. Repeatedly allocate, retain live roots across collections, check their
   contents afterward and release them. Record evidence that collections
   actually occur; a nonallocating greeting is insufficient.
5. Add serial input, line editing and an interactive Haskell shell over the
   same device API. Keep the serial driver and shell behavior in Haskell;
   restrict assembly to CPU instructions and boot/interrupt entry where needed.

The hosted GC check and platform-only serial check establish different parts
of this chain. Neither alone establishes a standalone modern Haskell OS.
