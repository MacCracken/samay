# samay — Current State

> Refreshed every release. CLAUDE.md is preferences/process/procedures
> (durable); this file is **state** (volatile).

## Version

**0.7.0** — security-audited restore (fail-closed input validation, ADR-0005) + deterministic scheduling (explicit tie-breaks, ADR-0004) atop full JSON `Serialize`/`Deserialize` snapshot/restore (v0.5.0) on toolchain 6.4.69, the `Str` migration, and M3 resource-aware placement. `NodeCapacity` holds real ai-hwaccel
accelerator profiles; `can_fit` delegates to `requirement_satisfied()` (ADR-0002).
Built on M2 cron correctness (0.3.0) and the 0.2.0 Rust→Cyrius parity port (Rust
reference frozen at `rust-old/`).

## Toolchain

- **Cyrius pin**: `6.4.69` (in `cyrius.cyml [package].cyrius`)

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
- `tests/samay.bcyr` — benchmarks (see `docs/benchmarks.md`).
- Gates: `cyrius fmt --check` clean, `cyrius lint` 0 warnings.

## Dependencies

- **ai-hwaccel** 2.3.15 (git) — `AcceleratorRequirement` `REQ_*` + lossless
  `profile_to_json`/`profile_from_json` (used by `NodeCapacity` serialization).
- **stdlib** — syscalls, string, alloc, str, fmt, vec, hashmap, io, fs,
  chrono, random, result, **bayan**, **math**, tagged, fnptr, freelist, atomic,
  sakshi, process, args, thread, assert, bench.
  (`bayan` = the JSON/YAML/TOML module — JSON is *not* named "json"; `math`
  supplies `f64_parse`, which `#derive(Serialize)` needs to deserialize f64.)
  Vendor with `cyrius lib sync` (not `cyrius deps`).

## Consumers

- daimon, kavach — declared consumers; do not yet reference samay (integration
  is future work). zugot has a placeholder marketplace recipe expecting a GH release.

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
- ⏭ **Consumer integration** — daimon/kavach green against `dist/samay.cyr`, carried over
  `sandhi` (AGNOS HTTP/JSON-RPC service boundary). Neither references samay yet. **The last
  open v1.0 criterion.**
- ⏭ **Audit follow-ups (Rec 3–5, non-blocking):** stable O(n log n) sort + terminal-task
  pruning (F5); cron aggregate-work budget (F8/F9); upstream stdlib hash seeding (F4).

Also queued: alloc-free cron matching (perf item deferred from M2).
