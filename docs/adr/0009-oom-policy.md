# ADR 0009 — samay checks every allocation it performs, and aborts on failure

**Status**: accepted (2026-08-30, v1.1.1).

## Context

`alloc(n)` returns **0** on OOM. samay had 16 raw `alloc(` call sites in `src/`
and checked none of them. The roadmap carried this as "an OOM becomes a wild
write at a small address."

**That premise was wrong**, and measuring it changed the shape of the release.

**Every one of the 16 already fails loudly.** Each stores to the fresh pointer at
a field offset ≤ 112, against `vm.mmap_min_addr = 65536` — so the store traps in
the guard page. Measured in six modules: exit 139 at the first store,
deterministically, *inside the named constructor*. Fifteen of the sixteen store at
offset 0 on the very next line. Guarding them converts an anonymous `signal 11`
into a named message. That is a diagnostic, not a crash fix.

**The dangerous allocations were not among the 16.** Eleven allocation points in
`src/` are not raw `alloc(` tokens — `vec_new`, `map_new_str`, `str_new`,
`str_builder_build` — so a mechanical `grep alloc(` never saw them. Those are the
ones where a null **escapes as struct data**: the constructor returns an object
that looks healthy. Two were measured producing a *wrong answer* before any crash:

- **`node_capacity_new`** stored `vec_new()`'s result into `accel_profiles`
  unchecked. On OOM that is 0; for a CPU node the `gpu_available` branch is
  skipped, so nothing touches the null vec and **the struct is returned intact**.
  `node_capacity_can_fit` then answered **1** for a `REQ_NONE` requirement
  (`_accel_ok` short-circuits before reading the vec), and a full
  `schedule_pending` pass **placed a task on the corrupt node** — one decision, no
  fault. It died much later in `vec_len(0)` on the JSON path. A successful, wrong
  scheduling decision is precisely the class this project's resource-awareness and
  determinism rules exist to forbid. The restore path had the identical bug.
- **`samay_uuid_v4`** returned `str_new(out, 36)` unchecked. The null `Str`
  becomes `ScheduledTask.task_id` and then a hashmap key — and it does **not**
  fault there, because `hash_str_v` null-guards (`lib/hashmap.cyr:85`). The task
  inserts under bucket 0 and `map_size` becomes 1. The SIGSEGV lands on a later,
  unrelated submit that probes into slot 0 and reaches `str_eq(0, key)`. Measured
  at the 8th, 10th and 10th subsequent submit across three runs — nondeterministic,
  cross-frame, and unattributable to the allocation that actually failed.

Note the irony: the *listed* site in `uuid.cyr` (`alloc(37)`) fails immediately
and harmlessly. The unlisted one is the bug.

## Decision

> **samay checks every allocation it performs and aborts on failure. It never
> propagates an OOM.** An "allocation samay performs" is a raw `alloc()` in
> `src/`, or a stdlib helper that returns 0 on OOM (`str_new`, `str_from`,
> `str_from_buf`, `str_builder_build`, `vec_new`, `map_new_str`) **whose result
> samay returns from the enclosing function or stores into one of its own
> `#derive(accessors)` struct fields**. Every such result is tested for 0 where it
> is produced, and a 0 calls `panic("samay: out of memory in <fn>")` — never a
> `0` return, never an `Err`. Two categories are deliberately left unchecked:
> results consumed by the very next statement (log-message builders, `str_eq_cstr`
> inputs, `_parse` inputs), which trap one statement away where a guard buys
> nothing; and values handed to a dependency's constructor (`bayan_json_v_*`,
> ai-hwaccel `profile_*`), which inherit that dependency's policy. `src/main.cyr`
> is the demo entry point and is out of scope.

**The one rule to remember: a null must never leave the function that created
it.** Everything else is a consequence.

28 guards across 7 modules. `panic` is `lib/assert.cyr:42` — three writes to fd 2
and `sys_exit(1). **It allocates nothing**, which is mandatory on this path, and
it routes through `sys_exit` so it is target-portable (unlike a raw
`syscall(60,1)`, which the stdlib always `#ifdef`-guards).

