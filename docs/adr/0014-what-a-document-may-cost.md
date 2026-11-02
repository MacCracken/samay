# 0014 — A document has a byte limit and a parse budget, and writers keep to both

**Status**: Accepted. **Amended** in v1.5.1: the budget counts bytes as `alloc()` takes them, and a
restore's tree is freed once it has been read. See *Amendment (v1.5.1)* below.
**Date**: 2026-11-02

## Context

[ADR-0005](0005-restore-input-validation.md) bounded restore with `SAMAY_JSON_MAX_ITEMS`, and said
that closed the out-of-memory vector. It did not. The limit counts records in four arrays, and it is
checked after bayan has parsed the whole document. Nothing limited the bytes, nothing limited a key
samay does not read, and nothing limited what the parse itself costs.

That cost depends on the shape of the text. Measured on cyrius 6.7.18 with bayan 1.11.1, in heap bytes
of parse tree per byte of input:

| Document | Tree per byte |
|---|---|
| What samay writes: tasks, nodes, GPU nodes, cron entries | 4.9 to 5.9 |
| The worst samay writes: one-letter names, zeroed numbers | 7.2 |
| `[0,0,…]` | 25 |
| `[[],[],…]` or `[{},{},…]` | 65 |
| `[[[…]]]` nested 120 deep, repeated | 88 |

So 10 MB of nested arrays took 868 MiB before anything was refused. 128 MiB of it would take 11 GB.

The writers had the opposite problem. `bayan_json_v_build` exits the process when its buffer needs more
than `ALLOC_MAX` (2 GiB), so a snapshot within the item limit could kill its writer instead of being
refused.

## Decision

**A document is refused before parsing past a byte limit, the parse is refused past a budget of ten
times its size, and every writer refuses what a reader would refuse.**

1. **`SAMAY_JSON_MAX_BYTES` = 128 MiB**, checked before the parse. Both item limits at once fit: 100,000
   tasks write 52 MB and 100,000 nodes 21 MB, which leaves room for about 470,000 GPU profiles at 117
   bytes each. 100,000 cron entries write 44 MB.
2. **`SAMAY_JSON_MAX_EXPANSION` = 10.** The tree is built through an allocator that forwards to
   `alloc()` and counts, and answers 0 once the tree passes ten times the input plus 4 KiB. bayan then
   fails the parse. A parse that ran out of budget is refused whatever bayan returned, so a partial
   tree cannot pass for the document. Ten leaves 40% above the worst samay writes, so a change in
   bayan's tree shows in the tests before it refuses a real snapshot. The 4 KiB is for small
   documents: `{}` alone takes 176 bytes.
3. **Writers refuse what no reader would take.** Every `*_to_json_str` builds through the same kind
   of allocator, with six times the byte limit: the builder doubles its buffer, so its buffers sum to
   under four times the text, and the text is copied once more. Text past the byte limit answers 0
   with a log line, as text past the item limit already did. A request past `ALLOC_MAX` is a refusal
   too, so no writer exits the process any more.
4. **Out of memory is still out of memory.** The allocator refuses only past its budget or past
   `ALLOC_MAX`. Any other 0 from `alloc()` is the host out of memory, and it panics as
   [ADR-0009](0009-oom-policy.md) requires, instead of passing for a refused document.
5. **Both are `var`s,** like `SAMAY_JSON_MAX_ITEMS`, so a consumer can lower them for its own memory. A
   restore can cost the input, plus the tree at up to ten times it, plus the objects restored, which
   measured 1.1 times the input for tasks and 3.5 for nodes.

## Consequences

- **Positive** — Parsing costs at most ten times the document, whatever its shape. 10 MB of nested
  arrays peaks at 126 MiB and is refused in 0.1 s, where it took 868 MiB and 0.9 s. A key samay does
  not read counts against the same budget as everything else.
- **Positive** — A writer refuses instead of exiting, and anything samay writes reads back.
- **Negative** — Restore takes 1.4 to 2.9% longer and a write 2% longer, from one indirect call per
  allocation. Measured interleaved on one pinned CPU, 1.4.4 against 1.4.5, five runs each:

  | Document | 1.4.4 | 1.4.5 |
  |---|---|---|
  | Restore, 100,000 tasks (52 MB) | 2.20 s | 2.25 s |
  | Restore, 100,000 nodes (21 MB) | 1.02 s | 1.03 s |
  | Restore, 100,000 cron entries (44 MB) | 1.92 s | 1.97 s |
  | Write, 100,000 tasks | 1.91 s | 1.95 s |

  Peak memory is unchanged for all four.
- **Negative** — A snapshot past 128 MiB was written and read through 1.4.4, up to bayan's 2 GiB. Now
  it is refused on both sides unless the consumer raises the limit. Nothing measured comes near it.
- **Negative** — The budget is a measurement of bayan's tree, not a property of JSON. If bayan's nodes
  grow, honest snapshots move towards the limit. `test_json_expansion_limit` restores cron entries
  with one-letter names, 6.5 times their text, with the limit at 8, so a change fails there first.
  (Corrected in v1.5.1: this said the worst shape, which is 7.2.)
- **Neutral** — Peak memory for a document that is read is what it was. The tree still lives on the
  bump heap after a restore and is never freed, as before. *Superseded in v1.5.1: see below.*

## Alternatives considered

- **A byte limit alone.** At 128 MiB the worst case is 11 GB, and a limit low enough to bound memory
  would refuse snapshots within the item limits.
- **Counting values before the parse.** It bounds memory only through an estimate of what each value
  costs, and it needs a second JSON scanner that agrees with bayan's on strings and escapes.
- **Parsing into an arena.** Arenas come from the global bump heap, and one of fixed capacity reserves
  all of it up front. A single arena reused across restores would also break
  [ADR-0008](0008-threading-contract.md), which lets separate schedulers live on separate threads.
- **bayan's streaming parser.** It would never build the tree at all, but every reader in `json.cyr` is
  written against the tree, and it would be a rewrite of all of them.

## Amendment (v1.5.1)

**The budget counts bytes as `alloc()` takes them.** `alloc()` rounds every request up to 8, and the
ratios in the table above were measured with `alloc_used()`, so they are rounded too. Through 1.5.0
the budget counted the requests unrounded, which let a parse take a little more than ten times its
document. It now counts what it measures.

**A restore's tree is freed.** It is built in an anonymous mapping of its own, as large as the
budget, which is only an address range until the tree touches it, and the mapping goes back to the
system when the reader returns. That is safe because no reader keeps a pointer into the tree:
constructors own every `Str` they keep (1.1.3), the task and node readers copy theirs, and
ai-hwaccel's profile reader copies its own (2.5.5). The suite checks it: every restore test runs
with its tree unmapped, and a pointer into it would fault. Where no mapping can be had (agnos and cx
have no `mmap`), the tree goes on the heap as before. A writer's tree still stays on the heap.

| Restore of 100,000 | Heap left behind, 1.5.0 | 1.5.1 |
|---|---|---|
| tasks (46 MB) | 282 MiB | 44 MiB |
| nodes (20 MB) | 172 MiB | 69 MiB |
| cron entries (40 MB) | 286 MiB | 43 MiB |

Peak memory rises by about 1%, since the mapping is counted while the tree is read.
