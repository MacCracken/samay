> **ARCHIVED 2026-11-01 — RESOLVED upstream.** ai-hwaccel 2.5.6 gives `tpu_chips` its own
> bound, `PJ_MAX_TPU_CHIPS`, of 16,384. samay took it in **1.2.2**.
>
> **Re-verified on samay 1.2.2** with the same program as below:
>
> | chips | 1.2.1 (ai-hwaccel 2.5.5) | 1.2.2 (ai-hwaccel 2.5.6) |
> |---:|---|---|
> | 1,024 | profile restored, fits | profile restored, fits |
> | 4,096 | **profile lost** | profile restored, fits |
> | 8,960 | **profile lost** | profile restored, fits |
> | 16,384 | **profile lost** | profile restored, fits |
> | 16,385 | profile lost, logged | profile lost, logged |
>
> **Still refused, and logged:** a profile past 16,384 chips or 16 TiB of device memory, and a
> TPU past 95 GiB per chip, which rules out a hand-built TPU7x pod (192 GiB per chip).
> `node_capacity_with_tpu` builds v4 profiles, so it can only reach the first. Upstream
> records all of this as not changed in 2.5.6.

# ai-hwaccel's profile bounds refuse profiles samay wrote itself

**Status:** resolved in ai-hwaccel 2.5.6. Found at samay 1.2.1 (ai-hwaccel 2.5.5).
**Affected:** any node whose accelerator profile was past the bounds below.

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
it. 1.2.2 cannot bring back a profile that is no longer in the snapshot.

## What samay did about it

- **Logs it.** Since 1.2.1 a refused profile is a `WARN` naming the node
  (`_log_profile_refused`). The refusal was silent until then, which broke samay's rule
  that it never silently drops.
- **Did not bypass the check.** Rebuilding the profile by hand would undo a hardening fix.
- **Pins it.** `test_json_node_profile_refused` checks real pods, the bound and one chip past it.
