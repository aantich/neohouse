# Practical Haskell OS with a REPL

Active direction, recorded 2026-11-12. Build a usable character-based Haskell
workspace inside House. Publication and novelty investigation are a
[separate deferred topic](RESEARCH_BACKLOG.md); they do not set the acceptance
criteria for this work.

## User experience

The terminal accepts real Haskell expressions, definitions and effectful OS
actions. Bindings remain available for subsequent input. Resource handles are
opaque Haskell values; inspecting a resource produces ordinary immutable data.
Effects are explicit in types and use a small OS API.

Illustrative interaction, **not an implemented API**:

```haskell
house> let twice x = x + x
house> twice (21 :: Int)
42
house> :type twice
twice :: Num a => a -> a
house> stats <- memoryInfo
house> heapBytes stats
5242880
house> writeLine console "hello from House"
hello from House
```

`memoryInfo :: OS MemoryInfo` returns a snapshot. `console :: Console` is a
granted capability, and `writeLine :: Console -> String -> OS ()` performs an
effect. These signatures describe the intended interface, not a sandbox that
already exists. The current kernel executes trusted code in a shared address
space; a newtype around `IO` does not establish isolation. Raw hardware access
and unsafe operations belong behind the platform boundary.

## Scope of the first REPL

- Real GHC parsing and type checking, with native machine-code generation.
- Expressions, function/value definitions, `:type`, and a documented initial
  import set. Add multiline input once single-line submission works.
- Session bindings, printed results and compiler diagnostics. A failed compile
  leaves the previous session usable.
- A small Haskell interface to console output and memory/GC diagnostics.
  Ordinary functions and immutable values are the default way to combine data.
- Compile on the host initially, execute compiled Haskell inside the guest.
  The compiler location must be visible in instructions and diagnostics.

This is a GHCi-like interface; embedding GHCi itself is not a prerequisite.
The existing runtime disables GHC's bytecode interpreter and dynamic loader.
Neither accepting command strings nor evaluating input entirely on Linux
would establish this REPL milestone. A small arithmetic language would not
establish Haskell support either.

## Implementation sequence

| Step | Deliverable | Completion evidence |
| --- | --- | --- |
| 1. Ordinary Haskell support | Extend the freestanding library/runtime boundary enough for `Int`, lists, strings, basic classes, rendering and controlled exception reporting. Configure native Haskell bignums before exposing `Integer`. Keep unsupported imports explicit. | A statically linked guest program runs representative expressions, prints values and handles an evaluation error, then continues and passes the existing GC checks. |
| 2. Native compilation contract | A host compiler driver accepts source against a fixed guest API and emits native IA32 code with a recorded compiler, ABI, imports and entry point. Use the pinned GHC toolchain. | A newly submitted module builds against the guest API and executes in a linked checkpoint image. Rebuilding/rebooting this checkpoint is an intermediate test, not a live REPL. |
| 3. Live native loading | Add a separate host/guest compiler channel and a narrow native-code loader. Resolve supported relocations/imports, initialize module roots/CAFs correctly, and retain loaded code for the entire session initially. | Enter a new expression after boot; its compiled code runs in that same guest without rebuilding or restarting the kernel. Values and loaded code survive GC. |
| 4. Stateful terminal session | Track bindings/imports, display inferred types/results, report errors and invoke the small `OS` API. Keep the source environment consistent with successfully installed modules. | Define a function, use it in later inputs, inspect its type, read a memory snapshot and print to the console. A type error preserves earlier bindings. |
| 5. Recoverable execution | Add timer-driven interruption and the runtime support needed to stop an evaluation, release its session roots and return to the prompt. Define what survives an exception or cancellation. | An exception and an infinite computation can each be interrupted without losing the prompt or corrupting retained values. Ctrl-C currently only cancels line editing; it does not meet this criterion. |

The immediate milestone is step 1 plus a small step-2 compilation checkpoint.
This tests the guest library and native execution contract before building a
code loader. Port only the runtime/library features these examples need,
while moving toward a reproducible freestanding source build rather than
growing the temporary ABI indefinitely.

For the first session implementation, immutable bindings and no native-code
unloading simplify lifetime management. Record limits on input, retained code
and heap use; report exhaustion explicitly. Binding redefinition, reclamation
of individual compiled modules and simultaneous users can follow. Compiler
errors must not install a partial session update. Effectful execution can have
performed I/O before failing; it is not an automatic transaction.

## Boundaries and later work

Keep the compiler on the host until the guest can support a compiler itself.
Boot/runtime operation still needs the GHC C/Cmm/assembly RTS and a narrow
CPU/platform boundary; the REPL does not imply a new C dependency. Audit the
actual native imports of every guest artifact. Use the native bignum backend
to avoid adding GMP to the guest. See [runtime constraints](RTS_PORT.md) and
the [license inventory](LICENSE_AUDIT.md).

The first target remains a trusted single-user development system on IA32
QEMU. Memory protection, enforceable resource limits and untrusted-code
execution require additional mechanisms; typed API design alone does not
provide them.

Deferred: GUI, POSIX compatibility, Nix-like package/deployment management,
persistent sessions, distributed compilation, self-hosted GHC, a 64-bit port
and publication-oriented experiments. Add storage/network/device APIs when
there is a practical use for them, rather than porting every historical driver
before the first REPL works.
