# samay — Current State

> Refreshed every release. CLAUDE.md is preferences/process/procedures
> (durable); this file is **state** (volatile).

## Version

**1.1.4** — dependencies to latest: ai-hwaccel 2.3.23 → **2.4.0**, bayan 1.5.6 →
**1.5.7**; cyrius unchanged at 6.6.6. No `src/` change. Two effects reach samay's
JSON snapshots, and tests now pin both. bayan's f64 parser is now correctly
rounded, so a near-tie double that 1.1.3 restored one ULP high now restores
exactly. Node snapshots now carry ai-hwaccel's schema-v6 `shared_memory_bytes`
for unified-memory accelerators, and older snapshots without the key still
restore. Placement is untouched: `requirement_satisfied` and
`find_satisfying_profile` are byte-identical across the bump.

Built on **1.1.3** (constructors own every `Str` they retain), **1.1.2** (the
cyrius 6.6.x `Result` value form), **1.1.1** (every allocation checked,
[ADR-0009](../adr/0009-oom-policy.md)), **1.1.0** (capped cron counts report as
floors, `>=`), **1.0.4** (threading contract,
[ADR-0008](../adr/0008-threading-contract.md)) and **1.0.3** (the P-1 sweep).
475 assertions.

## Toolchain

- **Cyrius pin**: `6.6.6` (in `cyrius.cyml [package].cyrius`)

## Source

- `src/{uuid,types,scheduler,cronexpr,cron,training,json}.cyr` + `src/lib.cyr`
  aggregation header + `src/main.cyr` demo. The seven `[lib].modules` bundle to
  2,463 lines in `dist/samay.cyr` (as `cyrius distlib` reports it); `json.cyr` is the largest module.
- **Strings are `Str` (ptr+len), not cstr** since **v0.5.0**
  ([ADR-0003](../adr/0003-str-string-representation.md)) — required because
  `#derive(Serialize)` core dumps on a cstr in a `Str`-typed field. Passing a
  bare literal where a `Str` is expected compiles and then segfaults, which is
  how the benchmark suite sat dead from v0.5.0 to v1.0.1 and how the README's
  own example was broken until v1.0.4. Wrap literals in `str_from(...)`.
- Bundle: `dist/samay.cyr` (regenerate with `cyrius distlib` after any src change).
- Rust reference: 1479 lines at `rust-old/` (frozen, do not edit).

## Tests

