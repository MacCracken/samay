# samay benchmarks

x86_64 Linux · cyrius 6.4.67 · `cyrius bench tests/samay.bcyr`.
Baseline captured 2026-07-18 (v0.2.0).

| Op                      | avg      | notes                          |
|-------------------------|----------|--------------------------------|
| `node_can_fit`          | 28 ns    | pure; best-fit inner loop      |
| `priority_from_numeric` | 4 ns     | pure                           |
| `uuid_v4`               | 686 ns   | getrandom(2) syscall-bound     |
| `scheduled_task_new`    | 2.24 µs  | alloc + uuid + `dt_now`        |

Re-run and update this table on any hot-path change. Never claim a performance
win without before/after numbers (project rule).
