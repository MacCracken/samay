# Samay (समय — "time")

Task scheduler for AGNOS — cron-like scheduling with **resource-aware,
accelerator-conscious** task placement. Cyrius port of the original Rust library.

- **Language**: Cyrius (toolchain 6.4.67) · **License**: GPL-3.0-only
- **Consumers**: daimon (task scheduling), kavach (sandboxed execution)
- **Status**: v0.2.0 — feature + test parity with Rust v0.1.x

## What it does

- Priority-aware task queue (Normal / High / Critical / Emergency), preemption,
  cancellation, deadline-aware scheduling, aggregate stats.
- Resource-aware node placement — CPU / memory / disk plus GPU / TPU / accelerator
  requirements (via ai-hwaccel `REQ_*`), best-fit by utilization.
- Cron-like recurring triggers (interval + optional specific hour / minute).
- Training-job templates (LoRA / QLoRA / … → High-priority GPU tasks).

## Build / test / bench

```sh
cyrius deps                          # resolve stdlib + ai-hwaccel into lib/
cyrius build src/main.cyr build/samay
./build/samay                        # runnable demo
cyrius test  tests/samay.tcyr        # 108/108 assertions
cyrius bench tests/samay.bcyr
```

## Use as a library

Consumers declare the dep and include the committed bundle:

```toml
[deps.samay]
git = "https://github.com/MacCracken/samay.git"
tag = "0.2.0"
modules = ["dist/samay.cyr"]
```

Then call the API — e.g.:

```
var s = task_scheduler_new();
task_scheduler_register_node(s, node_capacity_new("gpu-1", f64_from(8), 16384, 102400, 1));
task_scheduler_submit_task(s, scheduled_task_new("job", "desc", "agent", 7,
    resource_req_new(f64_from(2), 4096, REQ_GPU, 0, 0, 1024)));
var decisions = task_scheduler_schedule_pending(s);
```

See `src/main.cyr` for a worked demo and `tests/samay.tcyr` for the full API in use.

## Layout

- `src/{uuid,types,scheduler,cron,training}.cyr` — domain modules
- `src/lib.cyr` — aggregation header · `dist/samay.cyr` — bundled distributable
- `rust-old/` — the frozen Rust reference (parity oracle; do not edit)
- `docs/` — architecture, ADRs, roadmap, benchmarks
