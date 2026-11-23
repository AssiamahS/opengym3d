# ADR-0002 | Evidence required before adopting anatomy derivatives

- **Status:** Proposed, **not** yet approved as a general architecture rule
- **Recorded:** 2026-11-22
- **Decision needed:** What portable deformation/corrective mechanism, if any, should become a reusable Studio model variant?

## Context
The tracked skin-weight correction reduces tearing but increases the number of heavily compressed ordinary edges. The diagnostic dual-quaternion / preserve-volume experiment reduces compression in Blender but is not represented by the exported standard GLB. Shoulder attachments, hip folds, and knee surfaces still fail visual inspection. [Measured investigation](../HEATSY_DEFORMATION_REPAIR.md).

## Proposed policy
Before accepting a corrected anatomical model as a reusable character variant:
1. Preserve the pinned source asset and produce a separate, hash-addressed derivative with full CC BY-SA attribution.
2. Record **every** intentional change to weights, bones, binds, geometry and shader behavior. Preserve exact muscle IDs and their left/right meaning.
3. Compare whole-body and region-level stretching **and compression**, absolute edge changes, fold/collapse and self-intersections across neutral, standing, mid-descent and bottom.
4. Confirm that the actual exported GLB (not only Blender's modifier preview) deforms the same way in the browser.
5. Run non-regression checks for feet, loop, muscle selection, timing, normal behavior and the MPFB baseline.
6. Require explicit anatomical/movement review before labeling content instructional or publicly reusable.

## Alternatives to evaluate
- Attachment-aware bone/weight corrections with a very small surface/volume corrective set.
- Portable corrective blend shapes driven by joint poses, if they survive the export/browser path.
- A different compatible source anatomy/rig only if narrower corrections fail demonstrably.

Do **not** assume unrestricted smoothing, Blender-only dual-quaternion skinning, mesh deletion or silently relaxed parity is acceptable.

## Open decision
Select a candidate **only after** the bounded [next slice](../plans/NEXT-SLICE.md) establishes improvement without hidden regressions. Until then the corrected GLB remains experimental.
