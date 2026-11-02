# samay — Roadmap

> **Last refreshed**: 2026-11-01 (v1.4.1)
>
> **Forward-looking only.** Nothing shipped belongs here — per-release detail
> lives in [`../../CHANGELOG.md`](../../CHANGELOG.md) (complete from 0.1.0), the
> decisions in [`../adr/`](../adr/), and live state in [`state.md`](state.md).
>
> Version pins below are **targets that fix ordering, not commitments to dates**.
> An item moves when its dependencies are met; a trigger-gated item has no pin at
> all, deliberately — see [Trigger-gated](#trigger-gated--no-pin-by-design).

> **Current**: **v1.4.1**, cyrius pin **6.7.18**, deps ai-hwaccel **2.5.6** +
> bayan-json **1.11.1**. Gates green: **852 assertions**, **7/7 benchmarks**,
> coverage **82/82** public functions (each called by a test; 6.6.14 stopped counting `main`), lint 0-warn / 0
> untracked deferrals, fmt clean, `dist/` in sync (2,669 lines), 0 symbol collisions
> against the vendored deps. `src/` is 9 modules. The 1,479-line Rust oracle was
> retired after 1.1.5 ([`rust-old-removal.md`](rust-old-removal.md)).

## The arc at a glance

| Version | Theme | Risk | Gate to entry |
|---|---|---|---|
| ~~1.1.0~~ | ~~Cron catch-up counting tells the truth~~ | — | **shipped 2026-08-30** |
| ~~1.1.1~~ | ~~Checked `alloc()` across `src/`~~ | — | **shipped 2026-08-30** |
| ~~1.2.0~~ | ~~cyrius 6.7.9, bayan 1.5.13, `math` dropped~~ | — | **shipped 2026-11-01** |
| ~~1.3.0~~ | ~~Split `node_preference` ([ADR-0010](../adr/0010-request-and-assignment.md))~~ | — | **shipped 2026-11-01** |
| ~~1.4.0~~ | ~~F5 — one sort, task removal, refused oversized snapshots ([ADR-0011](../adr/0011-bounded-task-history.md))~~ | — | **shipped 2026-11-01** |
| ~~1.4.1~~ | ~~F8/F9 — exact due count, burst budget ([ADR-0012](../adr/0012-cron-burst-budget.md))~~ | — | **shipped 2026-11-01** |
| **1.4.2** | Write-side JSON codec | medium | byte-equality corpus |
| *(none)* | Trigger-gated items | — | a consumer event |

---

## 1.1.x — surfaced by the 2026-08-30 deferral sweep

**1.1.0 shipped 2026-08-30** and is recorded in the CHANGELOG, not here. Of the
three items it was scoped around, **two were not work**: verifying each against
current source found one a measured no-op and one already shipped in the original
port. Both are under [Considered and rejected](#considered-and-rejected) with the
evidence. That is the sweep working as intended — the check is the point, and it
cost less than either implementation would have.

**1.1.1 shipped 2026-08-30.** Scope corrected on contact with evidence: the
roadmap's premise — "OOM becomes a wild write at a small address" — was **false**
(every field offset is ≤ 112 against `mmap_min_addr` 65536, so the store traps).
The real exposure was **eleven allocation points that are not raw `alloc(`
tokens**, where the null escapes as struct data; two were measured producing a
*wrong scheduling decision* before any crash. 28 guards, a policy
([ADR-0009](../adr/0009-oom-policy.md)), and a CI gate that fails on an unguarded
allocation. See the CHANGELOG.

### Not version-pinned — do it independently of any release

- [x] **File the F4 hash-seeding issue upstream.** ✅ **Filed 2026-08-30** at
  `cyrius/docs/development/issues/2026-08-30-hashmap-unseeded-fnv1a-collision-dos.md`,
  with the audit's measured PoC (raw `map_set` at N=8,000: **493 ms** colliding vs
  **2.5 ms** distinct, ~197×; through `task_scheduler_from_json_str`, ~23–38×).
  Audit Rec 5 asked for this on 2026-07-21 and it sat unfiled for six weeks while
  the roadmap said "upstream, not ours" — which read as handled. The filing also
  raises the compatibility question the fix actually turns on: seeding makes
  `map_values` order differ between runs, which is a benefit (it surfaces latent
  order dependencies) but needs a migration window.

## 1.4.x — remaining repairs

The last repair was 1.6.0 until 2026-11-01, when the remaining repairs moved into
the 1.4.x line. F8/F9 shipped as 1.4.1.

### 1.4.2 — write-side JSON codec

- [ ] `_rr_node` / `_ce_node` still serialize-then-reparse through the `#derive`
  codec — measured 3.14 µs → 695 ns for a direct builder, ~68% of
  `scheduled_task_to_jsonv`. The read side moved to hand-written codecs in 1.0.3;
  the write side was held back so that release's emitted bytes were provably
  unchanged. *Entry gate*: a byte-equality corpus over ≥500 `ResourceReq` values
  including `1/3`, `0.1`, `7/9` — this is the one change that can silently alter
  the wire, so it ships alone or not at all.

---

## Trigger-gated — no pin, by design

Pinning these would be theatre: none can start until an external event occurs,
and a version number would just rot. Each names the event.

- [ ] **Opt-in concurrent-entry detector** — a debug mode that notices two threads
  inside one scheduler and aborts. Considered during the 1.0.4 audit and
  deliberately not built ([ADR-0008](../adr/0008-threading-contract.md)).
  *Trigger*: any consumer adopting a threaded shape.
- [ ] **Benchmark the accelerator placement path** — every `can_fit` /
  `_best_fit_node` figure on record used `REQ_NONE`, which short-circuits before
  touching profiles, so the numbers understate exactly the workload samay's domain
  principles are about. *Trigger*: before any placement perf claim.
- [ ] **Structure-aware fuzzing over `task_scheduler_from_json_str`** — all restore
  probing to date is hand-crafted against specific hypotheses. *Trigger*: a new
  restore-path finding, or a consumer accepting snapshots across a trust boundary.
- [ ] **Non-x86_64 verification** — no aarch64 or agnos measurements exist; the
  NaN/Inf handling added in 1.0.3 is most likely to differ. *Trigger*: an aarch64
  or agnos consumer.
- [ ] **Audit test *correctness*, not just coverage** — the P-1 sweep found a test
  asserting a defect as intended behaviour, wrong rule restated in its own comment,
  passing for four releases. Nothing establishes it was the only one. *Trigger*:
  fold into the next audit pass.
- [ ] **F4 — upstream hash seeding lands.** Filed 2026-08-30; once **fixed**
  upstream, re-check whether samay's own guarantees change (they should not —
  ADR-0004 sorts explicitly and never trusts `map_values` order, which is exactly
  why samay is unaffected by the seeding change). v1.0.3 already removed the one
  path by which bucket order reached a documented-deterministic decision.
  *Trigger*: an upstream release.
