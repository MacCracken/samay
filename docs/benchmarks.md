# samay benchmarks

x86_64 Linux · cyrius 6.5.36 · `cyrius bench tests/samay.bcyr`.
Baseline refreshed 2026-08-29 (v1.0.3); **re-run and confirmed unchanged at
v1.0.4** (2026-08-30) — that release added only `samay_init()`, a one-time
pre-warm off every hot path, and re-measured within noise of the table below
(28 / 4 / 628 ns, 2.14 µs, 23 ns).

| Op                      | avg      | v1.0.2   | notes                              |
|-------------------------|----------|----------|------------------------------------|
| `priority_from_numeric` | 4 ns     | 4 ns     | pure                               |
| `node_can_fit`          | 27 ns    | 28 ns    | REQ_NONE fast path (cpu/mem/disk)  |
| `cron_expr_matches`     | **22 ns**| 282 ns   | **12× — alloc-free prefilter**     |
| `samay_uuid_v4`         | 606 ns   | 613 ns   | getrandom(2) syscall-bound         |
| `scheduled_task_new`    | 2.07 µs  | 2.06 µs  | alloc + uuid + `dt_now`            |

## v1.2.2 — ai-hwaccel 2.5.5 → 2.5.6

1.2.1 against 1.2.2, both on cyrius 6.7.18, 60 rounds interleaved, shuffled and pinned to one
CPU (2026-11-01). The machine was quiet (load under 3). Medians:

| Op                      | 1.2.1    | 1.2.2    | Δ      |
|-------------------------|----------|----------|--------|
| `priority_from_numeric` | 4.06 ns  | 4.04 ns  | −0.3%  |
| `node_can_fit`          | 12.18 ns | 12.19 ns | +0.1%  |
| `cron_expr_matches`     | 13.30 ns | 13.37 ns | +0.5%  |
| `samay_uuid_v4`         | 617.5 ns | 618.0 ns | +0.1%  |
| `scheduled_task_new`    | 2.23 µs  | 2.24 µs  | +0.2%  |
| snapshot restore        | 196.0 µs | 196.1 µs | 0.0%   |
| snapshot write          | 279.2 µs | 279.4 µs | +0.1%  |

No row is under p = 0.05. The snapshot rows use the same scratch harness and 5.8 KB snapshot as
v1.2.1. The restore cost v1.2.1 took on from bayan 1.11.1 stays.

## v1.2.1 — cyrius 6.7.9 → 6.7.18, bayan 1.5.13 → 1.11.1

1.2.0 on cyrius 6.7.9 against 1.2.1 on 6.7.18, 60 rounds interleaved, shuffled and pinned to
one CPU (2026-11-01). Medians:

| Op                      | 1.2.0    | 1.2.1    | Δ       |
|-------------------------|----------|----------|---------|
| `priority_from_numeric` | 5.33 ns  | 5.41 ns  | +1.4%   |
| `node_can_fit`          | 14.68 ns | 14.79 ns | +0.7%   |
| `cron_expr_matches`     | 18.26 ns | 18.00 ns | −1.4%   |
| `samay_uuid_v4`         | 770.5 ns | 780.0 ns | +1.2%   |
| `scheduled_task_new`    | 2.57 µs  | 2.59 µs  | +0.6%   |
| snapshot restore        | 130.3 µs | 204.2 µs | **+56.8%** |
| snapshot write          | 268.0 µs | 290.6 µs | **+8.5%**  |

The last two rows come from a scratch harness over a 5.8 KB snapshot, because this suite has
no JSON row. Restore pays for bayan 1.11.1's bounds-checked parsers and duplicate-key set.
Write parses text on the way out, so it pays a smaller share. Both are p < 0.01; none of
the five suite rows is under p = 0.05. Load rose to about 6 during the run, so read the Δ,
not the medians.

## v1.2.0 — cyrius 6.6.20 → 6.7.9

1.1.7 on cyrius 6.6.20 against 1.2.0 on 6.7.9, 60 rounds interleaved, shuffled and pinned to
one CPU (2026-11-01). Medians:

| Op                      | 1.1.7    | 1.2.0    | Δ      |
|-------------------------|----------|----------|--------|
| `priority_from_numeric` | 4.54 ns  | 4.57 ns  | +0.7%  |
| `node_can_fit`          | 12.82 ns | 12.87 ns | +0.4%  |
| `cron_expr_matches`     | 14.54 ns | 14.53 ns | −0.1%  |
| `samay_uuid_v4`         | 682.0 ns | 680.0 ns | −0.3%  |
| `scheduled_task_new`    | 2.37 µs  | 2.37 µs  | +0.2%  |

No row is under p = 0.05, and none moved by more than 0.7%. The machine was not idle (load
about 4), so the absolute numbers run about 3% above the v1.1.7 table. Read the Δ, not the
medians.

## v1.1.7 — cyrius 6.6.14 → 6.6.20

1.1.6 on cyrius 6.6.14 against 1.1.7 on 6.6.20, 60 rounds interleaved, shuffled and pinned to
one CPU (2026-11-01). Medians:

| Op                      | 1.1.6    | 1.1.7    | Δ      |
|-------------------------|----------|----------|--------|
| `priority_from_numeric` | 4.31 ns  | 4.33 ns  | +0.4%  |
| `node_can_fit`          | 12.45 ns | 12.47 ns | +0.1%  |
| `cron_expr_matches`     | 13.94 ns | 13.96 ns | +0.1%  |
| `samay_uuid_v4`         | 663.0 ns | 663.0 ns | 0.0%   |
| `scheduled_task_new`    | 2.30 µs  | 2.31 µs  | +0.2%  |

No row moved by more than 0.4%. `priority_from_numeric` is the only one under p = 0.05, by
0.02 ns, and its source did not change.

## v1.1.6 — cyrius 6.6.6 → 6.6.14

1.1.5 on cyrius 6.6.6 against 1.1.6 on 6.6.14, 60 rounds interleaved, shuffled and pinned to
one CPU (2026-10-03). Medians:

| Op                      | 1.1.5    | 1.1.6    | Δ      |
|-------------------------|----------|----------|--------|
| `priority_from_numeric` | 4.3 ns   | 4.3 ns   | 0.0%   |
| `node_can_fit`          | 12.5 ns  | 12.5 ns  | 0.0%   |
| `cron_expr_matches`     | 14.0 ns  | 14.0 ns  | +0.3%  |
| `samay_uuid_v4`         | 656.5 ns | 667.0 ns | +1.6%  |
| `scheduled_task_new`    | 2.32 µs  | 2.32 µs  | +0.1%  |

Only `samay_uuid_v4` moved (p < 0.01), by 10 ns on a `getrandom(2)`-bound path whose source
and Linux syscall wrapper did not change. The table above is the v1.0.3 baseline on 6.5.36.

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