### Why not `return 0`

Reproduced, not argued. A propagated 0 travels **further**, not less far:

- A null `CronTaskTemplate` survived `cron_entry_new`, `cron_scheduler_add_entry`
  *and* `cron_scheduler_list_entries` — which reported a healthy `len=1` — before
  faulting in `to_json_str`.
- A two-task snapshot with one OOM-0 record restored as `tasks=1`, **exit 0**: the
  task silently lost, the restore reporting success. That directly contradicts the
  rule stated in `src/json.cyr` that samay never silently drops.

And in the JSON readers **0 is already spent**. [ADR-0005](0005-restore-input-validation.md)
gives it the fixed meaning "reject this record", and the container deserializers
act on it by dropping and continuing. An OOM-0 there would drop a **well-formed**
record from a **valid** snapshot — the exact case ADR-0005 says never happens.
Worse, it would make the ADR-0005 regression suite pass *for the wrong reason*:
every `reader(...) == 0` assertion is satisfied by an OOM.

The same collision exists in `preemption_action_new`: `task_scheduler_preempt_if_needed`
returns 0 for "no candidate needs preempting", so an OOM-0 would be an unlogged
wrong scheduling decision — and two existing tests assert that equality, so they
would pass on an OOM.

### Why not `Err`

Structural, not stylistic. `Ok`/`Err` each heap-allocate 16 bytes
(`lib/result.cyr`, measured via `alloc_used()` deltas) — constructing the error
value requires the allocation that just failed. In `cron_expr_parse` this is
total: the enum constructors are compiler-generated and unreachable from Cyrius
source, so **under true OOM that function cannot return at all**, not even to
reject a malformed expression. That is the strongest single argument for
fail-fast.

Adding an OOM `Err` arm to `task_scheduler_submit_task` would also be actively
unsafe today: daimon reads the payload with no tag check, so an `Err(1)` would be
read as a `Str` and fault — after daimon had already emitted HTTP 201.

## Consequences

- **No public signature changes**, so this is a legal patch release: zero test
  churn, zero consumer churn across all three consumers.
- **A library that aborts.** On OOM a long-lived host dies rather than degrading.
  That is a real cost, accepted because no caller can currently recover — every
  alternative was measured to produce silent data loss or a deferred, misattributed
  crash instead.
- **The OOM branch is not unit-testable.** `fail_after_n_allocs` intercepts
  `alloc_via` only, not bare `alloc()`. What is pinned instead is (a) the
  invariant — `test_no_null_fields_from_constructors` asserts no constructor
  returns a struct with a null field, which is what would have caught the
  `accel_profiles` bug — and (b) a **CI gate** asserting every raw `alloc(` in
  `src/` has a `panic` within a few lines. Verified to fail when a guard is
  removed. Prose does not keep a rule; the gate does.
- **Do not "simplify" a guard back into `return 0`.** The comments above the
  `resource_req_new`, `preemption_action_new` and `src/json.cyr` guards exist to
  prevent exactly that, and are the durable part of this change.

### Two assumptions deliberately left unverified

- **"The store will fault" depends on page 0 being unmapped.** That holds on this
  host (`mmap_min_addr = 65536`) and was **not** verified on
  `CYRIUS_TARGET_AGNOS`. The stdlib `#ifdef`-guards every `_die` path precisely
  because target behaviour diverges, so treating trap-on-null as portable is an
  assumption samay has not paid for. It affects only how bad the *unguarded* case
  was, not whether the guards are correct.
- **The relative likelihood of samay's allocation failing at all.**
  `task_scheduler_new` calls `samay_init()` → `epoch_to_date` → an unchecked
  `alloc(48)` in `lib/chrono.cyr` **one line before** its own `alloc(16)`. In
  nearly every pressure scenario the vendored allocation fails first. samay cannot
  fix that one; see [ADR-0008](0008-threading-contract.md) for the same module's
  other unfixable-from-outside defect.
