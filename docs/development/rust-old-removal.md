# rust-old/ removal readiness

> Audited 2026-09-23 against samay 1.1.4 (cyrius 6.6.6), following kavach's
> `docs/development/rust-old-removal.md`. Updated for 1.1.5, which fixed the three
> blockers the audit found. **`rust-old/` was removed after 1.1.5.** Tag `1.1.5` is the
> last revision that has it: `git show 1.1.5:rust-old/src/lib.rs`.

This document answers one question: can `rust-old/` be deleted without losing anything the
Cyrius port has not already captured? Once the oracle is gone, this file and the ADRs are
the only description of it, so everything the port dropped is written down here.

## Verdict

**Removed.** It was ready as of 1.1.5. The tree was deleted in the change after that tag,
and the [references](#references-to-update-at-removal) were updated in the same change.

Every public item in the Rust crate has a Cyrius equivalent, or an ADR recording what
replaced it. Every one of the 53 Rust tests has a counterpart. Nothing reads `rust-old/` at
build, test, CI or release time, and no ecosystem tooling reads `LINES_OF_RUST.txt`.

The 1.1.4 audit found three records that would have been wrong, or would have lost their
only check. All three are fixed in 1.1.5:

1. **ADR-0006 misdescribed the oracle it retires**, getting both the field names and the
   first-fire rule wrong. It is corrected, and it now also records that relative intervals
   have no replacement.
2. **Five Rust assertions were ported in name only.** One could never fail. Two passed for
   any utilization below 100%. One accepted a whole core of slack. One dropped its
   precondition. The port's own UUID-uniqueness test had the first defect too. All are
   fixed; see [below](#ported-in-name-not-in-force).
3. **Two entry points the Rust suite exercised were never executed:**
   `cron_scheduler_add_entry`, including its empty-name guard, and
   `cron_scheduler_check_due`. Both are now tested. So is every other public function,
   79/79, and CI enforces it.

The port also silently dropped some behaviour: ten log events, the error text, and relative
intervals. Before this audit, only the oracle recorded those decisions.
[Not ported](#not-ported) records them now.

## What `rust-old/` contains

| File | Lines | Anything to keep? |
|---|---:|---|
| `src/lib.rs` | 1,479 | The oracle: 14 public types, 34 public functions and trait impls, 53 inline tests |
| `Cargo.toml` | 25 | No. `cyrius.cyml` carries the description; keywords and categories have no counterpart |
| `Cargo.lock` | 844 | No. Resolved Rust crates |
| `LINES_OF_RUST.txt` | 1 | No. It holds `1479`, which is cited in `CLAUDE.md`, `state.md` and the roadmap |
| `codecov.yml` | 9 | A policy rather than a file: an 80% coverage gate ([Not ported](#not-ported), item 7) |
| `deny.toml` | 32 | No. cargo-deny license and source policy |
| `rust-toolchain.toml` | 3 | No |

The crate had no benches, examples, fuzz targets or docs. Unlike kavach, samay has no Rust
baseline numbers to carry out.

## Public API coverage

| Rust | Cyrius | Notes |
|---|---|---|
| `ResourceReq` + `Default` + `Clone` | `ResourceReq`, `resource_req_new`, `resource_req_default`, `resource_req_clone` | The `Tpu { min_chips }` payload is split into `accel_req` + `accel_min_chips` (ADR-0001 §2) |
| `TaskStatus` (7 variants) + `valid_transition` | `TASK_*`, `task_status_valid_transition` | All 10 edges. `Failed(String)` becomes `TASK_FAILED` + a `fail_reason` field (ADR-0001 §2); see [Not ported](#not-ported), item 4 |
| `TaskPriority` + `from_numeric` + `can_preempt` + `Ord` | `PRIO_*`, `task_priority_from_numeric`, `task_priority_can_preempt` | The integer enum carries the order |
| `ScheduledTask` + `new` + `priority_class` + `transition` | `ScheduledTask`, `scheduled_task_new`, `scheduled_task_priority_class`, `scheduled_task_transition` | Adds `fail_reason` and `reserved_on` (ADR-0007). The constructor owns its `Str`s (1.1.3) |
| `NodeCapacity` + `new`, `with_tpu`, `can_fit`, `utilization`, `reserve`, `release` | `node_capacity_*` (same names) + `node_capacity_add_accel` | `gpu_available` / `tpu_available` / `tpu_chip_count` are replaced by ai-hwaccel profiles. Rust's `_ => true` for Gaudi, Neuron and Any is fixed (ADR-0002) |
| `SchedulingDecision`, `PreemptionAction`, `SchedulerStats` + `Default` | Same structs + `*_new` | |
| `TaskScheduler::new` / `Default` | `task_scheduler_new` | |
| `register_node`, `submit_task`, `cancel_task` | `task_scheduler_register_node`, `_submit_task`, `_cancel_task` | Cancel releases through `reserved_on` (ADR-0007) |
| `get_task`, `get_task_mut` | `task_scheduler_get_task` | It returns a pointer, which is mutable, so one function covers both |
| `pending_tasks`, `tasks_for_node`, `schedule_pending`, `preempt_if_needed`, private `best_fit_node` | `task_scheduler_*`, `_best_fit_node` | Unique-key tie-breaks where Rust fell back to `HashMap` order (ADR-0004) |
| `stats` | `task_scheduler_stats` | Same counting rules, including the [inherited](#inherited-not-ported) ones |
| — | `task_scheduler_complete_task` | New in 1.0.3 (ADR-0007) |
| `CronEntry`, `CronTaskTemplate` | `CronEntry`, `CronTaskTemplate` + constructors | Interval, hour and minute are replaced by a cron expression + missed-schedule policy (ADR-0006) |
| `CronScheduler::new` / `Default`, `add_entry`, `remove_entry`, `list_entries`, `check_due` | `cron_scheduler_new`, `_add_entry`, `_remove_entry`, `_list_entries`, `_check_due` | Plus `cron_scheduler_add`, which parses an expression, and `check_due_at`, which takes an injected clock |
| `TrainingMethod` + `Display` + `preferred_accelerator` | `SamayTrainMethod` (`TM_*`), `samay_training_method_name`, `training_method_preferred_accel` | Renamed to avoid an ai-hwaccel collision (ADR-0001) |
| `TrainingJobTemplate` + `to_scheduled_task` | `training_job_template_new`, `training_job_to_scheduled_task` | Adds a deadline overflow clamp |
| `Serialize` / `Deserialize` on 12 types | `#derive(Serialize)` on 5 leaf types; `src/json.cyr` for the rest | Adds scheduler snapshots, which Rust never had. The wire format differs (ADR-0001) |

## Test parity

All 53 Rust tests have a counterpart in `tests/samay.tcyr` (118 test functions, 475
assertions). Several Rust tests share one Cyrius function. The cron tests were translated to
the expression model rather than copied. ⚠ marks a row that had a defect listed in the
next section; all of them were fixed in 1.1.5.

| Rust tests | Cyrius |
|---|---|
| `training_method_display`, `training_job_creates_high_priority_task`, `training_job_no_deadline_when_zero`, `training_job_requires_accelerator` | `test_training_method_name`, `_high_priority`, `_no_deadline_when_zero`, `_requires_accel`. Stricter than Rust: the task name must match exactly, not just `contains` |
| `test_submit_task`, `test_submit_task_initial_status` | `test_submit_task` |
| `test_submit_multiple_tasks` | `test_submit_multiple` ⚠ |
| 6 × `test_valid_transition_*` | `test_valid_transitions`, `test_running_to_failed`, `test_preempt_requeue` |
| 3 × `test_invalid_transition_*` | `test_invalid_transitions` ⚠, `test_invalid_completed_to_running` |
| `test_priority_from_numeric`, `test_priority_ordering`, `test_can_preempt_method` | Same names (`test_can_preempt`) |
| `test_pending_tasks_sorted_by_priority`, `…_same_priority_sorted_by_created`, `test_empty_scheduler_pending` | `test_pending_sorted_by_priority`, `test_pending_same_priority_by_created`, `test_empty_pending` |
| 3 × preemption | `test_preempt_higher_over_lower`, `test_no_preempt_same_priority`, `test_no_preempt_lower_priority` |
| `test_node_can_fit`, `…_gpu_requirement`, `…_tpu_requirement`, `test_node_gpu_or_tpu_satisfied_by_tpu` | `test_node_can_fit`, `_gpu`, `_tpu`, `test_node_gpu_or_tpu` |
| `test_node_utilization`, `test_node_utilization_empty`, `test_node_reserve_and_release` | Same names (`test_node_reserve_release`) ⚠ |
| 4 × `test_schedule_*`, `test_schedule_no_nodes`, `test_all_nodes_full`, `test_tasks_for_node` | `test_schedule_assigns_to_node`, `_prefers_preference`, `_fallback_when_full`, `_transitions`, and the same three names |
| `test_cancel_queued_task`, `test_cancel_nonexistent_task` | `test_cancel_queued`, `test_cancel_nonexistent` |
| `test_stats_empty`, `test_stats_counts`, `test_priority_clamped`, `test_deadline_field` | Same names |
| `test_cron_add_entry`, `…_add_empty_name_rejected`, `…_remove_entry`, `…_remove_nonexistent` | `test_cron_add_valid`, `_add_empty_name` ⚠, `_remove`, `_remove_nonexistent` |
| `test_cron_check_due_fires_first_time`, `…_respects_interval`, `…_disabled_skipped`, `test_cron_fires_when_interval_elapsed` | `test_cron_first_eval_match`, `_first_eval_nomatch`, `_disabled`, and `_catchup` / `_skip` (expression model, ADR-0006) ⚠ |

### Ported in name, not in force

This table records the state at 1.1.4. **Every row is fixed in 1.1.5**: exact `str_eq`
and `f64_eq` comparisons, the unchecked step asserted, and a test calling each unexecuted
entry point. Eight of nine mutations of the affected code passed the whole 1.1.4 suite; the
1.1.5 suite catches all nine (CHANGELOG, 1.1.5).

The first three rows were confirmed by running the assertion's own expression in a probe.
The last three were confirmed by searching every caller in `src/` and `tests/`.

| Rust assertion | Port | Why it cannot do its job |
|---|---|---|
| `assert_ne!(id1, id2)` | `str_eq_cstr(id1, id2) == 0` (`tests/samay.tcyr:265`) | `str_eq_cstr` takes a C string. Given a `Str`, its `strlen` measures the header, not the text, so `str_eq_cstr(u, u)` returns **0** for a UUID compared with itself. The assertion cannot fail. The port's own `test_uuid_unique` (`:49`) has the same defect |
| `assert_eq!(node.utilization(), 0.0)`, twice | `f64_to(util) == 0` (`:207`, `:229`) | `f64_to` truncates, so any utilization in [0, 1) passes. Measured passing at **82%** |
| `(available_cpu - 2.0).abs() < 0.001` | `f64_to(avail) == 2` (`:217`) | Accepts anything in [2, 3), so an under-reservation of up to one core passes |
| `add_entry` rejects an empty name | Tested on `cron_scheduler_add` (`:727`) instead | `cron_scheduler_add_entry`, the direct port of `add_entry`, is never executed by any test or source path |
| Every Rust cron test calls `check_due()` | The tests call `check_due_at` | `cron_scheduler_check_due`, the wall-clock entry point, is never executed |
| `task.transition(Cancelled).unwrap()` | Unchecked (`:97`) | If QUEUED → CANCELLED broke, the next assertion ("cancelled → queued is an error") would still pass, starting from QUEUED |

## Not ported

This section records what the port dropped. Before this file, nothing but the oracle did.

1. **Relative intervals.** `interval_seconds` fired N seconds after the *last fire*, for any
   N, sub-minute included; Rust's own tests used 1 s and 10 s. A cron expression is
   wall-clock-aligned and minute-granular, so "every 10 seconds" and "every 90 minutes since
   the last run" cannot be expressed. ADR-0006 records the model change but not this loss,
   and it describes the oracle wrongly:
   - The fields are `interval_seconds`, `specific_hour`, `specific_minute` and
     `last_fired`, not `interval_secs` / `last_run`.
   - An entry that has never fired fires on the **first** `check_due` (`lib.rs:673-679`,
     asserted by `test_cron_check_due_fires_first_time`), not "`interval` seconds after
     registration".
2. **Ten of the eleven `tracing` events.** Only `warn!("no node with sufficient capacity")`
   was restored (`src/scheduler.cyr:319`). These were dropped:
   - `info!`: task scheduler initialised · registered node · task submitted · task
     cancelled · preemption recommended · cron entry added · cron entry removed.
   - `debug!`: task status transition · task scheduled · cron entry fired.

   In the other direction, samay's eight `sakshi_warn` calls cover missed schedules,
   clamps and dropped profiles, none of which Rust logged.
3. **Error text.** Rust's four errors carried messages: `invalid task status transition:
   {from} -> {to}`, `task not found: {id}`, `cron entry name cannot be empty`, and
   `cron entry not found: {name}`. The port returns codes (`Err(1)`, `Err(2)`), documented
   per function. A caller that needs to tell an unknown id from a refused transition looks
   the task up first, as daimon's `src/sched.cyr` does.
4. **`Failed(String)` has no owning entry point.** The reason survives as a field.
   However, `task_scheduler_complete_task` takes no reason, and
   `ScheduledTask_set_fail_reason` stores the caller's pointer. That is the class of bug
   1.1.3 fixed for every constructor. daimon clones the reason before calling
   (`daimon/src/sched.cyr`, "⛔ CLONED"). This is a roadmap candidate, not a removal blocker.
5. **Derives.** Rust derived `Clone` on 12 types. The port has it where the library itself
   uses it (`resource_req_clone`). The other eleven were boilerplate; if a consumer ever
   needs a deep copy, a JSON round trip provides one. `Debug` is covered by
   `task_status_name` and the JSON codecs. `PartialEq` on `TaskStatus` also compared the
   `Failed` message; comparing the integer status does not.
6. **Wire format.** The port cannot read serde JSON written by the Rust crate
   (`"status":"Queued"`, RFC 3339 timestamps); see ADR-0001, Consequences. No Rust-era
   snapshot is known to exist, and kavach, daimon and stiva are all Cyrius.
7. **Coverage gate: replaced by a different measure.** `codecov.yml` required 80% line
   coverage, on the project and on each patch. samay 1.1.5 instead gates on functions:
   `cyrius coverage --min 100` (79/79), plus a strict check that every public function in
   `[lib].modules` is actually called by a test. Nothing measures line coverage. The strict
   check exists because the tool counts a name appearing anywhere in the tests. At 1.1.4
   that had credited two functions nothing called, so the tool reported 59/79 when the true
   figure was 57/79. `deny.toml` needs no counterpart: first-party git deps are
   commit-pinned in `cyrius.lock`, and `cyrius build` restores any vendored file whose hash
   disagrees with the lock (measured in 1.1.4).

## Inherited, not ported

These match the oracle and do not block removal. They are listed because deleting the
oracle removes the only other place anyone would check them, and matching the oracle is
not the same as being right.

- `stats` counts CANCELLED tasks as `completed` (`lib.rs:552`); `SchedulerStats` has no
  `cancelled` field.
- Nothing sets `started_at`. Neither crate has a start operation, so
  `average_wait_time_ms` and `average_run_time_ms` stay 0 unless the consumer sets it.
  daimon does, in `sched_task_start`.

## References to update at removal

All updated in the removal change. Line numbers move with every edit, so this table names
*what* changed, not where. `grep -rn rust-old --exclude-dir=lib --exclude-dir=.git .` finds
every remaining mention.

| File | What was done |
|---|---|
| `CLAUDE.md` | Project identity and Scaffolding now say the oracle is retired and give the anchor. The "cross-check against `rust-old/`" principle became "divergence needs an ADR", and the "do not modify" rule was dropped |
| `README.md`, `docs/guides/getting-started.md` | `rust-old/` removed from both layouts. The workflow step now points at the ADRs and this file |
| `docs/development/state.md`, `roadmap.md` | Now say "retired after 1.1.5" |
| `.gitignore` | `/rust-old/target/` removed |
| `src/types.cyr`, `src/scheduler.cyr`, and therefore `dist/samay.cyr`; `tests/samay.tcyr` | Oracle citations such as `lib.rs:483` and `lib.rs:68-83` are **kept as breadcrumbs**. `CLAUDE.md`'s Scaffolding section states that they refer to tag `1.1.5`, so no source file changed |
| ADR-0001, 0003, 0004, 0006, 0007; `docs/audit/2026-07-21-audit.md` | Citations kept. The ADR index's Conventions section states the anchor once, rather than each citation being rewritten |
| `CHANGELOG.md` | History left as it is. The removal is recorded under `[Unreleased]` |

## Pre-removal checklist

- [x] Correct ADR-0006's description of the oracle, and record the relative-interval loss
      (1.1.5).
- [x] Fix the five in-name-only assertions and the UUID one. Add tests for
      `cron_scheduler_add_entry` (including the empty name) and `cron_scheduler_check_due`
      (1.1.5).
- [x] Decide on a coverage gate: 100% of public functions, each called by a test, in CI
      (1.1.5).
- [x] Tag the last commit that still has `rust-old/`, and point every citation above at it.
      That is the `1.1.5` release tag (`7f39cab`, also on GitHub).
- [x] Update the references above in the same change that deletes the tree.

## Removal

Done in the change after `1.1.5`. The `1.1.5` release tag served as the anchor, so no
separate `samay-pre-rust-removal` tag was needed:

```sh
git show 1.1.5:rust-old/src/lib.rs       # the oracle, 1,479 lines
git ls-tree -r --name-only 1.1.5 rust-old # all 7 files
```
