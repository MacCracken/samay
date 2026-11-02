# ADR 0007 — Node capacity is returned on every exit from the running set

**Status**: accepted (2026-08-29, v1.0.3). Diverges from the Rust oracle deliberately.
**Amended** 2026-11-01 (v1.4.3): the invariant below held for a live scheduler and not across a
restore. A snapshot states node capacity and task reservations separately and nothing made them
agree, so a real 1.0.2 snapshot, written before capacity was ever returned, kept its leak for good.
The tasks are the record of who holds what, so restore now replays them over each node. A node that
agrees keeps its exact bits, and one that does not is rebuilt, with a log line. The same release makes
an idle node exactly full: the f64 sum could stop one bit short and refuse a whole-node task forever.
A reservation also holds any accelerator the task took
([ADR-0013](0013-accelerators-are-reserved.md)).

## Context

`task_scheduler_schedule_pending` reserves a node's capacity when it places a task
(`node_capacity_reserve`: subtract cpu/memory/disk, increment `running_tasks`). The
mirror operation, `node_capacity_release`, had exactly **one** caller in the whole
codebase — `_release_task_node`, reachable only from `task_scheduler_cancel_task`.

Nothing released on completion. There was no completion API on the scheduler at all, so
the only way for a consumer to finish a task was `scheduled_task_transition(task,
TASK_COMPLETED)`, which touches the task and never the node.

The consequence is not subtle. Two ordinary, successful completions on an 8-core node,
with no hostile input, no snapshot, and no clock skew:

```
start                      avail_cpu 8.000  avail_mem 8192  running_tasks 0
submit → schedule → RUNNING → COMPLETED    avail_cpu 4.000  avail_mem 4096  running_tasks 1
submit → schedule → RUNNING → COMPLETED    avail_cpu 0.000  avail_mem 0     running_tasks 2
stats: completed 2, running 0      tasks_for_node("n1"): 0
3rd task: can_fit 0, decisions 0
```

The node is permanently retired while `stats` reports nothing running. Availability
decays monotonically to zero as a function of throughput, which makes the project's
stated domain principle — *resource-aware placement; never schedule an accelerator task
without checking availability* — structurally unimplementable, because the availability
figure it depends on is guaranteed to be wrong.

A second, narrower arm of the same defect: `SCHEDULED → QUEUED` (including via
preemption) also never released, *and* `schedule_pending` overwrites `node_preference`
with the assigned node, so the preferred-node branch re-selected the same node and
reserved it a second time.

**This is inherited, not a port regression.**
`git show 1.1.5:rust-old/src/lib.rs | grep -n "\.release(\|\.reserve("` shows the oracle
has the identical shape: one `reserve` at :458, and one `release` at :383 inside
`cancel_task`. (The oracle was retired after 1.1.5; that tag is the last revision with
it.) At the time, CLAUDE.md set the correctness bar at "matches what Rust did" and
required an ADR to diverge. This is that ADR: the oracle is wrong here, and matching it
faithfully would ship a scheduler that stops scheduling.

## Decision

**A reservation is held while a task is `SCHEDULED` or `RUNNING`, and is returned on every
other transition**, at once through the scheduler's calls, and at the next pass after a raw
`scheduled_task_transition`.

1. **`ScheduledTask` gains a 15th field, `reserved_on: Str`** — the node whose capacity
   this task currently holds, or `0` for none. It is distinct from `node_preference`,
   which conflates the caller's request with the scheduler's assignment and is never
   cleared. `alloc(112)` becomes `alloc(120)` at **both** construction sites
   (`scheduled_task_new` and the restore path in `src/json.cyr`) — missing the second
   would write the new field 8 bytes past the allocation on every restored task.
2. **`_release_task_node` keys off `reserved_on` and clears it**, making a double release
   a no-op rather than a corruption.
3. **`_reconcile_reservations` runs at the head of `schedule_pending`** and returns the
   capacity of every task holding a reservation whose status is no longer `SCHEDULED` or
   `RUNNING`.
4. **`task_scheduler_complete_task(s, id, final_status)` is added** (additive, non-breaking)
   so the correct path is the obvious one, releasing at the moment of completion rather
   than at the next scheduling pass.
5. **`cancel_task` releases only after the transition is accepted**, so a rejected cancel
   cannot hand back capacity a task is still using.

**Reconciliation rather than a transition hook.** `scheduled_task_transition` is public
and terminal transitions through it are legal, so a consumer can drive a task terminal
without calling any scheduler API. A hook on the scheduler's own completion path would
leave that route open; reconciliation is self-healing regardless of how the consumer
drives the state machine. It costs one `map_values` pass on a path that already does one.

## Consequences

- **Wire format gains one nullable key**, `reserved_on`. This is not a break: readers
  look up fields by name and never enumerate, so a v1.0.2 reader ignores it. A v1.0.3
  reader restoring a **pre-1.0.3** snapshot (no such key) reconstructs the state — a task
  that was `SCHEDULED` or `RUNNING` held a reservation on the node `schedule_pending` had
  written into `node_preference`; anything else held none. Tested both directions.
- **Placement outcomes can change.** Releasing at the head of the loop means a requeued
  task may be re-placed on the node it previously occupied. That is correct — a task's
  own stale reservation should not block its own re-placement — but any test asserting a
  specific `node_id` after a requeue may legitimately need new expected values.
- **The invariant is now testable and tested**: once no task is `SCHEDULED` or `RUNNING`,
  every node is back to full capacity (`test_capacity_conservation`). That assertion is
  what would have caught this, and its absence is why it survived to v1.0.2.
- **Not fixed here**: splitting `node_preference` into a user preference and a current
  assignment. It is the cleaner model and would restore the accurate "preferred node"
  decision reason that `schedule_pending` currently destroys, but it changes the meaning
  of a shipped field. Deferred to a minor release with its own ADR, which is
  [ADR-0010](0010-request-and-assignment.md) (v1.3.0).
- Terminal tasks still accumulate in `TaskScheduler.tasks` — there is no removal API.
  Capacity is no longer leaked, but memory and per-pass sort cost still grow. Audit F5,
  closed in v1.4.0 by [ADR-0011](0011-bounded-task-history.md).

## Amendment (v1.5.1)

The 1.5.1 audit found three ways the invariant still broke.

- **Over-commitment counts below zero.** A reservation replayed on a node smaller than what its tasks
  hold (a node re-registered smaller, or a snapshot that says so) stopped at zero, and the next release
  gave back the whole amount, so the node was sold twice. Cores, memory and disk now go below zero
  there, as devices already went past capacity (ADR-0013), and a release brings them back to what is
  really free. An ordinary placement, which fits by can_fit's own test, still stops at zero, so every
  ordinary decision is unchanged. Amounts stop at -2^62, far below anything real, so nothing wraps.
- **A node registered after its tasks are restored is charged for them.** A snapshot that lacked a node
  its tasks held left those reservations with no node, and registering the node later charged nothing.
  Restore counts such tasks, and registering the node replays them.
- **`preempt_if_needed` reconciles first,** as a pass does. It counted a victim already stopped, or a
  task finished through its transition, as still holding its node, and stopped a second job needlessly.
