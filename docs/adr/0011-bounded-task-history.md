# 0011 — The stdlib sort, explicit task removal, and refusing an oversized snapshot

**Status**: Accepted
**Date**: 2026-11-01

## Context

Audit finding F5 had two halves. samay carried four hand-written insertion sorts, O(n²) on
collections a snapshot can fill to 100,000 items. And finished tasks stayed in
`TaskScheduler.tasks` forever, because there was no way to remove one. A third gap sat beside
them: [ADR-0005](0005-restore-input-validation.md) capped what restore accepts, but nothing
capped what the writers emit, so samay could write a snapshot it would then refuse to read.

The roadmap planned to consolidate the sorts, swap in a merge sort, add removal and pruning, and
cap the write side. Reading the code changed that plan in two places and added to it in one:

1. **A merge sort would leak on every pass.** `alloc()` is a bump allocator that never frees, and
   `schedule_pending` sorts on every call. `lib/vec.cyr` already has `vec_sort_by`: an introsort,
   O(n log n) in the worst case, that allocates nothing. Its header gives this exact reason for
   not being a merge sort.
2. **"Cap the write side" cannot mean truncate.** A snapshot missing records drops them silently,
   which samay never does.
3. **Capacity was released in hashmap order.** `node_capacity_release` adds f64s, and once a sum
   crosses a power of two the order of the adds changes the low bits. Map order changes with the
   per-process hash seed. Over 200 runs of one schedule on 1.3.0, `available_cpu` took 5 different
   values, from 92.57142857142854 to 92.5714285714286. That breaks
   [ADR-0004](0004-deterministic-tie-breaks.md): the same schedule gave different snapshot bytes,
   and could break a utilization tie differently.

## Decision

**Every sort is `vec_sort_by`, removal is explicit and limited to finished tasks, a snapshot past
the ceiling is refused whole, and capacity is released in `task_id` order.**

1. **The four sorts become `vec_sort_by` with one comparator each**: `_task_cmp`, `_task_id_cmp`,
   `_node_id_cmp` and `_entry_name_cmp`, over a shared `_samay_str_cmp`. `samay_str_lt` keeps its
   meaning and now calls that. `vec_sort_by` is not stable, and need not be. ADR-0004 made every
   one of these a total order ending on a unique key, so each has exactly one sorted result.
2. **`task_scheduler_remove_task(s, id)` refuses a task that is not finished**, with `Err(2)`.
   COMPLETED, FAILED and CANCELLED are finished. PREEMPTED is not: it goes back to QUEUED. A running
   task is still using its node, so removing it would hand that capacity to something else. The
   caller cancels first. A finished task can still hold a reservation, if a consumer drove it there
   through `scheduled_task_transition`, and removal returns it.
3. **`task_scheduler_prune_terminal(s, before_ns)` removes finished tasks that completed strictly
   before `before_ns`**, and returns how many went. samay never prunes on its own. The caller
   passes the time, as `cron_scheduler_check_due_at` takes it, so the same schedule at the same
   time prunes the same tasks. A task with no `completed_at` counts as the oldest.
4. **A writer past `SAMAY_JSON_MAX_ITEMS` refuses the whole snapshot**: it logs an error and answers
   `0`, from `*_to_jsonv` and `*_to_json_str`. This covers all four collections restore caps: tasks,
   nodes, cron entries and a node's accelerator profiles. A refused node refuses its scheduler.
5. **`_reconcile_reservations` and pruning release in `task_id` order.** Reconciling collects only
   the tasks that need releasing, so a normal pass allocates nothing extra.

## Consequences

- **Positive** — `task_scheduler_pending_tasks` at the 100,000-task ceiling takes 58.0 ms, down from
  57.9 s, with no allocation added on any pass. About 70 lines of sorting go. A long-lived scheduler
  can drop its history. samay cannot write a snapshot it would refuse to read. The same schedule now
  leaves the same capacity on every run: 200 runs, 200 hash orders, 1 value.
- **Positive** — Order is proven unchanged. 3,500 random inputs match the old insertion sort element
  for element, using its logic kept separately in the test, with priority and `created_at` tied
  constantly. A 6,000-task snapshot gives 1.3.0 and 1.4.0 byte-identical output: re-serialization,
  pending order, per-node order and every decision.
- **Negative** — `task_scheduler_to_json_str` and its siblings can now answer `0`. Through 1.3.0 they
  always returned a Str, so a caller that does not check will fault. This takes more than 100,000
  items, and restore would have refused that snapshot anyway.
- **Negative** — Removal does not return memory. `alloc()` never frees, so a removed task's struct
  stays allocated. What comes back is its share of each pass, and the snapshot. The hash table also
  keeps its peak capacity, so `map_values` walks those slots until the process restarts; a rebuild
  clears tombstones but does not shrink. A pass with nothing to place takes 21.7 ms over 100,000
  finished tasks, 2.22 ms once they are pruned, and 0.69 µs on a scheduler that never grew.
  `test_prune_churn` shows that repeated pruning at a steady size stays bounded.
- **Negative** — `task_scheduler_stats` counts the tasks it can see, so pruning lowers `completed`,
  `failed`, `total_tasks` and the averages. samay keeps no running totals, and adding them would be
  new wire state. A consumer that needs lifetime counts should read them before pruning.
- **Neutral** — Tombstones count toward a rebuild from cyrius 6.6.20. A consumer pinned below that
  should move up before pruning heavily.
- **Neutral** — The determinism fix changes low bits of `available_cpu` compared with some 1.3.0 runs.
  Those runs already disagreed with each other.

## Alternatives considered

- **A merge sort, as the roadmap planned.** Its scratch buffer leaks on every pass under `alloc()`.
  `fl_alloc` could reclaim it, but that is a second sort for samay to carry and test, for a stability
  no comparator here needs.
- **Sort every task in `_reconcile_reservations`.** Simpler, but O(n log n) on every pass to protect
  a path that usually has nothing to release.
- **Truncate an oversized snapshot.** Silent loss of arbitrary records, chosen by `task_id` order.
- **Write it anyway.** Restore refuses the whole document, so the failure moves to the moment the data
  is needed, when nothing can prune it. Refusing leaves the last good snapshot in place and the
  process alive to fix it.
- **Let `remove_task` take any status.** The roadmap's "releases any held reservation" read that
  way. It lets one call free capacity a running task is still using.
- **Prune automatically.** It would change `stats` and task history with no caller asking.
