# OpenGym3D

Open-source interactive 3D exercise library — a [gym-animations.com](https://gym-animations.com)
alternative where **Blender never runs on your machine**. Push a pose file to GitHub;
CI runs headless Blender, exports an animated `.glb` + thumbnail, and deploys the
Three.js viewer to GitHub Pages. Zero servers, zero cost, PC off.

## How it works

```
exercises/squat.json          (pose keyframes + muscle metadata — the source of truth)
        │  git push
        ▼
GitHub Actions (ubuntu runner)
        │  downloads Blender 4.5 LTS (cached), runs pipeline/build_exercise.py -b -noaudio
        ▼
site/assets/squat.glb         (skinned rig + baked animation, ~50 KB)
site/assets/squat.png         (Cycles CPU thumbnail, mid-rep frame)
        │  actions/deploy-pages
        ▼
https://assiamahs.github.io/opengym3d/
        (Three.js: orbit, play/pause, scrub, speed, muscle highlights)
```

Key insight: an interactive viewer needs **GLB exports, not renders**. Exporting
geometry + baked animation takes seconds on CPU — no GPU cloud (RunPod/Vast.ai)
required. Cycles is only used for the little thumbnail per exercise.

## Add or tune an exercise — from your phone

1. Open `exercises/` on github.com and edit any JSON (or copy one to a new file).
2. Commit. CI rebuilds and redeploys automatically (~3 min).

Pose format: keyframes at `t` (0→1 of one rep), per-bone euler rotations in degrees.
`thigh.*` applies to `.L` and mirrors to `.R`. `loc` on `pelvis` is a world-space
offset in meters (how squats drop the hips).

Bone names: `pelvis, spine, chest, neck, head, upper_arm.L/R, forearm.L/R,
hand.L/R, thigh.L/R, shin.L/R, foot.L/R`.

Muscles in `primary` / `secondary` drive the red/orange body-part highlights
(see `MUSCLE_BONES` in `pipeline/build_exercise.py`).

## Run locally (optional)

```sh
blender -b -noaudio -P pipeline/build_exercise.py -- exercises/squat.json /tmp/out
python3 -m http.server -d site 8000   # after copying website/* + assets into site/
```

## Roadmap

| Version | What | Built on |
|---|---|---|
| v0 | Procedural capsule figure, FK pose keyframes, GLB + viewer, full CI pipeline | Blender 4.5 LTS, Three.js r170 |
| **v1 (this)** | Real anatomical human (male, muscle 1.0), MakeHuman rig, muscles painted via skin-weight territories, A-pose-proof aim retargeting | [MPFB2](https://github.com/makehumancommunity/mpfb2) — the maintained successor to MB-Lab (MB-Lab is archived) |
| **v2** | Record yourself doing a lift on your phone → animation, no hand-keying | [BlendArMocap](https://github.com/cgtinker/BlendArMocap) (MediaPipe → Rigify) or [freemocap](https://github.com/freemocap/freemocap) |
| **v3** | Anatomical muscle visualization: per-muscle activation, contraction shading | [MuSkeMo](https://github.com/PashavanBijlert/MuSkeMo) + animated normal maps |
| **v4** | Full library: hundreds of exercises, search/filter, MP4/GIF export, embed API | this pipeline, scaled |

## Layout

```
exercises/    one JSON per exercise: metadata + pose keyframes
pipeline/     build_exercise.py (Blender headless), make_manifest.py
website/      static Three.js viewer (no build step)
.github/      render & deploy workflow
```
