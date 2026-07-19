# ADR 0001 — Rust → Cyrius port representation choices

**Status**: accepted (2026-07-18, v0.2.0)

## Context

Samay was a Rust library using owned `String`s, `chrono::DateTime<Utc>`, serde
derives, payload-carrying enums, and ai-hwaccel's `AcceleratorRequirement`.
Cyrius is i64-centric: C-style integer enums, free functions (no methods),
alloc'd pointer structs, no serde-derive over complex/nested types. The port
must match Rust behavior and its test suite (`rust-old/` is the oracle).

## Decision

1. **Structs** — `#derive(accessors)` heap structs (all fields 8-byte: i64 / f64
   bit-pattern / cstr pointer), `type_new(...)` constructors returning pointers;
   nested structs held as pointer fields. No inline `#` comments on field lines —
   the accessors derive mis-parses a trailing comment as a field name.
2. **Payload enums → tag + sibling field(s)**: `TaskStatus::Failed(String)` →
   `TASK_FAILED` + a `fail_reason` field; `AcceleratorRequirement::Tpu{min_chips}` →
   `accel_req` (ai-hwaccel `REQ_*`) + `accel_min_chips`.
3. **Time** — `DateTime<Utc>` → i64 epoch-nanoseconds (`lib/chrono` `dt_now` /
   `dt_add` / `dt_diff` / `dur_*`); `Option<DateTime>` → `0` sentinel. This
   required extending `lib/chrono` — proposal filed and landed in cyrius 6.4.67.
4. **Strings** — cstr (null-terminated) throughout, so a single `map_new`
   (cstr-keyed hashmap) serves all lookups; `uuid_v4` returns a cstr.
5. **Errors / logging** — `anyhow::Result` → `lib/result` (`Ok`/`Err`/`?`);
   `tracing` → `lib/sakshi`.
6. **AcceleratorRequirement** — consumed from ai-hwaccel's `REQ_*` enum. `can_fit`
   replicates Rust's self-contained match on node fields; using ai-hwaccel's
   `requirement_satisfied()` / profiles for placement is a v1.0 item.
7. **UUID** — RFC-4122 v4 synthesized from `random_bytes` (getrandom).

## Consequences

- JSON/serde output shape differs from Rust (int-tagged enums); runtime behavior
  is equivalent. Full `Deserialize` + roundtrip tests are deferred.
- `0`/empty-string None sentinels mean an empty `node_preference` and epoch `0`
  are indistinguishable from `None` — acceptable for this domain.
- Naming collision with ai-hwaccel forced `TrainingMethod` → `SamayTrainMethod`
  and `training_method_name` → `samay_training_method_name`. A full symbol-collision
  scan against the vendored deps is part of the pre-release gate.
