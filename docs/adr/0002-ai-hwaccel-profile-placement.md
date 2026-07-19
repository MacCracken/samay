# ADR 0002 — Resource-aware placement via ai-hwaccel profiles

**Status**: accepted (2026-07-18, v0.4.0) — fulfills the v1.0 item deferred in
[ADR 0001 §6](0001-port-representation.md).

## Context

The 0.2.0 parity port (ADR 0001 §6) kept Rust's *self-contained* accelerator
match: `NodeCapacity` carried flat `gpu_available` / `tpu_available` /
`tpu_chip_count` booleans, and `can_fit` hand-matched the `REQ_*` requirement
against them. Two problems:

1. **The Rust match had a stub arm.** `REQ_GAUDI`, `REQ_AWS_NEURON`, and
   `REQ_ANY_ACCELERATOR` all fell into Rust's `_ => true` — so a node with **no
   accelerator at all** was reported as able to fit a Gaudi/Neuron/any-accel
   task. That violates samay's domain rule: *never schedule an accelerator task
   without checking availability.*
2. **It duplicated ai-hwaccel.** ai-hwaccel already owns the authoritative
   requirement-vs-hardware logic (`requirement_satisfied`), the accelerator
   taxonomy (`ACCEL_*` families), and device profiles (`profile_cuda` /
   `profile_tpu` / `profile_gaudi` / `profile_neuron`). samay re-implementing a
   subset guarantees drift.

## Decision

`NodeCapacity` holds a **vec of real ai-hwaccel accelerator profiles**
(`accel_profiles`) instead of the flat booleans. Placement delegates to
ai-hwaccel:

```
fn _accel_ok(req_ar, req_chips, node) {
    if (req_ar == REQ_NONE) { return 1; }
    if (find_satisfying_profile(req_ar, req_chips, NodeCapacity_accel_profiles(node)) != 0) { return 1; }
    return 0;
}
```

- `node_capacity_add_accel(node, profile)` attaches any ai-hwaccel profile
  (`profile_cuda` / `profile_rocm` / `profile_tpu` / `profile_gaudi` /
  `profile_neuron`) — chainable.
- The parity constructors are kept and translate to profiles:
  `node_capacity_new(…, gpu_available=1)` registers one `profile_cuda`;
  `node_capacity_with_tpu(node, chips)` registers a `profile_tpu`.
- `requirement_satisfied` also honors each profile's `profile_available` flag,
  so a profile can advertise a device that is present-but-unavailable.

## Consequences

- **Behavior change (intended) vs the Rust oracle**: `REQ_GAUDI` /
  `REQ_AWS_NEURON` / `REQ_ANY_ACCELERATOR` now require an *actual* matching
  profile on the node, rather than always fitting. A GPU node no longer fits a
  `REQ_GAUDI` task. This is a correctness improvement, not silent drift — it is
  the whole point of M3, and is covered by regression tests
  (`test_node_gaudi_requires_profile`, `_neuron_`, `_any_accelerator`).
- samay no longer encodes accelerator taxonomy; adding a new accelerator family
  in ai-hwaccel is picked up automatically.
- `NodeCapacity`'s serialized shape changes (a profile list, not three bools) —
  consistent with ADR 0001's note that serde shape already differs from Rust.
- `REQ_TPU` min-chips semantics are unchanged (now enforced by
  `requirement_satisfied` via `profile_tpu_chips >= min_chips`).

## Alternatives considered

- *Keep the flat booleans, only fix the `_ => true` arm.* Rejected: still
  duplicates ai-hwaccel and can't express multi-accelerator or non-GPU/TPU nodes.
- *Store a single profile per node.* Rejected: real nodes are heterogeneous
  (e.g. GPU + Neuron); a vec + `find_satisfying_profile` is ai-hwaccel's own model.
