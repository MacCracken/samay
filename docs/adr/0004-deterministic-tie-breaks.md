# ADR 0004 — Deterministic scheduling via explicit tie-breaks

**Status**: accepted (2026-07-21, v0.6.0-dev / M5). Intentional divergence from the
`rust-old/` oracle.

## Context

samay's domain principle (CLAUDE.md) requires **deterministic scheduling**: the same
schedule at the same time must produce the same decisions, and ordering-sensitive output
must never depend on hashmap iteration order.

The Rust original (`rust-old/src/lib.rs`) stored tasks and nodes in
`std::collections::HashMap`, whose iteration order is randomized (SipHash with a
per-process seed). Its ordering logic left ties to that order:

- `pending_tasks` / `schedule_pending`: `sort_by(priority desc, then created_at asc)` —
  tasks equal on **both** keys keep `.values()` order.
- `best_fit_node`: `.values().min_by(utilization)` — `min_by` returns the **first**
  minimum in iteration order, so equal-utilization nodes tie by HashMap order.
- `preempt_if_needed`: manual scan; a candidate equal on priority **and** created_at keeps
  the first seen.
- `tasks_for_node`: returns `.values()` filter order — no sort at all.
- `CronScheduler::list_entries` / due-check: `.values()` order.

The Cyrius port faithfully reproduced these, so it inherited the non-determinism: two
schedulers built from identical data in different insertion orders could make different
placements, and a snapshot could not be reasoned about.

## Decision

Add an explicit final tie-break on the type's **unique key** everywhere ordering-sensitive
output is produced, turning every "arbitrary among equals" choice into a **total order**.
A single shared comparator `samay_str_lt` (lexicographic, unsigned byte-wise, in
`types.cyr`) backs all of it.

| site | primary order | added tie-break |
|---|---|---|
| `_task_before` (pending/schedule) | priority desc, created_at asc | `task_id` asc |
| `_best_fit_node` | utilization asc | `node_id` asc |
| `task_scheduler_preempt_if_needed` | priority asc, created_at desc | `task_id` asc |
| `task_scheduler_tasks_for_node` | — | `task_id` asc |
| `cron_scheduler_list_entries` | — | entry `name` asc |
| `cron_scheduler_check_due_at` | — | entry `name` asc (before firing/logging) |

`task_id` (a v4 UUID), `node_id`, and cron entry `name` are unique map keys, so each
tie-break is total. JSON serialization was already made deterministic in M4 (maps emit as
key-sorted arrays); it now shares the same `samay_str_lt` comparator.

## Consequences

- **Divergence from Rust in tie cases only.** Where Rust's answer was a coin-flip
  (HashMap order), samay now returns the lexicographically-smallest key. Non-tied
  decisions are unchanged, so all 130 parity assertions still pass. Matching Rust
  bit-for-bit in ties was never possible — its order was random, not a stable oracle.
- The determinism guarantee is now **tested**: `test_det_schedule_pending` builds two
  schedulers in opposite insertion order and asserts an identical decision sequence;
  `test_det_best_fit_tie`, `test_det_tasks_for_node`, `test_det_cron_list` pin each
  tie-break. (281/281 assertions.)
- Cost is O(k log k)-ish insertion sorts over already-small per-node/per-query sets; the
  scheduler benchmarks are unaffected.
- This closes the M5 "determinism guarantees (same schedule + same time → same decisions)"
  v1.0 criterion. Fuzz harnesses (stress insertion-order permutations) and the security
  audit remain open M5 items.
