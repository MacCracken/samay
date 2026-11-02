# Architecture Decision Records

Decisions about samay — what we chose, the context, and the consequences we accept. Use these when a future reader would reasonably ask *"why did we do it this way?"*

## Conventions

- **Filename**: `NNNN-kebab-case-title.md`, zero-padded to four digits. Never renumber.
- **One decision per ADR.** If a decision supersedes a prior one, add a new ADR and set the old one's status to `Superseded by NNNN`.
- **Status lifecycle**: `Proposed` → `Accepted` → (optionally) `Superseded` or `Deprecated`.
- Use [`template.md`](template.md) as the starting point.
- **Oracle citations** such as `rust-old/src/lib.rs:483` refer to tag `1.1.5`, the last
  revision that has the Rust oracle. `git show 1.1.5:rust-old/src/lib.rs` reads it.

## ADR vs. architecture note vs. guide

| Kind | Lives in | Answers |
|---|---|---|
| ADR | `docs/adr/` | *Why did we choose X over Y?* |
| Architecture note | `docs/architecture/` | *What non-obvious constraint is true about the code?* |
| Guide | `docs/guides/` | *How do I do X?* |

## Index

| ADR | Title | Status |
|---|---|---|
| [0001](0001-port-representation.md) | Rust → Cyrius port representation choices | Accepted (v0.2.0) — points 4 and 6 superseded |
| [0002](0002-ai-hwaccel-profile-placement.md) | Placement via ai-hwaccel device profiles | Accepted (v0.4.0) |
| [0003](0003-str-string-representation.md) | `Str` (ptr+len) as samay's string representation | Accepted (v0.5.0-dev) — supersedes 0001 point 4 |
| [0004](0004-deterministic-tie-breaks.md) | Deterministic scheduling via explicit tie-breaks | Accepted (v0.6.0-dev) — intentional divergence from Rust |
| [0005](0005-restore-input-validation.md) | Input validation on snapshot restore | Accepted (v0.7.0) — fail-closed deserialization (security audit) |
| [0006](0006-cron-expression-model.md) | Cron expression model and missed-schedule semantics | Accepted (v1.0.3) — records the v0.3.0 divergence from the oracle's interval model; Vixie DOM/DOW correction. Amended v1.1.5: oracle description corrected, relative intervals recorded as unreplaced |
| [0007](0007-reservation-lifecycle.md) | Node capacity returned on every exit from the running set | Accepted (v1.0.3) — intentional divergence from Rust (the oracle leaks capacity too) |
| [0008](0008-threading-contract.md) | samay is single-threaded by contract | Accepted (v1.0.4) — measured; no internal lock, deliberately |
| [0009](0009-oom-policy.md) | Check every allocation, abort on failure | Accepted (v1.1.1) — never propagate an OOM as `0` or `Err`; CI-gated |
| [0010](0010-request-and-assignment.md) | A task's request and its assignment are two fields | Accepted (v1.3.0) — `node_preference` stays as a view, in memory and on the wire |
| [0011](0011-bounded-task-history.md) | The stdlib sort, explicit task removal, and refusing an oversized snapshot | Accepted (v1.4.0) — closes audit F5; capacity is released in `task_id` order |
| [0012](0012-cron-burst-budget.md) | An exact due count, and a burst budget that holds entries instead of dropping them | Accepted (v1.4.1) — closes audit F8 and F9 |
| [0013](0013-accelerators-are-reserved.md) | Accelerators are reserved, and preemption has to help | Accepted (v1.4.3) — what 0002's availability has to mean; points 1 and 2 extended by 0016 |
| [0014](0014-what-a-document-may-cost.md) | A document has a byte limit and a parse budget, and writers keep to both | Accepted (v1.4.5) — what 0005's item limit could not bound |
| [0015](0015-a-pass-only-fills-nodes.md) | A pass only fills nodes, so it skips what it already knows fits nowhere | Accepted (v1.4.6) — decisions unchanged, proven against 1.4.5 binaries |
| [0016](0016-several-devices-or-a-share-of-one.md) | A request takes several whole devices, or a share of one | Accepted (v1.5.0) — extends 0013's unit; keys on the wire only when used |
| [0017](0017-cpu-work-goes-to-accelerator-nodes-last.md) | CPU work goes to accelerator nodes last | Accepted (v1.5.0) — changes decisions on mixed fleets |
