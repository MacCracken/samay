# samay — Roadmap

> **Last refreshed**: 2026-11-01 (v1.4.3)
>
> **Forward-looking only.** Nothing shipped belongs here — per-release detail
> lives in [`../../CHANGELOG.md`](../../CHANGELOG.md) (complete from 0.1.0), the
> decisions in [`../adr/`](../adr/), and live state in [`state.md`](state.md).
>
> Version pins below are **targets that fix ordering, not commitments to dates**.
> An item moves when its dependencies are met; a trigger-gated item has no pin at
> all, deliberately — see [Trigger-gated](#trigger-gated--no-pin-by-design).

> **Current**: **v1.4.3**, cyrius pin **6.7.18**, deps ai-hwaccel **2.5.6** +
> bayan-json **1.11.1**. Gates green: **1,224 assertions**, **11/11 benchmarks**,
> coverage **82/82** public functions (each called by a test; 6.6.14 stopped counting `main`), lint 0-warn / 0
> untracked deferrals, fmt clean, `dist/` in sync (3,353 lines), 0 symbol collisions
> against the vendored deps. `src/` is 9 modules. The 1,479-line Rust oracle was
> retired after 1.1.5 ([`rust-old-removal.md`](rust-old-removal.md)).

## Next

Nothing here is blocked. In order of who it helps.

### Reach: the work has not reached anyone

- [ ] **State samay's real toolchain floor.** bayan 1.11.1 does not parse on cyrius 6.6.10, so the
  floor rose during 1.2.x and nothing records it. A consumer finds out from a compile error. This
  blocks the next item.
- [ ] **Move the consumers forward.** kavach is on 1.1.6, daimon on 1.1.3 and stiva on 1.1.2, so
  **nothing from 1.2 to 1.4 has reached a consumer**. stiva runs the cron code 1.4.1 and 1.4.3
  repaired. daimon registers nodes through a route that re-registering used to corrupt. The work is in
  those repos; samay's part is a migration note, and 1.4.3 needs one most: accelerator tasks that
  used to share a device now queue.
- [ ] **Run stiva's full suite against current samay.** Only its `cron_due_at` has been checked,
  because samay's deps do not load on its pin. This closes when stiva moves.

### Decisions the sweep left open

Each of these is a feature, or changes meaning, so each needs a choice before any code.

- [ ] **Deadlines.** A task carries one and restore keeps it, but nothing schedules by it. 1.4.3
  stopped the README claiming otherwise. Either order by it or say plainly that it is only stored.
- [ ] **`ResourceReq.network`** is stored and affects nothing.
- [ ] **Sharing a device, and asking for several.** A task takes one whole GPU, or chips of one pod
  ([ADR-0013](../adr/0013-accelerators-are-reserved.md)). Neither "half a GPU" nor "four GPUs" can be
  said. Both need new requirement fields.
- [ ] **Preempting placed work, and more than one victim.** A SCHEDULED task holds capacity and
  cannot be chosen, and one running victim has to be enough.
- [ ] **Keep CPU work off the only GPU node.** A tie can leave a GPU node's CPU full and a CPU node
  idle while accelerator work waits for it.
- [ ] **What `task_scheduler_stats` calls things.** Cancelled counts as completed, and placed counts
  as queued. Both labels go back to the oracle, and neither is what the word means.
- [ ] **A way to fail a task with a reason.** `complete_task(TASK_FAILED)` has nowhere to put one.

### Limits that do not yet limit

Measured in the 1.4.3 sweep. None is reachable without a hostile or absurd snapshot, and no consumer
restores one across a trust boundary, so these wait on that event or on a real workload.

- [ ] **`SAMAY_JSON_MAX_ITEMS` does not bound memory or bytes.** bayan's tree costs about 64 bytes per
  array element, so 30 MB of `[[],[],...]` reaches 1.9 GB, and it is refused only after the parse.
  An unknown key is not capped at all. A byte limit before parsing would help, and bayan would need
  to help with the rest.
- [ ] **A writer can die instead of refusing.** Past bayan's 2 GiB build limit the process exits,
  though the snapshot is within the item limit. It should answer 0 as it does for items.
- [ ] **A pass is O(pending × nodes).** 100,000 unplaceable tasks against 100,000 nodes takes 366 s
  per pass. Skipping requirements already known not to fit would cut this for most real queues.
- [ ] **Public leaf decoders accept anything.** `SchedulingDecision_from_json("{}")` returns a struct
  with null Strs that crashes on the way back out. samay's own readers never use these.
- [ ] **Values only the constructors allow.** A node with `total_cpu` past 1e18 restores with none, a
  node with an empty id is dropped on restore, with a log line, and training method 99 becomes LORA.

### Make the checks permanent

Each of these ran by hand and can rot the way the benchmarks, the fuzz stub and the README example
did.

- [ ] **CI on aarch64 and in bounds-checked mode.** Both pass today and neither is gated.
- [ ] **CI runs the fuzz harness.** It is real since 1.4.3, and a harness no one runs is how the last
  one stayed a stub.
- [ ] **CI compiles the README example.** It stopped compiling for several releases while claiming
  to be run before each one. Declined for now on 2026-11-01; recorded because the failure was silent.
- [ ] **Whole-source mutation as a release gate.** It found more than any audit before it. The
  script is small, and a run takes about 20 minutes.

### Tidying

- [ ] **`docs/examples/` is empty**, though CLAUDE.md lists it as runnable examples. Fill it from
  `src/main.cyr`, or drop the link.
- [ ] **CLAUDE.md**: the `Goal` is still a TODO and needs the owner's words. The roadmap link still
  says "Milestones through v1.0", the gate list carries a benchmark count, which is state, and two
  statements are out of date: `Ok`/`Err` have not allocated since cyrius 6.6.0, and a bare
  `cyrius fmt --check` now fails loudly.
- [ ] **Version-stamped prose goes stale.** `docs/architecture/overview.md` and `state.md` still say
  kavach 3.8.0 and daimon 2.0.0. Point them at the pins.
- [ ] **`lib/hashmap_fast.cyr`** is outside the declared footprint and is noted on every resolve.
- [ ] **stiva's `src/fleet.cyr`** says samay's ledger leaks because only `cancel_task` releases. That
  stopped being true in 1.0.3, and it is a reason given for not adopting `NodeCapacity`.

---

## Trigger-gated — no pin, by design

Pinning these would be theatre: none can start until an external event occurs, and a version number
would just rot. Each names the event.

- [ ] **Opt-in concurrent-entry detector** — a debug mode that notices two threads inside one
  scheduler and aborts. Considered in the 1.0.4 audit and deliberately not built
  ([ADR-0008](../adr/0008-threading-contract.md)). *Trigger*: any consumer adopting a threaded shape.
- [ ] **agnos verification** — no agnos run exists. aarch64 passes; NaN/Inf handling is the part most
  likely to differ. *Trigger*: an agnos consumer.
- [ ] **Lifetime counters in `task_scheduler_stats`** — pruning lowers the totals, because samay keeps
  none ([ADR-0011](../adr/0011-bounded-task-history.md)). They would be new wire state. *Trigger*: a
  consumer that prunes and needs lifetime counts.
- [ ] **Remove `samay_init`.** It has done nothing since 1.4.3 and stays because it is public.
  *Trigger*: the next major version.

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

> **Trigger discipline.** Every trigger above names an event that actually occurs. Self-referential
> triggers ("at the next rewrite") never arrive, and a trigger that fires only after the mistake is
> not one. When one fires, check first whether the item has already shipped. An item that needs no
> external event does not belong under a trigger at all: this file held aarch64 there for months with
> qemu installed. And check them on every refresh: two items here were still waiting on upstream
> fixes that had already shipped.
