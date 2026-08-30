# samay — Current State

> Refreshed every release. CLAUDE.md is preferences/process/procedures
> (durable); this file is **state** (volatile).

## Version

**1.0.2** — maintenance release: toolchain 6.4.69→6.5.36, ai-hwaccel 2.3.15→2.3.19,
and bayan moved from the vendored stdlib monolith to the focused `bayan-json` sublib
(1.5.2) to clear 27 last-def-wins symbol collisions. Also restores the benchmark
suite, dead since the v0.5.0 `Str` migration. All v1.0 criteria remain met:
security-audited restore (ADR-0005) + deterministic scheduling (ADR-0004) + full JSON
snapshot/restore (v0.5.0) + ai-hwaccel placement + real cron. Both downstream consumers
(kavach 3.8.0, daimon 2.0.0) integrated. `NodeCapacity` holds real ai-hwaccel
accelerator profiles; `can_fit` delegates to `requirement_satisfied()` (ADR-0002).
Built on M2 cron correctness (0.3.0) and the 0.2.0 Rust→Cyrius parity port (Rust
reference frozen at `rust-old/`).

## Toolchain

- **Cyrius pin**: `6.5.36` (in `cyrius.cyml [package].cyrius`)

## Source

- `src/{uuid,types,scheduler,cronexpr,cron,training}.cyr` + `src/lib.cyr`
  aggregation header + `src/main.cyr` demo (~1000 lines Cyrius).
- **Strings are `Str` (ptr+len), not cstr** as of the unreleased M4 groundwork
  ([ADR-0003](../adr/0003-str-string-representation.md)) — required because
  `#derive(Serialize)` core dumps on a cstr in a `Str`-typed field.
- Bundle: `dist/samay.cyr` (regenerate with `cyrius distlib` after any src change).
- Rust reference: 1479 lines at `rust-old/` (frozen, do not edit).

## Tests

- `tests/samay.tcyr` — **296/296 assertions passing** (`cyrius test`). Includes
  cron regression (v0.3.0), accelerator-placement (v0.4.0), the M4 JSON roundtrip +
  snapshot/restore suite (v0.5.0), 7 M5 determinism guards incl. a self-validating
  hash-collision case (v0.6.0), and 13 security regression guards for fail-closed
  restore validation (v0.7.0).
- `tests/samay.bcyr` — benchmarks, all 5 green (see `docs/benchmarks.md`). Dead
  from v0.5.0 to v1.0.1: the `Str` migration (ADR-0003) left it passing bare
  cstring literals into `Str`-taking APIs, so it segfaulted in `cron_expr_parse`.
- Gates: `cyrius fmt <file> --check` clean, `cyrius lint <file>` 0 warnings
  (both take a file argument; `cyrius audit` runs the project-wide sweep).

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
- zugot has a placeholder marketplace recipe expecting a GH release.

## Next

See [`roadmap.md`](roadmap.md). M0–M4 done (M4 = full JSON Serialize/Deserialize, cut as
**v0.5.0**). **M5 (v0.6.0 → v1.0)** in progress; deterministic scheduling shipped in
**v0.6.0**:

- ✅ **Deterministic scheduling** (v0.6.0) — every ordering-sensitive path breaks ties on a
  unique key (`task_id`/`node_id`/entry `name`) via the shared `samay_str_lt`, instead of
  hashmap iteration order ([ADR-0004](../adr/0004-deterministic-tie-breaks.md)). Intentional
  divergence from Rust (which left ties to randomized `HashMap` order). Verified by a
  6-probe insertion-order fuzz pass (0 residual gaps across all 10 `map_values` sites) plus
  a self-validating hash-collision guard.
- ✅ **Security audit** (v0.7.0) — [`docs/audit/2026-07-21-audit.md`](../audit/2026-07-21-audit.md):
  multi-lens code review + adversarial PoC + live CVE/0day research. 10 findings, all
  snapshot-restore DoS (no Critical/High/RCE); parser boundaries and the 2024–2026
  cron/JSON CVE classes found closed. Crash-class remediated with fail-closed restore
  validation ([ADR-0005](../adr/0005-restore-input-validation.md)); 13 regression guards.
- ✅ **Consumer integration** (kavach 3.8.0) — kavach consumes `dist/samay.cyr` to size
  sandboxes from a task's `ResourceReq`. This was the last open v1.0 criterion — **all v1.0
  criteria are now met; samay is v1.0-ready.** daimon followed in its own 2.0.0 major
  migration, which surfaced and fixed the `uuid_v4`↔libro collision (v1.0.1).
- ⏭ **Audit follow-ups (Rec 3–5, non-blocking):** stable O(n log n) sort + terminal-task
  pruning (F5); cron aggregate-work budget (F8/F9); upstream stdlib hash seeding (F4).

Also queued: alloc-free cron matching (perf item deferred from M2).
