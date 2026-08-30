# samay — Roadmap

> **Last refreshed**: 2026-08-30 (v1.0.4)
>
> **Forward-looking only.** Nothing shipped belongs here — per-release detail
> lives in [`../../CHANGELOG.md`](../../CHANGELOG.md) (complete from 0.1.0), the
> decisions in [`../adr/`](../adr/), and live state in [`state.md`](state.md).
> The v1.0 criteria checklist and the M0–M5 milestone narrative were removed at
> this refresh: every item was `[x]`, and a roadmap that is mostly a trophy case
> stops being read.

> **Current**: **v1.0.4**, cyrius pin **6.5.36**, deps ai-hwaccel **2.3.19** +
> bayan-json **1.5.2**. Gates green: **416 assertions**, **5/5 benchmarks**,
> lint 0-warn / 0 untracked deferrals, fmt clean, `dist/` in sync (2,331 lines),
> 0 symbol collisions against the vendored deps. `src/` is 9 modules / 2,404
> lines against the frozen 1,479-line Rust oracle.
>
> v1.0 shipped at 1.0.0 (2026-07-21). The 1.0.2–1.0.4 arc was dependency
> currency, a P-1 audit sweep, and a concurrency audit — recorded in the
> CHANGELOG and in ADRs [0006](../adr/0006-cron-expression-model.md),
> [0007](../adr/0007-reservation-lifecycle.md) and
> [0008](../adr/0008-threading-contract.md), not here.

## Open — tracked follow-ups

Carried from [`../audit/2026-07-21-audit.md`](../audit/2026-07-21-audit.md) and
the 2026-08-29 P-1 sweep. Referenced by ID from the source comments that defer to
them, so `cyrius lint` can see each deferral is tracked — do not renumber.

- [ ] **F5 — stable O(n log n) sort + terminal-task pruning.** Four insertion
  sorts remain (`src/scheduler.cyr` ×2, `src/cron.cyr`, `src/json.cyr`); measured
  ~85× slower than a merge sort at n=8000. Consolidate the four into one shared
  `samay_sort_by_key` **first**, then replace the algorithm once — two of them are
  already exact `_sort_by_key` specialisations. Held out of 1.0.3 deliberately:
  ADR-0004's determinism guarantee rides on those comparators and that release
  was already cron- and JSON-heavy. Terminal tasks also accumulate in
  `TaskScheduler.tasks` with no removal API, so every subsequent sort and
  snapshot grows without bound. *Trigger*: a consumer with a long-lived scheduler
  or >1k concurrent tasks. *Medium.*
- [ ] **F8/F9 — cron aggregate-work budget.** Per-entry catch-up is bounded
  (`CRON_SCAN_WINDOW_SECS`, `CRON_MAX_COUNT`, `CRON_CATCHUP_CAP`); the aggregate
  across many entries in one `check_due_at` is not. 1.0.3's alloc-free prefilter
  cut the cost ~12× and removed the heap growth entirely, so this is now a
  **policy** question rather than an availability one: any budget needs an
  exhaustion rule, and every candidate collides with "missed schedules are never
  silently skipped". Lands in `_cron_check_entry`, which 1.0.3 extracted for
  exactly this. *Trigger*: a consumer running many cron entries across a long
  outage. *Medium.*
- [ ] **Wire-side write optimisation.** `_rr_node` / `_ce_node` still
  serialize-then-reparse through the `#derive` codec (~68% of
  `scheduled_task_to_jsonv`; measured 3.14 µs → 695 ns for a direct builder).
  The read side moved to hand-written codecs in 1.0.3; the write side was held
  back so that release's emitted bytes were provably unchanged. *Trigger*: needs
  a byte-equality corpus over ≥500 `ResourceReq` values before landing — it is
  the one change that can silently alter the wire. *Medium.*
