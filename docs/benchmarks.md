# samay benchmarks

x86_64 Linux · cyrius 6.5.36 · `cyrius bench tests/samay.bcyr`.
Baseline refreshed 2026-08-29 (v1.0.3).

| Op                      | avg      | v1.0.2   | notes                              |
|-------------------------|----------|----------|------------------------------------|
| `priority_from_numeric` | 4 ns     | 4 ns     | pure                               |
| `node_can_fit`          | 27 ns    | 28 ns    | REQ_NONE fast path (cpu/mem/disk)  |
| `cron_expr_matches`     | **22 ns**| 282 ns   | **12× — alloc-free prefilter**     |
| `samay_uuid_v4`         | 606 ns   | 613 ns   | getrandom(2) syscall-bound         |
| `scheduled_task_new`    | 2.07 µs  | 2.06 µs  | alloc + uuid + `dt_now`            |

## v1.0.3 — the two measured wins

**`cron_expr_matches`: 282 ns → 22 ns, and the miss path no longer allocates.**
`epoch_to_date` (lib/chrono.cyr) does an unconditional `alloc(48)` into a bump allocator
that never frees, then walks year-by-year from 1970. The matcher called it *before*
testing a single bitmask. Minute, hour and day-of-week are all derivable with plain
arithmetic, so they now run first and the calendar decomposition is reached only by a
candidate that has already passed them.

Measured over 100,000 calls that miss on the minute field:

| | bytes allocated |
|---|---|
| v1.0.2 | 4,800,000 |
| v1.0.3 | 3,312 |

The 3,312 residual is exactly the 69 calls whose minute *and* hour matched and which
therefore legitimately need the calendar. This closes the "alloc-free cron matching"
roadmap item carried since M2.

The reordering must be behaviour-identical, so it is gated by
`test_cron_matcher_differential`: an independent reference matcher kept in the test file,
compared across 20 expressions × 3,000 consecutive minutes plus boundary instants. The
pre-release sweep ran the same differential at 1,610,253 pairs (81,564 genuine hits) with
zero mismatches. Note this is *separate* from the Vixie DOM/DOW correction in the same
release — that one deliberately changes results for `*/N` in DOM/DOW (ADR-0006).

**Placement scan: one `map_values` per `schedule_pending`, not one per pending task.**
`_best_fit_node` rebuilt the entire node vector on every call. Measured at 200 nodes ×
500 pending tasks:

| | bytes allocated |
|---|---|
| v1.0.2 | 1,996,000 |
| v1.0.3 | 3,992 |

500× — exactly the pending-task count, as expected. Wall-clock is roughly unchanged; the
win is allocator pressure, which matters because nothing here is reclaimed.

## Still open

`node_can_fit` benches the `REQ_NONE` common path (the accelerator check short-circuits
before touching profiles); the accelerator path adds one `find_satisfying_profile` scan
over the node's profile vec (M3, ADR-0002) and is **not** benchmarked — the numbers above
understate the cost of exactly the workload the domain principles are written about.

The four insertion sorts (audit F5) are untouched: measured ~85× slower than a merge sort
at n=8000, but ADR-0004's determinism guarantee rides on those comparators and v1.0.3 was
already cron- and JSON-heavy. Tracked in [`development/roadmap.md`](development/roadmap.md).

Re-run and update on any hot-path change. Never claim a performance win without
before/after numbers (project rule).
