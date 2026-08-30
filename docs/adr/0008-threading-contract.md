# ADR 0008 — samay is single-threaded by contract

**Status**: accepted (2026-08-30, v1.0.4).

## Context

Nothing in samay had ever documented a threading contract, and no audit had examined
one. The v1.0.3 sweep closed with concurrency listed as an explicitly unretired risk.
This ADR retires it.

Everything below was measured on x86_64 Linux, cyrius 6.5.36, with harnesses under the
session scratchpad — not reasoned about.

### What is already safe

- **The allocator.** `lib/alloc.cyr` guards the shared bump heap with a genuine atomic
  CAS spinlock plus acquire/release fences, and `lib/thread.cyr:321` arms
  `_threads_active` **before** the clone, so there is no startup window in which two
  threads run unlocked. Measured: 8 threads, 80,000 allocations, **0 overlapping blocks,
  0 corrupted tags**. This matters because every samay operation allocates; had it been
  unsafe, nothing else would be worth discussing.
- **`samay_uuid_v4`.** Backed by `getrandom(2)` with no shared PRNG state. Measured:
  200,000 uuids across 8 threads, **0 duplicates**, 0 malformed. `task_id` uniqueness —
  which ADR-0004's determinism argument depends on — holds under concurrency.
- **bayan's decimal tables** (`_d_init_tables`) fill *then* publish, so a racing thread
  either re-fills with identical constants or sees a complete table. Correct as written.

### What is not safe

**1. A shared `NodeCapacity` loses reservations, and the loss is towards over-admission.**
`node_capacity_reserve`/`release` are read-modify-write over plain `load64`/`store64`
(`src/types.cyr`) with no atomicity. Measured, 8 threads × 160,000 reserve operations on
one node:

| | expected | actual |
|---|---|---|
| `running_tasks` | 160,000 | **43,299** |
| `available_cpu` (milli) | 840,000 | **968,161** |
| `available_memory_mb` | 840,000 | **925,184** |

73% of the increments vanished, and the node believes it has *more* free capacity than it
does. That is the dangerous direction: samay would place work on a node with no room,
which is precisely the failure the "resource-aware placement" domain principle exists to
prevent.

**2. A shared `TaskScheduler` corrupts its own hashmap bookkeeping.** Measured, 8 threads
submitting 8,000 tasks to one scheduler: 7,999 tasks actually reachable (one lost
outright), and the map's internal count read **7,911** against **7,999** genuinely
occupied slots. The size field and the contents disagree — an invariant violation inside
`lib/hashmap.cyr`, not merely a lost update.

**3. A process-global lazy initialiser in `lib/chrono.cyr` can yield a wrong date.**
`_chrono_init_mdays` publishes `_chrono_mdays` at line 186 and only then fills it with 12
`store64`s. A thread entering that window sees the non-zero pointer, skips the init, and
reads an all-zero table; `epoch_to_date`'s month loop never breaks, falls out at `m == 12`,
and reports **month 13** with a day-of-year in the day slot. samay reaches this from
`cron_expr_matches`, so the damage is a cron entry evaluated against the wrong date.

This one is different in kind from 1 and 2: **it does not require sharing anything.** Two
threads with entirely separate schedulers still share that global. Measured at 14 of 200
process runs with threads tightly synchronised on their first `epoch_to_date`, and 1 of
400 through samay's own public API in the worst realistic shape.

**4. `lib/sakshi.cyr` holds substantial mutable global state** — ring-buffer write and
count indices, span depth, trace ids, output target — with no synchronisation. samay
emits warnings from several v1.0.3 paths. Concurrent logging can interleave or corrupt
log output. Damage is confined to observability, not scheduling.

## Decision

**samay is not thread-safe. One scheduler instance is owned by one thread at a time;
callers that need concurrent access must serialise it externally.**

That is the contract, and it is now stated in the README, in the `scheduler.cyr` and
`cron.cyr` module headers, and here.

**samay does NOT take an internal lock, and this is deliberate.** The decisive reason is
the shape of the API: `task_scheduler_get_task`, `task_scheduler_pending_tasks`,
`task_scheduler_tasks_for_node` and `cron_scheduler_list_entries` all hand the caller
**raw pointers** into scheduler-owned structs. A mutex inside samay would protect the
lookup and then release before the caller touches what it was given. The result would be
an object that *looks* thread-safe, invites the assumption, and still corrupts — strictly
worse than an honest contract. Making the API genuinely lockable means not returning
interior pointers, which is a redesign, not a patch.

**samay DOES close the chrono window**, because item 3 breaks callers who are honouring
the contract. `samay_init()` (additive, public) forces the lazy initialiser to run while
the caller is still single-threaded; `task_scheduler_new()` and `cron_scheduler_new()`
call it, so the ordinary shape — build the scheduler, then spawn workers — is safe with
no knowledge of it. Consumers using only the free functions (`cron_expr_parse`,
`cron_expr_matches`, `training_job_to_scheduled_task`) should call it once before
spawning. Measured 1/400 → 0/400.

The defect is in `lib/`, which samay must not modify (CLAUDE.md), so this closes the
window from outside rather than fixing the cause. **Upstream ask, filed against cyrius:**
`_chrono_init_mdays` should fill a local pointer and publish it last, the same
fill-then-publish order `lib/bayan-json.cyr`'s `_d_init_tables` already uses.

## Consequences

- Consumers get an explicit, honest contract where they previously had silence. kavach
  3.8.0 and daimon 2.0.0 are unaffected: neither calls samay from more than one thread.
- The Rust oracle enforced this statically — `&mut self` on every mutating method means
  the compiler rejected concurrent mutation outright. The Cyrius port cannot express
  that, so **a compile-time guarantee has been replaced by a documented runtime one.**
  That is a real loss of safety inherent to the port, recorded here rather than left
  implicit.
- ADR-0004's determinism guarantee is unaffected *within* the contract, and undefined
  outside it: concurrent submission makes arrival order nondeterministic, and while the
  sort is insertion-order independent, tasks created in the same nanosecond tie-break on
  a random uuid.
- Not addressed: an opt-in debug mode that detects concurrent entry and aborts. It would
  help consumers catch violations early and is worth considering if anyone adopts a
  multi-threaded shape.
