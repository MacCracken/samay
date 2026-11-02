# samay — Claude Code Instructions

> **Core rule**: this file is **preferences, process, and procedures** —
> durable rules that change rarely. Volatile state (current version,
> module line counts, test counts, consumers) lives in
> [`docs/development/state.md`](docs/development/state.md).
> Do not inline state here.

## Project Identity

**samay** — the AGNOS task scheduler, written in Cyrius. Ported from Rust (see History).

- **License**: GPL-3.0-only
- **Language**: Cyrius (toolchain pinned in `cyrius.cyml [package].cyrius`)
- **Version**: `VERSION` at the project root is the source of truth — do not inline the number here
- **Standards**: [First-Party Standards](https://github.com/MacCracken/agnosticos/blob/main/docs/development/applications/first-party-standards.md) · [First-Party Documentation](https://github.com/MacCracken/agnosticos/blob/main/docs/development/applications/first-party-documentation.md)

## Goal

samay owns *what runs where and when* in the AGNOS stack: a deterministic task queue with real cron
schedules and resource- and accelerator-aware placement. It decides and never executes: kavach runs
the work.

## History

The original Rust was the parity oracle through 1.1.5, and was removed after an audit found
everything in it ported or recorded
([`docs/development/rust-old-removal.md`](docs/development/rust-old-removal.md)). To read it:
`git show 1.1.5:rust-old/src/lib.rs`. Citations of the form `rust-old/src/lib.rs:N`, in
ADRs, comments and tests, refer to that tag.

## Quick Start

```sh
cyrius deps                              # resolve dependencies
cyrius build src/main.cyr build/samay    # compile
cyrius test                              # run tests/*.tcyr
```

## Key Principles

- **Divergence needs an ADR** — what the Rust oracle did is recorded in the ADRs and
  `docs/development/rust-old-removal.md`; a change that departs from a recorded behaviour
  needs a new ADR. Matching the oracle was the default, never proof of correctness.
- **Correctness over cleverness** — a silent change in behaviour is a bug, however clean the code
- Test after every change, not after the feature is "done"
- ONE change at a time — never bundle unrelated changes
- Build with `cyrius build`, not by calling the compiler directly — the manifest auto-resolves deps
- Source files only need project includes — stdlib auto-resolves from `cyrius.cyml`
- `var buf[N]` = N **bytes**, not N entries
- **`alloc()` returns 0 on OOM — check it, then `panic`.** Guard every allocation samay makes whose result it *returns* or *stores into one of its own structs* (raw `alloc`, plus `str_new`/`str_from*`/`str_builder_build`/`vec_new`/`map_new_str`), and abort: `panic("samay: out of memory in <fn>")`. Never propagate an OOM as a `0` return or an `Err` — both already have meanings (ADR-0005 "rejected", "no preemption candidate", a malformed expression), so a host out of memory would read as bad input. Results consumed by the very next statement, and values handed to a dep's constructor, are left to trap. A null must never leave the function that created it. See [ADR-0009](docs/adr/0009-oom-policy.md); CI gates it.

## Domain Principles (samay-specific)

- **Deterministic scheduling** — same schedule + same time ⇒ same decisions. Sort explicitly; never rely on hashmap iteration order for ordering-sensitive output.
- **Resource-aware placement via ai-hwaccel** — never schedule a GPU/accelerator task without checking availability, which means free, not just present ([ADR-0013](docs/adr/0013-accelerators-are-reserved.md)). Accelerator requirement types come from ai-hwaccel (`REQ_*`).
- **Missed schedules handled explicitly** — never silently skip a due cron entry; follow the configured catch-up-vs-skip policy and log it (`sakshi`).
- **Cron expressions validated at parse time**, not at execution time.
- **Never claim a performance win without benchmark numbers** (`cyrius bench` → `docs/benchmarks.md`).
- **Every public type stays serializable** — keep the `#derive`/`*_to_json` surface intact, and give every new field a round-trip assertion of its own.
- **Symbol hygiene** — scan new public symbols against the vendored deps (esp. ai-hwaccel) before release; last-def-wins collisions are silent bugs.

## Cleanliness gate (run before claiming done)

**`fmt` and `lint` take a FILE argument**, so loop:

```sh
for f in src/*.cyr tests/*.tcyr tests/*.bcyr tests/*.fcyr; do cyrius fmt "$f" --check; done
for f in src/*.cyr; do cyrius lint "$f"; done   # 0 warnings AND 0 untracked deferrals
cyrius test                                     # all pass
cyrius test --bounds tests/samay.tcyr           # all pass, bounds-checked
cyrius test --aarch64 tests/samay.tcyr          # all pass, under qemu
cyrius fuzz tests/samay.fcyr                    # fuzz: ok
cyrius coverage --min 100                       # every public fn named in tests/*.tcyr
cyrius bench tests/samay.bcyr                   # every row reports
cyrius distlib                                  # regenerate dist/samay.cyr
cyrius distlib --check                          # exits 1 if the bundle is stale
```

`cyrius coverage` counts a name that appears anywhere in the tests, including a comment or
a longer name that contains it. CI adds a stricter check: every public fn in
`[lib].modules` must be *called* (`name(` outside a comment) by a `.tcyr`. A new public
function ships with a test that calls it.

Then: compile and run the README example, and scan new public symbols against the vendored
deps for collisions. CI does not cover every line above yet; the roadmap says which.

## Rules (Hard Constraints)

- **Do not commit or push** — the user handles all git operations
- **Never use `gh` CLI** — use `curl` to the GitHub API if needed
- Do not skip tests before claiming changes work
- Do not modify `lib/` files (vendored stdlib / dep symlinks)
- Do not hardcode toolchain versions in CI YAML — `cyrius = "X.Y.Z"` in `cyrius.cyml` is the source of truth

## Documentation

- [`docs/adr/`](docs/adr/) — Architecture Decision Records (*why X over Y?*)
- [`docs/architecture/`](docs/architecture/) — Non-obvious constraints
- [`docs/guides/`](docs/guides/) — Task-oriented how-tos
- [`docs/benchmarks.md`](docs/benchmarks.md) — Measured numbers
- [`docs/audit/`](docs/audit/) — Audit reports
- [`docs/development/state.md`](docs/development/state.md) — Live state
- [`docs/development/roadmap.md`](docs/development/roadmap.md) — Forward work: every item has a version
