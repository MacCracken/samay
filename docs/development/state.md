# samay — Current State

> Refreshed every release. CLAUDE.md is preferences/process/procedures
> (durable); this file is **state** (volatile).

## Version

**0.2.0** — Cyrius port at feature + test parity with Rust v0.1.x
(2026-07-18). 1479 lines of Rust preserved at `rust-old/` as the parity oracle.

## Toolchain

- **Cyrius pin**: `6.4.67` (in `cyrius.cyml [package].cyrius`)

## Source

- Rust reference: 1479 lines at `rust-old/` (frozen, do not edit).
- Cyrius port: `src/{uuid,types,scheduler,cron,training}.cyr`
  (~700 lines) + `src/lib.cyr` aggregation header + `src/main.cyr` demo.
- Bundle: `dist/samay.cyr` (regenerate with `cyrius distlib` after any src change).

## Tests

- `tests/samay.tcyr` — 44 test functions, **108/108 assertions passing**
  (`cyrius test`). Mirrors the Rust unit + training suite.
- `tests/samay.bcyr` — hot-path benchmarks (see `docs/benchmarks.md`).
- Gates: `cyrius fmt --check` clean, `cyrius lint` 0 warnings.

## Dependencies

Direct (declared in `cyrius.cyml`):

- **ai-hwaccel** 2.3.14 (git) — `AcceleratorRequirement` `REQ_*`.
- **stdlib** — syscalls, string, alloc, str, fmt, vec, hashmap, io, fs,
  chrono, random, result, tagged, fnptr, freelist, atomic, sakshi,
  process, args, thread, assert, bench.

## Consumers

- daimon, kavach — declared consumers; do not yet reference samay (integration
  is future work). zugot has a placeholder marketplace recipe expecting a GH release.

## Next

See [`roadmap.md`](roadmap.md). Parity (M1) is done; next is hardening toward
v1.0 — real cron-expression parsing, missed-schedule policy, ai-hwaccel
availability-driven placement, JSON `Deserialize` + roundtrip tests, determinism.