- [ ] **F4 — upstream stdlib hash seeding.** `lib/hashmap.cyr` uses an unseeded
  FNV-1a. samay cannot fix a vendored module, and 1.0.3 removed the one path by
  which bucket order could still reach a documented-deterministic decision (the
  NaN-utilization fall-through in `_best_fit_node`). Retained only so the
  deferral in `src/json.cyr` stays tracked. *Trigger*: upstream, not ours.

## Open — from the 1.0.4 concurrency audit

See [ADR-0008](../adr/0008-threading-contract.md) for the measurements.

- [ ] **Upstream: `lib/chrono.cyr` publishes `_chrono_mdays` before filling it.**
  A racing thread reads an all-zero month table and `epoch_to_date` returns month
  13 — a silently wrong date, reachable from `cron_expr_matches`. samay closes the
  window from outside with `samay_init()`, but the fix belongs upstream. **Filed**
  2026-08-30 at `cyrius/docs/development/proposals/2026-08-30-lazy-init-publish-before-fill.md`.
  Drop `samay_init`'s chrono pre-warm only once that ships *and* the pin moves
  past it. *Trigger*: upstream release.
- [ ] **Opt-in concurrent-entry detector.** A debug mode that notices two threads
  inside one scheduler and aborts or warns, so a consumer catches a contract
  violation immediately instead of via corrupted capacity. Considered during the
  audit and deliberately not built — no consumer is multi-threaded today.
  *Trigger*: any consumer adopting a threaded shape. *Medium.*

## Deferred — no trigger has fired

- [ ] **Split `node_preference` into user-preference and current-assignment.**
  `schedule_pending` overwrites the caller's requested node with the chosen one,
  which destroys the accurate "preferred node" decision reason. ADR-0007 balanced
  the accounting with a separate `reserved_on` instead; this is the cleaner model
  but changes the meaning of a shipped field. Achievable without a wire break if
  the new field is nullable and defaulted. *Trigger*: a minor release, with its
  own ADR. *Medium.*
- [ ] **Benchmark the accelerator placement path.** Every `can_fit` /
  `_best_fit_node` number on record used `REQ_NONE`, which short-circuits before
  touching profiles — so the figures understate exactly the workload samay's
  domain principles are written about. ai-hwaccel's `find_satisfying_profile` has
  never been measured inside the placement loop. *Trigger*: before any placement
  perf claim. *Low.*
- [ ] **Structure-aware fuzzing over `task_scheduler_from_json_str`.** All restore
  probing to date has been hand-crafted against specific hypotheses. 1.0.3's
  fail-closed validation is exactly what a fuzzer should be pointed at.
  *Trigger*: any new restore-path finding, or a consumer accepting snapshots
  across a trust boundary. *Medium.*
- [ ] **Non-x86_64 verification.** No aarch64 or agnos measurements exist. The
  NaN/Inf handling added in 1.0.3 is the part most likely to differ.
  *Trigger*: an aarch64 or agnos consumer. *Medium.*
- [ ] **Audit test *correctness*, not just coverage.** The P-1 sweep found one
  test asserting a defect as intended behaviour, with the wrong rule restated in
  its own comment; it had passed for four releases. Nothing establishes it was the
  only one. *Trigger*: fold into the next audit pass rather than scheduling
  separately. *Low.*

> **Trigger discipline.** Every item above names an event that actually occurs.
> Self-referential triggers ("at the next rewrite") never arrive. When a trigger
> fires, check first whether the item has already shipped — that check is what
> catches a completed item sitting on a deferred list for releases.

## Out of scope

- Distributed consensus / multi-scheduler coordination (single-scheduler only).
- Live task execution — samay decides placement; kavach executes.
- Timezone / DST support. Everything is UTC; adding a timezone changes the
  on-the-wire JSON and the whole cron model
  ([ADR-0006](../adr/0006-cron-expression-model.md)).
- Making samay thread-safe. It is single-threaded **by contract**, and an
  internal lock would be false safety while the query API returns interior
  pointers ([ADR-0008](../adr/0008-threading-contract.md)).