- [ ] **Drop `samay_init`'s chrono pre-warm.** samay stopped reading chrono's month
  table in 1.4.1, so the pre-warm protects only a consumer's own chrono calls.
  `samay_init` itself stays, because removing a public function is a major-version
  change. *Trigger*: an upstream fix to
  `cyrius/docs/development/proposals/2026-08-30-lazy-init-publish-before-fill.md`, or
  the next major version.

---

## Considered and rejected

Recorded so they are not re-proposed. Each was measured, not argued.

- **Clamp `last_fired` on restore to `>= now - CRON_SCAN_WINDOW_SECS`**
  (audit Rec 4, planned for 1.1.0). **A measured no-op.** `_cron_count_due`
  already floors `start` at `min_start`, so an ancient watermark and a clamped
  one scan the identical 527,040-minute window — **3.93 ms vs 3.93 ms**,
  indistinguishable across three runs with warm-up controlled. The only
  behavioural change would be suppressing `_cron_log_clamp`, a **true** warning
  that pre-window occurrences were dropped. Nothing gained, information lost.
  *The real cost here was the full-window scan itself, and 1.4.1 removed it by
  counting per day, which makes a restore clamp pointless a second time.*
- **Raise `CRON_MAX_COUNT` to the window size** (planned for 1.1.0). **Not free,
  as had been claimed.** A matching minute costs ~40× a missing one — it passes
  the v1.0.3 prefilter and reaches `epoch_to_date` — so `* * * * *` over a full
  window is **28.9 ms** capped at 100,000 against **~153 ms** uncapped. 5× more
  work to make a log line exact. v1.1.0 shipped the free half instead: the count
  carried a floor flag and the logs said `>=`. *1.4.1 made this moot by counting per
  day: the count is exact and cheaper than the cap was, so the cap is gone.*
- **Saturating subtraction in the stats averages** (audit Rec 6, planned for
  1.1.1). **Already shipped** — the guards have been in `task_scheduler_stats`
  since `e3861d2 "rust port parity"`, the original port. Rec 6 was filed as "no
  confirmed finding, still worth it" and was already satisfied when written.

- **SKIP-path early exit in `_cron_count_due`** (audit Rec 4, second half).
  Exiting the count early once a match is found would make the SKIP branch cheap
  — but that branch logs `due - 1`, the **exact** number of dropped occurrences.
  An early exit turns that number into a fabrication, and "missed schedules are
  never silently skipped" is not satisfied by reporting a wrong count instead of
  none. 1.1.0 makes the count *more* accurate for the same reason. *Not needed
  since 1.4.1: the exact count takes microseconds, so there is nothing to exit from.*
- **A budget on minutes scanned** (audit F8, 1.4.1). It rations a cost that can be
  removed. At 30 ms per check it clears about 10 stale entries, a week of checks for
  100,000 of them. Day-stepping took one stale entry from 26 ms to 30 µs instead, and
  the budget that shipped limits bursts, the one amplification left
  ([ADR-0012](../adr/0012-cron-burst-budget.md)).

## Out of scope

- Distributed consensus / multi-scheduler coordination (single-scheduler only).
- Live task execution — samay decides placement; kavach executes.
- Timezone / DST support. Everything is UTC; adding a timezone changes the
  on-the-wire JSON and the whole cron model
  ([ADR-0006](../adr/0006-cron-expression-model.md)).
- Making samay thread-safe. Single-threaded **by contract**; an internal lock
  would be false safety while the query API returns interior pointers
  ([ADR-0008](../adr/0008-threading-contract.md)).

> **Trigger discipline.** Every trigger above names an event that actually
> occurs. Self-referential triggers ("at the next rewrite") never arrive. When
> one fires, check first whether the item has already shipped — that check is
> what this sweep ran, and it found three audit recommendations still open and
> one never actioned.
