# 0015 — A pass only fills nodes, so it skips what it already knows fits nowhere

**Status**: Accepted
**Date**: 2026-11-02

## Context

`task_scheduler_schedule_pending` walks every node for every pending task: the preferred node first,
then `_best_fit_node` over the whole table. A task that fits nowhere costs the same walk as one that
is placed, on every pass, for as long as it waits. On 1.4.5, one pass over 100,000 tasks that fit no
node, against 100,000 nodes, took 756 s.

Stuck queues are rarely varied. A queue waiting on capacity holds many tasks asking for the same few
things, and a full fleet refuses most of them on one dimension: no node has the cores free.

The pass is also where determinism matters most ([ADR-0004](0004-deterministic-tie-breaks.md)): each
decision depends on every decision before it, through the capacity they took.

## Decision

**A pass refuses, without walking, a requirement it already knows fits nowhere. That knowledge rests on
one fact about a pass, and is dropped when the fact fails.**

1. **The fact: a pass only fills nodes.** A placement subtracts cpu, memory and disk, and holds a
   device. Nothing gives any of it back until the next pass reconciles. So whether a requirement fits a
   node can go from yes to no during a pass and never from no to yes, and a requirement that fit no node
   earlier in the pass fits none later.
2. **A record of shapes that fit nowhere.** When `_best_fit_node` finds nothing, the pass records the
   requirement. A later requirement equal in the fields `node_capacity_can_fit` reads (cores, memory,
   accelerator, chips, disk, and since 1.5.0 devices and share) is refused without the walk. `network` is not read, so it is not
   part of the shape. Cores compare with `f64_eq`, so 0 and -0 are one shape, as can_fit sees them, and
   a NaN matches nothing, which costs only a walk.
3. **Limits from the nodes.** When the first task of a pass looks past its preferred node, the pass
   takes the most cpu, memory and disk free on any one node. A requirement past any of them fits
   nowhere, the first time it is seen too. A node with NaN cores free lets anything past can_fit's cpu
   test, so it lifts the cpu limit.
4. **When the fact fails, start again.** Constructors cannot build a requirement or node that gives
   capacity back when reserved, but setters can: a negative amount, a node a hair below zero cores that
   rounds up to zero, or a TPU profile with fewer than no chips. After each placement the pass compares
   the node's free cpu, memory, disk and devices in use with what they were. If anything grew, it forgets
   every shape and takes the limits again.
5. **The record lives on the pass's stack.** 1,024 slots of requirement pointers, probed linearly and
   filled to half at most, then its count and the three limits: 8,224 bytes. Nothing is allocated,
   because `alloc()` never frees, and nothing is shared between schedulers, so separate schedulers on
   separate threads stay separate ([ADR-0008](0008-threading-contract.md)). A pass with more than 512
   shapes that fit nowhere walks the rest for every task, as 1.4.5 did. A pass whose tasks all fit
   their preferred nodes never builds the record.

Every skip replaces a walk whose answer was already known to be "no node", so every decision, score,
log line and node state is the one a full walk gives.

## Consequences

- **Positive** — A stuck queue costs what its log lines cost. 100,000 stuck tasks against 100,000
  nodes take 0.18 s a pass, down from 756 s. At 20,000 × 20,000, one repeated shape, a different size
  per task past every node, and a full fleet with 1,024 shapes each fall from about 9.5 s to 42 ms
  ([benchmarks](../benchmarks.md#v146--a-pass-that-skips-what-fits-nowhere)).
- **Positive** — The proof is on real binaries. A differential builds the same harness against 1.4.5
  and 1.4.6 and runs 3,000 seeded scenarios of four passes each, plus one probe per way a skip could
  go wrong, printing every decision, every log line and every node's state: 2,332,935 lines,
  identical. At 300 seeds it differed for each of 15 planted mistakes, among them dropping any one
  field from the shape, `<=` for `<` on any limit, and ignoring growth in any one of cpu, memory, disk
  or devices. Dropping a field from the comparison alone hides behind the hash, so the suite tests
  the comparison directly.
- **Negative** — A task that is placed still walks every node, so a pass that places `p` tasks is
  still O(p × nodes). The record only removes the walks that find nothing. Placing 500 tasks on 500
  nodes takes 18.2 ms a pass before and after.
- **Negative** — A pass whose stuck tasks are all different, and each inside every limit, gains
  nothing past the 512th shape and pays a probe per task: 20,000 such tasks against 20,000 nodes took
  12.57 s against 1.4.5's 12.50, within the runs' spread.
- **Negative** — The fact in point 1 is now load-bearing. A feature that gives capacity back during
  a pass, or makes fitting depend on something other than what a node has free, must reset the record
  where it does so, or decisions change. 1.5.0's shared devices are the one to watch: whatever sharing
  means, taking a share must never leave room for something that had none. Preemption runs outside a
  pass. `test_schedule_skips_soundly` and the differential are where a break shows.

## Alternatives considered

- **Index nodes by what they have free**, so best-fit finds its node without a walk. That would cut the
  placed tasks' walks too, but best-fit ranks by utilization, which every placement changes, ties go to
  the smaller id, and f64 sums round, so the index would have to reproduce `_best_fit_node`'s exact
  answer under every update. That is a larger change to the path determinism rests on, for the case
  that already makes progress.
- **Skip a shape that asks for at least as much as a known one.** It would catch more, but finding a
  known shape below a new one is a search over every known shape, and accelerator requirements do not
  order: a GPU-or-TPU request is not more or less than a TPU one.
- **Keep the record on the scheduler across passes.** Capacity comes back between passes, so it would
  have to be emptied at the start of each anyway, and a heap record either grows without freeing or
  changes `TaskScheduler`'s layout.
- **Stop logging a stuck task after the first pass.** It would make the remaining cost smaller, but the
  line is the one operational signal this loop gives, and that is a change in behaviour, not in cost.
