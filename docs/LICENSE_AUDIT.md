# License inventory and open-source release plan

Initial audit, 2026-11-11. This records observed notices, unresolved provenance
and release decisions; it is not a claim that the current import is cleared.

The governing requirement is an unrestricted open-source release, including
commercial use. Academic-use-only terms fail the Open Source Definition's
[prohibition on field-of-use restrictions](https://opensource.org/osd).
MIT is the intended license for new original code. Existing components keep
their own terms; do not replace the inherited `LICENSE` with a blanket MIT file.

## Observed components

Paths are relative to this repository. This is an initial inventory, not yet a
complete file-by-file manifest of the compiler, runtime and release image.

| Component | Observed terms/evidence | Planned disposition |
| --- | --- | --- |
| New `bootstrap/`, `scripts/` and toolchain code | Original MIT code, SPDX identifiers and `LICENSES/MIT.txt` | Preserve the MIT notice; no Gadgets code or historical boot header is used in these checkpoints |
| Programatica contributions | Three-clause BSD-style permission in `LICENSE`, including attribution and non-endorsement | Reuse where provenance is established; preserve notices in source and binary distributions |
| Otherwise unmarked hOp files | Custom permission to use, modify and distribute, including derived works; `LICENSE` | Retain this exact notice; do not label these files MIT merely because the terms are permissive |
| `kernel/Gadgets/` including `lib/`, demos and images | Academic-use-only redistribution in `LICENSE` and `kernel/Gadgets/README.txt` | Replace independently; exclude from public source, history and release artifacts |
| GHC compiler and RTS | [GHC's three-clause BSD license](https://www.haskell.org/ghc/license.html); actual release includes additional separately licensed components | Pin the chosen release and audit its libraries/native dependencies individually; preserve notices |
| `support/c/dlmalloc.c`, `libc.c`, `fakeerrno.c`, `Gen_wctype.hs` and generated tables | Public-domain declarations in the individual files and/or `support/c/LICENSE` | Verify each retained file, including incorporated code and table inputs; retain provenance |
| `support/c/bsearch.c` | File header says **LGPL-2.1-or-later**; `support/c/LICENSE` inaccurately calls it "GPLv2.1" | Prefer an independent Haskell implementation or removal if unused. If retained, satisfy the applicable LGPL distribution/relinking requirements |
| `support/m/` | Sun/fdlibm permission requiring notice retention; some files have additional provenance | Audit individual files and preserve applicable notices; replace only where it helps the C-reduction goal |
| `kernel/cbits/multiboot.h` | **GPL-2.0-or-later** notice in the header | Prefer independently authored definitions from the published boot protocol, with source provenance; otherwise assess obligations for the actual use. Do not claim the entire kernel's license solely from the header's presence |
| `mkbe2gbf` | "Released under GPL", without a version in the script | Replace the obsolete build script or exclude it; do not relabel the file MIT |
| Bundled GRUB stage files / `stage2` | Binary bootloader artifacts inherited from the historical distribution; exact source/build provenance not yet established | Use a pinned, source-available bootloader build with its license and corresponding-source obligations documented; keep its license distinct from the kernel |
| GMP / libgcc helpers | Historical recipes copy external archives; their exact versions/sources are not pinned here | Prefer GHC's native bignum backend to remove GMP from the guest. Audit any retained compiler-runtime helpers against the exact toolchain version and exceptions |
| `kernel/Util/FixedFont.hs`, `floppy_dir/fonts.hf`, `kernel/H/h/haskell_icon.gif`, other artwork/data | Not all original font/image/data provenance is established by the current audit | Quarantine from release approval; replace with original or verified open assets, with sources and notices |
| Historical kernel images and prebuilt user programs | Contents cannot be established from a top-level license alone; some differ from the adjacent source | Keep as external test references; ship newly built, auditable artifacts |
| Papers and historical screenshots | Research material; downloading does not establish permission to redistribute all embedded content | Keep outside the release; link to the papers rather than assuming they inherit the code license |

GPL and LGPL are open-source licenses. Their presence is not itself a failure
of the user's requirement. The reason to replace small inherited support pieces
is to reduce native code and simplify the intended permissive kernel/toolkit
distribution. Using an open-source compiler, emulator or separately distributed
bootloader does not by itself assign that tool's license to our original code.
Check the obligations of anything actually incorporated or linked into an image.

## Public repository and releases

The initial local commit `5cf4e5987cecb4eb80656a593fb3f194996ca386` imports
Gadgets. Deleting the directory in a later commit would leave it accessible in
history. Do not publish this history as the unrestricted project.

Preserve this local development/reference repository and the untouched parent
`upstream/` copies. Once the release source set is audited, create a fresh Git
repository from an explicit export allowlist, including the necessary notices,
new-code license text, source/build provenance and replacement implementation.
Verify all exported files and perform a build using only that export and its
declared open-source inputs. Publish that new history. No history rewrite or
publication has been performed by this planning step.

Before the first release, produce a file/component manifest with SPDX license
expressions where established, named custom licenses where necessary, and
explicit unresolved entries until investigated. Include dependency versions,
source hashes, license texts, binary notices and source/relinking materials
where required. The release gate is zero unresolved shipped components, not a
successful automated license-string scan.

An MIT label on new code cannot cure Gadgets' restriction. Changing to GPL
would not cure it either. The chosen route is replacement, not relicensing
someone else's work without permission.
