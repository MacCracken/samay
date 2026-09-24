# Samay (समय — "time")

Task scheduler for AGNOS — real cron scheduling with **resource-aware,
accelerator-conscious** task placement. Cyrius port of the original Rust library.

- **Language**: Cyrius (toolchain 6.6.6) · **License**: GPL-3.0-only
- **Consumers**: daimon (task scheduling), kavach (sandboxed execution)
- **Status**: **v1.1.5** — port complete, P-1 and concurrency audited. Real cron
  (Vixie DOM/DOW), ai-hwaccel placement, JSON snapshot/restore, deterministic
  scheduling, fail-closed restore, conserved node capacity. Both downstream
  consumers (kavach 3.8.0, daimon 2.0.0) integrated.

## What it does

- **Priority-aware task queue** (Normal / High / Critical / Emergency) with
  preemption, cancellation, deadline-aware scheduling, and aggregate stats.
- **Resource-aware placement** — CPU / memory / disk plus real accelerator
  availability: each node carries ai-hwaccel device profiles (CUDA / ROCm / TPU /
  Gaudi / Neuron) and `can_fit` places via ai-hwaccel `requirement_satisfied()`,
  best-fit by utilization (an accelerator task never lands on a node without a
  matching device — see [ADR-0002](docs/adr/0002-ai-hwaccel-profile-placement.md)).
- **Real cron expressions** — standard 5-field (`min hour dom month dow`) with
  `*`, ranges, lists, `*/step`, month/day names, and `@hourly`…`@yearly`
  shortcuts, **validated at parse time**. Missed schedules follow an explicit
  catch-up / skip policy — always logged, never silently dropped.
- **Training-job templates** (LoRA / QLoRA / … → High-priority accelerator tasks).

## Build / test / bench

```sh
cyrius deps                          # resolve stdlib + ai-hwaccel into lib/
cyrius build src/main.cyr build/samay
./build/samay                        # runnable demo
cyrius test  tests/samay.tcyr        # 558/558 assertions
cyrius bench tests/samay.bcyr
```

## Use as a library

Consumers declare the dep and include the committed bundle:

```toml
[deps.samay]
git = "https://github.com/MacCracken/samay.git"
tag = "1.1.5"
modules = ["dist/samay.cyr"]
```

Then call the API — e.g. register an accelerator node, schedule a GPU job, and a
weekday cron with catch-up:

> Every string argument is a `Str`, not a bare cstring — wrap literals in
> `str_from(...)` ([ADR-0003](docs/adr/0003-str-string-representation.md)).
> Passing a literal directly compiles and then segfaults, because `str_data`
> reads it as a ptr+len header.

```
var s = task_scheduler_new();
task_scheduler_register_node(s,
  node_capacity_add_accel(
    node_capacity_new(str_from("tpu-1"), f64_from(8), 16384, 102400, 0),
    profile_tpu(0, 8, TPU_V5P)));

# 4 TPU chips: this places on tpu-1. Ask for REQ_GPU instead and it is
# deliberately NOT placed -- an accelerator task never lands on a node with no
# matching device (ADR-0002), and the attempt is logged.
var task_id = result_unwrap(task_scheduler_submit_task(s,
  scheduled_task_new(str_from("job"), str_from("desc"), str_from("agent"), 7,
    resource_req_new(f64_from(2), 4096, REQ_TPU, 4, 0, 1024))));
var decisions = task_scheduler_schedule_pending(s);

# Finish a task and hand its capacity back to the node. Driving a task terminal
# with scheduled_task_transition alone does NOT release immediately -- the next
# schedule_pending reconciles it -- but this is the intended path (ADR-0007).
scheduled_task_transition(task_scheduler_get_task(s, task_id), TASK_RUNNING);
task_scheduler_complete_task(s, task_id, TASK_COMPLETED);

# recurring: 03:30 on weekdays, catching up anything missed after downtime
var cron = cron_scheduler_new();
var tmpl = cron_task_template_new(str_from("backup"), str_from("nightly"),
  str_from("agent"), 5, resource_req_default());
cron_scheduler_add(cron, str_from("nightly"), str_from("30 3 * * 1-5"), tmpl, 1, CRON_CATCHUP);
var due = cron_scheduler_check_due(cron);
```

The snippet above is compiled and run as written before each release — it
yields `decisions=1`.

See `src/main.cyr` for a worked demo and `tests/samay.tcyr` for the full API in use.

## Thread safety

**samay is not thread-safe.** One `TaskScheduler` / `CronScheduler` is owned by one
thread at a time; serialise externally if you need concurrent access. This is a
deliberate contract, not an oversight — the query functions return raw pointers into
scheduler-owned structs, so an internal lock could not make sharing safe. See
[ADR-0008](docs/adr/0008-threading-contract.md) for the measurements and the reasoning.

If your process has more than one thread — even with a *separate* scheduler per thread —
call `samay_init()` once before spawning them:

```
samay_init();            # then spawn
```

`task_scheduler_new()` and `cron_scheduler_new()` already do this, so the ordinary shape
(build the scheduler, then spawn workers) needs nothing extra. The explicit call matters
only if you use the free functions (`cron_expr_parse`, `cron_expr_matches`,
`training_job_to_scheduled_task`) with no scheduler. It forces a process-global lazy
initialiser in the vendored `chrono` module to run while you are still single-threaded;
without it, racing threads can read a half-published month table and evaluate a cron
expression against the wrong date.

## Layout

- `src/{uuid,types,scheduler,cronexpr,cron,training,json}.cyr` — domain modules
- `src/lib.cyr` — aggregation header · `dist/samay.cyr` — bundled distributable
- `docs/` — architecture, ADRs, roadmap, benchmarks

## Documentation

- [Architecture overview](docs/architecture/overview.md) · [ADRs](docs/adr/) · [Getting started](docs/guides/getting-started.md)
- [Roadmap](docs/development/roadmap.md) · [State](docs/development/state.md) · [Benchmarks](docs/benchmarks.md)
