# Samay (समय — "time")

Task scheduler for AGNOS — real cron scheduling with **resource-aware,
accelerator-conscious** task placement. Cyrius port of the original Rust library.

- **Language**: Cyrius (toolchain 6.4.67) · **License**: GPL-3.0-only
- **Consumers**: daimon (task scheduling), kavach (sandboxed execution)
- **Status**: v0.4.0 — parity + cron expressions + ai-hwaccel-driven placement

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
cyrius test  tests/samay.tcyr        # 130/130 assertions
cyrius bench tests/samay.bcyr
```

## Use as a library

Consumers declare the dep and include the committed bundle:

```toml
[deps.samay]
git = "https://github.com/MacCracken/samay.git"
tag = "0.4.0"
modules = ["dist/samay.cyr"]
```

Then call the API — e.g. register an accelerator node, schedule a GPU job, and a
weekday cron with catch-up:

```
var s = task_scheduler_new();
task_scheduler_register_node(s,
    node_capacity_add_accel(node_capacity_new("tpu-1", f64_from(8), 16384, 102400, 0),
                            profile_tpu(0, 8, TPU_V5P)));

task_scheduler_submit_task(s, scheduled_task_new("job", "desc", "agent", 7,
    resource_req_new(f64_from(2), 4096, REQ_GPU, 0, 0, 1024)));
var decisions = task_scheduler_schedule_pending(s);

# recurring: 03:30 on weekdays, catching up anything missed after downtime
var cron = cron_scheduler_new();
var tmpl = cron_task_template_new("backup", "nightly", "agent", 5, resource_req_default());
cron_scheduler_add(cron, "nightly", "30 3 * * 1-5", tmpl, 1, CRON_CATCHUP);
var due = cron_scheduler_check_due(cron);
```

See `src/main.cyr` for a worked demo and `tests/samay.tcyr` for the full API in use.

## Layout

- `src/{uuid,types,scheduler,cronexpr,cron,training}.cyr` — domain modules
- `src/lib.cyr` — aggregation header · `dist/samay.cyr` — bundled distributable
- `rust-old/` — the frozen Rust reference (parity oracle; do not edit)
- `docs/` — architecture, ADRs, roadmap, benchmarks

## Documentation

- [Architecture overview](docs/architecture/overview.md) · [ADRs](docs/adr/) · [Getting started](docs/guides/getting-started.md)
- [Roadmap](docs/development/roadmap.md) · [State](docs/development/state.md) · [Benchmarks](docs/benchmarks.md)
