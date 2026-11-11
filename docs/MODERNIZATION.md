# Modernization milestones

The agreed target is native CPU machine code with minimal C. Initial bring-up
uses single-CPU IA32 under QEMU to reduce changes relative to House. A 64-bit
target follows after a reliable modern-runtime boot.

## First three stages

1. **Create an isolated working copy and Git repository.** Done: House 0.8.93
   copied to this directory, original source/notices preserved, independent
   repository initialized on `codex/modern-ghc-bootstrap`. The parent upstream
   snapshots and historical boot evidence remain unchanged. The initial import
   is a local reference, not an approved public source release.
2. **Establish a reproducible modern Linux toolchain.** In progress: Docker's
   `linux/386` execution was verified on this Apple Silicon host. GHC 9.14.1 is
   the candidate with an official i386 Linux distribution. Pin the compiler
   archive/hash, base image digest, C compiler/binutils and package inputs;
   record dependency versions. First prove a hosted native executable can be
   built and run. That does not prove a freestanding RTS works.
3. **Boot a minimal standalone modern Haskell runtime.** Pending: audit and
   adapt the old startup/runtime changes against the selected GHC. Establish
   serial diagnostics, boot memory layout, linker configuration and required
   RTS platform hooks. The gate is a source-built kernel that enters Haskell,
   allocates repeatedly and completes multiple garbage collections under QEMU.
   A constant-output Haskell function or hosted Linux program does not satisfy
   this checkpoint.

Gadgets is excluded from the stage-3 target. Bring up a minimal program before
restoring the original shell, drivers and protected user execution. The new
[GUI plan](GUI_REPLACEMENT.md) provides the subsequent desktop milestones.

## C reduction policy

| Area | Initial approach | Longer-term direction |
| --- | --- | --- |
| Haskell compilation | GHC native code generation | Remain native; no bytecode VM is required |
| Runtime | Retain the necessary modern GHC RTS, including its C/Cmm/assembly | Reduce OS-facing shims; a Haskell-only replacement RTS is a separate research project |
| Boot/interrupt entry and privileged operations | Small, explicit assembly and platform glue | Keep the unavoidable CPU boundary narrow; move policy and driver logic into Haskell |
| Big integers | Evaluate GHC's native Haskell bignum backend | Remove GMP from the guest when the selected RTS/library build supports this configuration |
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
