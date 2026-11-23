# Using the reference library in Forged Motion Studio

1. Select the exact ID in [the variation catalog](data/exercise-variations.json). Resolve aliases deliberately; a workout is a later composition of variation IDs and prescriptions, never an exercise variation itself.
2. Follow `equipment_configuration_ids` to [configurations](data/equipment-configurations.json), then equipment IDs to [equipment](data/equipment.json). Inspect model-specific adjustments and contact surfaces. Unknown measurements are not defaults.
3. Read `grip_id` in [grips](data/grip-archetypes.json). Head-support and two-hand shaft holds are separate. Thumb opposition and web deformation require close-up evidence and rig-specific investigation.
4. Follow `reference_ids` to [references](data/references.json), open the cited source and media, and check the stated verification limits. Read the exercise page's phase table. Missing front/side/grip views remain missing.
5. Draft the body/equipment relationship: feet, seat, pads, hands, cable endpoints and moving machine parts. Label every inferred constraint. Never substitute a different manufacturer's kinematics without new evidence.
6. Reuse the existing normalized-motion, rig-adapter, Blender export and viewer paths described in [SYSTEM](../docs/architecture/SYSTEM.md). Research IDs do not automatically map to the existing `equipment-catalog/1` asset IDs or create executable pose recipes. No automatic importer is provided.
7. Render matching cameras at setup, intermediate, extreme and return phases. Compare silhouettes, contact, occlusion and equipment motion. Record the exact motion/model/tool revisions with the comparison; do not solve depth ambiguity by inventing bone coordinates.
8. Keep research sufficiency, technical export validation, visible appearance and qualified human movement/anatomy approval separate. Use the unchanged contact/parity/deformation gates. Heatsy repair exit 2 remains PARTIAL.

Current implementation context: [equipment review](../docs/EQUIPMENT_LIBRARY_REVIEW.md) at implementation commit `6c9a4a568dbf1ac18de14cdc8944c3312a3ac142`; research began from HEAD `8ea29c8dab459c306cbc5d20110ffad7584e5417`. The synthetic MPFB shaft-hold fixture is not validated by a superficially similar head-support photograph. This work changes no rig, animation, model, viewer or acceptance threshold.

Use JSON for relationships, CSV for filtering and Markdown for human review. `null` means not established. Preserve IDs across website moves; add aliases or supersession records rather than silently changing technique identity.

For a workout slot, follow `equipment_alternative_group_ids` to [equipment alternatives](EQUIPMENT-ALTERNATIVES.md). For example, the goblet-squat group offers a dumbbell head-support variation and a kettlebell horn variation. Select the exact variation for the available implement, then retrieve its own grip and configuration. Preserve the user's equipment preference; do not silently substitute loads, grips or animation tracks. A workout remains a future composition referencing these choices, not a new exercise family.

## Breadth-first handoff

Start with INDEX.md and the variation JSON/CSV. Search names and `aliases`, then follow the family, equipment alternatives and reference IDs. Current scope prioritizes approximately 300 distinct exercise families with usually 1–3 starter variations, rather than exhaustive grip permutations. Linked visuals with `visual_inspected: false` are candidates for the next model to open; they are not already confirmed poses. Before animating the chosen variation, inspect its exact equipment/support match and resolve only the detail needed for that implementation. Preserve unknown contacts and source conflicts instead of inventing them. No record is human-approved.

Local-reference update: use [local media and previews](LOCAL-MEDIA.md) and [cache policy](local-media-policy.md). Original files stay in ignored `work/reference-media`; download status is independent of visual inspection.
