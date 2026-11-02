# 0017 — CPU work goes to accelerator nodes last

**Status**: Accepted
**Date**: 2026-11-02

## Context

`_best_fit_node` ranks the nodes that fit by utilization, the mean of CPU and memory in use, and breaks
a tie by the smaller id ([ADR-0004](0004-deterministic-tie-breaks.md)). Nothing in that ranking knows
about devices. So a task that needs no accelerator can land on the only GPU node because it is a little
emptier, or because it ties and its id sorts first, while a CPU node has room. The GPU node's cores and
memory then fill with CPU work, and the next GPU task waits for them while its device sits free.

## Decision

**For a request that needs no accelerator, a node with no accelerator beats any node that has one.
Within each group, best fit is what it was.**

1. **What counts.** A node has an accelerator if any of its profiles is of a type other than
   `ACCEL_CPU`, whether or not it is in use. A device in use now is free later.
2. **The order** for a `REQ_NONE` request is: no accelerator first, then least utilization, then the
   smaller id. Every other request ranks as before.
3. **A requested node still comes first.** A task that names a node and fits there goes there.
4. **It is a ranking, not a refusal.** CPU work still goes to an accelerator node when nothing else
   fits, and never waits for a CPU node.

## Consequences

- **Positive** — CPU work leaves accelerator nodes' cores and memory to the work that needs their
  devices, until the CPU nodes are full.
- **Negative** — **Decisions change** where both kinds of node fit: CPU work now goes to a CPU node even
  when a GPU node is emptier. A fleet of only CPU nodes, or only accelerator nodes, decides as before.
- **Negative** — A busy CPU node is chosen over an idle GPU node, so CPU work can run more crowded than
  it did.
- **Neutral** — Preemption is unchanged: it asks whether any node fits, not which ranks first.

## Alternatives considered

- **Prefer CPU nodes only on a tie,** the roadmap's first wording. A GPU node a little emptier still
  takes the work, which is the case that strands accelerator work.
- **Hold back a fixed amount of a GPU node's CPU.** It needs a number per node, which is new node state
  on the wire, and the right number depends on the work.
- **Never put CPU work on an accelerator node.** That idles capacity, and a fleet of GPU nodes could
  run no CPU work at all.
- **A label on the node,** as Kubernetes taints do. New wire state, and every consumer would have to set
  it. Whether a node has a device is already known.
