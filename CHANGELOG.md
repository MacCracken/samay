# Changelog

All notable changes to Samay are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); this project adheres to
[Semantic Versioning](https://semver.org/).

## [0.3.0] — 2026-07-18

**M2 — cron correctness.** Replaces the interval+hour/minute trigger model with
real cron expressions and an explicit missed-schedule policy.

### Added
- `src/cronexpr.cyr` — standard 5-field cron parser + matcher: `*`, `N`, `N-M`,
  lists, `*/step`, `N-M/step`, 3-letter month/day names, and
  `@hourly`/`@daily`/`@weekly`/`@monthly`/`@yearly` shortcuts. Vixie/crontab(5)
  DOM–DOW rule, DOW `0|7` = Sunday. **Validated at parse time** (Err on any
  malformed field). `cron_expr_matches`, `cron_expr_next_after`.
- **Missed-schedule policy**: `CRON_CATCHUP` (one task per missed occurrence,
  capped at 1000) vs `CRON_SKIP` (fires once, logs the drop). Missed occurrences
  are always logged via sakshi — never silently discarded.
- Deterministic `cron_scheduler_check_due_at(c, now_ns)` (injected clock).
- Benchmark `cron_expr_matches` 298 ns; 12 new cron tests (incl. 6 regression
  tests from the adversarial review). **121/121 assertions pass.**

### Changed — breaking (pre-1.0)
- Cron API replaced: `cron_scheduler_add(c, name, expr_str, template, enabled,
  missed_policy)` (parses + validates the expression) supersedes the
  interval-based `cron_entry_new(name, interval, hour, minute, …)`. Entries are
  built from cron strings now.

### Fixed — from a 4-lens adversarial review (7 confirmed findings, 0 dismissed)
- **HIGH**: occurrences older than the ~366-day catch-up window are now **logged
  when dropped** (were silently discarded — violated the no-silent-skip invariant).
- Vixie DOM/DOW **star rule keys off the field's first character**, so a list like
  `15,*` is not mis-flagged as star and `*/step` in DOM/DOW is treated as star.
- `CRON_SKIP` logs an **accurate** dropped count (was capped at 1000).
- Trailing comma (`0,30,`), overlong/overflowing numeric fields, and pre-1970
  (negative) match times are now rejected/guarded.
- `cron_expr_next_after` scan window widened to ~10 years (reaches Feb-29 schedules).

### Known limitations
- `cron_expr_matches` allocates via `epoch_to_date` per call (~298 ns); a long
  post-downtime catch-up scan allocates proportionally. Alloc-free matching is a
  roadmap perf item.

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
