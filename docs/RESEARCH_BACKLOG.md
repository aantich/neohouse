# Deferred research topic

Recorded 2026-11-12. Status: **deferred**. The active project is the
[practical Haskell OS with a REPL](REPL.md). No publication, formal proof or
novelty claim is required for its initial implementation.

## Question to revisit

Can an interactive native Haskell operating environment support persistent
workspaces and live code evolution while preserving explicit authority over
hardware and other resources?

One candidate mechanism is preventing a restored workspace, old closure or
older code generation from reviving a revoked resource capability without a
fresh grant. Other possible questions concern cancellation and memory bounds
for native interactive computations, or safe migration of state between code
versions. These are hypotheses for investigation, not established novelty.

## Prior art to examine

- [Lisp machines](https://dspace.mit.edu/entities/publication/c6d82ef4-939b-43d6-afb4-ba562a28417a): integrated language and operating environments.
- [House](https://programatica.cs.pdx.edu/House/): the starting point for typed low-level Haskell interfaces.
- [Singularity](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/osr2007_rethinkingsoftwarestack.pdf): language-based isolation and typed communication.
- [EROS](https://www.usenix.org/legacy/event/usenix02/full_papers/shapiro/shapiro.pdf): persistence and capabilities.
- [Theseus](https://www.theseus-os.com/Theseus/book/misc/papers_presentations.html): safe-language OS evolution.
- [Nix](https://www.usenix.org/conference/lisa-04/nix-safe-and-policy-free-system-software-deployment): functional deployment.
- [Unison](https://github.com/unisonweb/unison): content-addressed typed code.

This is a starting reading list from the design discussion, not an exhaustive
literature review. A Haskell OS, a language REPL as its interface, capability
types or functional deployment alone should not be presented as new.

## Revisit when

The guest can accept, compile and execute Haskell interactively, keep values
alive across collections, and recover from failed or cancelled evaluation.
Then choose one precise claim, review the relevant literature in depth and
compare against a hosted baseline such as Linux plus GHCi and a restricted
resource API. Establish why OS integration matters before designing an
evaluation or selecting a publication venue.
