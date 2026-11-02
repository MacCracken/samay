# ADR 0005 — Input validation on snapshot restore

**Status**: accepted (2026-07-21, v0.7.0 / M5 security audit). **Amended** 2026-11-01 (v1.4.3):
the "wrong type" half of this contract had only reached nested requirements. Every record field and
container is now checked, a collection of the wrong type refuses the snapshot, two records under one
key refuse it, a node past the profile limit refuses its scheduler, and a dropped record is counted
and logged. Restore also checks each node against its tasks
([ADR-0007](0007-reservation-lifecycle.md)).
**Amended** 2026-11-02 (v1.4.5): point 3 bounded neither bytes nor memory, and
[ADR-0014](0014-what-a-document-may-cost.md) replaces its claim. Constructors now settle the same domain
restore reads, so a value comes back as it was built, and the derived leaf types gain readers that
refuse. See *Constructors agree with restore* below.

## Context

M4 added JSON `Serialize`/`Deserialize` for every public type, including
`TaskScheduler_to_json_str`/`_from_json_str` as a full scheduler+cron snapshot/restore.
The M5 security audit ([`docs/audit/2026-07-21-audit.md`](../audit/2026-07-21-audit.md))
found that the restore path trusts its input: the `*_from_jsonv` deserializers read each
field with a defaulting helper (`_jv_str` returns `0` for a missing/non-string field) and
store it verbatim into the reconstructed struct.

Because Cyrius has no bounds checks and `0` is the null/None `Str` sentinel, a snapshot
that merely **omits a required field** produces a half-initialized struct that faults
later — a null-`Str` deref (`str_len(0)` reads address 8) on re-serialization (F1), a
null map-key `str_eq(0,0)` crash during restore (F2), or a null nested
`resource_requirements` deref on the next schedule pass (F3). All three are deterministic
SIGSEGV denial-of-service, reproduced with running PoCs. Out-of-range scalars were also
accepted unchanged — an unclamped `priority` silently i64-overflows (F6), negative memory
is stored (F7) — diverging from the Rust oracle, whose serde deserialize **rejects**
missing required fields and out-of-domain typed values (`u8` priority, `u64` memory) for
free.

If snapshots can arrive from disk or the network, they are untrusted input crossing a
weak boundary.

## Decision

Validate at the restore boundary, matching Rust serde's fail-closed semantics:

1. **Reject on missing/invalid required fields.** Each `*_from_jsonv` reads its required
   `Str` fields and nested structs into locals and returns `0` (parse failure) if any is
   absent or the wrong type — for `ScheduledTask.{task_id,name,description,agent_id}` +
   `resource_requirements`, `NodeCapacity.node_id`, `CronEntry.{name,expr,task_template}`,
   `CronTaskTemplate.{name,description,agent_id}` + `resource_requirements`, and
   `TrainingJobTemplate.{model_id,dataset}`. Container deserializers already skip null
   sub-records, so a malformed record is **dropped, not fatal**; a structurally-sound
   snapshot restores unchanged.
2. **Clamp numeric-domain fields on restore**, as the constructors do: `priority` → 1–10,
   `status` → valid enum range, and the u64-domain node fields (memory/disk/running_tasks,
   via `_jv_uint`) → ≥0.
3. **Bound restored collection sizes** — `SAMAY_JSON_MAX_ITEMS` (100000) caps the `tasks`,
   `nodes`, `entries`, and `accel_profiles` arrays; a larger array rejects the snapshot.
   This closes the unbounded-allocation / OOM vector of the hash-collision (F4) and
   quadratic-sort (F5) DoS findings.

## Consequences

- **Every confirmed crash (F1–F3) is closed**, and the input-validation divergences from
  Rust (F6, F7) are restored to parity. Re-verified by re-running each finding's PoC to a
  clean reject/exit-0, plus permanent regression guards (`test_sec_*` in `tests/samay.tcyr`).
- **Contract change (intended):** a record type with missing required fields now
  deserializes to `0` (rejected) instead of a poisoned struct. The M4 malformed-input test
  that asserted `{}` → a defaulted struct encoded the vulnerable behavior and was updated
  to assert `{}` → `0` for record types. Container types (`{}` → empty scheduler) are
  unchanged — they have no required scalar fields.
- **Not fully closed here (tracked follow-ups, non-ship-blocking):** the within-cap cost of
  the O(n²) insertion sorts (F5 → stable O(n log n) sort + terminal-task pruning) and the
  unseeded-FNV hash-collision blowup (F4 → upstream stdlib hash seeding, a `lib/` change
  samay may not make), plus the cron aggregate-work budget (F8/F9). The size cap bounds all
  of these to a finite worst case; eliminating the residual is deferred rather than risk a
  sort rewrite destabilising the M5 determinism guarantee ([ADR-0004](0004-deterministic-tie-breaks.md)).
  F5 closed in v1.4.0 ([ADR-0011](0011-bounded-task-history.md)) and F8/F9 in v1.4.1
  ([ADR-0012](0012-cron-burst-budget.md)). **Amended 2026-11-02 (v1.4.5):** "the size cap bounds all
  of these to a finite worst case" was not true of memory. The cap is checked after the parse, and
  bayan's tree takes up to 88 times the text, so 10 MB took 868 MiB first. ADR-0014 limits the bytes
  and the parse itself.
- Fail-closed on a bad record means a corrupt snapshot loses that record silently. For a
  scheduler restoring its own well-formed snapshot this never triggers; it only drops
  attacker/corruption-injected records, which is the desired posture.
  **Amended 2026-11-01 (v1.2.1, v1.2.2):** this does not hold for every accelerator profile.
  ai-hwaccel refuses out-of-range values since 2.5.5, and that can reach a profile samay
  wrote itself ([issue](../development/issues/archive/2026-11-01-ai-hwaccel-profile-bounds.md)).
  2.5.6 raised the bound on TPU chips to 16,384, so real pods restore. Past the bounds the
  node stays without that profile. That is a valid record, not corruption, so samay logs it.

## Constructors agree with restore (v1.4.5)

Clamping on restore only helps if the constructors clamp to the same domain. Where they did not, a
value went out as one thing and came back as another, and nothing said so:

| Value | Constructor through 1.4.4 | Restore | Now, both |
|---|---|---|---|
| Node cores past 1e18 | kept | 0 | stop at 1e18, as a requirement's do |
| Node cores NaN | kept, written as `null` | node dropped | 0 |
| Node cores, memory or disk negative | kept | 0 | 0 |
| Node id empty | registered | record dropped | `register_node` answers 1, logs, registers nothing |
| Training method samay does not know | kept: "unknown", GPU or TPU | LoRA: GPU only | kept |
| Missed-schedule policy not `CRON_SKIP` | kept | `CRON_CATCHUP` | `CRON_CATCHUP`, as it already acted |
| `network` not 0 or 1 | kept | 1 | 1 |

Restore keeps an unknown training method rather than the constructor refusing one, for the reason it
keeps an unknown `accel_req`: a newer samay may know it, and what this one does with it, ask for a GPU
or a TPU, is the safe reading.

The five types with `#derive(Serialize)` decode through code the compiler emits, which cannot refuse
anything: `{}` gives a `SchedulingDecision` of null Strs, which crashes the first writer it meets.
samay's own readers never used it. `resource_req_from_json_str`, `cron_expr_from_json_str`,
`scheduling_decision_from_json_str`, `preemption_action_from_json_str` and
`scheduler_stats_from_json_str` read the same text, require every field the derive writes, and answer
0 for one missing or of the wrong type.
