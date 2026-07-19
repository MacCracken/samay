# samay — Current State

> Refreshed every release. CLAUDE.md is preferences/process/procedures
> (durable); this file is **state** (volatile).

## Version

**0.4.0** — resource-aware placement (M3). `NodeCapacity` holds real ai-hwaccel
accelerator profiles; `can_fit` delegates to `requirement_satisfied()` (ADR-0002).
Built on M2 cron correctness (0.3.0) and the 0.2.0 Rust→Cyrius parity port (Rust
reference frozen at `rust-old/`).

## Toolchain

- **Cyrius pin**: `6.4.67` (in `cyrius.cyml [package].cyrius`)

## Source

- `src/{uuid,types,scheduler,cronexpr,cron,training}.cyr` + `src/lib.cyr`
  aggregation header + `src/main.cyr` demo (~1000 lines Cyrius).
- Bundle: `dist/samay.cyr` (regenerate with `cyrius distlib` after any src change).
- Rust reference: 1479 lines at `rust-old/` (frozen, do not edit).

## Tests

- `tests/samay.tcyr` — **130/130 assertions passing** (`cyrius test`). Includes
  6 cron regression tests (v0.3.0) + 5 accelerator-placement tests (v0.4.0).
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

See [`roadmap.md`](roadmap.md). M0–M3 done; next is **M4 (v0.5.0)** — full JSON
`Serialize`/`Deserialize` for every public type with roundtrip tests (+ optional
snapshot/restore). Also queued: alloc-free cron matching (perf), determinism
guarantees (M5), consumer integration (daimon/kavach).
