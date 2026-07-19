# samay benchmarks

x86_64 Linux · cyrius 6.4.67 · `cyrius bench tests/samay.bcyr`.
Baseline captured 2026-07-18 (v0.3.0).

| Op                      | avg      | notes                              |
|-------------------------|----------|------------------------------------|
| `priority_from_numeric` | 4 ns     | pure                               |
| `node_can_fit`          | 28 ns    | pure; best-fit inner loop          |
| `cron_expr_matches`     | 298 ns   | `epoch_to_date` alloc + bitmask tests; check_due inner loop |
| `uuid_v4`               | 612 ns   | getrandom(2) syscall-bound         |
| `scheduled_task_new`    | 2.13 µs  | alloc + uuid + `dt_now`            |

`cron_expr_matches` is alloc-bound (one `epoch_to_date` per call); an alloc-free
decomposition is a roadmap perf item, relevant to long post-downtime catch-up
scans.

Re-run and update this table on any hot-path change. Never claim a performance
win without before/after numbers (project rule).
