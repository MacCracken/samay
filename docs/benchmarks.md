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

## v1.4.3 — what the P(-1) fixes cost

1.4.2 against 1.4.3, both on cyrius 6.7.18, interleaved, shuffled and pinned to one CPU, with the
suite rows at 60 rounds and the others at 30 (2026-11-01). Rows this release does not touch stayed
within 1%. Medians:

| Op                                  | 1.4.2    | 1.4.3    | Δ       |
|-------------------------------------|----------|----------|---------|
| `node_can_fit`                      | 12.61 ns | 15.86 ns | **+25.8%** |
| `cron_expr_matches`                 | 18.61 ns | 18.71 ns | +0.5%   |
| `node_can_fit_gpu`                  | 103.0 ns | 167.0 ns | **+62.1%** |
| `scheduled_task_new`                | 2.30 µs  | 2.36 µs  | +2.5%   |
| `scheduled_task_to_jsonv`           | 2.49 µs  | 2.47 µs  | −0.7%   |
| `best_fit_tpu_100_nodes`            | 11.68 µs | 13.72 µs | **+17.5%** |
| `pending_tasks_2000`                | 365.8 µs | 341.7 µs | −6.6%   |
| idle pass (scratch)                 | 303 ns   | 277 ns   | −8.6%   |
| check, nothing fires, per entry (scratch) | 455.5 ns | 484.5 ns | +6.4% |
| check, all fire, per entry (scratch) | 3.03 µs | 3.12 µs  | +3.0%   |
| snapshot write, 200 tasks (scratch) | 3.41 ms  | 3.42 ms  | +0.1%   |
| snapshot restore, 200 tasks (scratch) | 3.25 ms | 3.60 ms | **+10.5%** |

- **`node_can_fit_gpu` and `best_fit_tpu_100_nodes` are the first accelerator figures on record.**
  Every earlier `can_fit` number used `REQ_NONE`, which never reaches a profile. They got slower because
  they now ask whether a device is free.
- `node_can_fit` adds the 1e-9 core margin. Restore adds type checks and the capacity settle.
- The 1.4.2 `best_fit` figure includes the `map_values` copy it made on every call.

**Heap per call**, the reason for the pass-time gain. `alloc()` never frees, so this adds up.

| Call                                | 1.4.2    | 1.4.3    |
|-------------------------------------|----------|----------|
| idle `schedule_pending`             | 760 B    | 152 B    |
| with 1,000 finished tasks           | 33,016 B | 152 B    |
| with 100 tasks that cannot be placed | 37,336 B | 160 B   |
| quiet `check_due_at`, 10 entries    | 304 B    | 152 B    |
| quiet `check_due_at`, 100 entries   | 2,118 B  | 174 B    |

## v1.4.2 — nested leaves built directly

1.4.1 against 1.4.2, both on cyrius 6.7.18, interleaved, shuffled and pinned to one CPU, with the
suite rows at 60 rounds and the snapshot rows at 30 (2026-11-01). The rows this release does not touch
stayed within 1.3%. Medians:

| Op                              | 1.4.1    | 1.4.2    | Δ       |
|---------------------------------|----------|----------|---------|
| `priority_from_numeric`         | 4.50 ns  | 4.51 ns  | +0.1%   |
| `node_can_fit`                  | 12.58 ns | 12.58 ns | 0.0%    |
| `cron_expr_matches`             | 18.53 ns | 18.54 ns | 0.0%    |
| `samay_uuid_v4`                 | 663.5 ns | 655.0 ns | −1.3%   |
| `scheduled_task_new`            | 2.30 µs  | 2.30 µs  | +0.3%   |
| `cron_count_window`             | 24.12 µs | 24.12 µs | 0.0%    |
| `pending_tasks_2000`            | 366.9 µs | 369.5 µs | +0.7%   |
| `scheduled_task_to_jsonv`       | 6.39 µs  | 2.48 µs  | **−61.2%** |
| `cron_entry_to_jsonv`           | 10.64 µs | 2.58 µs  | **−75.8%** |
| snapshot, 200 tasks and 8 nodes (scratch) | 4.32 ms | 3.43 ms | **−20.8%** |
| snapshot, 200 cron entries (scratch) | 4.85 ms | 3.12 ms | **−35.7%** |

- **A whole snapshot gains much less than one document.** Most of a write goes on
  `bayan_json_v_build` emitting text, which did not change.
- Heap per document also fell: `scheduled_task_to_jsonv` 2,320 B to 1,872 B, and
  `cron_entry_to_jsonv` 2,904 B to 1,976 B.
- The roadmap's 3.14 µs for the bridge was measured on 6.5.36. On bayan 1.11.1 it took 5.1 µs per
  requirement.

## v1.4.1 — the due count, and a check after an outage

**One check.** 1.4.0 against 1.4.1, both on cyrius 6.7.18, a scratch harness on one CPU at 12:34.
Midnight has no partial days and flatters the count, at about 19 µs per entry. The 100,000-entry
figure for 1.4.0 is extrapolated from 100 entries, because no real host would finish it. Each figure
includes firing the entry's task and writing its log lines.

| One check                                     | 1.4.0            | 1.4.1          |
|-----------------------------------------------|------------------|----------------|
| one `0 0 1 1 *` entry, a full window behind   | 3.1 ms, 18.5 KB  | 29 µs, 960 B   |
| one `* * * * *` entry, a full window behind   | 26 ms, 4.8 MB    | 30 µs, 970 B   |
| 100,000 stale SKIP entries                    | ~43 min, ~480 GB | 3.1 s, 93 MB   |
| 100 hourly CATCHUP entries, 30 days behind    | 223 ms, 37 MB    | 24 ms, 4 MB    |

