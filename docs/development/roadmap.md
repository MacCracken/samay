# samay — Roadmap

> **Last refreshed**: 2026-11-02 (v1.4.6)
>
> **Forward-looking only.** Nothing shipped belongs here — per-release detail
> lives in [`../../CHANGELOG.md`](../../CHANGELOG.md) (complete from 0.1.0), the
> decisions in [`../adr/`](../adr/), and live state in [`state.md`](state.md).
>
> **Every forward item has a version.** A pin fixes the order, not a date. An item moves when
> its gate is met. Repairs stay in the 1.4.x line, features take a minor, and removals wait for
> 2.0.0. The only unpinned items wait on an event outside this repo:
> see [Event-gated](#event-gated--no-pin-by-design).

> **Current**: **v1.4.6**, cyrius pin **6.7.18**, floor **6.7.10**, deps ai-hwaccel **2.5.6** +
> bayan-json **1.11.1**. Gates green: **1,405 assertions**, **13/13 benchmarks**,
> coverage **87/87** public functions (each called by a test; 6.6.14 stopped counting `main`), lint 0-warn / 0
> untracked deferrals, fmt clean, `dist/` in sync (3,673 lines), 0 symbol collisions
> against the vendored deps. `src/` is 9 modules. The 1,479-line Rust oracle was
> retired after 1.1.5 ([`rust-old-removal.md`](rust-old-removal.md)).

## The arc at a glance

| Version | Theme | Risk | Gate to entry |
|---|---|---|---|
| **1.5.0** | Accelerator requests: shared and multi-device | high | consumers on 1.4.x, and an ADR on the unit of sharing |
| **1.6.0** | Preemption: placed tasks and several victims | medium | an ADR on the new return shape |
| **1.7.0** | Deadlines and `network`: make them work, or mark them for removal | medium | one ADR each |
| **1.8.0** | Accounting: stats counters, lifetime totals, failure reasons | low | an ADR on lifetime totals as wire state |
| **2.0.0** | Removals: `samay_init`, stats meanings, whatever 1.7.0 rejected | high | every consumer on 1.8.x |

The order is by who it helps. The repairs finished with 1.4.6. New features wait until consumers
can receive them, because nothing from 1.2 onward has reached one yet: consumer adoption is next.

---

## Consumer adoption — gate to 1.5.0

Not a samay release. **Nothing from 1.2 to 1.4 has reached a consumer**, and new requirement fields
are no use to a consumer that cannot build them. The toolchain floor and the
[migration note](../guides/migrating-to-1.4.md) are in place, so this can start at any time.

- [ ] **kavach** moves up from 1.1.6.
- [ ] **daimon** moves up from 1.1.3. Its node route reaches the re-registering fix in 1.4.3.
- [ ] **stiva** moves up from 1.1.2. It runs the cron code 1.4.1 and 1.4.3 repaired. Its full suite
  then runs against current samay for the first time, and the comment in `src/fleet.cyr` saying
  samay's ledger leaks can go: that stopped being true in 1.0.3.

---

## 1.5.0 onward — features

### 1.5.0 — accelerator requests

*Entry gate*: consumers on 1.4.x, and an ADR on the unit of sharing. Today a task takes one whole GPU,
or chips of one pod ([ADR-0013](../adr/0013-accelerators-are-reserved.md)). That ADR must keep a pass
filling nodes only: taking a share can never leave room for a request that had none, or the pass's
record of what fits nowhere goes wrong ([ADR-0015](../adr/0015-a-pass-only-fills-nodes.md)).

- [ ] **Sharing a device.** "Half a GPU" cannot be said. It needs a new requirement field, and
  exclusive stays the default.
- [ ] **Several devices.** "Four GPUs" cannot be said either: `accel_min_chips` applies to TPUs only.
- [ ] **Keep CPU work off the only GPU node.** A tie can fill a GPU node's CPU with CPU work while a
  CPU node sits idle and accelerator work waits for it.

### 1.6.0 — preemption

*Entry gate*: an ADR on the new return shape, since `PreemptionAction` names one victim.

- [ ] **Placed tasks can be chosen.** A SCHEDULED task holds capacity and cannot be preempted today.
- [ ] **More than one victim.** A task needing 8 cores on a node holding two 4-core tasks gets no
  answer today, because one victim has to be enough.

### 1.7.0 — deadlines and `network`

*Entry gate*: one ADR each. Both are stored, serialized and read by nothing, so each must start doing
something or be marked for removal in 2.0.0.

- [ ] **Deadlines.** Order by them within a priority, or say plainly that they are only stored.
- [ ] **`ResourceReq.network`.** Give nodes a network capability to match it against, or retire it.

### 1.8.0 — accounting

*Entry gate*: an ADR on lifetime totals, which are new wire state.

- [ ] **Stats that say what they mean.** Add `cancelled` and `scheduled` alongside today's fields.
  Today cancelled counts as completed and placed counts as queued. The old meanings go in 2.0.0.
- [ ] **Lifetime totals.** Pruning lowers `task_scheduler_stats`, because samay keeps none
  ([ADR-0011](../adr/0011-bounded-task-history.md)).
- [ ] **Failing a task with a reason.** `complete_task(TASK_FAILED)` has nowhere to put one.

---

## 2.0.0 — removals

*Entry gate*: every consumer on 1.8.x. This is the only release allowed to break a public name.

- [ ] **Remove `samay_init`.** It has done nothing since 1.4.3, and stays until now only because it
  is public.
- [ ] **`completed` and `queued` stop including cancelled and placed tasks.** 1.8.0 adds the honest
  counters first, so consumers can move before the meanings change.
- [ ] **Remove whatever 1.7.0 rejected.**

---

## Event-gated — no pin, by design

Only these two: each waits on something outside this repo, and a version number would just rot.

- [ ] **Opt-in concurrent-entry detector** — a debug mode that notices two threads inside one
  scheduler and aborts. Considered in the 1.0.4 audit and deliberately not built
  ([ADR-0008](../adr/0008-threading-contract.md)). *Event*: a consumer adopting a threaded shape.
- [ ] **agnos verification** — no agnos run exists. aarch64 passes; NaN/Inf handling is the part most
  likely to differ. *Event*: an agnos consumer.

---

## Considered and rejected

Recorded so they are not re-proposed. Each was measured, not argued.

- **Clamp `last_fired` on restore to `>= now - CRON_SCAN_WINDOW_SECS`** (audit Rec 4). **A measured
  no-op.** `_cron_count_due` already floors its start, so an ancient watermark and a clamped one scan
  the identical window. The only change would be suppressing `_cron_log_clamp`, a true warning that
  older occurrences are out of reach.
- **A budget on minutes scanned** (audit F8). It rations a cost that can be removed. At 30 ms per
  check it clears about 10 stale entries, a week of checks for 100,000 of them. Day-stepping took one
  stale entry from 26 ms to 30 µs instead ([ADR-0012](../adr/0012-cron-burst-budget.md)).
- **A merge sort** (audit Rec 3). Its scratch buffer leaks on every pass under `alloc()`, and no
  comparator here needs stability ([ADR-0011](../adr/0011-bounded-task-history.md)).
- **Device holds on the wire.** Reservations already record who holds what, so restore replays them
  and snapshots stay as they were ([ADR-0013](../adr/0013-accelerators-are-reserved.md)).

## Out of scope

- Distributed consensus / multi-scheduler coordination (single-scheduler only).
- Live task execution — samay decides placement; kavach executes.
- Timezone / DST support. Everything is UTC; adding a timezone changes the
  on-the-wire JSON and the whole cron model
  ([ADR-0006](../adr/0006-cron-expression-model.md)).
- Making samay thread-safe. Single-threaded **by contract**; an internal lock
  would be false safety while the query API returns interior pointers
  ([ADR-0008](../adr/0008-threading-contract.md)).

> **Pin discipline.** A new item gets a version when it is written down. Event-gated is for things
> this repo cannot make happen, and the event has to be one that actually occurs. Check those on
> every refresh: 1.4.3 found two items still waiting on upstream fixes that had already shipped, and
> aarch64 held behind a trigger with qemu installed.
