# samay — Roadmap

> Milestone plan through v1.0. State lives in [`state.md`](state.md);
> this file is the sequencing — what ships, in what order, against
> what dependency gates.

## v1.0 criteria

- [x] Rust → Cyrius surface parity verified against `rust-old/` (v0.2.0)
- [x] Test coverage mirrors the Rust suite + feature tests (237/237 assertions)
- [x] Benchmarks captured (`docs/benchmarks.md`)
- [x] Real cron-expression parsing + parse-time validation (v0.3.0)
- [x] Missed-schedule policy (catch-up vs skip), explicit + logged (v0.3.0)
- [x] Resource-aware placement wired through ai-hwaccel `requirement_satisfied()`/profiles (v0.4.0)
- [x] JSON `Serialize` + `Deserialize` with roundtrip tests for every public type (leaf types via `#derive(Serialize)`; container types via bayan `json_v` in `src/json.cyr`; 6.4.69 Grisu2 f64 is bit-exact)
- [x] Determinism guarantees (same schedule + same time → same decisions), tested — explicit tie-breaks on unique keys ([ADR-0004](../adr/0004-deterministic-tie-breaks.md))
- [ ] At least one downstream consumer (daimon or kavach) green against `dist/samay.cyr`
- [ ] CHANGELOG complete from v0.2.0 onward
- [ ] Security audit pass (`docs/audit/YYYY-MM-DD-audit.md`)

## Milestones

### M0 — Port scaffold (v0.1.0 tree) — ✅ 2026-07-18
`cyrius port` scaffold; Rust moved to `rust-old/`; doc tree established.

### M1 — Surface parity (v0.2.0) — ✅ 2026-07-18
All Rust types/functions ported across `src/*.cyr`; 108/108 assertions;
`dist/samay.cyr` bundle; lint/fmt clean; demo binary runs.

### M2 — Cron correctness (v0.3.0) — ✅ 2026-07-18
Real 5-field cron expressions (`src/cronexpr.cyr`) with parse-time validation,
Vixie DOM/DOW rule, names + `@shortcuts`; missed-schedule catch-up/skip policy,
always logged. Hardened via a 4-lens adversarial review (7 findings fixed).
Follow-up perf item: alloc-free `cron_expr_matches` (currently ~298 ns/call via
`epoch_to_date`).

### M3 — Resource-aware placement v2 (v0.4.0) — ✅ 2026-07-18
`NodeCapacity` holds real ai-hwaccel accelerator profiles; `can_fit` places via
`find_satisfying_profile()`/`requirement_satisfied()` — an accelerator task never
fits a node without a matching profile (fixes the Rust port's `_ => true` stub;
[ADR-0002](../adr/0002-ai-hwaccel-profile-placement.md)). Focused adversarial
review: 0 findings. Utilization/scoring refinements deferred.

### M4 — Serialization + persistence (v0.5.0) — ✅ 2026-07-21
Full JSON `Serialize`/`Deserialize` for every public type with roundtrip tests
(closes the `Deserialize` gap deferred in ADR-0001). Leaf types (all-scalar/all-`Str`)
via `#derive(Serialize)`; container types (pointer/vec/map fields) via bayan's `json_v`
value-tree API in `src/json.cyr`. `TaskScheduler_to_json_str`/`_from_json_str` is the
scheduler+cron snapshot/restore: `snapshot → restore → re-serialize` is byte-identical,
maps serialize as key-sorted arrays (deterministic), and a restored node still satisfies
the same ai-hwaccel placement (2.3.15 lossless profile codec). Hardened by a 6-lens
adversarial verification pass (escaping, determinism-under-reorder, empty collections,
malformed input, behavior parity, boundaries): 0 codec bugs, 5 regression guards added.
Bit-exact f64 depends on toolchain ≥6.4.69 (Grisu2 JSON codec).

### M5 — Determinism + hardening (v0.6.0 → v1.0) — in progress
- [x] Deterministic scheduling order — stable tie-breaks on unique keys, independent of
  hashmap iteration ([ADR-0004](../adr/0004-deterministic-tie-breaks.md)); tested by
  opposite-insertion-order equality (254/254).
- [ ] Fuzz harnesses (insertion-order permutations, malformed snapshots)
- [ ] Security audit (`docs/audit/YYYY-MM-DD-audit.md`)
- [ ] Consumer integration (daimon/kavach green against `dist/samay.cyr`, carried over sandhi)

## Out of scope (for v1.0)

- Distributed consensus / multi-scheduler coordination (single-scheduler only).
- Live task execution (samay decides placement; kavach executes).