- `tests/samay.tcyr` — **475/475 assertions passing** (`cyrius test`), up from 296 in
  v1.0.2. Includes the v1.0.3 additions: the capacity-conservation invariant (the
  assertion whose absence let ADR-0007's defect ship), a cron differential guard pinning
  the optimised matcher to an in-test reference implementation, back-compat snapshot
  restore, wrong-typed nested-leaf rejection, and the parser features that previously had
  **zero** coverage (every `@shortcut` expansion, month/day names, DOW `7`→Sunday).
  v1.0.4 adds the `samay_init()` pre-warm guards (that the chrono month table is
  *filled*, not merely published, after each constructor). v1.1.0 adds the
  capped-due-count guards and pins `task_status_name`, which had zero callers
  anywhere but is exported public API. v1.1.3 adds `test_ownership_retained_strs`,
  which checks that each constructor owns the `Str`s it keeps. v1.1.4 adds
  `test_json_node_shared_memory`, which is mutation-proven, and a bit-level f64
  round trip at a rounding near-tie.
- `tests/samay.bcyr` — 5 benchmarks, all green (see `docs/benchmarks.md`). Was dead
  (SIGSEGV) from v0.5.0 to v1.0.1: the `Str` migration left it passing bare cstring
  literals into `Str`-taking APIs. Now run by CI so it cannot rot silently again.
- Gates: `cyrius fmt <file> --check` clean, `cyrius lint <file>` 0 warnings and 0
  untracked deferrals, `cyrius distlib --check` in sync. **All four now run in CI** —
  note `fmt`/`lint` take a file argument, so a bare `cyrius fmt --check` gates nothing.

## Dependencies

- **ai-hwaccel** 2.4.0 (git) — `AcceleratorRequirement` `REQ_*` + lossless
  `profile_to_json`/`profile_from_json` (used by `NodeCapacity` serialization).
  Since 2.3.28 (schema v6) a profile carries `shared_memory_bytes`, which node
  snapshots pass through.
- **bayan** 1.5.7 (git) — `dist/bayan-json.cyr`, the focused JSON sublib, *not*
  the 641 KB monolith. bayan left the stdlib snapshot in 1.5.2; taking the
  monolith while ai-hwaccel pulls the sublib vendors both files and collides on
  27 JSON symbols under last-def-wins. The sublib omits the short `json_v_*`
  aliases, so `src/json.cyr` calls the fully-qualified `bayan_json_v_*` spelling
  — which resolves under either bayan packaging, so consumers of
  `dist/samay.cyr` are unconstrained in which they vendor.
- **stdlib** — syscalls, string, alloc, str, fmt, vec, hashmap, io, fs,
  chrono, random, result, **math**, tagged, fnptr, freelist, atomic,
  sakshi, process, args, thread, assert, bench.
  (`math` supplies `f64_parse`, which `#derive(Serialize)` needs to deserialize
  f64.) Vendor with `cyrius lib sync` (not `cyrius deps`).

## Consumers

- **kavach 3.8.0** — integrated: sizes sandboxes from a samay `ResourceReq`
  (`kavach/src/samay_bridge.cyr`), 436 assertions green against `dist/samay.cyr`.
- **daimon 2.0.0** — integrated: deleted its duplicated `scheduler.cyr`/`cron.cyr` and
  consumes samay as the single scheduler source of truth (api_sched rewired; 215 assertions).
  The migration surfaced + fixed the `uuid_v4`↔libro collision (samay 1.0.1).
- Current pins, as of 1.1.4: kavach 3.12.5 → samay `1.1.2`, daimon 2.4.3 → `1.1.3`,
  stiva 3.0.20 → `1.1.2`. kavach and daimon also set `path = "../samay"`, so local
  builds of them use this checkout, not the tag. The only samay JSON call among
  them is daimon's `SchedulingDecision_to_json`, which is emit-only. None of them
  restores a samay snapshot.
- zugot's marketplace recipe is stale: it still describes samay as a Rust crate at v0.1.0
  (cargo build, `Cargo.toml`, `runtime = "rust-crate"`). Needs a rewrite for Cyrius.

## Next

See [`roadmap.md`](roadmap.md) — it carries the full backlog with version pins and
is the single source for forward work. In brief: **1.1.0** shipped the one
deferral of three that survived verification (capped counts report as floors);
**1.1.1** is checked `alloc()`; **1.2.0**
splits `node_preference`; **1.3.0** is F5 (stable sort + terminal-task pruning),
the one item with real risk; **1.4.0** is the F8/F9 cron work budget; **1.5.0**
is the write-side JSON codec. Everything else is trigger-gated and deliberately
unpinned.

**Concurrency — audited in v1.0.4, see [ADR-0008](../adr/0008-threading-contract.md).**
Retired as an unknown; now a stated contract with measured backing. Open items from it:
the `lib/chrono.cyr` publish-before-fill ordering is an **upstream ask** filed against
cyrius (samay only closes the window from outside); `lib/sakshi.cyr`'s unsynchronised ring
indices and span depth can interleave log output under concurrent use (observability
only, and outside the contract); and an opt-in debug mode that *detects* concurrent entry
was considered and not built — worth revisiting if any consumer adopts a threaded shape.

**Not covered by any audit to date — treat as unretired risk:**
- **The accelerator placement path.** Every `can_fit`/`_best_fit_node` measurement used
  `REQ_NONE`, which short-circuits before touching profiles. ai-hwaccel's
  `find_satisfying_profile` has never been benchmarked inside the placement loop — the
  numbers understate exactly the workload the domain principles are about.
- **Test correctness, as distinct from coverage.** v1.0.3 found one test that asserted a
  defect and stated the wrong rule in its own comment. Nothing establishes it was the only
  one.
- **Non-x86_64 targets.** No aarch64 or agnos measurements; the new NaN/Inf handling is
  the part most likely to differ.
- **Fuzzing.** All restore probing has been hand-crafted against specific hypotheses. A
  structure-aware fuzzer over `task_scheduler_from_json_str` is the obvious next
  instrument, and v1.0.3's validation is what it should be pointed at.
