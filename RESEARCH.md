# How others do it (research, 2026-07-30)

## The market leader is not doing anything magic

gym-animations.com — the site this project clones — is a 10-person team of 3D
motion artists selling **MP4 videos only** (6s, 1080p, white bg) in bulk:
$199–$599 per package, 7000+ clips, non-exclusive royalty-free. Their look is
**grey body model + red highlighted muscles on white background** — which is
exactly the v0.22 figure. The "industry standard" aesthetic we already ship.

Our structural advantages over them: interactive GLB (orbit/scrub) vs flat
MP4, muscle manifest + form-cue JSON, MIT license, $19 vs $199.

## The standard solo-dev pipeline (nobody hand-rigs anatomy)

1. **Clean single-mesh manifold humanoid** (MakeHuman/MPFB2, Character
   Creator, DAZ) — never 665 loose shells. Single-mesh manifolds "almost
   never fail" automatic weights (46-character benchmark, jessyleite.dev).
2. **Buy mocap, retarget** — Unity Asset Store gym packs ($9–20 FBX),
   or commission. Real mocap is what makes motion look "perfect";
   hand-keyed poses always read robotic.
3. **Mixamo is free for embedded use** but its EULA bans redistributing
   raw animation files as asset packs — so Mixamo data can power the APP but
   can never go in the Gumroad pack. Our pose-JSON-derived animations are
   original and sellable: that's a moat, keep it.

## Bone heat failure — the canonical triage (jessyleite.dev, 2026-06)

Four causes: (1) non-manifold geometry → merge by distance 0.0001, degenerate
dissolve, recalc normals; (2) disconnected islands → bind each sub-mesh
separately, or join only after surfaces actually touch; (3) bone enclosed /
outside mesh; (4) unapplied transforms or extreme scale. Our écorché is
causes 1+2 at maximum severity (665 islands, non-manifold medical meshes) —
surface heat can never work on it.

Pro solutions are all **volumetric**: Voxel Heat Diffuse Skinning addon
(mesh-online.net, voxelizes + diffuses through 3D volume, built for exactly
this), AccuRig (free, handles multi-mesh), Mixamo auto-rig (single mesh
T-pose only). Our nearest-bone inverse-square fallback is a crude volumetric
method — same family, zero dependencies, CI-safe. Upgrade path if joints look
stiff: per-muscle rigid binding (each muscle is nearly rigid anatomically),
or port a small voxel diffuse into pipeline/.

## What "perfect" means, concretely, for this repo

1. Site