# samay — Current State

> Refreshed every release. CLAUDE.md is preferences/process/procedures
> (durable); this file is **state** (volatile).

## Version

**1.5.0** — several GPUs, or a share of one
([ADR-0016](../adr/0016-several-devices-or-a-share-of-one.md)). `resource_req_with_devices` and
`resource_req_with_share` set two new requirement fields; exclusive stays the default, and the keys
reach a snapshot only when used. CPU work goes to accelerator nodes last
([ADR-0017](../adr/0017-cpu-work-goes-to-accelerator-nodes-last.md)), the one change to decisions:
without it, 1.5.0 matches 1.4.6 over the whole differential. Shipped ahead of consumer adoption. A
release before 1.5.0 must not restore a snapshot holding a multi-device task. 1,522 assertions.

**1.4.6** — a pass skips what it already knows fits nowhere
([ADR-0015](../adr/0015-a-pass-only-fills-nodes.md)). Nodes only fill during a pass, so a pass records
each requirement that fit no node and the most cpu, memory and disk free on any one, and refuses what
those rule out without walking the nodes. 100,000 stuck tasks against 100,000 nodes take 0.18 s a
pass, down from 756 s; a pass that places its tasks costs what it did. Every decision is 1.4.5's, proven by a
differential against real 1.4.5 binaries. This finishes the 1.4.x repairs. 1,405 assertions.

**1.4.5** — limits that limit ([ADR-0014](../adr/0014-what-a-document-may-cost.md)). A document is
refused before parsing past 128 MiB, and its parse past ten times its size, through an allocator that
counts: 10 MB of nested arrays peaks at 126 MiB instead of 868. Every writer refuses past the same
limit instead of exiting the process. The derived leaf types gain readers that refuse, and constructors
settle the domain restore reads ([ADR-0005](../adr/0005-restore-input-validation.md)). Restore costs 1.4
to 2.9% more time. 1,322 assertions.

**1.4.4** — standing gates, and no change to `src/`. CI now runs the fuzz harness, the suite on aarch64
and in bounds-checked mode, the README example, the examples, and a build on the toolchain floor,
**cyrius 6.7.10**, found by building. Whole-source mutation runs locally, not in CI. Each gate was shown to
fail on a planted defect. `docs/examples/` holds two runnable examples, and
[`migrating-to-1.4.md`](../guides/migrating-to-1.4.md) tells consumers what moved under them. 1,232
assertions: comparing mutation runs found four tests that passed by luck, now closed.

**1.4.3** — a P(-1) sweep. Accelerators are reserved ([ADR-0013](../adr/0013-accelerators-are-reserved.md)):
through 1.4.2 one GPU went to four tasks. `preempt_if_needed` names a victim only if that places the
task. Restore checks nodes against tasks, so a real 1.0.2 snapshot no longer strands capacity, and it
refuses wrong types and duplicate ids. A pass no longer allocates with history: 33 KB to 152 B at 1,000
finished tasks. Cron gained a clock reset and honest logs ([ADR-0006](../adr/0006-cron-expression-model.md)).
Whole-source mutation kills 87%, up from 76%, and `tests/samay.fcyr` is a real fuzz harness. 1,224
assertions.

**1.4.2** — the write-side JSON codec. `_rr_node` and `_ce_node` build their tree directly instead of
printing with the derive and parsing it back, so a whole snapshot writes 21 to 36% faster. Every byte
is unchanged, proven against real 1.4.1 binaries and held by a permanent corpus in the suite. The
derive stays, so there are two writers of each shape, and the corpus fails if they drift. 864
assertions.

**1.4.1** — closes audit F8 and F9 ([ADR-0012](../adr/0012-cron-burst-budget.md)). Cron evaluation
no longer allocates, and the due count steps by day, so one stale entry costs about 30 µs on any
expression, down from up to 26 ms and 4.8 MB, and the count is exact. A check limits bursts to
`CRON_BURST_BUDGET`: an entry past it is held with its watermark, oldest first next time, and a
single fire is never held. Nothing is dropped. 852 assertions.

