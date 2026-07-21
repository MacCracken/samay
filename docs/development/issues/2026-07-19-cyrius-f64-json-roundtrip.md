# f64 JSON roundtrip is lossy — M4 blocker (upstream: cyrius)

**Status:** OPEN — filed upstream, samay M4 blocked on the fix.
**Upstream issues:**
- `cyrius/docs/development/issues/2026-07-19-f64-json-roundtrip-6-decimal-cap.md` — the
  formatter/parser defect (library side).
- `cyrius/docs/development/issues/2026-07-19-derive-serialize-f64-second-implementation.md`
  — `#derive(Serialize)` inlines its own copy of the formatter and uses a *different*
  parser. **This is the one that gates samay**, because samay's M4 plan is built on
  `#derive(Serialize)`, and a library-only fix would not reach it.

**Affects:** cycc 6.4.67, bayan 1.2.0.

## Why samay cares

M4 requires bit-exact JSON `Serialize`/`Deserialize` roundtrip for every public type.
Every f64 serialization path in Cyrius funnels through `fmt_float_buf(v, buf, 6)` —
6 decimal places, no exponent form, no non-finite handling. Measured on 6.4.67:

- `1/3` → `0.333333` → reads back losing ~9 mantissa bits
- any `|x| < 5e-7` → `0.000000` → reads back as exactly `0`
- `+Inf` / `NaN` / `|x| >= 2^63` → `-.00000-`, which is **not valid JSON**
- bayan's `_jp_atof` and math's `f64_parse` disagree by 1 ULP on identical text
- **DoS**: parse work is linear in the *value* of a number's exponent, so the 17-byte
  document `{"x":1e100000000}` costs **237 ms** and returns `+Inf`. samay does not parse
  untrusted JSON today, but any consumer that does (kavach, daimon) would inherit this.

This is not an edge case for samay. [`scheduler.cyr:181`](../../../src/scheduler.cyr)
computes `score = 1 - node_capacity_utilization(node)`, and utilization averages resource
ratios — so `1/3` and `2/3` are the *common* values. A scheduler snapshot could not be
persisted and restored without perturbing placement decisions, which also undermines the
M5 determinism guarantee.

## samay-side status

- **Not worked around.** Baking a lossy encoding (hex bit-patterns, scaled integers) into
  the on-disk format would be hard to change later, so M4 waits for the upstream fix
  rather than shipping a format we'd have to break.
- The other M4 prerequisite — the cstr → `Str` migration
  ([ADR-0003](../../adr/0003-str-string-representation.md)) — **has landed**, 130/130
  assertions green. `#derive(Serialize)` is confirmed as the mechanism; only f64 fields
  are blocked.

## Unblocking condition

Upstream item (1) — stop emitting invalid JSON for non-finite / `>= 2^63` — plus item (2)
— enough emitted precision to roundtrip (17 significant digits is sufficient for a
double), **landed on the `#derive(Serialize)` path**, not only in bayan.

Note the rebuild requirement: the derive inlines its formatter into generated code, so a
new toolchain is not enough on its own — samay must re-run `cyrius lib sync`, rebuild, and
regenerate `dist/samay.cyr`. No samay-side *design* change is needed either way.

A library-only fix would be a **regression** for samay's purposes: bayan-built and
derive-built JSON would then disagree on float format within the same document set.

## Related

- `cyrius/docs/development/issues/2026-07-19-fmt-hex-high-bit-prints-nothing.md` — separate
  bug found in the same investigation (`fmt_hex*` prints nothing for high-bit-set values).
  No samay impact; debug output only.
