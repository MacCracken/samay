# samay — Current State

> Refreshed every release. CLAUDE.md is preferences/process/procedures
> (durable); this file is **state** (volatile).

## Version

**0.4.0** (+ unreleased M4 groundwork) — resource-aware placement (M3). `NodeCapacity` holds real ai-hwaccel
accelerator profiles; `can_fit` delegates to `requirement_satisfied()` (ADR-0002).
Built on M2 cron correctness (0.3.0) and the 0.2.0 Rust→Cyrius parity port (Rust
reference frozen at `rust-old/`).

## Toolchain

- **Cyrius pin**: `6.4.67` (in `cyrius.cyml [package].cyrius`)

## Source

- `src/{uuid,types,scheduler,cronexpr,cron,training}.cyr` + `src/lib.cyr`
  aggregation header + `src/main.cyr` demo (~1000 lines Cyrius).
- **Strings are `Str` (ptr+len), not cstr** as of the unreleased M4 groundwork
  ([ADR-0003](../adr/0003-str-string-representation.md)) — required because
  `#derive(Serialize)` core dumps on a cstr in a `Str`-typed field.
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
  chrono, random, result, **bayan**, **math**, tagged, fnptr, freelist, atomic,
  sakshi, process, args, thread, assert, bench.
  (`bayan` = the JSON/YAML/TOML module — JSON is *not* named "json"; `math`
  supplies `f64_parse`, which `#derive(Serialize)` needs to deserialize f64.)
  Vendor with `cyrius lib sync` (not `cyrius deps`).

## Consumers

- daimon, kavach — declared consumers; do not yet reference samay (integration
  is future work). zugot has a placeholder marketplace recipe expecting a GH release.

## Next

See [`roadmap.md`](roadmap.md). M0–M3 done. **M4 (v0.5.0)** is in progress:

- ✅ Prerequisite: cstr → `Str` migration ([ADR-0003](../adr/0003-str-string-representation.md)),
  130/130 still green.
- ✅ Established that `#derive(Serialize)` (`Type_to_json(&v, sb)` /
  `Type_from_json(bayan_json_parse(js))`) is the mechanism — no hand-written codec needed.
- ⛔ **Blocked** on an upstream float-roundtrip fix — filed as
  [`issues/2026-07-19-cyrius-f64-json-roundtrip.md`](issues/2026-07-19-cyrius-f64-json-roundtrip.md)
  (upstream: `cyrius/docs/development/issues/2026-07-19-f64-json-roundtrip-6-decimal-cap.md`). The JSON emit path
  `fmt_float_buf(v, buf, 6)` (stdlib `lib/fmt.cyr`, shared by both `#derive(Serialize)`
  and bayan) is capped at 6 decimals: `1/3` → `0.333333` loses ~9 mantissa bits, and
  any `|x| < 5e-7` → `0.000000` is annihilated. Two divergent parsers (bayan
  `_jp_atof`, math `f64_parse`) disagree by 1 ULP on identical input. This matters
  because `SchedulingDecision.score` is `1 - utilization`, so values like 1/3 and 2/3
  are the common case, not the edge case.

Also queued: alloc-free cron matching (perf), determinism guarantees (M5), consumer
integration (daimon/kavach).
