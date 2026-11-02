# 0012 — An exact due count, and a burst budget that holds entries instead of dropping them

**Status**: Accepted
**Date**: 2026-11-01

## Context

Audit findings F8 and F9 said one `cron_scheduler_check_due_at` had per-entry limits but no limit
across entries. The roadmap called what remained a policy question, and said v1.0.3 had removed the
heap growth. Every way of stopping early seemed to collide with "missed schedules are never silently
skipped": stop early, skip the remaining entries, or degrade to SKIP.

Reading and measuring the code changed that account in three places:

1. **The heap growth was only gone on a miss.** A matching minute still reached `epoch_to_date`,
   which allocates 48 bytes that are never freed. On 1.4.0 one entry behind the whole window costs
   3.1 ms and 18.5 KB for `0 0 1 1 *`, and **26 ms and 4.8 MB** for `* * * * *`. So 100 stale
   per-minute entries burn 480 MB in one check. This was an availability problem, and rationing it
   with a budget would still have left a leak.
2. **Most of the cost was a count that did not need scanning.** `_cron_count_due` tested every
   minute of a 527,040-minute window, for a number used in a log line and a cap. The time of day and
   the calendar day are independent fields, so a whole day that matches holds a known number of
   minutes.
3. **There is a consumer, and it writes the watermark itself.** stiva's `cron_due_at` runs CRON_SKIP
   only, rebuilds the scheduler on every `stiva cron check`, and stores `now` as every enabled job's
   `last_fired` whatever samay did. An entry held back with its old watermark would have that
   watermark overwritten, and its fire would vanish with no log line. That is the silent skip the
   rule forbids, in code that already ships. Any rule that can hold a single fire is wrong for this
   reason.

Once the count is cheap, one amplification remains: a CRON_CATCHUP entry can fire 1,000 tasks, so
100 stale entries still create 100,000 tasks and 45 MB in one check, and the restore ceiling allows
100,000 entries.

## Decision

**The count is exact and costs almost nothing, only bursts are budgeted, and a held entry keeps its
watermark.**

1. **`cron_expr_matches` no longer allocates, on a hit or a miss.** `_cron_month_day` is the
   Gregorian civil-from-days conversion: O(1), with no allocation and no table. The matcher is now
   two halves, `_cron_time_matches` and `_cron_day_matches`.
2. **`_cron_count_due` steps by UTC day, using those same two halves**, so a count cannot disagree
   with the matcher. A whole matching day adds a precomputed total; only the two partial days at the
   ends are walked. The result is always exact, so `CRON_MAX_COUNT`, the floor flag and the logged
   `>=` are gone. Bits past a field's range are not counted, because restore does not range-check
   masks and the matcher can never test them.
3. **`CRON_BURST_BUDGET` (10,000) limits the tasks bursts fire in one check.** A burst is an entry
   firing more than one task, which only CRON_CATCHUP can do. **A single fire is never held and never
   spends the budget**: not a SKIP entry, not an on-time CATCHUP entry, not a first evaluation. So one
   check fires at most `entries + CRON_BURST_BUDGET` tasks, and no schedule that is on time can be
   delayed, however large it is.
4. **An entry that would pass the budget is held: no task, no log line of its own and no watermark
   move.** Its whole debt stays due, and the check logs one line with how many entries it held.
   Nothing is dropped, so the principle holds without weakening it. A held entry that runs later
   looks exactly like an entry whose host was down for longer, which the catch-up path already
   handles.
5. **A check evaluates oldest watermark first, then by name.** The watermarks are the queue: a held
   entry has the oldest one, so it goes first next time, with no cursor and nothing new on the wire.
   Each entry that fires moves behind every held entry, and the first burst of a check always runs,
   so every held entry gets its turn. Name order alone would starve: the same few names would spend
   the budget on every check.
6. **To clear a backlog sooner, call again at the same `now_ns` until a check returns nothing.** No
   new function is needed, and a repeated check cannot fire anything twice.

The audit's other proposals, a scan budget and a SKIP early exit, are not built. With no scan left to
ration they would add a limit with nothing to protect.

## Consequences

