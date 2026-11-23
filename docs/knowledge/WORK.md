# Work | Single work board

**Source of truth for task priority and next action.** Use [GitHub](https://github.com/Forged-Sent/ForgedMotionStudio/pulls) for actual PR/CI state. Update a row in the same PR that changes the related work. No derived Kanban file to regenerate.

## Next

| ID | Task | State | Done when | Next action |
| --- | --- | --- | --- | --- |
| FMS-01 | Attachment-aware deformation / volume feasibility | **PARTIAL: bounded candidates rejected** | Corrected shoulder/hip/knee evidence improves without hiding stretching, compression or attachment defects; human appearance approval remains distinct | Use [new attachment evidence](../HEATSY_ATTACHMENT_REVIEW.md) to scope explicit attachment constraints; do not repeat global contrast tuning |
| FMS-02 | Native Blender parity diagnosis | **PARTIAL (independent)** | Cause of native discrepancy is isolated with a regression, without loosening the 10 µm gate | [Native rest-matrix probe](../HEATSY_ATTACHMENT_REVIEW.md#native-blender-precision-investigation) confirms thigh reconstruction non-rigidity; isolate Blender's numerical cause |

## Waiting for review or input

| ID | Task | State | Done when | Next action |
| --- | --- | --- | --- | --- |
| FMS-03 | Anatomical and movement acceptance | **Waiting** | Named reviewer approves representative poses and complete playback, with recorded caveats | Review actual exported front/side videos; bring appearance references |
| FMS-04 | Rights-cleared squat motion | **Waiting** | Reusable input has source, performer consent and redistribution/derivative grant | Prepare controlled capture or suitable licensed skeletal motion |

## Later, gated by accepted bodyweight proof

| ID | Task | State | Done when | Next action |
| --- | --- | --- | --- | --- |
| FMS-05 | Goblet and dual-dumbbell variations | **Later** | Three distinct technique/equipment variants export and pass separate movement/grip review | Reuse one approved lower-body base; define grip/contact presets |
| FMS-06 | Portable versioned release bundle | **Later** | GLB, MP4/WebP, poster and manifest agree on timing, rights, IDs, hashes and approvals | Define small consumer contract without Flutter coupling |
| FMS-07 | Minimal nontechnical authoring UI | **Later** | Person can pick exercise/variation/muscles/camera and preview/export without code | Only after core animated quality is acceptable |

## Completed engineering proofs (not product approvals)

- **MPFB squat:** local synthetic GLB, MP4 and viewer path; [milestone review](../MILESTONE_REVIEW.md).
- **Static Heatsy:** loss-tested geometry and muscle attributes; [compatibility evidence](../HEATSY_COMPATIBILITY_REVIEW.md).
- **Animated Heatsy diagnostic:** technical loop and comparisons; **deformation PARTIAL**. [Report](../HEATSY_BODYWEIGHT_REVIEW.md).
- **Deterministic weight correction:** tearing reduced but remaining severe compression; expected exit code 2. [Repair report](../HEATSY_DEFORMATION_REPAIR.md).

One person/agent owns each active code change. If a task spans sessions before it has a PR, create one [handoff](handoffs/TEMPLATE.md).
