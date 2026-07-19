# Changelog

All notable changes to Samay are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); this project adheres to
[Semantic Versioning](https://semver.org/).

## [0.2.0] — 2026-07-18

Cyrius port at **feature + test parity** with the Rust v0.1.x library. The
Rust source is preserved at `rust-old/` as the parity oracle.

### Added
- Full Cyrius (6.4.67) port across `src/{uuid,types,scheduler,cron,training}.cyr`,
  bundled to `dist/samay.cyr` via `cyrius distlib`.
- 108 unit-test assertions (44 test functions) in `tests/samay.tcyr` mirroring
  the Rust suite — **108/108 passing** (`cyrius test`).
- Hot-path benchmarks (`tests/samay.bcyr`), x86_64: `node_can_fit` 28 ns,
  `priority_from_numeric` 4 ns, `uuid_v4` 686 ns, `scheduled_task_new` 2.24 µs.
- RFC-4122 v4 UUID task ids from the kernel CSPRNG (`src/uuid.cyr`).

### Changed — port representation (see `docs/adr/0001-port-representation.md`)
- `chrono::DateTime<Utc>` → i64 epoch-ns (`lib/chrono` `dt_*`); `Option<DateTime>` → `0` sentinel.
- Payload enums flattened: `TaskStatus::Failed(String)` → `TASK_FAILED` + `fail_reason`;
  `AcceleratorRequirement::Tpu{min_chips}` → `accel_req` (ai-hwaccel `REQ_*`) + `accel_min_chips`.
- `tracing`/`anyhow` → `lib/sakshi` + `lib/result`; structs are `#derive(accessors)` heap
  pointers; strings are cstr.
- `TrainingMethod`/`training_method_name` renamed to `SamayTrainMethod`/`samay_training_method_name`
  to avoid a collision with ai-hwaccel's identically-named symbols.

### Dependencies
- `ai-hwaccel` 2.3.14 (`AcceleratorRequirement` `REQ_*`); Cyrius stdlib
  (chrono, hashmap, random, result, sakshi, str, vec, …).

### Notes
- `TaskStatus`/`AcceleratorRequirement` JSON shape differs from Rust serde (int-tagged);
  runtime behavior is equivalent. Full `Deserialize` + roundtrip tests are deferred to a later release.
- The chrono stdlib additions this port needed (`DateTime`/`Duration`/`strftime`) were
  proposed and **landed in cyrius 6.4.67**
  (`docs/development/proposals/archived/2026-07-18-chrono-datetime-duration-format.md`).

## [0.1.0]
- Rust library (pre-port), preserved at `rust-old/`.
