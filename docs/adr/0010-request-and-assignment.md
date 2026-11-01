# 0010 — A task's request and its assignment are two fields

**Status**: Accepted
**Date**: 2026-11-01

## Context

`ScheduledTask.node_preference` meant two things. It held the node the caller asked for
until `task_scheduler_schedule_pending` placed the task, and from then on it held the node
the scheduler chose. The request was overwritten and nothing kept it. [ADR-0007](0007-reservation-lifecycle.md)
recorded this and deferred the split to a minor release with its own ADR.

The overwrite made every requeue wrong, because the next pass read the old assignment back
as a request. Measured on 1.2.2:

| case | 1.2.2 | 1.3.0 |
|---|---|---|
| asked for n1, fell back to n2, n1 frees, requeued | n2, "preferred node" | n1, "preferred node" |
| asked for nothing, placed on n1, n1 gets busy, requeued | n1, "preferred node" | n2, "best-fit selection" |

Both 1.2.2 rows report a preference nobody expressed, and the first ignores the one that was.

The roadmap planned to fix this with one new nullable field, with no wire break. That reading
keeps `node_preference` as the request and adds the assignment. Checking it against real
readers found three constraints it misses:

1. **Consumers read the name as the assignment.** daimon's `_api_task_json` publishes
   `ScheduledTask_node_preference` as `"node"`, documented as "where it was placed", and an
   executor uses it to find its work. daimon follows this checkout through `path =
   "../samay"`. Narrowing the getter compiles cleanly and turns `node` to null for every
   best-fit task.
2. **Old readers read the wire key as the assignment.** `task_scheduler_tasks_for_node` uses
   it at every release, and before 1.0.3 `_release_task_node` returned capacity on it.
3. **Old snapshots do not hold the request.** Placing a task overwrote it, so for a placed
   task the information is gone.

## Decision

**Two fields with one meaning each, and the old name kept as a view of both, in memory and
on the wire.**

1. **`node_preference` becomes `requested_node`, and `assigned_node` is added**, a 16th field.
   Only the caller writes the request. Only `schedule_pending` writes the assignment, and it
   stays after the task ends, so a finished task still says where it ran. `reserved_on` is
   unchanged: it is the node the task holds capacity on now. `alloc(120)` becomes `alloc(128)`
   at both construction sites.
2. **`schedule_pending` reads `requested_node` and writes `assigned_node`.** It no longer
   touches the request.
3. **`ScheduledTask_node_preference` and its setter stay, hand-written.** The getter answers
   `assigned_node`, else `requested_node`, which is what the field held through 1.2.x. The
   setter writes the request. `task_scheduler_tasks_for_node` keeps using the view, so a task
   a consumer drove to `SCHEDULED` itself is still listed on the node it asked for.
4. **The wire key `node_preference` keeps carrying the view.** Two nullable keys are appended,
   `requested_node` and `assigned_node`. Readers look fields up by name, so older ones ignore
   them, and for the same history the rest of the snapshot does not change.
5. **Restore tests the keys, not the decoded values**, as `reserved_on` does, because an
   explicit null is an answer. For an old snapshot, with the keys absent:
   - `assigned_node` is the recorded node if the task was placed (`scheduled_at` is set, or it
     is `SCHEDULED` or `RUNNING`), otherwise `0`.
   - `requested_node` is the recorded node. For a placed task this is a guess. It may be a real
     request, such as a training job's `target_node`, and it is how 1.2.x read that snapshot.

## Consequences

- **Positive** — A requeued task goes where it asked to go, or to the best fit, and its decision
  reason is true. The caller's request survives placement and snapshots. No consumer needs a
  source change, and no older reader changes behaviour.
- **Positive** — The gate is on record, with real binaries of 1.0.2, 1.0.4, 1.1.2 and 1.2.2,
  built on their own toolchains. Each read its own snapshot, 1.3.0 restored it, and the release
  read 1.3.0's output back and re-emitted identical tasks and nodes. Each also read a native
  1.3.0 snapshot and listed the same tasks per node. With the same history, 1.2.2's and 1.3.0's
  snapshots differ only by the two new keys. `tests/fixtures` keeps the 1.0.2, 1.0.4 and 1.2.2
  snapshots for the forward direction, in CI.
- **Negative** — A requeue can place a task on a different node than 1.2.x did. That is the fix,
  but a task with no request loses the accidental stickiness it had.
- **Negative** — Three names now describe node placement, and the view has to stay while
  consumers and old readers use it. Snapshots grow about 43 bytes per task.
- **Negative** — A placed task restored from an old snapshot keeps the recorded node as its
  request, so it can still report "preferred node" for a node nobody asked for. Nothing can
  recover the real request.
- **Neutral** — An older release drops the two keys when it rewrites a snapshot, so a snapshot
  that passes through one comes back to 1.3.0 as an old snapshot.
- **Neutral** — On a task already placed, the setter changes the request while the getter keeps
  naming the assignment until the next pass. No consumer sets it after placement today.
- **Neutral** — daimon can read `ScheduledTask_assigned_node` for `"node"` when it wants the
  strict answer: today that field also shows a queued task's requested node.

## Alternatives considered

- **The roadmap's reading: `node_preference` is the request, on the wire too, plus
  `assigned_node`.** Rejected on measurement. Run through the same gate, all four old readers
  lost tasks on a native snapshot (`tasks_for_node` n1 1 of 2, n2 0 of 1), and placed tasks
  without a request wrote `node_preference` as null. daimon's `node` would change silently.
- **Keep `node_preference` as it is, and capture the request in a new field at first placement.**
  No consumer break, but the name stays ambiguous, and a consumer re-targeting a placed task
  would be silently ignored, because the scheduler would read the captured value.
- **Use `reserved_on` as the assignment and add nothing.** It is cleared on release, so a finished
  task would lose where it ran, and the writer could not produce the view for old readers.
- **Treat a placed task in an old snapshot as having no request.** The reason would always be
  true, but it silently drops real requests, and `target_node` is the one that matters.
- **`#deprecated` on the view.** It would warn in every consumer build for a name that still
  gives the right answer. Revisit once consumers have moved.