**1.4.0** — closes audit F5 ([ADR-0011](../adr/0011-bounded-task-history.md)). The four insertion
sorts are the stdlib's `vec_sort_by`, so a pass at 100,000 tasks takes 58 ms, not 58 s, and the order
is proven unchanged. `task_scheduler_remove_task` and `task_scheduler_prune_terminal` drop finished
tasks. A snapshot past the restore limit is refused whole. Capacity is released in `task_id` order,
which fixes run-to-run differences in `available_cpu`. 804 assertions.

**1.3.0** — the caller's request and the scheduler's assignment are two fields,
`requested_node` and `assigned_node` ([ADR-0010](../adr/0010-request-and-assignment.md)). A
requeued task goes where it asked to go, or to the best fit, and its reason is true.
`ScheduledTask_node_preference` and the snapshot key stay as a view of the two, so no consumer
changes and releases back to 1.0.2 still read a 1.3.0 snapshot. 728 assertions.

**1.2.2** — ai-hwaccel 2.5.6, which fixes 1.2.1's regression: a TPU pod's profile survives
a snapshot again, up to 16,384 chips. A snapshot written after a 1.2.1 restore has already
lost the profile, and 1.2.2 cannot bring it back. 575 assertions.

**1.2.1** — cyrius 6.7.18, bayan 1.11.1, ai-hwaccel 2.5.5, the latest of each. ai-hwaccel
refused a TPU profile over 1,024 chips on restore, so such a node lost that profile. samay
logs a refused profile since this release, and the bound was
[reported upstream](issues/archive/2026-11-01-ai-hwaccel-profile-bounds.md). Snapshots read
both ways between 1.2.0 and 1.2.1, byte for byte. 572 assertions.

**1.2.0** — cyrius 6.7.9, bayan 1.5.13, and `math` out of `[deps] stdlib`. ai-hwaccel
stays at 2.4.2: no tag targets 6.7.9, and 2.5.0 moves to 6.7.18. No `src/` or test
change, and `dist/samay.cyr` differs from 1.1.7's only in its version line. 558 assertions.

**1.1.7** — cyrius 6.6.20, bayan 1.5.12, ai-hwaccel 2.4.2. No `src/` or test change.
`dist/samay.cyr` gains a `# Requires` block, and `dist/samay.deps` lists the 4 leaves
6.6.20's distlib proves the bundle needs, instead of 23. 558 assertions.

**1.1.6** — cyrius 6.6.14, bayan 1.5.11, ai-hwaccel 2.4.1, and `rust-old/` removed. The
18 `bayan_json_v_obj_get` calls in `src/json.cyr` (deprecated by bayan 1.5.10) read
through `bayan_json_v_obj_get_by_cstr`; every key is a string literal, so the lookups are
unchanged. The tag `1.1.5` is the last revision with `rust-old/`
(`git show 1.1.5:rust-old/src/lib.rs`). 558 assertions.

**1.1.5** — test correctness and coverage, done as preparation for deleting
`rust-old/` ([removal readiness](rust-old-removal.md)). No `src/` change. Seven
assertions ported from the Rust oracle could not fail, or were weaker than the
oracle's; all are fixed. Every public function is now called by a test (79/79),
and CI gates on that. ADR-0006's account of the oracle's cron model is corrected.
558 assertions.


Built on **1.1.4** (ai-hwaccel 2.4.0, bayan 1.5.7), **1.1.3** (constructors own
every `Str` they retain), **1.1.2** (the cyrius 6.6.x `Result` value form),
**1.1.1** (every allocation checked, [ADR-0009](../adr/0009-oom-policy.md)),
**1.1.0** (capped cron counts report as floors, `>=`), **1.0.4** (threading
contract, [ADR-0008](../adr/0008-threading-contract.md)) and **1.0.3** (the P-1
sweep).

## Toolchain

