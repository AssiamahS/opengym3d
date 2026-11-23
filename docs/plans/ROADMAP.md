# Roadmap | Quality before editor

This is the **sequence of capabilities**, not a promise of dates. Only [WORK](../knowledge/WORK.md) tracks next actions; live PR state is on GitHub.

| Stage | Status | Observable result | Go/no-go |
| --- | --- | --- | --- |
| 0. Reproducible MPFB bodyweight proof | **Engineering proof completed** | Synthetic GLB/MP4, viewer, QA and deterministic rebuild | Retain as regression baseline |
| 1. Heatsy static anatomy compatibility | **Engineering proof completed** | Preserved geometry, 56 joints, anatomy attributes and static selection | Keep model provenance |
| 2. Animated Heatsy squat and deformation | **PARTIAL, active** | Loop plays, highlights attach, but compression/shoulder/hip/knee surface problems remain | Resolve critical defects; human review remains pending |
| 3. Correctness and approved source motion | **Waiting** | Rights-cleared input and explicitly reviewed technique/anatomical appearance | Separate review records; do not infer from QA |
| 4. Three squat variations | **Deferred** | Bodyweight, goblet and dual-dumbbell have distinct grips and props, each reviewed | Only after bodyweight animation is acceptable |
| 5. Portable asset contract and Quick Peek/Detail | **Deferred** | Versioned GLB/MP4/WebP/poster + metadata and lightweight consumer | Match actual exported movement, rights and approvals |
| 6. Small nontechnical Studio authoring flow | **Deferred** | Search, configure, preview and locally export without code | Keep user interface narrowly tied to real generator |

## Product rule
A **variation** changes movement technique or equipment. A **workout** composes variation IDs with sets/reps/rest and is a different later concern.

## Work principle
Invest in the smallest reproducible test of visual quality. Defer broad UI, cloud, accounts, mass exercise generation, Flutter integration and speculative cross-device optimization until a single accepted anatomical animation exists.

Source reports: [bodyweight](../HEATSY_BODYWEIGHT_REVIEW.md) · [repair](../HEATSY_DEFORMATION_REPAIR.md).
