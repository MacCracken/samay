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
- [x] Security audit pass ([`docs/audit/2026-07-21-audit.md`](../audit/2026-07-21-audit.md)) — 10 findings, crash-class remediated ([ADR-0005](../adr/0005-restore-input-validation.md))

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
- [x] Deterministic scheduling order (v0.6.0) — stable tie-breaks on unique keys, independent
  of hashmap iteration ([ADR-0004](../adr/0004-deterministic-tie-breaks.md)); tested by
  opposite-insertion-order equality.
- [x] Security audit (v0.7.0) — [`docs/audit/2026-07-21-audit.md`](../audit/2026-07-21-audit.md):
  multi-lens review + adversarial PoC + live CVE/0day research; 10 findings (all
  snapshot-restore DoS, no Critical/High), crash-class remediated with fail-closed input
  validation ([ADR-0005](../adr/0005-restore-input-validation.md)).
- [x] Fuzz harnesses — insertion-order permutation fuzz (M5 determinism) + adversarial
  malformed-snapshot probing (security audit); in-suite regression guards.
- [ ] Consumer integration (daimon/kavach green against `dist/samay.cyr`, carried over sandhi)
- [ ] Follow-ups from the audit (Rec 3–5): stable O(n log n) sort + terminal-task pruning;
  cron aggregate-work budget; upstream stdlib hash seeding.

## Out of scope (for v1.0)

- Distributed consensus / multi-scheduler coordination (single-scheduler only).
- Live task execution (samay decides placement; kavach executes).
