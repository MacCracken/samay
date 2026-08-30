# samay benchmarks

x86_64 Linux · cyrius 6.5.36 · `cyrius bench tests/samay.bcyr`.
Baseline refreshed 2026-08-29 (v1.0.2).

| Op                      | avg      | notes                              |
|-------------------------|----------|------------------------------------|
| `priority_from_numeric` | 4 ns     | pure                               |
| `node_can_fit`          | 28 ns    | REQ_NONE fast path (cpu/mem/disk)  |
| `cron_expr_matches`     | 282 ns   | `epoch_to_date` alloc + bitmask tests |
| `samay_uuid_v4`         | 613 ns   | getrandom(2) syscall-bound         |
| `scheduled_task_new`    | 2.06 µs  | alloc + uuid + `dt_now`            |

`node_can_fit` benches the `REQ_NONE` common path (accelerator check
short-circuits before touching profiles); the accelerator path adds one
`find_satisfying_profile` scan over the node's profile vec (M3, ADR-0002).
`cron_expr_matches` is alloc-bound — alloc-free matching is a roadmap perf item.

These are the first numbers since v0.4.0. The `Str` migration (ADR-0003, v0.5.0)
left `tests/samay.bcyr` passing bare cstring literals to APIs that had become
`Str`-taking, so `cron_expr_parse` segfaulted on `str_data` of a cstring and the
harness died before reporting `cron_expr_matches`. Fixed in v1.0.2; the `Str`
arguments are now built once outside every timed loop, so `str_from`'s 16-byte
header allocation is not folded into the figures above.

Re-run and update on any hot-path change. Never claim a performance win without
before/after numbers (project rule).
