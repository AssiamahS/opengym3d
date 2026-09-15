# OpenGym3D

[![MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

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

## Motion: real capture, not hand-keyed poses

Every live exercise is driven by motion capture, from one of three lanes
the spec's `"mocap"` field names (details in `docs/ASSET_PIPELINE.md`):

| Lane | Spec value | Lives in | Licence | In the sold pack? |
|---|---|---|---|---|
| CC0 pack | `cc0/mesh2motion/human-addon-animations.glb#Pushup` | `motions/cc0/` | CC0 | yes |
| Your own video | `video/lunge.json` (from `pipeline/video_mocap.py`) | `motions/video/` | yours | yes |
| Mixamo | `mixamo/air_squat.fbx` | private `opengym3d-mocap` checkout | Adobe terms | no |

CI imports the clip headless and retargets it onto the MakeHuman rig by
aiming each bone at the source bone's posed world direction, frame by frame,
carrying the source roll so limbs never flip. A phone clip goes through
Google MediaPipe Pose on your Mac first (`pipeline/video_mocap.py`, $0,
on-device) and comes out as the same per-bone directions. Specs without a
`mocap` field are `"status": "draft"`: kept for their muscle map and form
steps, hidden from the render and the site until they get motion.

`assets/ASSET_LIBRARY.json` lists every human, motion and implement with its
licence; `python3 pipeline/asset_library.py check exercises` shows which
renders may ship. Mixamo's terms allow the clips inside a project but not as
redistributed files, so those renders are app-only and the pack takes the
CC0 and own-capture ones.

## Joint QA and the rig inspector

A render finishing proves nothing about the rig. Every exported GLB carries
the full skeleton and the baked clip, so CI grades the export itself with
`pipeline/qa_glb.py` (stdlib, no Blender): bone-length drift along each limb,
knee/elbow range, roll flips between adjacent frames, root-relative pops,
planted-foot slide, implement-to-hand distance on every frame, and loop
closure. Critical failures keep the exercise **out of the public manifest**
— a barbell exercise never ships with empty hands, an arm whose forearm
flips 150° mid-rep never reaches the grid. The report is printed in the run
log and written next to the asset as `<id>.glb.qa.json`.

`inspect.html` on the site is the same skeleton, drawn: joint markers
coloured by verdict, hinge angles and hand-to-implement gaps live, front /
side / 3-4 / back / top, frame stepping, a 12-frame strip shot from any
angle, the CI contact sheet, and a QA table whose failing rows seek to the
frame. Excluded exercises stay inspectable there.

```
python3 pipeline/qa_glb.py site/assets/*.glb     # grade, write reports, exit 1 on FAIL
python3 pipeline/make_manifest.py exercises site/exercises.json site/assets
```

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
| v1 | Real anatomical human (male, muscle 1.0), MakeHuman rig, muscles painted via skin-weight territories, A-pose-proof aim retargeting | [MPFB2](https://github.com/makehumancommunity/mpfb2) — the maintained successor to MB-Lab (MB-Lab is archived) |
| v1.5 | Real mocap: Mixamo fitness clips retargeted onto the MakeHuman rig in CI; hand-keyed specs demoted to drafts | [Mixamo](https://www.mixamo.com/) |
| v1.6 | Asset library with licensing as data; CC0 motion lane (Mesh2Motion); phone-video lane (MediaPipe → motion JSON) | `assets/ASSET_LIBRARY.json`, `pipeline/video_mocap.py` |
| **v2 (this)** | The exercise factory: `movement.pattern` per spec, anatomy gate (does the figure do THIS exercise?), two-view skeleton sheets, `factory.py resolve/ingest/grade` | `docs/FACTORY.md` |
| **v3** | Anatomical muscle visualization: per-muscle activation, contraction shading | [MuSkeMo](https://github.com/PashavanBijlert/MuSkeMo) + animated normal maps |
| **v4** | Full library: hundreds of exercises, search/filter, MP4/GIF export, embed API | this pipeline, scaled |

## Layout

```
exercises/    one JSON per exercise: metadata + pose keyframes
pipeline/     build_exercise.py (Blender headless), qa_glb.py (joint gate), anatomy_qa.py (movement gate),
              sheet_glb.py (skeleton sheets), factory.py (resolve / ingest / grade), make_manifest.py
website/      static Three.js viewer + inspect.html rig inspector (no build step)
.github/      render & deploy workflow
```

## Tests

```
python3 -m unittest discover -s tests    # stdlib only, ~0.05s
```

The pose maths needs Blender, but the bugs that actually break the site are
plain data — a muscle name the painter doesn't know, an unsorted rep, a
"Dumbbell" exercise with no prop. CI runs these first and gates the render on
them, so a typo fails in seconds instead of after a 40-minute Blender job.
