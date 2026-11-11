# Independent Haskell GUI replacement

Decision recorded 2026-11-11: replace Gadgets with an independently implemented
Haskell toolkit. The release must permit use, modification, redistribution and
commercial use. Target native CPU code, with no new C GUI dependency.

## License and provenance

Use MIT for new original toolkit code and examples. Preserve the applicable
BSD-style and hOp notices on reused House code. This permits a mixed-license,
fully open-source distribution; it does not make the whole inherited system
MIT. See [the license audit](LICENSE_AUDIT.md).

Do not copy, translate, mechanically modernize or derive the replacement from
Gadgets source. Do not reuse its demos, images, fonts or adapter implementation.
Write the implementation from the functional requirements below and public
hardware/protocol specifications. We have already inspected some Gadgets
integration code, so this work must not be described as a formally isolated
clean-room process. Record the provenance of each reused module and asset.

Keep the historical source in the parent workspace as research material. The
current local Git import contains it; a later deletion commit is insufficient
for the publication requirement. Seed a fresh public history from an audited
export when the source set is ready. Do not automatically bundle the old PDFs,
screenshots, floppy images or archived source into the new release.

## Architecture

Proposed module names describe responsibilities, not an already implemented API:

| Layer | Responsibility | Native dependencies |
| --- | --- | --- |
| `House.UI.Core` | Geometry, logical coordinates, layout, state transitions, hit testing, focus and input events | None beyond the Haskell runtime |
| `House.UI.Render` | Clipped fills, lines, bitmap text, cursor and damaged-region drawing into a surface | Haskell memory access; no C graphics toolkit |
| `House.UI.Widgets` | Labels, buttons, text input, scrolling and a terminal view | Core and renderer |
| `House.UI.Desktop` | Window placement, stacking, focus, dragging, resizing and repaint scheduling | Core, widgets and surfaces |
| `House.UI.Backend.Framebuffer` | Validated framebuffer description and presentation; input arrives through House drivers | Existing boot/hardware boundary, audited separately |
| `House.UI.App` | An application-facing view/event API, independent of physical video memory | Initially in-kernel; a protected-process transport is a later milestone |

The pure UI core produces drawing commands and effects from application state
and events. The platform layer owns buffers and performs effects. Separate
layout and rendering from PS/2 input and VBE setup so that the portable parts
can be developed and tested on the host before the modern kernel is ready.

The first renderer is software drawing in Haskell. Reuse independently audited,
permissively licensed House graphics/input mechanisms where appropriate;
`Kernel.Driver.IA32.VbeGraphics` and the PS/2 drivers are candidates, not a
completed provenance approval. The new UI must not import `Gadgets`, `Demo`,
`HOpBadget`, or any other module from the restricted subtree.

Avoid introducing SDL, Cairo, GTK, Qt, a browser engine or a C font rasterizer
into the guest. A future acceleration backend should fit behind the surface
interface without changing application layout and event handling.

## Initial feature set

1. A framebuffer surface with width, height, pitch, pixel format and accessible
   byte length. Check clipping, offset arithmetic and buffer bounds before
   writes; do not assume pitch equals width times bytes per pixel.
2. Solid rectangles, simple lines, bitmap text and a software pointer. Start
   with an original small bitmap font or a font with verified redistribution
   terms; preserve its source, license and regeneration recipe.
3. Pointer and keyboard events, key-up/down state, focus, pointer capture during
   dragging, and bounded input queues. Define overflow behavior explicitly.
4. Basic windows with title bars, stacking, dragging and resizing; labels,
   buttons, a text field and a scrolling terminal. Keep the shell's command
   handling separate from its presentation.
5. Fresh counter and calculator examples plus a graphical shell. The target is
   useful equivalent functionality, not Gadgets source or API compatibility.

Use a single UI event loop initially; worker threads communicate through
messages rather than drawing into shared screen memory. Track damaged regions
and redraw them on demand. Prefer an opaque software renderer first; advanced
compositing, animation and GPU drivers come after a stable desktop.

## High-resolution displays

Represent layout in logical units and apply an explicit display scale at the
rendering boundary. Provide at least 1x and 2x operation in the first release;
generate or supply text glyphs at the intended size. Host QEMU zoom remains a
convenience, not the implementation of guest display scaling.

Remove the inherited assumptions that a framebuffer is tightly packed or fits
within the fixed 32 MiB VBE mapping. For example, 5120 by 2880 at four bytes per
pixel needs 58,982,400 bytes (56.25 MiB) for one tightly packed buffer, before
pitch padding or a back buffer. Mapping limits, reserved memory and overflow
checks must match the selected video mode. QEMU's emulated video hardware must
also expose that mode. A later 64-bit boot target and modern display backend
will be assessed separately; the initial IA32 milestone does not promise 5K.

Full Unicode shaping, accessibility infrastructure, GPU acceleration, multiple
monitors and general application isolation are later features, with interfaces
that leave room for them. The initial bitmap font must be described honestly
as a limited character set.

## Implementation order and acceptance

| Milestone | Deliverable | Completion evidence |
| --- | --- | --- |
| 0. Establish provenance | File/license inventory; restricted code and assets identified; publication procedure recorded | No unresolved component is approved for release; original references preserved outside the release set |
| 1. Portable UI core | Geometry, layout, events, basic widgets and a memory-backed renderer | Host tests for clipping/bounds, focus/drag behavior and scaling; deterministic rendered examples |
| 2. Modern runtime boot | Native Haskell startup, diagnostic output, allocation and repeated garbage collection | A source-built kernel using the pinned modern compiler boots in QEMU and passes the allocation/GC checkpoint |
| 3. First new desktop | Framebuffer backend, input, windows, terminal, counter and calculator | QEMU input script and screenshots demonstrate interaction, resizing and 1x/2x layouts; no Gadgets module is compiled or linked |
| 4. Public release | Audited sources and clean Git history, notices, asset sources, dependency manifest and reproducible instructions | Build from the public export without access to the historical workspace; inspect source archive and linked components |
| 5. Application platform | Stable app API, display service and protected-process transport | Separate applications communicate through bounded messages/surfaces without access to arbitrary kernel/framebuffer memory |

Portable UI work can proceed while the runtime port is underway. Integration
into a modern boot waits for the allocation/GC checkpoint; a hosted preview is
not evidence that the standalone kernel works.

## Release requirements

- Enumerate shipped source files, generated data, binaries, fonts and images
  with origin, version/hash and license. Record linked libraries separately
  from build-only tools and separately distributed boot components.
- Preserve source and binary attribution notices and provide the required
  license texts. Review copyleft obligations for the actual linked artifact.
- Publish the preferred source and regeneration recipes for generated assets.
- Exclude academic-only or unknown-license material from the release and its
  public history. A string search alone cannot establish provenance.
- Verify that the exported repository builds without fetching Gadgets or
  reading a private historical checkout.
