# ADR 0006 — Cron expression model and missed-schedule semantics

**Status**: accepted (2026-08-29, v1.0.3). Records a divergence that shipped
unrecorded in v0.3.0, and the semantics settled by the P-1 sweep.

## Context

The Rust oracle (`rust-old/`) has no cron expressions. Its recurring-task support is an
**interval** in seconds: an entry stores `interval_secs` plus `last_run`, and each
`check_due` call pushes at most one task per entry when `now - last_run >= interval`.

M2 (v0.3.0) replaced that wholesale with standard 5-field cron expressions, parse-time
validation, and an explicit missed-schedule catch-up/skip policy. That is a substantial
behavioural divergence from the oracle and it was never recorded in an ADR — CLAUDE.md
requires one ("diverge only with an ADR"). This ADR records it retroactively, and settles
three semantic questions the 2026-08-29 P-1 sweep surfaced as either wrong or undefined.

The sweep found the DOM/DOW combination rule was implemented incorrectly, and that two
watermark behaviours were undefined in a way that produced silent, surprising bursts of
task creation.

## Decision

### 1. Expression model (retroactive, v0.3.0)

Recurring entries carry a parsed 5-field cron expression, not an interval. Fields are
i64 bitmasks; every expression is validated at **parse** time, never at execution time.
Consequences that differ from the oracle and are accepted deliberately:

- **First fire.** An interval entry fires `interval` seconds after registration; a cron
  entry fires at the next instant matching the expression, and never retroactively on
  first evaluation (`last_fired == 0` anchors the watermark at `now`).
- **Fires per call.** Rust pushes at most one task per entry per `check_due`. samay fires
  every missed occurrence under `CRON_CATCHUP`, bounded by `CRON_CATCHUP_CAP` (1000).
  Under `CRON_SKIP` it fires exactly one and logs the rest as dropped.

### 2. The Vixie DOM/DOW rule is AND-when-starred, and the mask always applies

`crontab(5)` and Vixie's `cron.c` combine day-of-month and day-of-week as: if **either**
field begins with `*`, the two masks are AND-ed; otherwise they are OR-ed. samay
implemented the star flag correctly (any field beginning with `*`, so `*/N` sets it too)
but then **discarded the starred field's mask** instead of AND-ing it.

That is equivalent to Vixie only when the starred field is a bare `*`, whose mask is
all-ones and therefore an AND identity. For a step it is not: `*/2` over DOM 1-31 is the
odd days. So `0 0 */2 * *` fired 365 days a year instead of 183, and `0 0 * * */2` fired
7 days a week instead of 4. Both masks are now always applied.

This is a **behavioural break for any schedule using `*/N` in DOM or DOW**, and it is
intentional — the previous behaviour did not match the documented rule, the module
header, or `docs/architecture/overview.md`. The blast radius is provably confined to that
one shape: a bare `*` is an AND identity, so every other expression is bit-for-bit
unchanged, verified by a 1.6M-pair differential sweep against a reference matcher.

An existing test (`test_cron_step_star_dom`) asserted the defective behaviour and stated
the wrong rule in its comment; it was rewritten from the Vixie source.

### 3. The watermark advances monotonically

`last_fired` was stored unconditionally, so a backward clock step (NTP correction, VM
restore, or any caller of the injected-clock `check_due_at`) rewound it and the next
forward call re-fired the whole intervening interval — measured at 9 tasks for 6 distinct
minutes, with distinct `task_id`s a consumer cannot deduplicate.

The watermark now only ever moves forward, and a backward step is logged rather than
acted on. `cron_scheduler_check_due` reads `CLOCK_REALTIME`, so this needed no caller
error to trigger.

### 4. A disabled entry tracks the clock; it does not accrue debt

The whole per-entry body was gated on `enabled == 1`, so `last_fired` froze while an
entry was disabled and the entire disabled interval counted as "missed" on re-enable:
**720 tasks** in a single `check_due_at` after a 30-day disable of `0 * * * *` — and
**silently**, because only the capped path logged.

A disabled entry now advances its watermark like an enabled one, so disabling means "do
not run", not "queue it all up for later". Chosen because the alternative is a burst of
task creation for a window the operator deliberately turned the schedule off, which is
both surprising and unbounded by anything except the catch-up cap. Neither consumer
(kavach, daimon) calls the cron API today, so nothing downstream depended on the old
behaviour — this was the free moment to settle it.

### 5. Every catch-up burst is logged

Previously only a `CRON_CATCHUP_CAP`-capped burst logged. A sub-cap burst fired silently,
which violates the domain principle that the missed-schedule policy is always visible.
All three outcomes — skip, catch-up, and capped catch-up — now emit a `sakshi` warning.

## Consequences

- Schedules using `*/N` in DOM or DOW change behaviour. This is a correctness fix; the
  old behaviour cannot be recovered and should not be.
- Disable/enable cycles no longer replay. Anyone who *wanted* replay must record their
  own watermark and use `check_due_at`.
- `cron_expr_matches` is now alloc-free on the miss path (a prefilter runs the minute,
  hour and day-of-week masks before the calendar decomposition), 282 ns → 22 ns. That is
  a required-identical transformation, and the differential sweep is kept in the suite as
  `test_cron_matcher_differential` so it stays that way.
- Everything here is UTC. There is no DST or timezone handling, so "02:30 nightly" is
  wrong by an hour twice a year in a zone that observes DST. Timezone support would
  change the on-the-wire format and is deferred.
- The cross-entry aggregate work budget (audit F8/F9) is still open and is tracked in
  [`docs/development/roadmap.md`](../development/roadmap.md); it lands in
  `_cron_check_entry`.
