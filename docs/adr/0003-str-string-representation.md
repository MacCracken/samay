# ADR 0003 — `Str` (ptr+len) as samay's string representation

**Status**: accepted (2026-07-19, v0.5.0-dev) — supersedes [ADR 0001](0001-port-representation.md) point 4.

## Context

ADR-0001 point 4 chose cstr (NUL-terminated `char*`) for every samay string, so that a
single cstr-keyed `map_new` could serve all lookups. That held through v0.4.0.

M4 (JSON `Serialize`/`Deserialize` for every public type) invalidates it. The Cyrius
serialization mechanism is `#derive(Serialize)`, which generates
`Type_to_json(&val, sb)` / `Type_from_json(parsed)` for `Str` fields. samay's structs
*declared* fields as `Str` while *storing* raw cstr pointers — the two are not
interchangeable: `Str` is a ptr+len header, and the derive reads a cstr as if it were
one. Verified on cyrius 6.4.67: serializing a struct whose `Str` field holds a cstr
**core dumps**.

The alternatives were to hand-roll `*_to_json`/`*_from_json` for ~12 types in both
directions (the ai-hwaccel approach — which has 19 hand-written `*_to_json` and no
`from_json` at all), or to bridge with per-type "wire" structs. Both mean permanently
maintaining by hand what the compiler generates.

## Decision

Store every samay string as a real `Str`.

1. `uuid_v4()` returns `Str` (backing buffer stays NUL-terminated, so `str_cstr` and
   direct `syscall` writes still work).
2. Hashmaps become `map_new_str()` — Str keys hash by **content** (`hash_str_v`) and
   compare via `str_eq`, so lookup by an equal-but-distinct `Str` succeeds. Under the
   old cstr maps this already worked via `hash_str`; the change is that key identity is
   now explicitly content-based.
3. `streq` → `str_eq` (Str vs Str) or `str_eq_cstr` (Str vs literal); `strlen` →
   `str_len`; builders return `str_builder_build(sb)` directly instead of
   `str_data(...)` on a NUL-terminated build.
4. `cron_expr_parse` takes a `Str`; `@shortcut` expansion rebinds an internal byte
   pointer + length (every expansion is exactly 9 bytes).
5. **Exception** — `task_status_name` and `samay_training_method_name` keep returning
   static cstr literals. They are display helpers, not stored state; returning `Str`
   would mean allocating for a constant.
6. The `0` sentinel for `None` is unchanged and still works: a null `Str` pointer is 0.

## Consequences

- `#derive(Serialize)` becomes usable across the type surface, so M4 needs almost no
  hand-written codec.
- **Breaking for any consumer** that passed cstr into a samay constructor — call sites
  now need `str_from("...")`. No consumer references samay yet (daimon/kavach are
  declared but not integrated), so the blast radius is internal.
- Behavioral parity with `rust-old/` is preserved: 130/130 assertions pass unchanged,
  the demo binary produces identical output, and benchmarks are unaffected.
- `uuid_v4` now allocates a 16-byte `Str` header in addition to the 37-byte buffer.
- ADR-0001's stated rationale for cstr ("uniform `map_new` keys") is obsolete —
  `map_new_str` provides the same uniformity.
- Does **not** resolve M4's other blocker: f64 fields still cannot roundtrip
  bit-exactly, because the emit path (`fmt_float_buf(v, buf, 6)` in stdlib `lib/fmt.cyr`)
  is capped at 6 decimals and there are two divergent float parsers. That is tracked
  separately as an upstream fix.