- **Positive** — One entry behind the whole window costs about 30 µs on either expression, down from
  3.1 ms and 26 ms, and 4.8 MB becomes nothing. That includes firing its one task, and is measured
  mid-day; at midnight there are no partial days, and it is about 19 µs. 100,000 stale SKIP entries
  take 3.1 s and 93 MB, all of it the tasks they fire. By extrapolation from 100 entries, 1.4.0
  needed about 43 minutes and 480 GB, which no real host would finish.
- **Positive** — A long outage is smoothed out. 100 hourly CATCHUP entries after 30 days owe 72,000
  tasks: 1.4.0 fired them in one 223 ms, 37 MB check, and 1.4.1 fires them over 8 checks of 24 ms
  and 4 MB. The total is unchanged.
- **Positive** — Logs now give the true figure. `fired 1000 of 527041` replaces
  `fired 1000 of >= 100000`.
- **Positive** — The same schedule at the same time holds the same entries, because the budget counts
  tasks rather than time. A snapshot taken mid-drain carries the held work, because it is only
  watermarks.
- **Positive** — samay no longer reaches `epoch_to_date` from any cron path, which removes the one
  route to the chrono race [ADR-0008](0008-threading-contract.md) worked around.
- **Negative** — A check that fires nothing costs 70 ns more per entry, 387 ns to 458 ns, or +18%. At
  1,000 entries that is 0.07 ms per check. The likely cause is evaluation order, which now reads two
  watermarks per comparison, though the split was not measured. It was accepted rather than adding a
  second code path used only when a backlog exists. A check that fires gets 4% cheaper, and a real
  match takes 44 ns, down from 271 ns.
- **Negative** — `cron_expr_matches` costs 4.6 ns more on a day-of-week miss, 13.9 ns to 18.5 ns,
  because the matcher is now two calls. That is the path the suite's row measures, so that row reads
  +33%. The two calls are what keep a count from disagreeing with the matcher.
- **Negative** — A held CATCHUP entry can pass `CRON_CATCHUP_CAP` while it waits, so occurrences that
  would have fitted are capped instead, and the cap's log line reports it. The oldest-first order
  keeps the wait short: at least ten full bursts run per check at the default budget.
- **Negative** — A caller that stores watermarks itself must read them back from the entries. Writing
  `now_ns` over a held entry deletes what it owed. stiva does this today and is safe only because it
  runs CRON_SKIP, which is never held. A CRON_CATCHUP consumer built the same way would lose work.
- **Negative** — A pass recounts every held entry, about 25 µs each: 2.6 s per check if 100,000
  entries are all held at once. That is bounded, and it applies only while such a backlog drains.
- **Neutral** — When watermarks differ, the returned tasks come oldest debt first rather than by name.
  Over 3,000 random schedules and 5.45M fires against real 1.4.0 binaries, the tasks fired and every
  log line match, and when watermarks tie the order is byte-identical too. A count past the old
  100,000 stop is now exact, which is the intended change.
- **Neutral** — `CRON_MAX_COUNT` is gone from the bundle. Nothing in daimon, kavach or stiva read it.

## Alternatives considered

- **A budget on minutes scanned, as the audit proposed.** It rations a cost that can simply be
  removed, and it drains badly: a 30 ms budget clears about 10 stale entries per check, so 100,000 of
  them would take a week at one check a minute.
- **Clamp the remaining entries' `last_fired` on exhaustion, as the audit proposed.** The roadmap
  already rejected this clamp as a measured no-op, since the scan floor gives the same window.
- **Stop and advance the watermark.** This drops occurrences. The log line would make it visible, but
  it would still replace the operator's chosen policy with an accident of entry order.
- **Degrade CATCHUP to SKIP past the budget.** The same objection: the policy is the operator's.
- **Budget every fire, single fires included.** Simpler to state, but a fleet of 20,000 entries at
  midnight would be late on an ordinary day, and stiva would silently lose held jobs.
- **Fire part of a burst, leaving the watermark at the last occurrence fired.** It uses the budget
  exactly, but it needs the time of the Nth occurrence, and the entry's cap log would no longer mean
  what it says. Holding the whole entry is simpler, and the budget is only ever a rough limit.
- **A cursor for where the last check stopped.** It would be new wire state, or lost on restore.
  Oldest-first gives the same fairness from data the snapshot already has.
- **Name order, re-sorting by watermark only when a backlog exists.** Slightly cheaper on a quiet
  check, but the path that matters most would be the one that runs least.
