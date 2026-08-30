# samay — Current State

> Refreshed every release. CLAUDE.md is preferences/process/procedures
> (durable); this file is **state** (volatile).

## Version

**1.0.4** — concurrency audit; retires the risk v1.0.3 left explicitly open.
**samay is not thread-safe, by contract** ([ADR-0008](../adr/0008-threading-contract.md)):
one scheduler per thread, serialise externally. Deliberately no internal lock — the query
functions return raw pointers into scheduler-owned structs, so a mutex would look safe,
invite the assumption, and still corrupt. Measured under 8 threads sharing one scheduler:
73% of node reservations lost (towards **over-admission**), and the tasks hashmap's size
field left disagreeing with its contents. One race IS fixed, because it breaks callers who
honour the contract: `lib/chrono.cyr` publishes its month table before filling it, so
racing threads — even with separate schedulers — could evaluate cron against the wrong
date (1/400 through samay's public API). New additive `samay_init()` closes it from
outside; both constructors call it. Verified safe by measurement: the allocator (0
overlapping blocks in 80,000), `samay_uuid_v4` (0 duplicates in 200,000), and v1.0.3's
reconciliation. 416 assertions. Toolchain 6.5.36, ai-hwaccel 2.3.19, bayan-json 1.5.2.
Both consumers (kavach 3.8.0, daimon 2.0.0) integrated and unaffected — neither is
multi-threaded. `NodeCapacity` holds real
## Toolchain

- **Cyrius pin**: `6.5.36` (in `cyrius.cyml [package].cyrius`)

## Source

- `src/{uuid,types,scheduler,cronexpr,cron,training,json}.cyr` + `src/lib.cyr`
  aggregation header + `src/main.cyr` demo. The seven `[lib].modules` bundle to
  2,331 lines in `dist/samay.cyr` (as `cyrius distlib` reports it); `json.cyr` is the largest module.
- **Strings are `Str` (ptr+len), not cstr** as of the unreleased M4 groundwork
  ([ADR-0003](../adr/0003-str-string-representation.md)) — required because
  `#derive(Serialize)` core dumps on a cstr in a `Str`-typed field.
- Bundle: `dist/samay.cyr` (regenerate with `cyrius distlib` after any src change).
- Rust reference: 1479 lines at `rust-old/` (frozen, do not edit).

## Tests

- `tests/samay.tcyr` — **416/416 assertions passing** (`cyrius test`), up from 296 in
  v1.0.2. Includes the v1.0.3 additions: the capacity-conservation invariant (the
  assertion whose absence let ADR-0007's defect ship), a cron differential guard pinning
  the optimised matcher to an in-test reference implementation, back-compat snapshot
  restore, wrong-typed nested-leaf rejection, and the parser features that previously had
  **zero** coverage (every `@shortcut` expansion, month/day names, DOW `7`→Sunday).
  v1.0.4 adds the `samay_init()` pre-warm guards (that the chrono month table is
  *filled*, not merely published, after each constructor).
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

See [`roadmap.md`](roadmap.md). M0–M5 complete; v1.0 shipped, and v1.0.3 closes the P-1
sweep. Open items are tracked under "Post-1.0 tracked follow-ups" in the roadmap:

- ⏭ **F5** — stable O(n log n) sort + terminal-task pruning. Four insertion sorts remain,
  ~85× slower than merge sort at n=8000. Held out of v1.0.3 deliberately: ADR-0004's
  determinism guarantee rides on those comparators and the release was already cron- and
  JSON-heavy. Consolidate the four into one shared comparator first.
- ⏭ **F8/F9** — cron cross-entry aggregate work budget. v1.0.3's prefilter cut the cost
  ~12× and removed the heap growth, so this is now a policy question (any exhaustion rule
  collides with "missed schedules are never silently skipped"), not an availability one.
- ⏭ **F4** — upstream stdlib hash seeding; in `lib/`, off-limits to samay. v1.0.3's NaN
  guard removed the last path by which bucket order could reach a documented-deterministic
  decision.
- ⏭ **Write-side codec** — `_rr_node`/`_ce_node` still serialize-then-reparse (~68% of
  `scheduled_task_to_jsonv`). Held back so v1.0.3's emitted bytes are provably unchanged.
- ⏭ **`node_preference` split** into user-preference vs current-assignment
  ([ADR-0007](../adr/0007-reservation-lifecycle.md) Consequences). Needs a minor release.

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