- **Cyrius pin**: `6.7.18` (in `cyrius.cyml [package].cyrius`)

## Source

- `src/{uuid,types,scheduler,cronexpr,cron,training,json}.cyr` + `src/lib.cyr`
  aggregation header + `src/main.cyr` demo. The seven `[lib].modules` bundle to
  3,889 lines in `dist/samay.cyr` (as `cyrius distlib` reports it); `json.cyr` is the largest module.
- **Strings are `Str` (ptr+len), not cstr** since **v0.5.0**
  ([ADR-0003](../adr/0003-str-string-representation.md)) — required because
  `#derive(Serialize)` core dumps on a cstr in a `Str`-typed field. Passing a
  bare literal where a `Str` is expected compiles and then misbehaves at runtime, which is
  how the benchmark suite sat dead from v0.5.0 to v1.0.1 and how the README's
  own example was broken until v1.0.4. Wrap literals in `str_from(...)`.
- Bundle: `dist/samay.cyr` (regenerate with `cyrius distlib` after any src change).
- Rust reference: retired after 1.1.5. Its 1,479 lines are at tag `1.1.5`
  (`git show 1.1.5:rust-old/src/lib.rs`). What it did is recorded in the ADRs and
  [`rust-old-removal.md`](rust-old-removal.md).

## Tests

