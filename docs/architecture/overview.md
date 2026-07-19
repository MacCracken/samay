# samay — Architecture Overview

Single-scheduler, in-memory task scheduler. Pure decision engine: it decides
*what runs where and when*; execution is a consumer's job (kavach).

## Module map (`src/`, dependency order)

| Module          | Owns                                                                 |
|-----------------|---------------------------------------------------------------------|
| `uuid.cyr`      | RFC-4122 v4 task ids (getrandom → hex).                              |
| `types.cyr`     | `ResourceReq`, `TaskStatus`, `TaskPriority`, `ScheduledTask`, `NodeCapacity`, `SchedulingDecision`, `PreemptionAction`, `SchedulerStats` + their logic (transitions, can-fit, utilization, reserve/release). |
| `scheduler.cyr` | `TaskScheduler` — submit/get/cancel, pending ordering, best-fit placement, `schedule_pending`, preemption, stats. |
| `cronexpr.cyr`  | `CronExpr` — standard 5-field cron parse (parse-time validated) + `cron_expr_matches` / `cron_expr_next_after` (Vixie DOM/DOW rule, names, `@shortcuts`). |
| `cron.cyr`      | `CronScheduler`, `CronEntry`, `CronTaskTemplate` — recurring triggers via `CronExpr` + missed-schedule catch-up/skip policy, `check_due_at`. |
| `training.cyr`  | `SamayTrainMethod`, `TrainingJobTemplate` — training jobs → High-priority GPU tasks. |
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
schedule_pending ──►  sort pending (priority desc, created_at asc)
                      └─ per task: preferred node → best_fit (min utilization, can_fit)
                                     └─ reserve node · task→Scheduled · SchedulingDecision
cron check_due ───►  due entries fire ScheduledTasks ─► submit_task
preempt_if_needed ►  lowest-priority running task a new task outranks ─► PreemptionAction
```

## Representation notes

All structs are heap pointers (`#derive(accessors)`); strings are cstr;
timestamps are i64 epoch-ns; optional fields use `0`/empty sentinels. A task's
accelerator requirement is an ai-hwaccel `REQ_*` constant; a node's accelerator
*availability* is a list of ai-hwaccel device profiles, matched via
`requirement_satisfied()`. See [ADR 0001](../adr/0001-port-representation.md)
and [ADR 0002](../adr/0002-ai-hwaccel-profile-placement.md).

## Consumers

daimon (task scheduling) and kavach (sandboxed execution) — integration is
roadmap work; neither references samay yet.
