# Samay (समय — "time")

Task scheduler for AGNOS — real cron scheduling with **resource-aware,
accelerator-conscious** task placement. Cyrius port of the original Rust library.

- **Language**: Cyrius (toolchain 6.7.18, floor 6.7.10) · **License**: GPL-3.0-only
- **Consumers**: daimon (task scheduling), kavach (sandboxed execution), stiva (scheduled containers)
- **Status**: **v1.5.0** — port complete, P-1 and concurrency audited. Real cron
  (Vixie DOM/DOW), ai-hwaccel placement, JSON snapshot/restore, deterministic
  scheduling, fail-closed and memory-bounded restore, conserved node capacity. Downstream consumers
  kavach, daimon and stiva are integrated.

## What it does

- **Priority-aware task queue** (Normal / High / Critical / Emergency) with
  preemption, cancellation, and aggregate stats. A task can carry a deadline, stored
  and serialized, but nothing schedules by it yet.
- **Resource-aware placement** — CPU / memory / disk plus real accelerator
  availability: each node carries ai-hwaccel device profiles (CUDA / ROCm / TPU /
  Gaudi / Neuron), and a placed task holds its device, or its chips of a TPU pod,
  until it finishes. A task can ask for several GPUs on one node, or a share of one
  (`resource_req_with_devices`, `resource_req_with_share`). Placement is best-fit by
  utilization: an accelerator task never lands on a node without a free matching device,
  CPU work goes to accelerator nodes last, and a pass does not search again for a
  requirement it already knows fits nowhere
  ([ADR-0002](docs/adr/0002-ai-hwaccel-profile-placement.md),
  [ADR-0013](docs/adr/0013-accelerators-are-reserved.md),
  [ADR-0015](docs/adr/0015-a-pass-only-fills-nodes.md),
  [ADR-0016](docs/adr/0016-several-devices-or-a-share-of-one.md),
  [ADR-0017](docs/adr/0017-cpu-work-goes-to-accelerator-nodes-last.md)).
- **Real cron expressions** — standard 5-field (`min hour dom month dow`) with
  `*`, ranges, lists, `*/step`, month/day names, and `@hourly`…`@yearly`
  shortcuts, **validated at parse time**. Missed schedules follow an explicit
  catch-up / skip policy — always logged, never silently dropped. A large catch-up
  burst waits for a later check instead of landing all at once
  ([ADR-0012](docs/adr/0012-cron-burst-budget.md)).
- **Training-job templates** (LoRA / QLoRA / … → High-priority accelerator tasks).

## Build / test / bench

```sh
cyrius deps                          # resolve stdlib + ai-hwaccel into lib/
cyrius build src/main.cyr build/samay
./build/samay                        # runnable demo
cyrius test  tests/samay.tcyr        # 1522/1522 assertions
cyrius bench tests/samay.bcyr
```

## Use as a library

Consumers declare the dep and include the committed bundle:

```toml
[deps.samay]
git = "https://github.com/MacCracken/samay.git"
tag = "1.5.0"
modules = ["dist/samay.cyr"]
```

samay needs cyrius 6.7.10 or later at its pinned deps, bayan 1.11.1 and ai-hwaccel 2.5.6.

Then call the API — e.g. register an accelerator node, schedule a GPU job, and a
weekday cron with catch-up:

> Every string argument is a `Str`, not a bare cstring — wrap literals in
> `str_from(...)` ([ADR-0003](docs/adr/0003-str-string-representation.md)).
> Passing a literal directly compiles, and what happens next depends on its bytes,
> because `str_data` reads it as a ptr+len header: a segfault, a misleading
> out-of-memory panic, or a silent wrong value.

```
var s = task_scheduler_new();
task_scheduler_register_node(s,
  node_capacity_add_accel(
    node_capacity_new(str_from("tpu-1"), f64_from(8), 16384, 102400, 0),
    profile_tpu(0, 8, TPU_V5P)));

# 4 TPU chips: this places on tpu-1. Ask for REQ_GPU instead and it is
# deliberately NOT placed -- an accelerator task never lands on a node with no
# matching device (ADR-0002), and the attempt is logged.
var id_t, id_v = task_scheduler_submit_task(s,
  scheduled_task_new(str_from("job"), str_from("desc"), str_from("agent"), 7,
    resource_req_new(f64_from(2), 4096, REQ_TPU, 4, 0, 1024)));
var task_id = result_unwrap(id_t, id_v);
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

If you store `last_fired` yourself, read it back from the entries after a check. A burst past
the budget is held with its old watermark, and writing `now` over that deletes what it owed.

See [`docs/examples/`](docs/examples/) for runnable examples, `src/main.cyr` for a worked demo, and
`tests/samay.tcyr` for the full API in use. Coming from 1.1.x? Read the
[migration note](docs/guides/migrating-to-1.4.md): accelerator tasks that used to share a device now
queue unless they ask for a share, and CPU work now leaves accelerator nodes for last.

## Thread safety

**samay is not thread-safe.** One `TaskScheduler` / `CronScheduler` is owned by one
thread at a time; serialise externally if you need concurrent access. This is a
deliberate contract, not an oversight — the query functions return raw pointers into
scheduler-owned structs, so an internal lock could not make sharing safe. See
[ADR-0008](docs/adr/0008-threading-contract.md) for the measurements and the reasoning.

Separate schedulers on separate threads need nothing extra. `samay_init()` used to be
needed before spawning, against a race in the vendored `chrono` module. chrono fixed that
in cyrius 6.5.37, so the function now does nothing and stays only because it is public.

## Layout

- `src/{uuid,types,scheduler,cronexpr,cron,training,json}.cyr` — domain modules
- `src/lib.cyr` — aggregation header · `dist/samay.cyr` — bundled distributable
- `docs/` — architecture, ADRs, roadmap, benchmarks

## Documentation

- [Architecture overview](docs/architecture/overview.md) · [ADRs](docs/adr/) · [Getting started](docs/guides/getting-started.md) · [Migrating to 1.4](docs/guides/migrating-to-1.4.md)
- [Roadmap](docs/development/roadmap.md) · [State](docs/development/state.md) · [Benchmarks](docs/benchmarks.md)
