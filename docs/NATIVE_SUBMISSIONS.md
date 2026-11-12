# Native Haskell submission checkpoint

This is the build-time bridge toward the [live REPL](REPL.md). A trusted
ordinary Haskell module is compiled by the pinned GHC on the host, linked
into a standalone kernel and executed inside QEMU. Each submission incrementally
builds an image and reboots the guest. There is no live code loader or persistent
REPL session yet, and the Haskell source is currently supplied from a host file.

From this repository:

```sh
python3 scripts/submission.py examples/repl/HelloHouse.hs
```

Use `--build-only` to produce `build/submission/kernel.elf` without booting.
The first library source build is substantially slower than a cached build.
Unchanged RTS objects, the RTS archive, bootstrap C/assembly objects and Haskell
modules are reused. Staging identical submission source preserves its timestamp.
GHC recompiles changed modules and affected dependents; a changed module requires
relinking the static kernel. Repeating an unchanged submission reuses the linked
image as well. The ELF dependency audit still runs on cached images. Switching
between the terminal and submission configurations can recompile modules because
their compiler options differ.

Docker runs the IA32 compiler; native QEMU runs the freestanding kernel.
The compiler's hosted dependencies are separate from guest dependencies.
The batch runner has a 30-second VM watchdog. A timeout stops the whole VM;
it does not establish in-guest cancellation.

## Module contract

The file must declare `module HouseSubmission (submission) where` and export
`submission :: OS ()`. For example:

```haskell
module HouseSubmission (submission) where
import House

twice :: Num a => a -> a
twice x = x + x

submission :: OS ()
submission = do
    printValue console (twice (21 :: Int))
    snapshot <- memoryInfo
    printValue console snapshot
```

The compiler parses and type-checks this as Haskell, then emits IA32 native
code. `SubmissionRunner` invokes the compiled action after the boot checks.
Compile/link failure prevents the runner from booting an old image. The ELF
audit must pass before the submission artifact is copied to its output path.
The source hash, guest API interface hashes, actual link inputs, image hash,
UART output and exit status are recorded under ignored `build/submission/`.

## Initial OS interface

`House` exports an opaque `OS a`, opaque `Console` and an initial console
capability. The kernel's runner uses the constructor in `House.Internal.OS`.

```haskell
console    :: Console
writeLine  :: Console -> String -> OS ()
printValue :: Show a => Console -> a -> OS ()
memoryInfo :: OS MemoryInfo
collect    :: OS ()
evaluate   :: a -> OS a
attempt    :: OS a -> OS (Either String a)
```

`MemoryInfo` is an immutable record with `heapBytes` (megablocks currently
acquired by the RTS), `usableBytes` (physical memory admitted by the platform
allocator), and `collections`. The first field is not a live-object count,
and physical memory admitted by the allocator is not the configured RTS heap
limit. Taking a snapshot does not reserve memory or update it later.

`evaluate` forces weak head normal form, matching `Control.Exception.evaluate`.
`attempt` catches Haskell exceptions raised while its action runs; a lazy
returned value can still throw when demanded later. To catch a rendering
failure, render inside the protected action. Effects performed before failure
remain performed. Neither function provides a timeout or interrupts a loop.

The guest supports a growing pure Prelude/library subset. The console remains
ASCII serial. Unix file/handle APIs, arbitrary native FFI libraries, general
floating-point math and Template Haskell execution are outside this contract.
An unsupported native import must fail the link/audit rather than pull Linux
services into the guest. The program is trusted kernel code: restricting the
public module exports is not memory protection or an enforceable import
sandbox.

## Runtime/library build

`rebuild-libraries.py` builds the needed `ghc-internal` dependency graph from
the matching verified GHC source, using the package's Haskell2010 defaults,
`BIGNUM_NATIVE` and separately collectable sections. It generates matching
`.hsc` modules using the pinned configuration headers. The primitive module
has an empty on-disk placeholder interface; its real primitive interface is
supplied by the compiler, as in GHC's own interface loader.

The staged platform changes disable file hashing and IPE backtraces explicitly,
select Haskell UTF-8 for foreign strings with no iconv fallback, and access the
kernel errno location with numeric Haskell diagnostics. The original source
tree remains unchanged. A small existing public-domain MD5 C helper supports
type fingerprints; no native bignum or external crypto library is added.

A local package database selects these guest interfaces and code only for
kernel compilation. It does not replace the compiler's own installed runtime
or its Linux libraries. Compiling parts of the Unix-facing library graph is
not a port of those services: final linking discards unused sections, and the
audit checks the actual ELF. This is still a partial freestanding port using
the matching bindist's configuration headers and native RTS objects, not a
complete new-target GHC distribution build.

## Checks

```sh
python3 scripts/check_runtime.py
python3 scripts/check_submission.py
python3 scripts/check_runtime.py       # restore/check the default image
python3 scripts/check_terminal.py --no-build
python3 scripts/check_serial.py
python3 scripts/toolchain.py run -- python3 scripts/check_native_cache.py
python3 scripts/toolchain.py run -- python3 scripts/check_elf_audit.py
```

The runtime checks exercise functions, a list pipeline, signed/derived
printing, native arbitrary-precision arithmetic, decimal rendering and
retention across major GC. Opaque inputs prevent compile-time evaluation of
the arithmetic test cases. Exception checks include Int/Integer division by
zero, `error`, an empty-list operation and failure while rendering a lazy
value, followed by successful evaluation on the same thread. It also checks
typed exception matching, allocator failure/errno, UTF-8 string conversion and
rejection of unavailable codecs, file hashing and IPE configuration.

The submission check boots the example module and checks its results and OS
effects, repeats it while checking that every object/archive/image and staged
source retain their timestamps and hashes, then edits the module and boots its
changed output while checking reuse of unrelated objects. Finally it asks GHC
to compile an ill-typed module. That compile must fail
without booting or replacing the existing runtime image. Results are recorded
under `build/submission-tests/`.

Next: a compiler transport, live native loading and session bindings. Timer
interrupts and cancellation remain necessary before an infinite evaluation
can safely return control to the prompt.
