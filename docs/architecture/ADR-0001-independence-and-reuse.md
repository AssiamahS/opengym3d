# ADR-0001 | Standalone Studio, reuse before rebuild

- **Status:** Accepted, documenting the existing product direction and codebase
- **Recorded:** 2026-11-22
- **Scope:** Repo, runtime and generation boundaries

## Context
Forged Motion Studio is an independent tool for authoring anatomical exercise assets. It may eventually supply Forged & Sent, but must remain independently buildable and maintainable. OpenGym3D already contains motion normalization, MPFB rendering, exports, browser viewing and QA; Heatsy supplies a separate, attributed anatomical model.

## Decision
- Maintain `Forged-Sent/ForgedMotionStudio` independently of `ForgedAndSentFitness`.
- Reuse the existing OpenGym3D pipeline as the working MPFB baseline.
- Keep Heatsy as a separate character/retargeting/derivative lane so experiments never break the MPFB route.
- Prefer local Blender/Python/Three.js tools, small change sets and reproducible commands.
- Add a nontechnical editor only after one attractive, validated anatomical exercise is feasible; add no cloud/backend just for the proof.
- Distinguish automated technical gates from human technique, anatomical and rights approval.

## Alternatives considered
- Rewrite a generalized animation engine: too much unproven work.
- Tie assets directly to the Flutter app: would couple development and publication to the consumer.
- Treat the static Heatsy model as plug-compatible: contradicted by importer/retargeting evidence.

## Consequences
Preserve two model lanes and their attribution. Build a small future asset interface rather than sharing app internals. Accept limited local scripting until the quality gate is genuinely met.

## Evidence
[Static compatibility](../HEATSY_COMPATIBILITY_REVIEW.md) · [Animated bodyweight](../HEATSY_BODYWEIGHT_REVIEW.md) · [Repair investigation](../HEATSY_DEFORMATION_REPAIR.md)
