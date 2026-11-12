# Modernization milestones

The agreed target is native CPU machine code with minimal C. Initial bring-up
uses single-CPU IA32 under QEMU to reduce changes relative to House. A 64-bit
target follows after a reliable modern-runtime boot.

## Terminal first

The first usable system is a character-based Haskell REPL, per the user's
updated scope. The serial command shell is an implemented foundation; real
Haskell evaluation is the next target. Defer GUI rendering, fonts, widgets,
windows, mouse interaction and DPI work. Gadgets must not be compiled or
linked into any new boot target.

Bring up COM1 serial diagnostics first, with QEMU connected to a normal host
terminal. Then add input, line editing and a small shell over that character
stream. The host terminal supplies readable fonts and window scaling. A VGA
text console and PS/2 keyboard path can follow once boot and the runtime work;
they must not be prerequisites for early serial debugging.

The sequence is: serial boot marker; modern RTS startup; Haskell output;
repeated allocation and GC; serial input and line editing; interactive shell;
then real Haskell compilation, live native-code loading and recoverable
evaluation. Additional drivers follow practical REPL needs. Keep unsupported
runtime OS operations explicit so a stub cannot silently report success. The
old graphics desktop and its assets remain external historical references.

## First three stages

1. **Create an isolated working copy and Git repository.** Done: House 0.8.93
   copied to this directory, original source/notices preserved, independent
   repository initialized on `codex/modern-ghc-bootstrap`. The parent upstream
   snapshots and historical boot evidence remain unchanged. For NeoHouse's
   public repository, history was rewritten to retain the new modernization
   code and documentation and exclude the historical reference import.
2. **Establish a reproducible modern Linux toolchain.** Done for initial
   bring-up: the Docker builder pins GHC 9.14.1 by archive hash, its Debian base
   by digest and packages by dated snapshot. GCC 12.2.0 and binutils 2.40 are
   recorded with the full package manifest. The hosted ELF32 native-code check
   passed, allocating 16.8 MB and completing 24 collections with live-data
   checks. See [the toolchain instructions](../toolchain/README.md) and
   [recorded results](BRINGUP_STATUS.md). A freestanding RTS is still separate.
3. **Boot a minimal standalone modern Haskell runtime.** Checkpoint passed:
   the new kernel enters GHC 9.14.1 native Haskell, allocates 16.8 MB and performs
   24 collections while checking retained chains. The backend supplies boot
   memory allocation, HPET time, CPU setup and fault diagnostics. A basic
   Haskell serial shell also boots and accepts commands. This uses a restricted
   library interface and a partly rebuilt RTS: its C objects are rebuilt from
   the matching verified source, while 22 native Cmm/assembly objects come from
   the pinned compiler bindist. It does not establish a complete source build
   of the GHC distribution or a port of the historical House kernel modules.

Gadgets is excluded from the stage-3 target. The
[GUI plan](GUI_REPLACEMENT.md) is deferred until the REPL target is useful.

## Next work

Follow the [practical REPL plan](REPL.md). Ordinary Haskell functions, lists,
classes, rendering, native `Integer` and controlled exception recovery now
pass in the standalone guest. The [submission checkpoint](NATIVE_SUBMISSIONS.md)
compiles a source module on the host against the initial `OS` API and runs its
native code in a rebuilt/rebooted image. Live loading, session bindings and
timer-driven cancellation follow; compilation and execution remain separate
host/guest responsibilities.

Move toward a properly configured freestanding RTS/library source build,
while preserving the native Haskell bignum configuration, rather than
expanding the restricted first-boot ABI indefinitely. Port interrupts/timers
and other House modules when these milestones need them. VGA text/PS2,
paging, isolation, protected user execution and a 64-bit target remain
separate milestones. The [research/publication topic](RESEARCH_BACKLOG.md)
is parked for later and does not block the practical implementation.

## C reduction policy

| Area | Initial approach | Longer-term direction |
| --- | --- | --- |
| Haskell compilation | GHC native code generation | Remain native; no bytecode VM is required |
| Runtime | Retain the necessary modern GHC RTS, including its C/Cmm/assembly | Reduce OS-facing shims; a Haskell-only replacement RTS is a separate research project |
| Boot/interrupt entry and privileged operations | Small, explicit assembly and platform glue | Keep the unavoidable CPU boundary narrow; move policy and driver logic into Haskell |
| Big integers | Source-built native Haskell bignum backend in the guest | Keep GMP out of guest artifacts; the hosted compiler can retain its own dependencies |
| GUI and input | Haskell renderer, UI and House drivers | No new native GUI/font library dependency; independent replacement for Gadgets |
| libc/allocator/math/compiler helpers | Link only demonstrated necessities; audit each exact source | Replace small support routines where practical, avoid imposing a broad libc on the guest |
| Build tools | Isolated open-source compiler, C toolchain and emulator | Distinguish build-host software from code shipped in the kernel |

GHC's native bignum option requires configuring/building the relevant GHC
libraries; it is not a switch that removes GMP from an arbitrary prebuilt
compiler's runtime libraries. The first toolchain experiment may use the
official hosted compiler while that guest configuration is developed.

Modern GHC uses Hadrian for its build. Port semantics of the historical RTS
patches rather than attempting to apply GHC-6.8.2 patches mechanically. Keep a
record of each runtime change and the non-Haskell code actually linked into the
resulting kernel. See the [GHC build-system migration notes](https://www.haskell.org/ghc/blog/20220805-make-to-hadrian.html)
and the [GHC 9.14.1 distribution](https://www.haskell.org/ghc/download_ghc_9_14_1.html).

All retained and new components must meet the open-source release requirements
in [the license audit](LICENSE_AUDIT.md). Minimal C and open-source licensing
are separate requirements; neither implies the other.
