# samay — Roadmap

> **Last refreshed**: 2026-08-30 (v1.1.0)
>
> **Forward-looking only.** Nothing shipped belongs here — per-release detail
> lives in [`../../CHANGELOG.md`](../../CHANGELOG.md) (complete from 0.1.0), the
> decisions in [`../adr/`](../adr/), and live state in [`state.md`](state.md).
>
> Version pins below are **targets that fix ordering, not commitments to dates**.
> An item moves when its dependencies are met; a trigger-gated item has no pin at
> all, deliberately — see [Trigger-gated](#trigger-gated--no-pin-by-design).

> **Current**: **v1.1.0**, cyrius pin **6.5.36**, deps ai-hwaccel **2.3.19** +
> bayan-json **1.5.2**. Gates green: **432 assertions**, **5/5 benchmarks**,
> lint 0-warn / 0 untracked deferrals, fmt clean, `dist/` in sync (2,345 lines),
> 0 symbol collisions against the vendored deps. `src/` is 9 modules against the
> frozen 1,479-line Rust oracle.

## The arc at a glance

| Version | Theme | Risk | Gate to entry |
|---|---|---|---|
| ~~1.1.0~~ | ~~Cron catch-up counting tells the truth~~ | — | **shipped 2026-08-30** |
| **1.1.1** | Checked `alloc()` across `src/` | low | none — ready |
| **1.2.0** | Split `node_preference` (ADR-0009) | medium | wire back-compat proof |
| **1.3.0** | F5 — stable sort + terminal-task pruning | **high** | sort consolidation first |
| **1.4.0** | F8/F9 — cron aggregate work budget | medium | an ADR on the exhaustion rule |
| **1.5.0** | Write-side JSON codec | medium | byte-equality corpus |
| *(none)* | Trigger-gated items | — | a consumer event |

---

## 1.1.x — surfaced by the 2026-08-30 deferral sweep

**1.1.0 shipped 2026-08-30** and is recorded in the CHANGELOG, not here. Of the
three items it was scoped around, **two were not work**: verifying each against
current source found one a measured no-op and one already shipped in the original
port. Both are under [Considered and rejected](#considered-and-rejected) with the
evidence. That is the sweep working as intended — the check is the point, and it
cost less than either implementation would have.

### 1.1.1 — checked `alloc()` across `src/`

- [ ] **Check the 16 `alloc()` results in `src/`.** `alloc` returns 0 on OOM, and
  none of the sites test it, so OOM becomes a wild write at a small address
  rather than a recoverable failure. The P-1 sweep **refuted** the specific crash
  scenario originally filed — under real memory pressure the process dies inside
  `lib/chrono.cyr`'s allocation first, never reaching samay's sites — so this is
  defensive coding, not a demonstrated defect. Add the rule to CLAUDE.md's Key
  Principles beside the `var buf[N]` note so new code inherits it.

### Not version-pinned — do it independently of any release

- [ ] **File the F4 hash-seeding issue upstream.** Audit Rec 5 said to file it;
  the roadmap has said "upstream, not ours" ever since; **nobody filed it.**
  Verified 2026-08-30: nothing matching in `cyrius/docs/development/issues/` or
  `proposals/`. `lib/hashmap.cyr`'s unseeded FNV-1a means the collision set is
  precomputable once against every consumer. samay cannot fix a vendored module,
  but it can stop being the reason nobody knows.

## 1.2.x – 1.5.x — existing backlog, re-sequenced

Ordering is by dependency and blast radius, not by appetite. F5 (1.3.0) is the
one with real risk, and it sits behind a mechanical refactor that must land first.

### 1.2.0 — split `node_preference` into request and assignment

- [ ] `schedule_pending` overwrites the caller's requested node with the chosen
  one (`src/scheduler.cyr`), which destroys the accurate "preferred node"
  decision reason. ADR-0007 balanced the *accounting* with a separate
  `reserved_on` and deliberately left the field semantics alone, because changing
  the meaning of a shipped field is not a patch-release action. **Needs its own
  ADR-0009.** Achievable without a wire break if the new field is nullable and
  defaulted on restore — the same shape `reserved_on` used in 1.0.3, which is the
  proof that it works. *Entry gate*: a back-compat restore test over a 1.0.x
  snapshot corpus, both directions.

### 1.3.0 — F5: stable sort + terminal-task pruning

- [ ] **Consolidate the four insertion sorts first, then swap the algorithm
  once.** `src/scheduler.cyr` ×2, `src/cron.cyr`, `src/json.cyr`; two are already
  exact `_sort_by_key` specialisations, so the consolidation is mechanical and
  removes ~40 lines. Only then replace the algorithm — measured ~85× slower than
  a merge sort at n=8000.
- [ ] **Prune terminal tasks.** They accumulate in `TaskScheduler.tasks` forever;
  there is no removal API at all. Adds `task_scheduler_remove_task` (additive) and
  an optional `task_scheduler_prune_terminal`, both caller-driven and off by
  default. Depends on `reserved_on` (shipped 1.0.3) so a removal releases any held
  reservation. Also cap the **write** side of `task_scheduler_to_jsonv` at
  `SAMAY_JSON_MAX_ITEMS` — today the read side rejects >100k while the write side
  has no cap, so samay can emit a snapshot it will then refuse to restore.
- **Why this is the risky one**: ADR-0004's determinism guarantee rides on those
  comparators. *Entry gate*: sort 2,000 randomised inputs and assert the merge
  result is element-for-element identical to the insertion result, plus the
  existing determinism group green.

### 1.4.0 — F8/F9: cron aggregate work budget

- [ ] Per-entry catch-up is bounded (`CRON_SCAN_WINDOW_SECS`, `CRON_MAX_COUNT`,
  `CRON_CATCHUP_CAP`); the aggregate across many entries in one `check_due_at` is
  not. v1.0.3's alloc-free prefilter cut the cost ~12× and removed the heap growth
  entirely, so this is now a **policy** question rather than an availability one.
  Lands in `_cron_check_entry`, which v1.0.3 extracted for exactly this.
  *Entry gate*: an ADR settling the exhaustion rule — every candidate (stop early,
  skip remaining entries, degrade to SKIP) collides with "missed schedules are
  never silently skipped", and that conflict is the actual work.

### 1.5.0 — write-side JSON codec

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
- [ ] **F4 — upstream hash seeding lands.** Once filed (above) and fixed upstream,
  re-check whether samay's own guarantees change. v1.0.3 already removed the one
  path by which bucket order reached a documented-deterministic decision.
  *Trigger*: an upstream release.
- [ ] **Drop `samay_init`'s chrono pre-warm.** Only once
  `cyrius/docs/development/proposals/2026-08-30-lazy-init-publish-before-fill.md`
  ships **and** the pin moves past it. *Trigger*: an upstream release.

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
  *The real cost here is the full-window scan itself (~3.9 ms per stale entry),
  and the fix for that is the aggregate budget at 1.4.0, not a restore clamp.*
- **Raise `CRON_MAX_COUNT` to the window size** (planned for 1.1.0). **Not free,
  as had been claimed.** A matching minute costs ~40× a missing one — it passes
  the v1.0.3 prefilter and reaches `epoch_to_date` — so `* * * * *` over a full
  window is **28.9 ms** capped at 100,000 against **~153 ms** uncapped. 5× more
  work to make a log line exact. v1.1.0 shipped the free half instead: the count
  now carries a floor flag and the logs say `>=` (v1.1.0).
- **Saturating subtraction in the stats averages** (audit Rec 6, planned for
  1.1.1). **Already shipped** — the guards have been in `task_scheduler_stats`
  since `e3861d2 "rust port parity"`, the original port. Rec 6 was filed as "no
  confirmed finding, still worth it" and was already satisfied when written.

- **SKIP-path early exit in `_cron_count_due`** (audit Rec 4, second half).
  Exiting the count early once a match is found would make the SKIP branch cheap
  — but that branch logs `due - 1`, the **exact** number of dropped occurrences.
  An early exit turns that number into a fabrication, and "missed schedules are
  never silently skipped" is not satisfied by reporting a wrong count instead of
  none. 1.1.0 makes the count *more* accurate for the same reason. Revisit only
  with a bounded form that reports "≥ N" honestly.

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
