# 0016 — A request takes several whole devices, or a share of one

**Status**: Accepted
**Date**: 2026-11-02

## Context

[ADR-0013](0013-accelerators-are-reserved.md) made the profile the unit: a task takes one whole device,
or chips of one TPU pod. Two things real work asks for could not be said:

- **Half a GPU.** Inference services and notebooks share a device. Through 1.4.2 any number of tasks
  shared one by accident; since 1.4.3 none can.
- **Four GPUs.** Training spans several devices on one node. `accel_min_chips` counts chips of one pod,
  and ai-hwaccel's `requirement_satisfied` ignores it for everything else, so `REQ_GPU` means one GPU.

Constraints on the answer:

- **Consumers call `resource_req_new` with six arguments.** Its signature cannot change in 1.x.
- **A pass only fills nodes** ([ADR-0015](0015-a-pass-only-fills-nodes.md)): taking part of a device
  must never leave room for a request that had none.
- **Decisions are deterministic** ([ADR-0004](0004-deterministic-tie-breaks.md)), and capacity sums
  must be exact. CPU is f64 and needs a rounding margin for that reason; a device need not.
- **Snapshots.** Every release so far reads every earlier snapshot, and a snapshot that does not use a
  feature has kept its bytes.

## Decision

**A request names how many devices it takes, or what share of one, in thousandths. Exclusive stays the
default, and only a request that uses either writes it.**

1. **Two fields on `ResourceReq`.** `accel_devices`: how many devices, default 1. `accel_share`:
   thousandths of one device, default 1000, which is all of it. A share below 1000 is of a single
   device; a request for several devices takes each of them whole. Integers, so shares add exactly.
2. **Units on a profile.** A TPU pod offers its chips, and a request takes chips of it as ADR-0013
   says. Any other profile offers 1000 thousandths, and a request takes its share. A request takes
   `accel_devices` distinct profiles of one node, and is never split across nodes. A pod counts as
   one device.
3. **Which profiles.** Whole devices go by ai-hwaccel's ranking, as before: highest `profile_rank`, then
   most memory, then lowest index. A share goes first to a device that is already partly taken, then
   by that ranking, so it does not break a whole device while a shared one has room.
4. **Built, not passed.** `resource_req_new` keeps its arguments and builds one whole device.
   `resource_req_with_devices(req, n)` and `resource_req_with_share(req, thousandths)` set them, and
   return the request. The last one called wins: several devices are each whole, and a share is of one.
   Out of range settles, as every constructor's values do since 1.4.5: fewer than one device is one,
   and a share of 0 or less, or 1000 or more, is the whole device. Restore settles the same way.
   Placement reads a 0 in either field as the default too, since setters and the derive's decoder can
   leave one. `SAMAY_ACCEL_WHOLE` names 1000.
5. **On the wire only when used.** Both keys follow `disk_mb`, in the struct's order, and are written
   only for a request that is not one whole device. A snapshot that uses neither is byte for byte what
   1.4.6 writes. The derive's `ResourceReq_to_json` writes them always, and every reader takes both.
6. **Holds.** A request holds one entry per profile it took, a release gives every one back, and
   preemption's check takes them all away before asking whether the task would fit.
7. **A pass still only fills nodes.** Taking a share or a device only adds to what is in use. The pass's
   record of what fits nowhere compares both fields.

## Consequences

- **Positive** — "Half a GPU" is `resource_req_with_share(req, 500)`, and "four GPUs" is
  `resource_req_with_devices(req, 4)`. Two half-shares fill one device, and a third waits.
- **Positive** — Nothing changes for a request that uses neither: same placement, same bytes, and every
  older release reads the snapshot as before.
- **Negative** — **A release before 1.5.0 must not restore a snapshot holding a multi-device task.** It
  ignores the keys and replays one device for it, so the others look free while the task uses them.
  A share read that way is a whole device, counted past capacity, so nothing is offered twice.
- **Negative** — A share is of the device, not of its memory. Two half-shares of a 16 GB GPU are not
  checked to fit in 8 GB each; the executor has to hold them to it.
- **Negative** — Node choice still goes by CPU and memory, so two half-GPU tasks can land on two nodes
  and leave neither GPU whole.
- **Negative** — A multi-device task gets no preemption victim unless one running task frees enough,
  since one victim has to be enough (ADR-0013). 1.6.0 takes that on.
- **Neutral** — A TPU pod is still shared by chips. A share does nothing on a pod.

## Alternatives considered

- **A fraction as f64**, as in Ray's `num_gpus=0.5`. Sums of f64 shares round, which is why CPU has a
  margin, and a device does not need one.
- **Sharing by device memory.** It ties sharing to memory alone, and a profile can report none: the
  `gpu_available` convenience registers a CUDA profile with 0 bytes.
- **One field for both,** where 4000 is four devices and 500 half of one. 1500 then needs a rule, and two
  fields say what they mean.
- **New arguments to `resource_req_new`.** Every consumer's call would break.
- **Write both keys always.** Every snapshot's bytes would change for requests that use neither, and
  the fixtures from earlier releases would no longer write back as they came.

## Amendment (v1.5.1)

Point 5 wrote the two keys from the struct as it stood, so a 0 left by a setter or the derive's decoder
wrote both and lost them on the next restore. The writer now writes them as placement reads them, and
leaves them out for one whole device whatever the struct holds.
