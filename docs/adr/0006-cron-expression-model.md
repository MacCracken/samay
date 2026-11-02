# ADR 0006 — Cron expression model and missed-schedule semantics

**Status**: accepted (2026-08-29, v1.0.3). Records a divergence that shipped
unrecorded in v0.3.0, and the semantics settled by the P-1 sweep.
**Amended** 2026-11-01 (v1.4.3): a large backward clock step re-anchors the watermark (section 3),
an entry replaced under the same name keeps its place (section 6), disabling an entry logs what it
gave up (section 4), and every late fire is logged (section 5).
**Amended** 2026-09-23 (v1.1.5). The first version misdescribed the oracle's model, both
its field names and its first-fire rule. It also did not record the one capability that
had no replacement. Both corrections are made below. This ADR is the record of the
oracle's cron model once `rust-old/` is deleted, so it has to be right.

## Context

The Rust oracle (`rust-old/src/lib.rs:598-709`) has no cron expressions. A `CronEntry`
carries `interval_seconds`, an optional `specific_hour` and `specific_minute`, and a
`last_fired` watermark. `check_due` fires an enabled entry in two cases:

- it has never fired;
- `now - last_fired >= interval_seconds`.

If `specific_hour` or `specific_minute` is set, the current UTC hour or minute must also
match. A call pushes at most one task per entry and sets `last_fired = now`.

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

- **First fire.** An interval entry that has never fired fires on the very first
  `check_due`, at whatever time that is (`lib.rs:673-679`; the oracle's own
  `test_cron_check_due_fires_first_time` asserts it). A cron entry fires on its first
  evaluation only if that minute matches the expression, and never retroactively:
  `last_fired == 0` anchors the watermark at `now`.
- **Fires per call.** Rust pushes at most one task per entry per `check_due`. samay fires
  every missed occurrence under `CRON_CATCHUP`, bounded by `CRON_CATCHUP_CAP` (1000).
  Under `CRON_SKIP` it fires exactly one and logs the rest as dropped.
- **Relative intervals have no replacement.** An interval was measured from the last fire,
  in seconds, with no alignment to the clock; the oracle's tests used 1 s and 10 s. A cron
  expression names wall-clock minutes. That leaves two kinds of schedule with no
  expression:
  - a sub-minute schedule, such as "every 10 seconds";
  - a period that does not divide the hour or the day, counted from the last run, such as
    "every 90 minutes since the last fire".

  A consumer that needs one runs its own timer and submits tasks with
  `task_scheduler_submit_task`. This is accepted: every schedule in the domain so far is
  wall-clock, and expressions are what make parse-time validation and the missed-schedule
  policy possible.

### 2. The Vixie DOM/DOW rule is AND-when-starred, and the mask always applies

`crontab(5)` and Vixie's `cron.c` combine day-of-month and day-of-week as: if **either**
field begins with `*`, the two masks are AND-ed; otherwise they are OR-ed. samay
implemented the star flag correctly (any field beginning with `*`, so `*/N` sets it too)
but then **discarded the starred field's mask** instead of AND-ing it.

That is equivalent to Vixie only when the starred field is a bare `*`, whose mask is
all-ones and therefore an AND identity. For a step it is not: `*/2` over DOM 1-31 is the
odd days. So `0 0 */2 * *` fired 365 days a year instead of 186, and `0 0 * * */2` fired
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

**v1.4.3: a backward step past 3 hours re-anchors.** A monotonic watermark has a failure of its
own: one reading ahead of the truth, a bad clock at boot, leaves every entry waiting for real
time to catch up, and a 30-day error stops all cron work for 30 days. Vixie's `cron.c` solves the same
problem the same way: a small step back waits, and a large one starts again from now. So a step
of up to `CRON_CLOCK_RESET_SECS` (3 hours) holds the watermark as above, and a larger one treats the
entry as a first evaluation, firing if the current minute matches. The cost is that a real clock step
back of more than 3 hours, such as a restored VM, re-fires that interval as it passes again.

### 4. A disabled entry tracks the clock; it does not accrue debt

The whole per-entry body was gated on `enabled == 1`, so `last_fired` froze while an
entry was disabled and the entire disabled interval counted as "missed" on re-enable:
**720 tasks** in a single `check_due_at` after a 30-day disable of `0 * * * *` — and
**silently**, because only the capped path logged.

A disabled entry now advances its watermark like an enabled one, so disabling means "do
not run", not "queue it all up for later". Chosen because the alternative is a burst of
task creation for a window the operator deliberately turned the schedule off, which is
both surprising and unbounded by anything except the catch-up cap. Neither consumer
(kavach, daimon) called the cron API then, so nothing downstream depended on the old
behaviour — this was the free moment to settle it.

**v1.4.3:** disabling gives up what the entry owed from before it was disabled, too, and until then
said nothing. The first check that sees it disabled now logs how many occurrences it gave up. The flag
is read only at a check, so disabling and re-enabling between two checks is not seen at all.

### 5. Every catch-up burst is logged

Previously only a `CRON_CATCHUP_CAP`-capped burst logged. A sub-cap burst fired silently,
which violates the domain principle that the missed-schedule policy is always visible.
All three outcomes — skip, catch-up, and capped catch-up — now emit a `sakshi` warning.

**v1.4.3:** so does a single late fire, which is all a daily entry ever does, under either policy. An
occurrence that is on time is not counted as missed. A count past the 366-day window covers only the
window and says so.

### 6. An entry replaced under the same name keeps its place (v1.4.3)

`cron_scheduler_add` built a new entry with no history, so editing a schedule re-fired the current
minute and forgot everything owed since the last check, with no log line. A replaced entry now takes
the old watermark, unless the new one brings its own, as stiva's does. Removing an entry and adding it
back is different: nothing is left to keep, and it starts fresh.

### 7. Grammar that differs from Vixie (v1.4.3, recording what shipped)

- `N/S` is accepted and runs from N to the end of the field, as in cronie. Vixie refuses it. `JAN/3`
  and `MON/2` follow.
- `@reboot` is refused at parse time: samay has no boot to run at.
- A number has at most 9 digits, so `*/1000000000` and `0000000001` are refused.

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
- The cross-entry aggregate work budget (audit F8/F9) closed in v1.4.1
  ([ADR-0012](0012-cron-burst-budget.md)). That also corrected this ADR's prefilter note: it
  kept `epoch_to_date` off the miss path only, and a match still allocated until then.