The last row fires 72,000 tasks at once on 1.4.0, and over 8 checks on 1.4.1. If 100,000 entries
are all held, each check takes 2.6 s to recount them.

**The suite.** 60 rounds interleaved, shuffled and pinned to one CPU, with the scratch rows at 30
(2026-11-01). The rows this release does not touch stayed within 0.2%. Medians:

| Op                                  | 1.4.0    | 1.4.1    | Δ       |
|-------------------------------------|----------|----------|---------|
| `priority_from_numeric`             | 4.30 ns  | 4.30 ns  | 0.0%    |
| `node_can_fit`                      | 12.44 ns | 12.46 ns | +0.2%   |
| `cron_expr_matches`                 | 13.94 ns | 18.50 ns | **+32.8%** |
| `samay_uuid_v4`                     | 660.0 ns | 660.5 ns | +0.1%   |
| `scheduled_task_new`                | 2.32 µs  | 2.32 µs  | +0.1%   |
| `pending_tasks_2000`                | 371.1 µs | 378.6 µs | +2.0%   |
| `cron_count_window`                 | 27.1 ms  | 24.4 µs  | **−99.9%** |
| a real match (scratch)              | 270.5 ns | 43.8 ns  | **−83.8%** |
| check, nothing fires, per entry (scratch) | 387.0 ns | 457.5 ns | **+18.2%** |
| check, all fire, per entry (scratch) | 3.21 µs | 3.08 µs  | −4.1%   |

- **Two rows got slower, on purpose.** `cron_expr_matches` lands on a day-of-week miss, so it pays for
  the matcher being two calls and gains nothing from the change to the match path. A check that fires
  nothing pays 70 ns per entry, and evaluation order is the likely cause, though the split was not
  measured.
- `pending_tasks_2000` runs no code this release changed, so its 2% is probably code layout. That was
  not proven.
- The 1.4.0 arm ran `cron_count_window` 20 times, not 1,000, because that many full scans would have
  taken 27 s and 4.8 GB each round.

## v1.4.0 — one sort, and task removal

**Sorting.** 1.3.0 against 1.4.0, both on cyrius 6.7.18, 60 rounds interleaved, shuffled and pinned
to one CPU (2026-11-01). The machine was busy for part of it (load 2 to 6). Medians:

| Op                      | 1.3.0    | 1.4.0    | Δ       |
|-------------------------|----------|----------|---------|
| `priority_from_numeric` | 4.21 ns  | 4.21 ns  | 0.0%    |
| `node_can_fit`          | 12.31 ns | 12.30 ns | −0.1%   |
| `cron_expr_matches`     | 13.61 ns | 13.56 ns | −0.3%   |
| `samay_uuid_v4`         | 645.0 ns | 643.0 ns | −0.3%   |
| `scheduled_task_new`    | 2.23 µs  | 2.23 µs  | 0.0%    |
| `pending_tasks_2000`    | 15.23 ms | 359.6 µs | **−97.6%** |
| snapshot restore        | 196.8 µs | 198.4 µs | +0.8%   |
| snapshot write          | 288.0 µs | 288.1 µs | 0.0%    |

`pending_tasks_2000` is new in this release, and both columns ran the same row (p < 0.01). None of
the others is under p = 0.05. The snapshot rows use the v1.2.1 scratch harness, and their sorts are
small next to the JSON work.

`task_scheduler_pending_tasks` at growing sizes, from a scratch harness, best of three runs:

| queued tasks | 1.3.0    | 1.4.0    | faster |
|--------------|----------|----------|--------|
| 100          | 43.9 µs  | 10.7 µs  | 4×     |
| 1,000        | 3.60 ms  | 146 µs   | 25×    |
| 8,000        | 225 ms   | 2.09 ms  | 107×   |
| 100,000      | 57.9 s   | 58.0 ms  | 998×   |

100,000 is the snapshot ceiling, so through 1.3.0 a restored scheduler at the limit could spend about
a minute on one `schedule_pending`. 1.4.0's sort allocates nothing.

**Pruning.** `task_scheduler_schedule_pending` with nothing to place, 40 passes, three runs:

| scheduler                               | one pass |
|-----------------------------------------|----------|
| 100,000 finished tasks                  | 21.7 ms  |
| the same, pruned to none                | 2.22 ms  |
| one that never grew                     | 0.69 µs  |

Pruning is worth 10×, not more, because the hash table keeps its peak capacity and `map_values` walks
every slot. Pruning those 100,000 tasks took about 250 ms.

## v1.3.0 — `node_preference` split into two fields

1.2.2 against 1.3.0, both on cyrius 6.7.18, 60 rounds interleaved, shuffled and pinned to one
CPU (2026-11-01). The machine was quiet (load under 3.5). Medians:

| Op                      | 1.2.2    | 1.3.0    | Δ      |
|-------------------------|----------|----------|--------|
| `priority_from_numeric` | 4.24 ns  | 4.24 ns  | +0.1%  |
| `node_can_fit`          | 12.35 ns | 12.38 ns | +0.3%  |
| `cron_expr_matches`     | 13.77 ns | 13.77 ns | 0.0%   |
| `samay_uuid_v4`         | 650.0 ns | 648.5 ns | −0.2%  |
| `scheduled_task_new`    | 2.28 µs  | 2.27 µs  | −0.3%  |
| snapshot restore        | 201.0 µs | 202.6 µs | **+0.8%** |
| snapshot write          | 286.7 µs | 295.2 µs | **+3.0%** |

The two snapshot rows are real (p < 0.01): each task carries two more keys. `node_can_fit` is the
only suite row under p = 0.05, by 0.03 ns, and its source did not change. The snapshot rows use
the v1.2.1 scratch harness over the same 5.8 KB snapshot, which is an old one, so restore takes
the back-compat path.

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
