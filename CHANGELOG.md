# Changelog

All notable changes to Samay are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); this project adheres to
[Semantic Versioning](https://semver.org/).

## [0.5.0] — 2026-07-21

**M4 complete — JSON `Serialize`/`Deserialize` for every public type.** Leaf types
via `#derive(Serialize)` (0.4.1); container types (pointer/vec/map fields) via bayan's
`json_v` value-tree API in the new `src/json.cyr`. `TaskScheduler_to_json_str` /
`_from_json_str` is the full scheduler+cron snapshot/restore. Hardened by a 6-lens
adversarial verification pass (0 codec bugs). 237/237 assertions.

### Added
- `src/json.cyr`: `to_jsonv`/`from_jsonv` (node) + `to_json_str`/`from_json_str` (Str)
  for `TrainingJobTemplate`, `CronTaskTemplate`, `ScheduledTask`, `NodeCapacity`,
  `CronEntry`, `CronScheduler`, and `TaskScheduler` (the top-level scheduler snapshot).
- ai-hwaccel dep bumped `2.3.14 → 2.3.15`; `NodeCapacity.accel_profiles` delegates each
  profile to ai-hwaccel's `profile_to_json`/`profile_from_json` (lossless, incl. TPU
  chip counts). A `NodeCapacity` round-trips and the rebuilt node still satisfies the
  same `requirement_satisfied` placement (M3 property preserved).
- 68 new roundtrip assertions (**169 → 237**): container roundtrips, a full scheduler
  snapshot→restore→re-serialize identity check, TPU-placement parity, plus 5 regression
  guards from the verification pass (string/UTF-8 fidelity, determinism-under-reorder,
  empty collections, malformed-input robustness, numeric boundaries).

### Notes
- **Determinism:** maps (cron entries, scheduler tasks/nodes) serialize as arrays
  sorted by key `Str`, so output is byte-identical regardless of hashmap iteration
  order — samay's determinism principle, now covered on the wire.
- Nested leaf structs (`ResourceReq`, `CronExpr`) bridge through their `#derive` codec
  (exact, since leaves have no `Str` fields); container `Str` fields go through the
  bayan DOM, which escapes/unescapes correctly.

## [0.4.1] — 2026-07-20

Toolchain `6.4.67 → 6.4.69` (Grisu2 round-trip-correct f64 JSON), the `Str`
representation migration that JSON serialization requires, and the first slice of
M4 — `#derive(Serialize)` on the leaf types. Container types (pointer/vec/map
fields) remain for a later release; **v0.5.0 (full M4)** is not yet complete.

**M4 groundwork — string representation migrated to `Str`.** Prerequisite for JSON
`Serialize`/`Deserialize`: `#derive(Serialize)` core dumps on a cstr held in a
`Str`-typed field. See [ADR-0003](docs/adr/0003-str-string-representation.md).

### Changed — breaking (pre-1.0)
- Every samay string is now a real `Str` (ptr+len) instead of a cstr. `uuid_v4()`
  returns `Str`; task/node hashmaps are `map_new_str()` (content-hashed keys);
  `cron_expr_parse` takes a `Str`. Callers passing string literals into samay
  constructors now need `str_from("…")`.
- `task_status_name` / `samay_training_method_name` still return static cstr
  literals — display helpers, not stored state.

**M4 — JSON `Serialize` for leaf types (via `#derive`).** On toolchain 6.4.69 (which
landed the Grisu2 round-trip-correct f64 JSON codec), the all-scalar/all-`Str` types
now derive their JSON codec.

### Added
- `#derive(Serialize)` on `ResourceReq`, `SchedulingDecision`, `PreemptionAction`,
  `SchedulerStats`, `CronExpr` — emits `Type_to_json(ptr, sb)` /
  `Type_from_json(bayan_json_parse(js))`. f64 fields (`cpu_cores`, `score`)
  round-trip **bit-exact**; verified including a semantic check that a deserialized
  `CronExpr` matches the same instants as the original. 39 new roundtrip assertions
  (**130 → 169**, all green).
- `bayan` (JSON/YAML/TOML) and `math` (`f64_parse`) declared in `[deps].stdlib`;
  toolchain pin `6.4.67 → 6.4.69`.

### Notes
- The migration to `Str` is behavior-preserving against the `rust-old/` oracle; the
  demo and benchmarks are unaffected.
- **Container types are next, via the library — not hand-rolled.** `ScheduledTask`,
  `NodeCapacity`, `CronEntry`/`CronScheduler`, `TaskScheduler` and
  `TrainingJobTemplate` (nullable `target_node`) hold pointer/vec/map fields or a
  nullable `Str`, which the derive can't handle (it inlines nested structs and its
  flat-parser `from_json` doesn't unescape). These compose over bayan's `json_v`
  value-tree API (`json_v_obj_set`/`json_v_arr_push` → `json_v_build`; read via
  `json_v_parse`/`json_v_obj_get`), which handles escaping, nesting and arrays
  natively. `NodeCapacity` delegates each accel profile to ai-hwaccel ≥2.3.15's
  `profile_to_json`/`profile_from_json`. The eventual service boundary
  (daimon/kavach) carries these bodies over `sandhi`.

## [0.4.0] — 2026-07-18

**M3 — resource-aware placement via ai-hwaccel.** Node accelerator availability
is now a list of real ai-hwaccel device profiles; placement delegates to
ai-hwaccel's `requirement_satisfied()`. See [ADR-0002](docs/adr/0002-ai-hwaccel-profile-placement.md).

### Added
- `NodeCapacity.accel_profiles` — a vec of ai-hwaccel accelerator profiles.
  `node_capacity_add_accel(node, profile)` attaches `profile_cuda` / `profile_rocm`
  / `profile_tpu` / `profile_gaudi` / `profile_neuron` (chainable).
- 5 placement tests (gaudi/neuron/any-accelerator require a real profile;
  `add_accel` wiring; TPU insufficient-chips). **130/130 assertions pass.**
- Demo registers a real 8-chip TPU-v5p node via `add_accel`.

### Changed — breaking (pre-1.0)
- `node_capacity_can_fit`'s accelerator check delegates to ai-hwaccel
  `find_satisfying_profile()` / `requirement_satisfied()`; the flat
  `gpu_available` / `tpu_available` / `tpu_chip_count` fields are removed. Parity
  constructors kept: `node_capacity_new(…, gpu=1)` → a CUDA profile,
  `node_capacity_with_tpu(node, chips)` → a TPU profile.

### Fixed — intended divergence from the Rust oracle (ADR-0002)
- `REQ_GAUDI` / `REQ_AWS_NEURON` / `REQ_ANY_ACCELERATOR` now require an **actual
  matching accelerator profile** on the node. The Rust port's `_ => true` stub
  fit them on any node — including accelerator-less ones — violating the
  "never schedule an accelerator task without checking availability" rule.

### Reviewed
- Focused 2-lens adversarial review (placement correctness + integration/lifetime): 0 findings.

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
