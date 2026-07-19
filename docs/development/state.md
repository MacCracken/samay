# samay — Current State

> Refreshed every release. CLAUDE.md is preferences/process/procedures
> (durable); this file is **state** (volatile).

## Version

**0.3.0** — cron correctness (M2). Real cron expressions + missed-schedule
policy, hardened via adversarial review. Built on the 0.2.0 Rust→Cyrius parity
port (Rust reference frozen at `rust-old/`).

## Toolchain

- **Cyrius pin**: `6.4.67` (in `cyrius.cyml [package].cyrius`)

## Source

- `src/{uuid,types,scheduler,cronexpr,cron,training}.cyr` + `src/lib.cyr`
  aggregation header + `src/main.cyr` demo (~1000 lines Cyrius).
- Bundle: `dist/samay.cyr` (regenerate with `cyrius distlib` after any src change).
- Rust reference: 1479 lines at `rust-old/` (frozen, do not edit).

## Tests

- `tests/samay.tcyr` — **121/121 assertions passing** (`cyrius test`). Includes
  6 regression tests from the v0.3.0 cron adversarial review.
- `tests/samay.bcyr` — benchmarks (see `docs/benchmarks.md`).
- Gates: `cyrius fmt --check` clean, `cyrius lint` 0 warnings.

## Dependencies

- **ai-hwaccel** 2.3.14 (git) — `AcceleratorRequirement` `REQ_*`.
- **stdlib** — syscalls, string, alloc, str, fmt, vec, hashmap, io, fs,
  chrono, random, result, tagged, fnptr, freelist, atomic, sakshi,
  process, args, thread, assert, bench.

## Consumers

- daimon, kavach — declared consumers; do not yet reference samay (integration
  is future work). zugot has a placeholder marketplace recipe expecting a GH release.

## Next

See [`roadmap.md`](roadmap.md). M2 (cron) done; next is M3 — resource-aware
placement wired through ai-hwaccel `requirement_satisfied()`/profiles. Also
queued: alloc-free cron matching (perf), JSON `Deserialize` + roundtrip tests.
