# samay benchmarks

x86_64 Linux · cyrius 6.4.67 · `cyrius bench tests/samay.bcyr`.
Baseline refreshed 2026-07-18 (v0.4.0).

| Op                      | avg      | notes                              |
|-------------------------|----------|------------------------------------|
| `priority_from_numeric` | 4 ns     | pure                               |
| `node_can_fit`          | 29 ns    | REQ_NONE fast path (cpu/mem/disk)  |
| `cron_expr_matches`     | 296 ns   | `epoch_to_date` alloc + bitmask tests |
| `uuid_v4`               | 612 ns   | getrandom(2) syscall-bound         |
| `scheduled_task_new`    | 2.11 µs  | alloc + uuid + `dt_now`            |

`node_can_fit` benches the `REQ_NONE` common path (accelerator check
short-circuits before touching profiles); the accelerator path adds one
`find_satisfying_profile` scan over the node's profile vec (M3, ADR-0002).
`cron_expr_matches` is alloc-bound — alloc-free matching is a roadmap perf item.

Re-run and update on any hot-path change. Never claim a performance win without
before/after numbers (project rule).
