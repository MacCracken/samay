# 0018 — A task records its devices, and a node has at most 1,024

**Status**: Accepted
**Date**: 2026-11-02

## Context

[ADR-0013](0013-accelerators-are-reserved.md) kept device holds off the wire. A restore replayed every
reservation in placement order and let each one pick its devices again, on the claim that "counts stay
exact" and only which profile a task holds could change. The 1.5.1 audit showed that was wrong, by two
auditors working apart, on ordinary schedules:

- **A finished task between two others changes the replay.** On a node with a GPU and a Gaudi, `x` takes
  the GPU, `f` (any accelerator) the Gaudi, `x` finishes, and `y` takes the GPU. Replayed, `f` comes
  first and takes the GPU, and `y` is counted on top of it, past capacity, while the Gaudi shows free.
  The next Gaudi task is placed on the device `f` is running on.
- **Shares repack.** Two GPUs at 1000 and 1000 thousandths restored as 1400 and 600, and a share was
  sold on the full one.
- **A node re-registering with the same hardware** replayed the same way, with no snapshot at all.

A second defect was the cost of replay. Holding several devices picked them one at a time, each pick a
walk of every profile, and nothing limited how many profiles a node had. A 1 MB snapshot of one node
and one task holding 32,000 devices took 87 seconds to restore.

## Decision

**A task's devices are written with it, a restore and a re-registration take exactly those, and a node
has at most `SAMAY_MAX_NODE_DEVICES` profiles.**

1. **`held_profiles` on the wire.** A task holding devices writes the indices of the profiles it holds
   on its node, lowest first, as `"held_profiles":[...]` at the end of its record. It is written only
   by the scheduler's snapshot, which knows the node, and only for a task holding a device, so a
   snapshot without devices is what 1.5.0 wrote. Readers before 1.5.1 ignore the key.
2. **Restore takes the record when it fits.** Each index must be a profile on the node that satisfies
   the request, none twice, and no more than the request takes. Room is not asked: the record is what
   was held, past capacity or not. A record that does not fit is chosen again as before, and logged. A
   record that is not a list of whole numbers refuses its task, as any wrong type does
   ([ADR-0005](0005-restore-input-validation.md)).
3. **Re-registration carries holds by index.** The old node knows which profiles each task held, and the
   new description takes the same indices where they still fit; where the hardware changed, they are
   chosen again.
4. **At most 1,024 profiles a node.** `node_capacity_add_accel` past the ceiling adds nothing and logs
   it, and a snapshot with a node past it is refused, as the item limit refuses one. It is a `var`, so a
   consumer can raise it.
5. **Whole devices are held in one walk.** Their order is ai-hwaccel's ranking alone, so a node keeps
   its profiles sorted in that order, built when a hold first needs it, and a hold of several devices
   takes them in one pass. A share still asks which devices are in use, and picks as before.

## Consequences

- **Positive** — A restored or re-registered scheduler holds the same devices as the live one. The
  auditors' random checker, which found per-profile counts wrong within a few hundred steps on 1.5.0,
  finds none over 32 runs of 3,000 steps.
- **Positive** — Restore cost no longer grows with what a document can claim. A thousand tasks each
  holding 1,024 devices restore in 0.17 s; the worst shape at the ceiling, 100,000 over-committed
  one-GPU tasks on one node, takes 5.4 s for a 38.6 MB document, against 1.9 s for an ordinary one of
  that size.
- **Negative** — Snapshots with devices gain a key: 1.5.1 writes bytes 1.5.0 did not, for any task
  holding a GPU, TPU or other accelerator. 1.5.0 reads them, ignoring the key, as before.
- **Negative** — A snapshot from before 1.5.1 has no record, so its holds are chosen by replay, with the
  defect above, until it is written again.
- **Negative** — A node with more than 1,024 accelerator profiles cannot be registered whole. No host
  has that many devices; a TPU pod is one profile.
- **Neutral** — Device identity is still not in a decision. The record is an index into the node's own
  profiles, for samay to restore, not for an executor to read.

## Alternatives considered

- **Replay most constrained first.** Placing the tasks with fewest satisfying profiles first fixes the
  GPU-and-Gaudi case, but packing shares and chips is bin packing, and no replay order is exact in
  general. A record is exact.
- **Record holds on the node instead.** The tasks are the record of who holds what since
  [ADR-0007](0007-reservation-lifecycle.md), and a node's record would have to name tasks.
- **No ceiling, only a faster hold.** One walk per hold still makes a restore cost tasks times profiles,
  and both are limited only by 100,000 items.
