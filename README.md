# House modernization

Working port of House 0.8.93 to a modern GHC, targeting native CPU machine code
with as little C as practical. The first boot target remains single-CPU IA32
under QEMU; a later 64-bit target is a separate milestone.

The active target is a **character-based Haskell REPL**: expressions,
definitions and typed OS actions in a live workspace. The existing COM1
terminal is the starting point; it is currently a command shell, not a Haskell
evaluator. GUI work and publication research are deferred.

This checkout was copied from upstream commit
`37a52cc7ea108d2d7ed89ec99a15ab51a15d7d3d` of
[dls/house](https://github.com/dls/house). The original `README` and `LICENSE`
are preserved. Unmodified upstream snapshots, papers and the successful original
binary boot baseline are kept in the parent workspace, outside this repository.

## Current status

- A separate Git repository is initialized on `codex/modern-ghc-bootstrap`.
- The historical House 0.8 image boots in QEMU in text and graphics modes.
  That is evidence for the old binary, not a modern source build.
- The pinned GHC 9.14.1 IA32 Linux toolchain builds and runs native ELF32 code.
  Its hosted allocation check completed 24 collections with live-data checks.
- The new standalone GHC 9.14.1 image enters native Haskell, allocates 16.8 MB
  and completes 24 collections with retained-data checks under QEMU.
- A Haskell serial terminal supports `help`, `mem`, `gc`, `selftest`, `echo`,
  `clear` and `halt`, with bounded ASCII line editing. It uses a restricted
  runtime/library interface; the historical House drivers are not ported yet.
- The guest library graph is now rebuilt from GHC source with native Haskell
  bignums. Functions, lists, `Show`, `Integer`, GC retention and recoverable
  evaluation exceptions run in the standalone kernel without GMP.
- A host-side submission driver compiles an ordinary Haskell module against
  the initial `OS` API and boots its native code inside House. Each submission
  still rebuilds/reboots; live loading and REPL bindings are next.
- The imported GUI is **academic-use-only Gadgets**. This working import is not
  ready for an unrestricted open-source release. Its initial Git commit also
  contains Gadgets. There is no public remote configured.

## Plans

- [Active target: practical Haskell OS with a REPL](docs/REPL.md)
- [Compile and run a native Haskell submission](docs/NATIVE_SUBMISSIONS.md)
- [Modernization milestones and C reduction](docs/MODERNIZATION.md)
- [Pinned toolchain and initial checkpoints](toolchain/README.md)
- [Standalone runtime bring-up work map](docs/RTS_PORT.md)
- [Checkpoint results and remaining work](docs/BRINGUP_STATUS.md)
- [Independent Haskell GUI replacement](docs/GUI_REPLACEMENT.md)
- [License inventory and publication requirements](docs/LICENSE_AUDIT.md)
- [Deferred research and publication topic](docs/RESEARCH_BACKLOG.md)

## Run the terminal

From this repository in a normal host terminal:

```sh
python3 scripts/terminal.py
```

This builds with the pinned Docker image and runs QEMU with serial attached to
your terminal, using its fonts and scaling. Type `help`, then `halt` to exit.
Use `--no-build` to reuse an existing image. Reproducible setup and automated
checks are in [the toolchain instructions](toolchain/README.md).

To watch boot and use the same guest terminal in its own QEMU window:

```sh
python3 scripts/terminal.py --window
```

On macOS this starts fullscreen with scaling for Retina displays. `--fullscreen`
also selects this mode explicitly; `--windowed` opens a smaller resizable window.
Use `--no-build` to boot the existing image immediately. Click inside the window
to type. The window displays the guest's serial console using QEMU's terminal
renderer; House's command loop, memory management and Haskell runtime run
inside the VM. Guest VGA/PS2 drivers are not needed for this mode.

To compile and boot an ordinary Haskell module using the initial OS API:

```sh
python3 scripts/submission.py examples/repl/HelloHouse.hs
```

The example uses functions, lists, a large `Integer`, a memory snapshot and
exception recovery. This is the static compilation checkpoint toward the REPL.

New original bootstrap code uses MIT. Existing files retain their own
licenses and notices. Adding an MIT file will not relicense the imported tree.
New bootstrap scripts and programs carry MIT identifiers; their license text
is in `LICENSES/MIT.txt`.
Before publication, create a fresh repository from the audited source set so
that academic-only material, uncleared assets and historical binaries are
absent from both the public tree and its history. Preserve the upstream
reference copies separately.
