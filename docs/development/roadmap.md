# samay — Roadmap

> Milestone plan through v1.0. State lives in [`state.md`](state.md);
> this file is the sequencing — what ships, in what order, against
> what dependency gates.

## v1.0 criteria

- [x] Rust → Cyrius surface parity verified against `rust-old/` (v0.2.0)
- [x] Test coverage mirrors the Rust suite (108/108 assertions)
- [x] Benchmarks captured (`docs/benchmarks.md`)
- [ ] Real cron-expression parsing + parse-time validation
- [ ] Missed-schedule policy (catch-up vs skip), explicit + logged
- [ ] Resource-aware placement wired through ai-hwaccel `requirement_satisfied()`/profiles
- [ ] JSON `Serialize` + `Deserialize` with roundtrip tests for every public type
- [ ] Determinism guarantees (same schedule + same time → same decisions), tested
- [ ] At least one downstream consumer (daimon or kavach) green against `dist/samay.cyr`
- [ ] CHANGELOG complete from v0.2.0 onward
- [ ] Security audit pass (`docs/audit/YYYY-MM-DD-audit.md`)

## Milestones

### M0 — Port scaffold (v0.1.0 tree) — ✅ 2026-07-18
`cyrius port` scaffold; Rust moved to `rust-old/`; doc tree established.

### M1 — Surface parity (v0.2.0) — ✅ 2026-07-18
All Rust types/functions ported across `src/*.cyr`; 108/108 assertions;
`dist/samay.cyr` bundle; lint/fmt clean; demo binary runs.

### M2 — Cron correctness (v0.3.0)
Replace the interval+hour/minute model with real cron expressions
(`* * * * *` fields), validated at parse time (not execution). Missed-schedule
catch-up vs skip policy, always logged (never silently skipped).

### M3 — Resource-aware placement v2 (v0.4.0)
Build ai-hwaccel profiles from `NodeCapacity` and place via
`requirement_satisfied()`; never schedule an accelerator task without an
availability check. Utilization/scoring refinements.

### M4 — Serialization + persistence (v0.5.0)
Full JSON `Serialize`/`Deserialize` for every public type with roundtrip tests;
optional snapshot/restore of scheduler + cron state.

### M5 — Determinism + hardening (v0.6.0 → v1.0)
Deterministic scheduling order (stable tie-breaks independent of hashmap
iteration), fuzz harnesses, security audit, consumer integration (daimon/kavach).

## Out of scope (for v1.0)

- Distributed consensus / multi-scheduler coordination (single-scheduler only).
- Live task execution (samay decides placement; kavach executes).
