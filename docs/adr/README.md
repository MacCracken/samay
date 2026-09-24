# Architecture Decision Records

Decisions about samay — what we chose, the context, and the consequences we accept. Use these when a future reader would reasonably ask *"why did we do it this way?"*

## Conventions

- **Filename**: `NNNN-kebab-case-title.md`, zero-padded to four digits. Never renumber.
- **One decision per ADR.** If a decision supersedes a prior one, add a new ADR and set the old one's status to `Superseded by NNNN`.
- **Status lifecycle**: `Proposed` → `Accepted` → (optionally) `Superseded` or `Deprecated`.
- Use [`template.md`](template.md) as the starting point.

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
