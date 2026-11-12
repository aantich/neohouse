# Source provenance and dependency licenses

Updated 2026-11-12 for the public NeoHouse repository.

## Published sources

The published history contains only independently authored modernization code
and documentation. Git history was rewritten using an explicit source allowlist:

- `bootstrap/`: new kernel/platform boundary, Haskell runtime interface and checks.
- `scripts/`: new compiler, build, inspection, submission and VM launch tools.
- `toolchain/`: pinned dependency descriptions and Docker build instructions.
- `examples/`: new native Haskell submission examples.
- `docs/`, `README.md`, `.gitignore`, `.dockerignore` and project license files.

These original sources are covered by [MIT](../LICENSE), with a second copy at
[`LICENSES/MIT.txt`](../LICENSES/MIT.txt). SPDX identifiers identify source files.
No historical House implementation is relabeled MIT by this publication.

Gadgets' academic-only source, its adapters/demos, historical kernels and
bootloader binaries, fonts, generated assets, support libraries and old GHC
patches are absent from every published commit. The unmodified historical
sources and a backup of the pre-rewrite development history remain external
local research references. They are not inputs to the NeoHouse build.

House remains an architectural reference. The historical import was based on
[dls/house at 37a52cc7](https://github.com/dls/house/tree/37a52cc7ea108d2d7ed89ec99a15ab51a15d7d3d).
That project's hOp, Programatica, Gadgets and component notices apply to its
own files, which are excluded here. Research papers are linked rather than
redistributed.

## Downloaded and linked dependencies

Dependencies are pinned in [`toolchain/lock.json`](../toolchain/lock.json).
Downloaded archives and generated objects/images are ignored by Git.

| Component | Recorded license/provenance | Use |
| --- | --- | --- |
| GHC 9.14.1 compiler and selected RTS/library objects | GHC BSD-style license and additional component notices in the verified source and `ghc-internal/LICENSE` | Compiler runs on the host; selected RTS/library code is linked into the guest |
| GHC native bignum implementation | Part of the source-built `ghc-internal` graph, retaining upstream notices | Haskell arbitrary-precision arithmetic; no GMP in the guest |
| GHC `libraries/ghc-internal/cbits/md5.c` | Colin Plumb public-domain declaration | Small C helper for type fingerprints |
| Debian `libgcc-12-dev` 12.2.0-14+deb12u1 helpers | GPL-3.0-or-later with GCC Runtime Library Exception 3.1, per the exact Debian package notice | `__divdi3`, `__udivdi3`, `__udivmoddi4` in the current guest |
| Debian/GCC/binutils and hosted GHC dependencies | Their package-specific open-source notices | Build environment; hosted libraries do not automatically become guest dependencies |
| QEMU | Its own GPL and component notices | Separately installed emulator; not linked into NeoHouse |

The build preserves full GHC/`ghc-internal` notices, including notices applying
to Report-derived library code. Four staged library modifications retain those
upstream notices. The small MD5 helper introduces no external crypto library.

`build/runtime/dependencies.json` records the actual linked members, helper
symbols, compiler versions, source hashes, API interfaces and kernel hash.
`build/runtime/dependency-notices/` contains copied GHC, library, MD5, libgcc
and project notices. These records concern the particular generated image;
the project's MIT license does not replace third-party dependency licenses.

## Source publication versus binary distribution

This publication provides project source and build recipes, not prebuilt OS or
compiler binaries. The prototype still retains 22 matching GHC Cmm/assembly
objects from the hash-verified compiler bindist. A fully source-reproducible
compiler/runtime build remains a milestone.

Before distributing binary images, retain their exact dependency manifest and
all required notices, and provide corresponding source/relinking material
where the applicable dependency terms require it. Review the exact libgcc
exception and generated artifact, rather than inferring its terms from the
project's MIT label.

Future historical House modules or assets must have established provenance
and suitable open-source terms before being introduced into this repository.
The deferred GUI must be independently implemented; Gadgets is not an input.
