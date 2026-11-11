# Standalone runtime bring-up notes

Source inspected: the verified GHC 9.14.1 source archive pinned in
`toolchain/lock.json`. It is extracted locally under ignored `.cache/ghc-9.14.1`.
The first restricted backend now boots and passes allocation/GC checks. This
map also describes the broader target work still needed for a complete port.

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
of this chain. The additional `check_runtime.py` now establishes steps 2–4 for
the restricted native program. `check_terminal.py` exercises step 5 through
the real emulated UART.

## Implemented first-boot boundary

- `bootstrap/runtime/memory.c` admits whole megablocks from Multiboot usable
  ranges, excludes reserved overlaps, kernel, boot tables/command line and
  modules, then implements allocation/reuse/release. The separate coalescing
  C metadata allocator occupies an 8 MiB kernel BSS arena.
- `clock.c` reads QEMU's 64-bit HPET without enabling interrupts. CPU time
  currently equals elapsed time on the sole continuously active CPU. Wall
  time is unavailable. Own flat GDT, FPU/SSE setup and an exception IDT precede
  Haskell entry; paging and hardware interrupts stay disabled.
- `startup.c` initializes the non-threaded scheduler, two-generation copying
  collector, stable roots and required state. Tick delivery, Unix signals,
  tracing files, heap profiling, bytecode execution and dynamic loading are
  unavailable. Empty scheduler I/O polling is valid; actual Unix waits fail.
- `iface.c` supplies the GHC 9.14 `HsIface` fields needed by this program,
  including the **string-literal info tables**. Unavailable callback closures
  halt with a diagnostic. Unused boxing tables are NULL and their C APIs are
  discarded at link time. This is not a general `base` implementation.
- Haskell is compiled as a library entry (`HouseKernel.entry`), avoiding GHC's
  normal process-main wrapper and its Unix-facing `TopHandler` graph. The
  program uses primitive types and operations; it does not use `Integer`.
- `Serial.hs` implements UART polling in Haskell over two port-instruction
  wrappers. `HouseKernel.hs` implements editing, command parsing and GC checks.
- `rebuild-rts.py` replaces nine Linux/unsupported RTS objects, rebuilds the
  other 138 C objects with section GC, and retains 22 matching native objects.
  The collector's sole `pow(2,x)` call is redirected to an x87 helper, avoiding
  a broad libm dependency. The original verified GHC source tree is unmodified;
  the changed collector source is staged under ignored `build/runtime/rts/`.

The post-link audit rejects unresolved symbols, hosted ELF segments, Linux
syscall instructions and named GMP/libffi/pthread/Unix services, and records
the actual archive members and project input hashes. This check is useful
evidence for the prototype; it does not replace a complete component/license
audit or a full freestanding GHC build.