- `tests/samay.tcyr` — **1522/1522 assertions passing**, on x86_64, aarch64 under qemu, and in bounds-checked mode (`cyrius test`), up from 296 in
  v1.0.2. Includes the v1.0.3 additions: the capacity-conservation invariant (the
  assertion whose absence let ADR-0007's defect ship), a cron differential guard pinning
  the optimised matcher to an in-test reference implementation, back-compat snapshot
  restore, wrong-typed nested-leaf rejection, and the parser features that previously had
  **zero** coverage (every `@shortcut` expansion, month/day names, DOW `7`→Sunday).
  v1.0.4 adds the `samay_init()` pre-warm guards (that the chrono month table is
  *filled*, not merely published, after each constructor). v1.1.0 adds the
  capped-due-count guards and pins `task_status_name`, which had zero callers
  anywhere but is exported public API. v1.1.3 adds `test_ownership_retained_strs`,
  which checks that each constructor owns the `Str`s it keeps. v1.1.4 adds
  `test_json_node_shared_memory`, which is mutation-proven, and a bit-level f64
  round trip at a rounding near-tie. v1.1.5 fixes seven assertions ported from the
  oracle that could not fail or were weaker than the oracle's, and four of the
  port's own with the same defects. It also adds nine tests that call the 22 public
  functions no test called. Eight of nine mutations of those functions passed the
  whole 1.1.4 suite; the 1.1.5 suite catches all nine. v1.2.1 adds three tests that
  pin what ai-hwaccel 2.5.5 and bayan 1.11.1 change on restore. v1.2.2 moves the first to
  ai-hwaccel 2.5.6's bound, with real pods on one side of it and one chip past it on the other.
  v1.3.0 adds the request/assignment split's tests and `tests/fixtures/`: snapshots written by
  real 1.0.2, 1.0.4 and 1.2.2 binaries, which every run restores. All 13 mutations of the split
  are caught. v1.4.0 adds the sort gate (3,500 random inputs against the old insertion sort), a
  test of every sort site at a size luck cannot pass, the release-order tests, and removal,
  pruning and write-cap tests. All 34 mutations of that work are caught. v1.4.1 adds the calendar
  gate (every day for 438 years against `epoch_to_date`), the due count against a minute-by-minute
  walk, no-allocation checks, the budget's rules, and the first tests that read samay's log lines,
  through a sakshi emit hook. All 37 mutations of that work are caught. v1.4.2 adds the wire corpus:
  over 4,000 `ResourceReq` and `CronExpr` values must match the derive byte for byte, which is the
  only thing keeping the two writers of those shapes together. All 23 mutations are caught. v1.4.3
  was driven by whole-source mutation, with 151 of 1,176 surviving, all read. It adds tests for
  accelerators, preemption, restore, stats, disk and every snapshot field. v1.4.4 closes four
  tests that passed by luck, whose mutants came and went with the hash seed or where uuids sorted:
  the preemption and best-fit ties, a restore keeping a snapshot's own bits, and a lost reservation.
  Each now rests on 32 entries or a planted value, and each mutant dies on every run measured.
  v1.4.5 adds the limits at their exact byte, the budget allocator's boundaries, the leaf readers
  against the derive's text and seven shapeless documents, and a byte-for-byte round trip for every
  value a constructor kept and restore changed. v1.4.6 adds the record of shapes that fit nowhere,
  tested directly, and passes that must place what a full walk places: a neighbour of a refused shape
  in each field, and each way a node can gain capacity mid-pass through setters. v1.5.0 adds devices
  and shares end to end: constructors, holds, release, preemption, restore and the wire, and the
  CPU-work ranking on mixed fleets.
- `tests/samay.fcyr` — restores mutated snapshots and drives each through a working life, checking
  capacity invariants, with a pinned seed. `cyrius fuzz tests/samay.fcyr`. CI runs it.
- `tests/samay.bcyr` — 16 benchmarks, all green (see `docs/benchmarks.md`). Was dead
  (SIGSEGV) from v0.5.0 to v1.0.1: the `Str` migration left it passing bare cstring
  literals into `Str`-taking APIs. Now run by CI so it cannot rot silently again.
- Gates: `cyrius fmt <file> --check` clean, `cyrius lint <file>` 0 warnings and 0
  untracked deferrals, `cyrius distlib --check` in sync. **All four run in CI.** `fmt` and `lint` take a file
  argument, so CI loops over the files.
- Coverage (v1.5.0): `cyrius coverage --min 100`, **89/89** (cyrius 6.6.14's tool no longer
  counts `src/main.cyr`'s `main`; 1.1.5 read 79/79 on 6.6.6), plus a strict CI check
  that every public function in `[lib].modules` is *called* by a test. The strict
  check exists because the tool counts a name that appears anywhere in the tests,
  including in a comment or inside a longer name. That counting credited
  `cron_scheduler_check_due` and `samay_str_lt` while no test called either.

## Dependencies

- **ai-hwaccel** 2.5.6 (git, the latest tag) — `AcceleratorRequirement` `REQ_*` +
  `profile_to_json`/`profile_from_json` (used by `NodeCapacity` serialization).
  Since 2.3.28 (schema v6) a profile carries `shared_memory_bytes`, which node
  snapshots pass through. `profile_from_json` refuses out-of-range values, so the
  codec is not lossless past 16,384 TPU chips, 16 TiB of device memory, or 95 GiB per
  TPU chip. samay logs each refusal
  ([issue](issues/archive/2026-11-01-ai-hwaccel-profile-bounds.md)).
- **bayan** 1.11.1 (git, the latest tag and the version cyrius 6.7.18 folds) — `dist/bayan-json.cyr`, the focused JSON sublib, *not*
  the 641 KB monolith. bayan left the stdlib snapshot in 1.5.2; taking the
  monolith while ai-hwaccel pulls the sublib vendors both files and collides on
  27 JSON symbols under last-def-wins. The sublib omits the short `json_v_*`
  aliases, so `src/json.cyr` calls the fully-qualified `bayan_json_v_*` spelling
  — which resolves under either bayan packaging, so consumers of
  `dist/samay.cyr` are unconstrained in which they vendor.
- **stdlib** — syscalls, string, alloc, str, fmt, vec, hashmap, io, fs,
  chrono, random, result, tagged, fnptr, freelist, atomic,
  sakshi, process, args, thread, assert, bench.
  (`math` left this list in 1.2.0, and samay calls nothing in it or in `slice`.
  `cyrius deps` vendors both from bayan-json's sidecar.) `cyrius deps` vendors all of it from an empty `lib/`.
  `cyrius lib sync` also copies the unused `lib/hashmap_fast.cyr`, so do not run it here: 1.4.4 took
  that file out of `lib/` and the lock.

## Consumers

- **kavach** — integrated: sizes sandboxes from a samay `ResourceReq`
  (`kavach/src/samay_bridge.cyr`), 436 assertions green against `dist/samay.cyr`.
- **daimon** — integrated: deleted its duplicated `scheduler.cyr`/`cron.cyr` and
  consumes samay as the single scheduler source of truth (api_sched rewired; 215 assertions).
  The migration surfaced + fixed the `uuid_v4`↔libro collision (samay 1.0.1).
- Current pins, as of 1.5.0: kavach 3.13.2 → samay `1.1.6`, daimon 2.4.3 → `1.1.3`,
  stiva 3.0.22 → `1.1.2`. daimon also sets `path = "../samay"`, so its local
  builds use this checkout, not the tag. The only samay JSON call among
  them is daimon's `SchedulingDecision_to_json`, which is emit-only. None of them
  restores a samay snapshot.
- **stiva** — the one caller of `cron_scheduler_check_due_at` (`src/cron.cyr`, `stiva cron
  check`). It runs CRON_SKIP only, rebuilds the scheduler on each `check`, and stores `now` as
  every enabled job's `last_fired` whatever samay did. That is safe because a SKIP entry is never
  held. If stiva ever offers CRON_CATCHUP it must read watermarks back from the entries, or held
  jobs lose what they owed ([ADR-0012](../adr/0012-cron-burst-budget.md)).
- zugot's marketplace recipe is stale: it still describes samay as a Rust crate at v0.1.0
  (cargo build, `Cargo.toml`, `runtime = "rust-crate"`). Needs a rewrite for Cyrius.

## Next

See [`roadmap.md`](roadmap.md), the single source for forward work, with every item pinned to a
version. **1.5.0** shipped ahead of consumer adoption, and **1.5.1** audits everything to date. Features
then run from **1.6.0** to **1.8.0**, and removals wait for **2.0.0**.

**Concurrency — audited in v1.0.4, see [ADR-0008](../adr/0008-threading-contract.md).**
Retired as an unknown; now a stated contract with measured backing. Open items from it:
`lib/chrono.cyr`'s publish-before-fill ordering was fixed upstream in cyrius 6.5.37; `lib/sakshi.cyr`'s unsynchronised ring
indices and span depth can interleave log output under concurrent use (observability
only, and outside the contract); and an opt-in debug mode that *detects* concurrent entry
was considered and not built — worth revisiting if any consumer adopts a threaded shape.

**Audited in the 1.4.3 sweep, which retired the four risks previously listed here:**
- **The accelerator placement path** was run with real profiles, which found that devices were never
  reserved ([ADR-0013](../adr/0013-accelerators-are-reserved.md)), and it now has benchmark rows.
- **Test correctness** has a number: whole-source mutation, recorded in the CHANGELOG. A second audit
  read every assertion against an authority other than the code.
- **aarch64** passes the whole suite under qemu, and so does bounds-checked mode. CI gates both.
- **Fuzzing** is real: `tests/samay.fcyr` restores mutated snapshots and then drives them through a
  working life. It was a stub until 1.4.3.

**Retired in 1.4.5:** restore's memory. The item limits bounded neither memory nor bytes, and a byte
limit with a parse budget now does ([ADR-0014](../adr/0014-what-a-document-may-cost.md)).

**Retired in 1.4.6:** the cost of a stuck queue. A pass walked every node for every waiting task
([ADR-0015](../adr/0015-a-pass-only-fills-nodes.md)). A placed task still walks every node.

**Still unretired:** agnos has no run at all. Replay after a restore can assign a different device than
the original on a node whose profiles overlap (ADR-0013). Every restore leaves its parse tree, about six
times the document, on the heap for good, since `alloc()` never frees: pinned to 1.5.1, with a P(-1)
audit of everything to date.
