# samay — Architecture Overview

Single-scheduler, in-memory task scheduler. Pure decision engine: it decides
*what runs where and when*; execution is a consumer's job (kavach).

## Module map (`src/`, dependency order)

| Module          | Owns                                                                 |
|-----------------|---------------------------------------------------------------------|
| `uuid.cyr`      | RFC-4122 v4 task ids (getrandom → hex).                              |
| `types.cyr`     | `ResourceReq`, `TaskStatus`, `TaskPriority`, `ScheduledTask`, `NodeCapacity`, `SchedulingDecision`, `PreemptionAction`, `SchedulerStats` + their logic (transitions, can-fit, utilization, reserve/release). `ScheduledTask.reserved_on` names the node whose capacity the task currently holds, distinct from `node_preference` ([ADR-0007](../adr/0007-reservation-lifecycle.md)). Also `samay_init()`. |
| `scheduler.cyr` | `TaskScheduler` — submit/get/cancel, pending ordering, best-fit placement, `schedule_pending`, preemption, stats. |
| `cronexpr.cyr`  | `CronExpr` — standard 5-field cron parse (parse-time validated) + `cron_expr_matches` / `cron_expr_next_after` (Vixie DOM/DOW rule — either field starred => AND both masks, else OR, [ADR-0006](../adr/0006-cron-expression-model.md); names, `@shortcuts`). |
| `cron.cyr`      | `CronScheduler`, `CronEntry`, `CronTaskTemplate` — recurring triggers via `CronExpr` + missed-schedule catch-up/skip policy, `check_due_at`. |
| `training.cyr`  | `SamayTrainMethod`, `TrainingJobTemplate` — training jobs → High-priority GPU tasks. |
| `json.cyr`      | JSON `Serialize`/`Deserialize` for every public type — `#derive(Serialize)` for the all-scalar leaves, hand-written `bayan_json_v_*` codecs for the container types, and the full scheduler+cron snapshot/restore. Fail-closed on malformed input ([ADR-0005](../adr/0005-restore-input-validation.md)). The largest module. |
| `lib.cyr`       | include-only aggregation header (whole-library entry).              |
| `main.cyr`      | in-tree demo (excluded from the dist bundle).                       |

`dist/samay.cyr` is the concatenated bundle (via `cyrius distlib`) that
consumers include.

## Data flow

```
submit_task ─► tasks map (Queued)
                    │
   register_node ─► nodes map
                    │
schedule_pending ──►  reconcile reservations (release anything no longer
                      │                        Scheduled/Running)
                      ├─ sort pending (priority desc, created_at asc, task_id)
                      └─ per task: preferred node → best_fit (min utilization, can_fit)
                                     └─ reserve node · task→Scheduled · reserved_on
                                        · SchedulingDecision
complete_task ────►  transition to Completed/Failed ─► release reserved_on
cancel_task ──────►  transition to Cancelled ─► release reserved_on
cron check_due ───►  due entries fire ScheduledTasks ─► submit_task
preempt_if_needed ►  lowest-priority running task a new task outranks ─► PreemptionAction
```

A reservation is held for exactly as long as a task is `Scheduled` or `Running`.
Reconciliation runs at the head of every `schedule_pending` rather than hooking
the transition, because `scheduled_task_transition` is public — a consumer can
drive a task terminal without calling any scheduler API
([ADR-0007](../adr/0007-reservation-lifecycle.md)).

## Representation notes

All structs are heap pointers (`#derive(accessors)`); **strings are `Str`
(ptr+len), not cstr** — migrated in v0.5.0 because `#derive(Serialize)` core
dumps on a cstr in a `Str`-typed field ([ADR-0003](../adr/0003-str-string-representation.md)).
Passing a bare literal where a `Str` is expected compiles and then segfaults, so
callers wrap with `str_from(...)`. Timestamps are i64 epoch-ns; optional fields
use `0`/empty sentinels. A task's
accelerator requirement is an ai-hwaccel `REQ_*` constant; a node's accelerator
*availability* is a list of ai-hwaccel device profiles, matched via
`requirement_satisfied()`. See [ADR 0001](../adr/0001-port-representation.md)
and [ADR 0002](../adr/0002-ai-hwaccel-profile-placement.md).

## Concurrency

**samay is single-threaded by contract** — one `TaskScheduler` / `CronScheduler`
per thread, serialised externally if shared. Deliberately no internal lock: the
query functions hand out raw pointers into scheduler-owned structs, so a mutex
would protect the lookup and release before the caller touches what it was
given. Measured, audited, and reasoned through in
[ADR-0008](../adr/0008-threading-contract.md). `samay_init()` closes the one
process-global hazard that bites even callers who honour the contract.

## Consumers

Both integrated, both green against `dist/samay.cyr`:

- **kavach 3.8.0** — sizes sandboxes from a samay `ResourceReq`
  (`kavach/src/samay_bridge.cyr`). samay decides placement; kavach executes.
- **daimon 2.0.0** — deleted its own duplicated scheduler and consumes samay as
  the single source of truth.

Neither calls samay's cron or JSON API today, and neither is multi-threaded.
