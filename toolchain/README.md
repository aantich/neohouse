# IA32 build environment

This toolchain runs in Docker on the host; it is not an OS dependency of the
eventual House guest. `lock.json` pins the official GHC 9.14.1 i386 bindist and
matching source hashes, Debian base image digest, and Debian package snapshot.
The normal build/run wrapper uses `linux/386` explicitly.

From the `modern/` repository:

```sh
python3 scripts/toolchain.py fetch
python3 scripts/toolchain.py fetch --source
python3 scripts/toolchain.py build
python3 scripts/toolchain.py hosted-check
python3 scripts/check_serial.py
python3 scripts/check_runtime.py
python3 scripts/check_terminal.py
```

The first two commands verify downloaded files before accepting them. The
builder verifies the bindist hash again inside the image. Debian repository
signatures and package checksums remain enabled; only snapshot expiry is
disabled. Downloads stay in ignored `.cache/`. The Docker context includes only
the toolchain definition, lock and compiler archive, excluding Gadgets and
historical boot binaries. Build-time network access is required; ordinary run
containers have networking disabled. The repository is mounted at `/work`.

Arbitrary compiler commands can be run with:

```sh
python3 scripts/toolchain.py run -- ghc --info
python3 scripts/toolchain.py run -- sh
```

Use `run -i -- sh` for an interactive terminal. The host GHC installation is
unaffected. Building the image requires several gigabytes of free Docker disk
space in addition to the host's download space.

## Separate checkpoints

The hosted check compiles a native ELF32 program with GHC and verifies live
data survives repeated garbage collections. It records the ELF header, exact
Debian/Haskell package lists, compiler versions, native shared libraries and GC
statistics under `build/hosted/`. This program runs under **Linux**, not on bare
hardware. It uses the bindist's existing libraries, including GMP; the proposed
native Haskell bignum guest build remains separate work.

The platform serial check assembles an original Multiboot entry and boots it
directly with the host's QEMU 11.1.x PC machine. It validates the boot magic and
writes a COM1 marker, then exits through QEMU's test device. Its ELF has no C
library or GHC runtime linked. Logs and a machine-readable result are written
to `build/serial/`. It **does not execute Haskell** and does not satisfy the
modern-runtime boot milestone. It provides a minimal independent starting point
for that integration. The check VM has networking disabled and exits after the
marker; it does not interact with any existing House VM.

The assembly-only check can also use the dependencies stage before GHC is
installed: build the Dockerfile with `--target dependencies` and tag it
`house-ghc:9.14.1-i386-dependencies`, then pass that tag to
`check_serial.py --build-image house-ghc:9.14.1-i386-dependencies`.

The standalone runtime check builds an original kernel entry, a restricted
GHC 9.14.1 backend and native Haskell allocation test. It verifies the source
archive and unpacks it automatically, rebuilds the C RTS objects, and retains
the bindist's 22 matching Cmm/assembly objects. It checks the final ELF and
native dependencies, boots headlessly, verifies at least 24 collections with
retained-data checks and exits QEMU. Evidence is under `build/runtime/`,
including `dependencies.json`, notices, source hashes, ELF layout and logs.

The terminal check starts the same kernel with `house.shell=1`, drives commands
through its emulated UART, checks editing and repeated GC, then halts. It writes
`build/terminal/serial.log` and `run.json`. Both checks accept `--no-build` for
debugging. None of these targets compiles Gadgets, old fonts or image assets.

For an interactive session in a normal host terminal, run:

```sh
python3 scripts/terminal.py
```

Type `help` for commands and `halt` to exit. Your host terminal supplies the
font size and Retina scaling. The current serial driver busy-polls on one CPU;
interrupt-driven idle waits and richer terminal support come later. The shell
is ASCII-only with a 256-character line limit, backspace/delete, Ctrl-U and
Ctrl-C. Arrow-key escape sequences are ignored. An isolated Escape key waits
for a following byte. No filesystem, Unix process API or network is provided.

## Sources and licensing

- [Official compiler distribution and checksum links](https://www.haskell.org/ghc/download_ghc_9_14_1.html)
- [Debian snapshot semantics and signature/expiry settings](https://snapshot.debian.org/)
- [Multiboot protocol](https://www.gnu.org/software/grub/manual/multiboot/multiboot.html)
- [QEMU direct kernel loading](https://www.qemu.org/docs/master/system/qemu-manpage.html)

The bootstrap assembly and scripts are new MIT code. The protocol constants
are implemented directly; no historical `multiboot.h` or Gadgets source is
included. The compiler, runtime and Debian packages retain their own licenses.
No compiler binaries are added to Git. The package manifest is a dependency
record, not a substitute for the release license audit.
