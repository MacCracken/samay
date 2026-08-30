# samay — Current State

> Refreshed every release. CLAUDE.md is preferences/process/procedures
> (durable); this file is **state** (volatile).

## Version

**1.1.1** — every allocation samay performs is checked, and aborts on failure
([ADR-0009](../adr/0009-oom-policy.md)). The planned scope was wrong and the
evidence corrected it: an unchecked `alloc()` does **not** produce a wild write
(offsets ≤ 112 against `mmap_min_addr` 65536, so it traps), and the 16 listed
sites already failed loudly. The real defect was **eleven allocation points that
are not raw `alloc(` tokens**, where a null escapes as struct data — two measured
producing a wrong answer before any crash: `node_capacity_new` stored a null
`accel_profiles` vec, returned an intact-looking struct, and
`schedule_pending` **placed a task on it**; `samay_uuid_v4` produced a null
`task_id` that inserted fine and crashed on the 8th-to-10th *subsequent* submit.
28 guards, plus a CI gate (verified to fail on a removed guard) because the OOM
branch is not unit-testable. `return 0` and `Err` were both rejected on
reproduced evidence — a propagated 0 silently lost a task from a valid snapshot
while reporting success, and `Ok`/`Err` allocate the 16 bytes that just failed.

Built on **1.1.0** (capped cron counts report as floors, `>=`), **1.0.4**
(threading contract, [ADR-0008](../adr/0008-threading-contract.md)) and **1.0.3**
(the P-1 sweep). 446 assertions. Toolchain 6.5.36, ai-hwaccel 2.3.19,
bayan-json 1.5.2. Both consumers (kavach 3.8.0, daimon 2.0.0) integrated and
unaffected; a third, **stiva**, was found during this release pinned to samay
1.0.1 with its `accel` feature default-ON.

## Toolchain

- **Cyrius pin**: `6.5.36` (in `cyrius.cyml [package].cyrius`)

## Source

- `src/{uuid,types,scheduler,cronexpr,cron,training,json}.cyr` + `src/lib.cyr`
  aggregation header + `src/main.cyr` demo. The seven `[lib].modules` bundle to
  2,331 lines in `dist/samay.cyr` (as `cyrius distlib` reports it); `json.cyr` is the largest module.
- **Strings are `Str` (ptr+len), not cstr** since **v0.5.0**
  ([ADR-0003](../adr/0003-str-string-representation.md)) — required because
  `#derive(Serialize)` core dumps on a cstr in a `Str`-typed field. Passing a
  bare literal where a `Str` is expected compiles and then segfaults, which is
  how the benchmark suite sat dead from v0.5.0 to v1.0.1 and how the README's
  own example was broken until v1.0.4. Wrap literals in `str_from(...)`.
- Bundle: `dist/samay.cyr` (regenerate with `cyrius distlib` after any src change).
- Rust reference: 1479 lines at `rust-old/` (frozen, do not edit).

## Tests

- `tests/samay.tcyr` — **446/446 assertions passing** (`cyrius test`), up from 296 in
  v1.0.2. Includes the v1.0.3 additions: the capacity-conservation invariant (the
  assertion whose absence let ADR-0007's defect ship), a cron differential guard pinning
  the optimised matcher to an in-test reference implementation, back-compat snapshot
  restore, wrong-typed nested-leaf rejection, and the parser features that previously had
  **zero** coverage (every `@shortcut` expansion, month/day names, DOW `7`→Sunday).
  v1.0.4 adds the `samay_init()` pre-warm guards (that the chrono month table is
  *filled*, not merely published, after each constructor). v1.1.0 adds the
  capped-due-count guards and pins `task_status_name`, which had zero callers
  anywhere but is exported public API.
- `tests/samay.bcyr` — 5 benchmarks, all green (see `docs/benchmarks.md`). Was dead
  (SIGSEGV) from v0.5.0 to v1.0.1: the `Str` migration left it passing bare cstring
  literals into `Str`-taking APIs. Now run by CI so it cannot rot silently again.
- Gates: `cyrius fmt <file> --check` clean, `cyrius lint <file>` 0 warnings and 0
  untracked deferrals, `cyrius distlib --check` in sync. **All four now run in CI** —
  note `fmt`/`lint` take a file argument, so a bare `cyrius fmt --check` gates nothing.

## Dependencies

- **ai-hwaccel** 2.3.19 (git) — `AcceleratorRequirement` `REQ_*` + lossless
  `profile_to_json`/`profile_from_json` (used by `NodeCapacity` serialization).
- **bayan** 1.5.2 (git) — `dist/bayan-json.cyr`, the focused JSON sublib, *not*
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
- Neither consumer calls samay's cron or JSON API today, so v1.0.3's restore-validation
  tightening and cron semantics changes have zero downstream blast radius. Both pin
  `tag = "1.0.1"` and should move to `1.0.3`.
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
