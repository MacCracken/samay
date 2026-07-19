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
