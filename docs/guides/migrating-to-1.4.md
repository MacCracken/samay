# Moving a consumer to samay 1.4

For a consumer on 1.1.x moving to the 1.4 line. Nothing here needs a source change to compile, and
no public function was removed or changed its arguments. What changes is behaviour, and the first
item below can change what your scheduler decides. Per-release detail is in the
[CHANGELOG](../../CHANGELOG.md).

## Do this first

1. **Move to cyrius 6.7.10 or later.** That is samay's floor at its pinned deps, bayan 1.11.1 and
   ai-hwaccel 2.5.6. CI builds and tests on it. Through 6.7.9 a snapshot cannot compile: the stdlib
   lacks `str_builder_add_json_cstr`. `dist/samay.cyr` on its own compiles further back with older
   deps, and daimon's tests pass that way on 6.6.6, but nothing gates that.
2. **Move the pins.** `[deps.samay]` to the new tag, `[deps.ai-hwaccel]` to 2.5.6 or later.
3. **Re-vendor from an empty `lib/`.** Run `cyrius deps` on the new pin. It also vendors the stdlib
   leaves `dist/samay.deps` lists.

## ⚠ Accelerator tasks now queue

Through 1.4.2 samay never reserved an accelerator, so one GPU went to any number of tasks. Since 1.4.3
a task takes a whole device, or its chips of a TPU pod, and holds it until it finishes
([ADR-0013](../adr/0013-accelerators-are-reserved.md)).

- **A node registered with `gpu_available = 1` has one GPU, so it runs one GPU task at a time.** To run
  more, attach a profile per device with `node_capacity_add_accel`.
- **`node_capacity_can_fit` now means free**, not present.
- **There is no way to ask for sharing or for several devices yet.** The roadmap pins that to 1.5.0.
- A snapshot written before 1.4.3 can hold several tasks on one GPU. They all stay counted, and the
  device comes free when the last one finishes.

## Calls that answer differently

| Call | Since | What changes | If you |
|---|---|---|---|
| `task_scheduler_submit_task` | 1.4.3 | `Err(1)` for an id already present | read its payload without checking the tag, check it |
| `task_scheduler_register_node` | 1.4.3 | An id already known keeps what its tasks hold | treated re-registering as a reset, it no longer is one |
| `task_scheduler_preempt_if_needed` | 1.4.3 | Answers only for a queued task that fits nowhere, and only names a victim that would place it | expected an action on priority alone, expect `0` |
| `*_to_json_str` | 1.4.0 | Answers `0` past 100,000 items | write snapshots, check for `0` before using it |
| `*_from_json_str` | 1.4.3 | Refuses wrong types and duplicate ids, and rebuilds a node that disagrees with its tasks | restore a hand-edited snapshot, watch the log |
| `resource_req_new` | 1.4.3 | Negative and NaN become 0, and cores stop at 1e18 | relied on a negative requirement, stop |
| `cron_expr_next_after` | 1.4.3 | `-1` now means never, not "not within ten years" | treated `-1` as a horizon, it no longer is one |
| `task_scheduler_register_node` | 1.4.5 | Answers `1` for an empty id, and registers nothing | take ids from a client, check the answer |
| `*_to_json_str` | 1.4.5 | Every writer answers `0` past 128 MiB of text, and none exits the process | write snapshots, check for `0` as above |
| `*_from_json_str` | 1.4.5 | Refuses past 128 MiB, or a parse past ten times the text ([ADR-0014](../adr/0014-what-a-document-may-cost.md)) | restore something larger, raise `SAMAY_JSON_MAX_BYTES` |
| `node_capacity_new` | 1.4.5 | Negative and NaN become 0, and cores stop at 1e18, as for a requirement | built a node with negative capacity to keep work off it, stop |
| `cron_entry_new` | 1.4.5 | A policy other than `CRON_SKIP` is stored as `CRON_CATCHUP`, which is how it already acted | read the policy back expecting your own value, expect `CRON_CATCHUP` |
| `resource_req_new` | 1.4.5 | `network` is stored as 0 or 1 | compared it with another number, compare with 1 |

## Things that used to need work from you

- **`scheduled_task_transition` stamps `started_at` and `completed_at`** since 1.4.3, so stamping them
  yourself is no longer needed. Doing so still works.
- **`samay_init()` does nothing** since 1.4.3, and stays because it is public. You can stop calling it.
- **A task copies its `ResourceReq`** since 1.4.3, so reusing one across tasks is safe. To change a
  task's requirement afterwards, use `ScheduledTask_resource_requirements(t)`, not your own pointer.
- **Constructors own every `Str` they keep** since 1.1.3, and `ScheduledTask_set_node_preference` and
  `target_node` since 1.4.3.
- **The leaf types have readers that refuse** since 1.4.5. `scheduling_decision_from_json_str` and its
  four siblings answer `0` for a missing or wrong-typed field. The derive's own
  `SchedulingDecision_from_json` cannot refuse: `{}` gives null Strs, which crash the next writer.

## Node fields

Since 1.3.0 a task records what it asked for and where it went separately
([ADR-0010](../adr/0010-request-and-assignment.md)). `ScheduledTask_node_preference` still reads as
before: the assignment if there is one, else the request. Use `ScheduledTask_requested_node` or
`ScheduledTask_assigned_node` for just one of them. Snapshots gain both keys, and older readers ignore
them.

## Cron

- **If you store `last_fired` yourself, read it back from the entries after a check.** A CATCHUP burst
  past `CRON_BURST_BUDGET` is held with its old watermark, and writing `now` over that deletes what it
  owed ([ADR-0012](../adr/0012-cron-burst-budget.md)). CRON_SKIP entries are never held.
- **To clear a backlog sooner, call again at the same `now_ns`** until a check returns nothing.
- **A clock step back of more than 3 hours re-anchors** the watermark, so a task can fire again for time
  that passes twice. A smaller step still waits.
- **Replacing an entry keeps its watermark**, so it neither re-fires nor forgets. Removing and adding it
  back starts fresh.
- **`CRON_MAX_COUNT` is gone.** Log lines changed in 1.4.1 and 1.4.3, so do not parse them.

## A long-lived scheduler

`alloc()` never frees. A pass no longer grows with history since 1.4.3, but every finished task stays
in the table until you remove it.

- `task_scheduler_prune_terminal(s, before_ns)` forgets finished tasks. samay never does this on its own.
- `task_scheduler_stats` counts what is left, so read lifetime figures before pruning.
- Prune with cyrius 6.6.20 or later, which the floor above already covers.

## By consumer

- **kavach** reads `ResourceReq` fields through `samay_bridge.cyr`, so only the toolchain and pins
  apply.
- **daimon**: `POST /v1/scheduler/nodes` reaches the re-registering fix, and `gpu_available` nodes now
  run one GPU task at a time. It already answers 400 for an empty `node_id`, so the 1.4.5 refusal never
  reaches it. Its `submit_task` route already checks the tag. Its own `started_at`
  stamp in `src/sched.cyr` can go. To report where a task runs, read `ScheduledTask_assigned_node`.
- **stiva**: `cron_due_at` runs CRON_SKIP and writes `now` back, which is safe because a SKIP entry is
  never held. Adding CRON_CATCHUP would need it to read watermarks back. The comment in `src/fleet.cyr`
  saying samay's ledger leaks stopped being true in 1.0.3.
