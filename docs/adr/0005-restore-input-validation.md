# ADR 0005 — Input validation on snapshot restore

**Status**: accepted (2026-07-21, v0.7.0 / M5 security audit).

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
- Fail-closed on a bad record means a corrupt snapshot loses that record silently. For a
  scheduler restoring its own well-formed snapshot this never triggers; it only drops
  attacker/corruption-injected records, which is the desired posture.
