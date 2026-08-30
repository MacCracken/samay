# Changelog

All notable changes to Samay are documented here. Format follows
[Keep a Changelog](https://keepachangelog.com/); this project adheres to
[Semantic Versioning](https://semver.org/).

## [1.1.1] — 2026-08-30

**Two measured wrong-answer paths closed, and a named abort everywhere else an
allocation can fail.** 446 assertions (was 432). No public signature changed, no
wire-format change — all 28 guards are pure insertions, so zero test churn and
zero change for kavach, daimon or stiva.

### The scope this release was planned with was wrong

The roadmap said an unchecked `alloc()` "becomes a wild write at a small
address." **It does not.** Every one of the 16 raw sites stores to the fresh
pointer at a field offset ≤ 112, against `vm.mmap_min_addr = 65536` — so the
store traps in the guard page. Measured across six modules: exit 139 at the first
store, deterministically, inside the named constructor. Fifteen of sixteen store
at offset 0 on the very next line. Guarding those buys a **message**, not a fix.

The real defect was in eleven allocation points that are **not raw `alloc(`
tokens** — `vec_new`, `map_new_str`, `str_new`, `str_builder_build` — which a
mechanical `grep alloc(` never saw. Those are where a null **escapes as struct
data** and the constructor returns an object that looks healthy.

### Fixed — a task was placed on a corrupt node, with no fault

`node_capacity_new` stored `vec_new()`'s result into `accel_profiles` unchecked.
On OOM that is 0; for a CPU node the `gpu_available` branch is skipped, so nothing
touches the null vec and **the struct is returned intact**. Measured:
`node_capacity_can_fit` answered **1** for a `REQ_NONE` requirement, and a full
`task_scheduler_schedule_pending` pass **placed a task on the corrupt node** — one
decision, no error. It died much later in `vec_len(0)` on the JSON path.

A successful but wrong placement is the class this project's resource-awareness
and determinism rules exist to forbid. `node_capacity_from_jsonv` had the
identical bug on the restore path.

### Fixed — a null task_id that crashes on someone else's request

`samay_uuid_v4` returned `str_new(out, 36)` unchecked. The null `Str` becomes
`ScheduledTask.task_id` and then a hashmap key — and it does **not** fault there,
because `hash_str_v` null-guards. The task inserts under bucket 0 and `map_size`
becomes 1. The SIGSEGV lands on a **later, unrelated submit** that probes into
slot 0 and reaches `str_eq(0, key)`: measured at the 8th, 10th and 10th subsequent
submit across three runs. Nondeterministic, cross-frame, and unattributable to the
allocation that actually failed.

The *listed* site in that module (`alloc(37)`) fails immediately and harmlessly.
The unlisted one was the bug.

### Added — [ADR-0009](docs/adr/0009-oom-policy.md), 28 guards, and a CI gate

The policy: **check every allocation samay performs whose result it returns or
stores into one of its own structs, and `panic` on 0. Never propagate an OOM.**
A null must never leave the function that created it.

`return 0` was rejected on reproduced evidence, not taste — a propagated 0 travels
*further*: a null `CronTaskTemplate` survived three API layers reporting a healthy
`len=1` before faulting, and a two-task snapshot with one OOM-0 record restored as
`tasks=1` with **exit 0** — the task silently lost, the restore reporting success,
contradicting samay's own never-silently-drop rule. In the JSON readers 0 is
already spent: ADR-0005 gives it the meaning "reject this record", so an OOM-0
would drop a well-formed record from a valid snapshot *and* make the ADR-0005
regression suite pass for the wrong reason. `preemption_action_new` has the same
collision with "no candidate needs preempting".

`Err` is unavailable structurally: `Ok`/`Err` each heap-allocate 16 bytes, so
building the error needs the allocation that just failed. In `cron_expr_parse`
that is total — under true OOM it cannot return at all.

Because the OOM branch is not unit-testable (`fail_after_n_allocs` intercepts
`alloc_via`, not bare `alloc()`), two things pin this instead:
- `test_no_null_fields_from_constructors` — asserts no constructor returns a
  struct with a null field. This is what would have caught the `accel_profiles`
  bug.
- **A CI gate** asserting every raw `alloc(` in `src/` has a `panic` within a few
  lines, verified to fail when a guard is removed. Prose does not keep a rule.

### Not claimed
This is **not** a crash fix for the 16 listed sites — they already trapped, and
now do so with a name instead of an anonymous `signal 11`. Nothing here changes
the benchmarks, so no performance claim is made.

## [1.1.0] — 2026-08-30

**Cron catch-up counts stop overstating their own precision.** 432 assertions
(was 416). No public signature changed, no wire-format change.

This release is smaller than the roadmap said it would be, because verifying the
three planned items against current source found **two already closed or not
worth doing**. That check is recorded below rather than quietly dropped — see
*Planned and dropped*.

### Fixed — a capped due-count was stated as if it were exact

`_cron_count_due` short-circuits at `CRON_MAX_COUNT` (100,000). When it does, the
value it returns is a **floor**, not the true count — the catch-up window holds
**527,040** minutes, so a `* * * * *` entry genuinely has 527,040 due occurrences
while the function reports 100,000. Both callers then stated that figure as fact:

- `_cron_log_skip` — "skip policy dropped 99,999 missed occurrence(s)"
- `_cron_log_catchup_cap` — "fired 1000 of 100000 due occurrence(s)"

Off by **427,040** in the worst case. samay's domain principle is that a missed
schedule is never silently dropped; reporting a wrong number is a quieter version
of the same failure, so the count now carries a `capped_out` flag and both logs
prefix the figure with `>=` when it is a floor.

**The cap itself is deliberately kept.** Measured on 6.5.36: a *matching* minute
costs roughly 40× a missing one, because a match passes the v1.0.3 prefilter and
reaches `epoch_to_date`. So `* * * * *` over a full window is **28.9 ms** capped
at 100,000, against **~153 ms** uncapped — 5× more work to make a log line exact.
Saying `>=` is free. The stale comment claiming the count is "accurate for
realistic downtimes" (false past ~69 days for a per-minute entry) is corrected.

### Added
- `test_cron_count_capped_flag` — pins that a per-minute expression trips the cap
  and is flagged a floor, that a daily expression over the same window is exact
  and unflagged, and that a short recent window is neither capped nor clamped.
- `test_task_status_name` — `task_status_name` has zero callers in `src/`,
  `tests/`, the bench, or either consumer, but it is exported public API and
  mirrors `samay_training_method_name`, which *is* used in three places. Removing
  an exported symbol is a major-version action, so it is kept and pinned instead
  of deleted.

### Planned and dropped — verified against source, not assumed

Two of the three items this release was scoped around turned out not to be work:

- **Clamp `last_fired` to `>= now - CRON_SCAN_WINDOW_SECS` on restore**
  (audit Rec 4). **No-op.** `_cron_count_due` already floors `start` at
  `min_start`, so an ancient watermark and a clamped one scan the identical
  527,040-minute window — measured 3.93 ms vs 3.93 ms, indistinguishable. The
  only thing the clamp would change is suppressing `_cron_log_clamp`, a **true**
  warning that occurrences older than the window were dropped. It would trade
  nothing for less information.
- **Saturating subtraction in the stats averages** (audit Rec 6). **Already
  shipped** — `if (ms < 0) { ms = 0; }` and `if (wms < 0) { wms = 0; }` have been
  in `task_scheduler_stats` since `e3861d2 "rust port parity"`, the original
  port. Rec 6 was filed as "no confirmed finding, still worth it" and was already
  satisfied when written.

Both were carried on the roadmap as open. They were listed from the audit's
recommendation text without re-checking the code — the exact failure the
roadmap's own trigger-discipline note warns about, committed by the note's
author. The roadmap now records both under *Considered and rejected*.

## [1.0.4] — 2026-08-30

**Concurrency audit — the risk v1.0.3 left explicitly unretired.** samay now states a
threading contract, and closes the one race that could bite a caller who honours it.
416 assertions (was 406). No public signature changed; one additive function.

Everything below was measured on x86_64 with threaded harnesses, not reasoned about.

### Added
- **`samay_init()`** — additive, public. Forces the process-global lazy initialisers
  samay depends on to run while the caller is still single-threaded.
  `task_scheduler_new()` and `cron_scheduler_new()` call it, so the ordinary shape
  (build, then spawn) is covered automatically.
- **[ADR-0008](docs/adr/0008-threading-contract.md)** — the contract, the measurements,
  and why samay deliberately does *not* take an internal lock.

### Fixed
- **A racing thread could evaluate a cron expression against the wrong date.**
  `lib/chrono.cyr`'s `_chrono_init_mdays` publishes the month-length table pointer
  *before* filling it, so a second thread sees non-zero, skips the init, and reads an
  all-zero table — `epoch_to_date`'s month loop then never breaks and reports month 13.
  **This needs no shared state**: two threads with entirely separate schedulers still
  share that global, so it breaks callers who are honouring the single-threaded contract.
  Measured 14/200 process runs with threads tightly synchronised, and 1/400 through
  samay's own public API in the worst realistic shape; 0 with the pre-warm.
  The defect is in `lib/`, which samay must not modify, so this closes the window from
  outside. Upstream ask filed: `_chrono_init_mdays` should fill a local and publish last,
  the order `bayan-json`'s `_d_init_tables` already uses correctly.

### Documented — not fixed, deliberately
Sharing one scheduler across threads corrupts it. This is now stated in the README, both
module headers, and ADR-0008 rather than papered over with a lock:
- **Node reservations are lost, towards over-admission.** 8 threads × 160,000 reserves on
  one node: `running_tasks` 43,299 against 160,000 expected, and `available_cpu` *higher*
  than the truth — samay would place work on a node with no room, the exact failure the
  resource-aware-placement principle exists to prevent.
- **The tasks hashmap corrupts its own bookkeeping.** 8 threads submitting 8,000 tasks:
  one lost outright, and the map's internal count read 7,911 against 7,999 occupied slots.
- **`lib/sakshi.cyr` has unsynchronised global state** (ring indices, span depth, trace
  ids); concurrent logging can interleave output. Observability only.

**Why no internal lock:** `task_scheduler_get_task`, `pending_tasks`, `tasks_for_node`
and `cron_scheduler_list_entries` all return **raw pointers** into scheduler-owned
structs. A mutex would protect the lookup and release before the caller touches what it
was handed — an object that looks safe, invites the assumption, and still corrupts. That
is worse than an honest contract. Making the API lockable means not returning interior
pointers: a redesign, not a patch.

### Verified safe (measured negatives worth recording)
- **The allocator.** `lib/thread.cyr` arms the shared-heap lock *before* the clone, and it
  is a real atomic CAS with fences — no startup window. 8 threads, 80,000 allocations,
  0 overlapping blocks. Every samay operation allocates, so this was the load-bearing one.
- **`samay_uuid_v4`.** 200,000 uuids across 8 threads, 0 duplicates — `task_id`
  uniqueness, which ADR-0004 depends on, holds under concurrency.
- **bayan's decimal tables** fill then publish; correct as written.
- **v1.0.3's `_reconcile_reservations`** held up under a completer/reconciler race with no
  phantom capacity.

### Parity note
The Rust oracle enforced this statically: `&mut self` on every mutating method meant the
compiler rejected concurrent mutation outright. Cyrius cannot express that, so a
compile-time guarantee has become a documented runtime one. Recorded in ADR-0008 rather
than left implicit.

## [1.0.3] — 2026-08-29

**P-1 audit sweep: two correctness defects fixed, ADR-0005's contract completed, and the
first CI gate on the artifact consumers actually compile.** 406 assertions (was 296).
No public signature removed or changed; one additive function and one additive nullable
JSON key. kavach 3.8.0 and daimon 2.0.0 need no migration.

Findings came from a multi-agent sweep across eight dimensions (security, memory safety,
arithmetic, Rust parity, cron, determinism/JSON, performance, refactor/test-gaps): 45 raw
findings, 43 surviving adversarial refutation. The two most severe were both found *off*
the finder axis — one by a completeness critic asking what nobody had run.

### Fixed — correctness

- **A node was permanently retired after two successful task completions.**
  `node_capacity_release` had exactly one caller, reachable only from `cancel_task`, and
  there was no completion API at all. An 8-core node went to 0.000 available CPU after two
  ordinary completions while `stats` reported 0 running — availability decayed
  monotonically with throughput, making resource-aware placement structurally
  unimplementable. Capacity is now returned on **every** exit from the running set, via
  reconciliation at the head of `schedule_pending` plus a new
  `task_scheduler_complete_task`. The same defect leaked on `SCHEDULED → QUEUED` and
  double-reserved on re-placement. **This is inherited from the Rust oracle, which has the
  identical shape** — diverging deliberately, per [ADR-0007](docs/adr/0007-reservation-lifecycle.md).
- **`*/N` in day-of-month or day-of-week was silently ignored.** `_cron_parse_field`
  correctly sets Vixie's star flag for any field beginning with `*`, but the matcher then
  *discarded that field's mask* instead of AND-ing it. Equivalent to Vixie only for a bare
  `*` (an all-ones mask, so AND is the identity) — but `*/2` over DOM is the odd days. So
  `0 0 */2 * *` fired 365 days a year instead of 183, and `0 0 * * */2` fired 7 days a week
  instead of 4. Both masks are now always applied ([ADR-0006](docs/adr/0006-cron-expression-model.md)).
  Blast radius is provably confined to that one shape, verified by a 1,610,253-pair
  differential sweep. **An existing test asserted the defect and stated the wrong rule in
  its comment; it was rewritten from the Vixie source.**
- **A backward clock step re-fired already-fired occurrences.** `last_fired` was stored
  unconditionally, so an NTP correction or VM restore rewound the watermark — 9 tasks for
  6 distinct minutes, with `task_id`s a consumer cannot deduplicate. The watermark now
  only moves forward; a regression is logged instead.
- **Re-enabling a disabled cron entry fired a silent burst.** The watermark froze while
  disabled, so the whole disabled interval counted as missed: 720 tasks after a 30-day
  disable of `0 * * * *`, logging nothing (only the *capped* path logged). Disabled
  entries now track the clock, and every catch-up burst is logged.
- **A profile containing a quote or backslash destroyed itself on serialization.**
  ai-hwaccel writes string values unescaped, so `_parse` returned 0 and bayan rendered the
  child as literal `null` — restore then dropped the accelerator, turning a node that
  could fit a GPU task into one that could not, purely by round-tripping. Now skipped with
  a warning rather than emitted as data-losing output.
- **Training deadlines could wrap into the past.** `dur_seconds` multiplies by 1e9;
  above ~9.2e9 seconds the product overflowed i64 while still passing the `max > 0` guard.
  Now clamped to the available headroom and logged.

### Fixed — hardening (completes [ADR-0005](docs/adr/0005-restore-input-validation.md))

ADR-0005 promised rejection when a required field is *"missing **or the wrong type**"*.
The wrong-type half was unimplemented for the two nested leaves, which bridged through
their `#derive` codec — and that codec cannot fail: it allocs and returns a pointer
whatever it is handed, over kernel-zeroed pages. So a string, int, array, `null` or `{}`
in `resource_requirements` all produced a **non-zero, all-zero** `ResourceReq` (which fits
any node), and every `req == 0` guard downstream was dead code.

- Nested `resource_requirements` / `expr` are now read explicitly and type-checked.
- `ResourceReq` numerics are clamped. Negative values previously ran *backwards* through
  `node_capacity_reserve` — which computes `available - required` and so **added**
  capacity, driving `available` above `total` and utilization to −61.
- `NodeCapacity` enforces `0 ≤ available ≤ total` on all three axes and rejects
  non-finite f64. A snapshot with `available_cpu: 1e18` against `total_cpu: 1.0` made that
  node win every placement forever; `1e400` became `+Inf`, making utilization NaN.
- `_best_fit_node` guards NaN utilization. Every IEEE comparison against NaN is false, so
  both `f64_lt` and `f64_eq` failed and the ADR-0004 tie-break was skipped entirely —
  letting hashmap bucket order pick the winner, the one thing ADR-0004 exists to prevent.
- Empty `task_id` / `node_id` / cron entry `name` are rejected (all are map keys); flag
  fields compared with `== 1` are normalised to 0/1; out-of-domain enums fall back to
  their default rather than being clamped to a nearest bound that invents a meaning.

### Added

- `task_scheduler_complete_task(s, id, final_status)` — additive.
- `ScheduledTask.reserved_on` — additive nullable JSON key. v1.0.2 readers ignore it;
  v1.0.3 readers reconstruct it from a pre-1.0.3 snapshot. Tested both directions.
- **CI now gates on `cyrius fmt`, `cyrius lint`, `cyrius distlib --check` and `cyrius bench`.**
  `dist/samay.cyr` is the only artifact consumers compile and nothing had ever checked it
  was in sync. Note `fmt`/`lint` take a *file* argument — a bare `cyrius fmt --check`
  prints usage and exits 0, so a gate written that way checks nothing.
- [ADR-0006](docs/adr/0006-cron-expression-model.md) also records, retroactively, the
  v0.3.0 replacement of the oracle's interval model with cron expressions — a divergence
  that shipped without one.

### Performance

- **`cron_expr_matches` 282 ns → 22 ns (12×), miss path now alloc-free** — 4,800,000 →
  3,312 bytes per 100k missing calls. `epoch_to_date` allocates 48 bytes with no free and
  walks years from 1970; the matcher called it before testing any bitmask. Closes the
  alloc-free-matching roadmap item carried since M2.
- **Placement scan 1,996,000 → 3,992 bytes** at 200 nodes × 500 pending (500×):
  `_best_fit_node` rebuilt the whole node vector once per pending task.

### Tests

296 → 406 assertions. New: the capacity-conservation invariant (the assertion whose
absence let the headline defect ship), the cron differential guard, back-compat snapshot
restore, and the parser features that had **zero** coverage — every `@shortcut`
expansion, month/day names, DOW `7`→Sunday folding. Swapping the `@monthly` and `@weekly`
literals previously left all 296 assertions green.

### Known / deferred

Stable O(n log n) sorts + terminal-task pruning (F5), the cron cross-entry work budget
(F8/F9), upstream hash seeding (F4), and the write-side codec optimisation are tracked in
[`docs/development/roadmap.md`](docs/development/roadmap.md). Concurrency was **not**
audited: whether `TaskScheduler`/`CronScheduler` are safe under concurrent access is
unknown, and every figure here is single-threaded.

## [1.0.2] — 2026-08-29

**Maintenance: toolchain 6.5.36, ai-hwaccel 2.3.19, bayan on the focused JSON sublib.**
No behavior change to the scheduler; 296/296 assertions still green.

### Changed
- **Toolchain** pinned to Cyrius **6.5.36** (was 6.4.69). CI reads the pin from
  `cyrius.cyml`, so no workflow edit was needed.
- **ai-hwaccel** 2.3.15 → **2.3.19**.
- **bayan** now consumed as a git dependency at **1.5.2**, taking `dist/bayan-json.cyr`
  — the focused JSON sublib — instead of the vendored 641 KB stdlib monolith
  (`lib/` drops from 641 KB to 100 KB for this dependency). bayan graduated out of
  the stdlib snapshot in 1.5.2 and ai-hwaccel 2.3.19 pulls the sublib transitively;
  keeping the monolith alongside it vendored **both** files and produced 27
  duplicate JSON definitions resolved by last-def-wins — precisely the silent-bug
  class samay's own symbol-hygiene principle forbids.
- **`src/json.cyr` now calls the fully-qualified `bayan_json_v_*` spelling.** The
  short `json_v_*` aliases live only in bayan's monolith, not the sublib. The
  qualified names exist in *both* packagings, so this is strictly more portable:
  consumers of `dist/samay.cyr` may vendor either bayan module. No signature or
  behavior change — the aliases were one-line forwarders.

### Fixed
- **`json_v_parse_str` no longer exists in bayan** — renamed upstream to
  `json_v_parse_buf` (`_str` is a Cyrius dispatch suffix and collided with
  `X_str` routing). samay's `_parse` helper called it, so the build emitted
  `undefined function 'json_v_parse_str'`. Now calls `bayan_json_v_parse_buf`,
  which is the same function body under the new name.
- **Benchmark suite restored — it had been segfaulting since v0.5.0.**
  `tests/samay.bcyr` passed bare cstring literals to APIs that became `Str`-taking
  in the ADR-0003 migration; `cron_expr_parse` then ran `str_data` over a cstring
  and died (SIGSEGV, exit 139) before reporting the last benchmark. Literals are
  now wrapped in `str_from`, hoisted outside the timed loops so the 16-byte header
  allocation is not folded into the reported figures. All 5 benchmarks report
  again; `docs/benchmarks.md` refreshed with the first numbers since v0.4.0.
- Reformatted `src/main.cyr` and `tests/samay.tcyr` for the 6.5.36 formatter's
  canonical continuation indent (whitespace only).

## [1.0.1] — 2026-07-21

**Symbol-hygiene fix — `uuid_v4` → `samay_uuid_v4`.** samay's `uuid_v4` collided with
libro's incompatible `uuid_v4(buf)` (a buffer-writing UUID generator used by libro's
security-critical audit chain); under the ecosystem's last-def-wins linking, bundling
both silently broke one. Surfaced while integrating daimon (which depends on libro).
Renamed samay's generator to the namespaced `samay_uuid_v4` — the fix samay's own
"symbol hygiene" domain principle mandates. No behavior change; only the internal
`scheduled_task_new` and the uuid tests referenced it (no known external consumer did).

## [1.0.0] — 2026-07-21

**v1.0 — the Rust → Cyrius port is complete.** Every v1.0 criterion is met; no source
change lands in this release beyond the version stamp — it marks the milestone. The
surface has been stable since the 0.2.0 parity port and hardened release-by-release
through 0.7.0.

### v1.0 criteria — all met
- **Surface parity** with the frozen Rust oracle (`rust-old/`), verified test-for-test (0.2.0).
- **Real cron** — 5-field expressions with parse-time validation + Vixie DOM/DOW rule, and
  an explicit, always-logged missed-schedule catch-up/skip policy (0.3.0).
- **Resource-aware placement** through ai-hwaccel device profiles —
  `requirement_satisfied()`, no accelerator task fits a node without a matching profile
  ([ADR-0002](docs/adr/0002-ai-hwaccel-profile-placement.md), 0.4.0).
- **JSON `Serialize`/`Deserialize`** for every public type — `#derive(Serialize)` leaves +
  a bayan `json_v` container codec; full scheduler snapshot/restore is byte-identical, f64
  bit-exact (0.5.0).
- **Deterministic scheduling** — every ordering-sensitive path breaks ties on a unique key,
  never hashmap iteration order; fuzz-verified across all `map_values` sites
  ([ADR-0004](docs/adr/0004-deterministic-tie-breaks.md), 0.6.0).
- **Security audit** — multi-lens review + adversarial PoC + live CVE/0day research
  ([`docs/audit/2026-07-21-audit.md`](docs/audit/2026-07-21-audit.md)); crash-class
  remediated with fail-closed restore validation ([ADR-0005](docs/adr/0005-restore-input-validation.md), 0.7.0).
- **Downstream consumer green** — **kavach 3.8.0** sizes its sandboxes from a samay
  `ResourceReq` against `dist/samay.cyr`.
- **Benchmarks** captured; **CHANGELOG** complete from 0.2.0; `fmt`/`lint` clean; 296/296
  assertions.

### Notes
- **Toolchain:** requires cyrius ≥ 6.4.69 (the derive's Grisu2 f64 JSON codec).
- **Not in v1.0** (tracked): daimon integration — samay is the extraction of daimon's own
  scheduler, so it is a breaking major migration rather than an additive one. Audit
  follow-ups Rec 3–5 (stable O(n log n) sort, cron aggregate budget, upstream hash
  seeding) remain non-blocking hardening items.

## [0.7.0] — 2026-07-21

**M5 (part 2) — security audit + restore-path hardening.** A multi-lens security audit
(code review + adversarial PoC + live CVE/0day web research) of the untrusted-input
surface — cron parsing and JSON snapshot restore. Report:
[`docs/audit/2026-07-21-audit.md`](docs/audit/2026-07-21-audit.md). 10 confirmed findings,
all denial-of-service on the snapshot-restore path (no Critical/High, no corruption/RCE);
the parser boundaries and the 2024–2026 cron/JSON CVE classes were found closed.

### Fixed — security (fail-closed restore validation, [ADR-0005](docs/adr/0005-restore-input-validation.md))
- **Null-`Str` deref SIGSEGV DoS** on snapshots missing required fields (F1/F2/F3): the
  `*_from_jsonv` deserializers now **reject** a record (`return 0`) when a required `Str`,
  nested struct, or map-key field is absent or the wrong type, matching Rust serde. A
  malformed record is dropped by the container loop, not fatal; well-formed snapshots
  restore unchanged.
- **Input-validation divergences from Rust** (F6/F7): `priority` clamped to 1–10 and
  `status` range-checked on restore; `NodeCapacity` u64-domain fields (memory/disk/
  running_tasks) clamped to ≥0 via `_jv_uint`.
- **Unbounded-allocation DoS** (F4/F5 vector): `SAMAY_JSON_MAX_ITEMS` (100000) caps
  restored `tasks`/`nodes`/`entries`/`accel_profiles`; larger arrays reject the snapshot.

### Tests
- 13 new security regression guards (**283 → 296**): required-field rejection per record
  type, malformed-record-dropped-not-fatal, priority clamp, negative-resource clamp.

### Notes
- Tracked audit follow-ups (Rec 3–5, non-ship-blocking): stable O(n log n) sort +
  terminal-task pruning; cron aggregate-work budget; upstream stdlib hash seeding. The
  size cap bounds these to a finite worst case; the residual is bounded DoS, deferred
  rather than risk a sort rewrite destabilising the v0.6.0 determinism guarantee.

## [0.6.0] — 2026-07-21

**M5 (part 1) — deterministic scheduling.** Every ordering-sensitive path now breaks ties
on a unique key (`task_id` / `node_id` / cron entry `name`) instead of hashmap iteration
order, via one shared `samay_str_lt` comparator. Intentional divergence from the Rust
oracle, which left ties to randomized `HashMap` order — see
[ADR-0004](docs/adr/0004-deterministic-tie-breaks.md). Fuzz harnesses, security audit, and
consumer integration remain open M5 items toward v1.0.

### Changed
- `pending_tasks`/`schedule_pending` tie-break by `task_id`; `best_fit_node` by `node_id`
  on equal utilization; `preempt_if_needed` by `task_id` on equal priority+created_at;
  `tasks_for_node` returns `task_id`-sorted; `cron` `list_entries`/`check_due_at` emit in
  entry-`name` order. Non-tied decisions are unchanged (all parity assertions still pass).
- `src/json.cyr`'s local string comparator folded into the shared `samay_str_lt`.

### Tests
- 7 determinism guards (**237 → 281**): opposite-insertion-order decision equality,
  best-fit tie → lowest node_id, `tasks_for_node` ordering, cron listing order, plus
  three from a 6-probe fuzz pass — **hash-colliding** task_ids (self-validating: proves
  the raw bucket order differs, then that decisions don't), the preempt tie-break, and
  cron listing across a map rehash. The fuzz pass found **0 residual gaps** across all
  10 `map_values` sites.

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
