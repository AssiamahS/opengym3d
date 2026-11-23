# Precor Resolute RSL0605: Leg extension

ID: `precor-rsl0605-leg-extension` · **PARTIAL / human unreviewed** · 2026-11-23

[Library](../../INDEX.md) · [Family](INDEX.md)

Research draft; inferential motion fields require manual and human review.

Equipment: [precor-rsl0605](../../equipment/precor-rsl0605.md)

Grip: [machine-handle-unspecified](../../grips/machine-handle-unspecified.md). Configuration IDs: config.precor-rsl0605-leg-extension.precor-rsl0605.

## Movement interpretation

| Field | Description |
| --- | --- |
| joints | ["knee"] |
| motions | Knee extension; return flexion (inferred from exercise name). |
| start | Flexed knees; exact angle unknown. |
| end | Extended knees; limit unknown. |
| equipment_motion | Roller linkage; axis and radius unmeasured. |
| feet_contact | Not floor-supported during repetition (inferred). |
| hands_contact | Unknown. |
| torso | Back supported. |
| basis | Qualitative engineering inference from source instructions, not measured biomechanics. |

## Phase map

| Phase | Description | Basis |
| --- | --- | --- |
| setup | Flexed knees; exact angle unknown. | source-guided interpretation |
| action | Knee extension; return flexion (inferred from exercise name). | Qualitative engineering inference from source instructions, not measured biomechanics. |
| endpoint | Extended knees; limit unknown. | Batch field: may mean extreme position OR completed repetition; inspect source before using. |
| return | Unknown | Separate return trajectory and timing not verified. |

## Visual evidence

- [Precor source](https://www.precor.com/en-US/products/RSL0605) · Matching media unavailable — Manufacturer text verified; no motion frames inspected. Verification: text-verified; visual-not-verified. View: unknown; phase: unknown.

Local copies, where available, are internal references in the ignored cache. No redistribution grant established.

## Missing evidence and conflicts

- Human technique approval
- Front and side start/mid/end motion
- Measured pivots, limits and contact coordinates
- Model-specific exercise placard/manual verification

Incomplete; absence of recorded conflicts is not consensus.

## Model-specific machine contacts

| Field | Evidence |
| --- | --- |
| model | Precor Resolute RSL0605 |
| adjustments | ["start position", "ankle roller", "gas-assisted back pad"] |
| supports | ["seat", "back pad", "ankle pad"] |
| contacts | ["lower leg to roller; precise region unknown"] |
| moving_components | ["roller linkage"] |
| constraints | ["Fit roller and back support before authoring motion."] |
