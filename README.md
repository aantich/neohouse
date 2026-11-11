# House modernization

Working port of House 0.8.93 to a modern GHC, targeting native CPU machine code
with as little C as practical. The first boot target remains single-CPU IA32
under QEMU; a later 64-bit target is a separate milestone.

The first usable target is a **character-based terminal and shell**. Start with
COM1 serial output/input in a normal host terminal. GUI work is deferred.

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
- A new assembly-only image boots in QEMU and writes a COM1 serial marker.
  It does not yet start the Haskell runtime. The standalone RTS port is the next
  integration step; a modern interactive shell is not ready yet.
- The imported GUI is **academic-use-only Gadgets**. This working import is not
  ready for an unrestricted open-source release. Its initial Git commit also
  contains Gadgets. There is no public remote configured.

## Plans

- [Modernization milestones and C reduction](docs/MODERNIZATION.md)
- [Pinned toolchain and initial checkpoints](toolchain/README.md)
- [Standalone runtime bring-up work map](docs/RTS_PORT.md)
- [Checkpoint results and remaining work](docs/BRINGUP_STATUS.md)
- [Independent Haskell GUI replacement](docs/GUI_REPLACEMENT.md)
- [License inventory and publication requirements](docs/LICENSE_AUDIT.md)

New original bootstrap code uses MIT. Existing files retain their own
licenses and notices. Adding an MIT file will not relicense the imported tree.
New bootstrap scripts and programs carry MIT identifiers; their license text
is in `LICENSES/MIT.txt`.
Before publication, create a fresh repository from the audited source set so
that academic-only material, uncleared assets and historical binaries are
absent from both the public tree and its history. Preserve the upstream
reference copies separately.
