# 0013 — Accelerators are reserved, and preemption has to help

**Status**: Accepted. Points 1 and 2 extended by [ADR-0016](0016-several-devices-or-a-share-of-one.md)
(v1.5.0): a request can take several devices, or a share of one, and a device is counted in
thousandths. Point 5 superseded by [ADR-0018](0018-a-task-records-its-devices.md) (v1.5.1): replay in
placement order double-booked devices, so a task's holds are on the wire after all.
**Date**: 2026-11-01

## Context

The 1.4.3 P(-1) sweep ran the accelerator path with real profiles, which no audit had done, and found
that placement never consumed an accelerator. `can_fit` asked ai-hwaccel whether a device existed.
Nothing recorded that it had been taken, so one GPU went to four tasks, and one 8-chip TPU pod to
three tasks that each needed all 8 chips. No hostile input was involved. Only CPU and memory stopped
it, and on a node with ample of both, nothing did.

[ADR-0002](0002-ai-hwaccel-profile-placement.md) quotes the domain rule this breaks: never schedule an
accelerator task without checking availability. It delivered "is there such a device", and nobody
asked whether that was the same thing as "is it free".

`task_scheduler_preempt_if_needed` had the matching gap. It compared priorities and nothing else. It
would stop a job for a task that already fitted, that could never run, or that had already finished.
For an Emergency task needing a GPU it stopped the lowest-priority job anywhere, which was usually a
CPU job on another node, and did so on every round while the GPU's holder ran on.

## Decision

**A reservation takes accelerator capacity as it takes CPU and memory, and preemption returns a victim
only if stopping that victim places the task.**

1. **The unit is the profile.** A profile is one device, and a task takes the whole device. The
   exception is a TPU pod, which ai-hwaccel already describes by chip count: a task takes
   `accel_min_chips` chips of it, and tasks share the pod while chips remain.
2. **`accel_min_chips` applies to TPUs only.** That is ai-hwaccel's rule, and `requirement_satisfied`
   ignores it for every other requirement. `REQ_GPU` means one GPU whatever the count says. A task
   needing four GPUs across four profiles cannot be expressed. `REQ_GPU_OR_TPU` and
   `REQ_ANY_ACCELERATOR` do not check chips either, so such a request can name more chips than a pod
   has. It then takes the pod.
3. **`can_fit` now means free.** Selection among profiles keeps ai-hwaccel's ranking: highest
   `profile_rank`, then most memory, then lowest index.
4. **A node records which profile each reservation took.** Release has to give back that profile.
   Undoing a pick by requirement type alone frees the wrong one when requirements overlap: on a node
   with a TPU and a GPU, releasing a `REQ_ANY_ACCELERATOR` task could free the GPU a `REQ_GPU` task is
   using, and strand the TPU chip for good.
5. **Holds are not on the wire.** A task's `reserved_on` already says who holds what, so restore
   replays the holds in placement order, `scheduled_at` then `task_id`. Snapshots gain no key and their
   bytes do not change, and a snapshot from any earlier release restores correctly.
6. **Over-commitment stays visible.** A snapshot from 1.4.2 can hold four tasks on one GPU. All four
   are counted, past capacity, so the device is not offered again until the last of them is gone.
   Refusing the snapshot would lose running work, and dropping three of them from the count would
   offer the device while they run.
7. **`preempt_if_needed` answers only for a queued task that fits nowhere, and only names a victim
   whose node would then fit it.** Among those, the choice is unchanged: lowest priority, then newest.
   Checking leaves every number as it was: a release and a re-reserve would round the node's CPU.
8. **One victim has to be enough.** Stopping two tasks to free one space is a plan, and samay makes
   single decisions. Without this a task needing 8 cores on a node holding two 4-core tasks would stop
   one on every round, and the freed 4 cores would go straight back to it.

## Consequences

- **Positive** — The domain rule now holds. One GPU takes one task, an 8-chip pod takes 8 chips, and
  the next task waits in the queue, logged, until they are free.
- **Positive** — Following a `PreemptionAction` now places the task, and can no longer livelock.
- **Positive** — The accelerator path is measured for the first time: see
  [`benchmarks.md`](../benchmarks.md).
- **Negative** — **Placement changes for anyone with accelerators.** Work that used to pile onto one
  device now queues. That is the fix, but a consumer that relied on sharing a GPU between tasks will
  see tasks wait. There is no way to ask for sharing yet; it would be a new requirement field.
- **Negative** — `preempt_if_needed` returns less. A consumer calling it with no node registered, or
  with a running task that holds no reservation, now gets 0. No consumer calls it today, and the
  oracle-ported tests that pinned the old behaviour were rewritten around real contention.
- **Negative** — SCHEDULED tasks are not preempted, though they hold capacity like running ones. A
  node full of placed but unstarted low-priority work yields no action.
- **Negative** — Replay rebuilds which task holds which profile from placement order. After a release
  that order can differ from what happened: on a node whose profiles overlap, a restored scheduler may
  assign a later task to a different profile than the original would have. Counts stay exact, and the
  same snapshot always restores to the same state. *Wrong, found in v1.5.1:* per-profile counts did not
  stay exact, and a busy device was offered again. ADR-0018 records the holds. The decisions name nodes, not devices, so this only
  matters when one overlapping requirement could fit on one profile and not on the other.
- **Neutral** — Device identity stays unexposed. A decision names a node, and which GPU to use is the
  executor's business.

## Alternatives considered

- **Put holds on the wire.** Exact across a restore, but it is new state for every reader, and an old
  snapshot would still need the replay. The reservations already record the fact.
- **Counters per profile, with no per-reservation record.** Simpler, and it leaks: see point 4.
- **Shared GPUs by default, with a limit.** Sharing is real, but nothing in the domain asks for it yet,
  and exclusive is the only default that cannot silently break a workload.
- **Leave `preempt_if_needed` alone and document it.** A function called "if needed" that does not check
  need, and now the main way an urgent task reaches a held device, is a defect, not a limitation.
- **Multi-victim preemption.** Possible later, but it needs a search and a return type that names
  several tasks, and it changes what a consumer has to do with the answer.
