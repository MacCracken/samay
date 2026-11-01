# ai-hwaccel's profile bounds refuse profiles samay wrote itself

**Status:** open, upstream in ai-hwaccel. Found at samay 1.2.1 (ai-hwaccel 2.5.5).
**Affects:** any node whose accelerator profile is past the bounds below.

## Defect

`profile_from_json` gained range checks in ai-hwaccel 2.5.5. They are right for a corrupt
or hostile document, but two of them also refuse real hardware:

| value | bound | real hardware past it |
|---|---:|---|
| `tpu_chips` | 1,024 (`PJ_MAX_DEVICE_ID`, shared with device IDs) | TPU v4 pod: 4,096 chips. TPU v5p pod: 8,960 chips |
| device memory | 16 TiB (`PJ_MAX_DEVICE_MEMORY`) | none known |

`profile_tpu` has no such bound, and neither does `profile_to_json`, so ai-hwaccel builds and
writes a profile that it then refuses to read. `tpu_chips` is the one that matters: it
borrows the device-ID bound, and a chip count is not a device ID.

## Reproduction

The same program on both versions, for a node with one `profile_tpu(0, chips, TPU_V4)`:

| chips | 1.2.0 (ai-hwaccel 2.4.2) | 1.2.1 (ai-hwaccel 2.5.5) |
|---:|---|---|
| 8 | profile restored, fits | profile restored, fits |
| 1,024 | profile restored, fits | profile restored, fits |
| 1,025 | profile restored, fits | **profile lost, no longer fits** |
| 4,096 | profile restored, fits | **profile lost, no longer fits** |
| 8,960 | profile restored, fits | **profile lost, no longer fits** |

## Impact on samay

`node_capacity_from_jsonv` keeps the node and drops the refused profile. The node looks
healthy after a restore, but it can no longer place the TPU work it could place before.

**The loss becomes permanent at the next snapshot.** The snapshot being restored still holds
the full profile, but the node in memory does not, so the next snapshot samay writes omits
it. Keep the older snapshot if the profile matters.

## What samay does about it

- **Logs it.** Since 1.2.1 a refused profile is a `WARN` naming the node
  (`_log_profile_refused`). The refusal was silent until then, which broke samay's rule
  that it never silently drops.
- **Does not bypass the check.** Rebuilding the profile by hand would undo a hardening fix.
- **Pins it.** `test_json_node_profile_refused` asserts the loss at 4,096 chips.

## Asked of ai-hwaccel

Give `tpu_chips` its own bound, above the largest pod `tpu_hbm_per_chip` knows about, rather
than `PJ_MAX_DEVICE_ID`.

## When this closes

When ai-hwaccel raises the bound, `test_json_node_profile_refused`'s 4096 asserts fail. Then
update them, and archive this file. Amend ADR-0005's note as well.
