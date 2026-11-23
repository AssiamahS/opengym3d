# Precor Resolute RSL0602: Seated leg press

ID: `precor-rsl0602-leg-press` · **PARTIAL / human unreviewed** · 2026-11-23

[Library](../../INDEX.md) · [Family](INDEX.md)

Research draft; inferential motion fields require manual and human review.

Equipment: [precor-rsl0602](../../equipment/precor-rsl0602.md)

Grip: [machine-handle-unspecified](../../grips/machine-handle-unspecified.md). Configuration IDs: config.precor-rsl0602-leg-press.precor-rsl0602.

## Movement interpretation

| Field | Description |
| --- | --- |
| joints | ["hip", "knee"] |
| motions | Hip/knee extension; return flexion (inferred). |
| start | Flexed legs; angles unknown. |
| end | Legs extended; limit unknown. |
| equipment_motion | Rail travel reported; moving carriage identity unverified. |
| feet_contact | Foot platform; stance unknown. |
| hands_contact | Unknown. |
| torso | Back pad angled 35 degrees; angle datum unspecified. |
| basis | Qualitative engineering inference from source instructions, not measured biomechanics. |

## Phase map

| Phase | Description | Basis |
| --- | --- | --- |
| setup | Flexed legs; angles unknown. | source-guided interpretation |
| action | Hip/knee extension; return flexion (inferred). | Qualitative engineering inference from source instructions, not measured biomechanics. |
| endpoint | Legs extended; limit unknown. | Batch field: may mean extreme position OR completed repetition; inspect source before using. |
| return | Unknown | Separate return trajectory and timing not verified. |

## Visual evidence

- [Precor source](https://www.precor.com/en-US/products/RSL0602) · Matching media unavailable — Manufacturer text verified; no motion frames inspected. Verification: text-verified; visual-not-verified. View: unknown; phase: unknown.

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
| model | Precor Resolute RSL0602 |
| adjustments | ["seated fit", "load"] |
| supports | ["seat", "back pad", "foot platform"] |
| contacts | ["back to pad", "feet to platform"] |
| moving_components | ["rail-guided assembly; identify before rigging"] |
| constraints | ["Do not assume platform moves instead of seat."] |
