# Bodyweight milestone

This local slice reuses OpenGym3D's normalized motion, MPFB character, retargeter,
GLB exporter, QA, skeleton sheet and Three.js playback approach. The input is an
explicitly synthetic MIT engineering fixture. It is not a captured squat or an
approved exercise demonstration. No private repository or MOCAP_TOKEN is needed.

## Windows commands

Prerequisites: Python 3.13, Node/npm, FFmpeg and ffprobe on PATH. The tested FFmpeg
build is recorded in each provenance.json; identical encoded bytes across other
FFmpeg/GPU versions are not promised. Setup downloads ~400 MB Blender plus MPFB
and Chromium. After setup, building and viewing use local files only.

```powershell
Set-Location C:\ws_c\ForgedMotionStudio
python studio/setup.py
python studio/build.py
python -m http.server 8765 --bind 127.0.0.1
```

Open http://127.0.0.1:8765/studio/ . Stop the server with Ctrl+C. The viewer offers
orbit, front/side/rear/three-quarter views, pause, speed and synchronized scrubbing.
MP4 looping is a player setting (`loop` is enabled in the viewer), not an MP4 flag.

Validation alone, against the current bundle:

```powershell
python -m unittest discover -s tests -v
node studio/validate_gltf.mjs
python pipeline/validate_squat.py
```

## Files and gates

All generated files are in `outputs/bodyweight/` (gitignored). Main files:
`squat-technical.glb`, `squat-technical.mp4`, `squat-technical.png`,
`validation.json`, `provenance.json`, `strict-motion.json`, `viewer-parity.json`,
`preview.json`, `media.json`, `squat-technical.glb.qa.json`,
`squat-technical.glb.gltf.json`, and `squat-technical.sheet.png`.
Front/side MP4s, decoded contact strips, bottom-pose images and logs accompany them.

The build marks validation BUILDING before doing work, fails on missing animation
or required checks/reports, and binds reports to the final GLB hash. The selected
gate requires every expected QA result, whole-interval foot drift <=20 mm, root
closure <=5 mm, joint loop error <=2 degrees, and sampled skin-floor penetration
<=5 mm. Browser FK is compared against Python FK. MP4 timing and decoded image
parity are checked. `technical_pass` never changes `public_ready`,
`movement_approved` or `appearance_approved` from false.

The preview frames come directly from the final GLB in the local viewer. This
deliberately uses one render recipe for video and interactive playback; it does
not claim pixel parity with Blender Cycles. The stock character's macro shape
keys are applied at export; a bogus morph animation is disabled for this fixture.
Standing soles receive one automatically measured constant vertical offset.
There is no per-frame floor clamp, manual keyframe correction or foot IK.

## Provenance and boundaries

- Existing repository was clean at OpenGym3D commit
  `ea3a60130fdcfb3c4771e44d09f84ebab4ee9bae`; existing origin is
  `https://github.com/Forged-Sent/ForgedMotionStudio.git`.
- Original README is retained as `docs/UPSTREAM_README.md`; root MIT LICENSE
  remains intact. Upstream deploy workflow is preserved as `.yml.disabled` so
  this local milestone does not trigger private checkout or publication.
  The upstream spike renderer is manual-only for the same reason.
- Blender 4.5.11 and MPFB 2.0.16 archives are hash checked by setup.py. Local
  extension and Blender user files live under work/. Three.js stays at 0.170.0.
- Full notices and asset terms are in `studio/licenses/` and copied into outputs.
  Synthetic provenance survives normalized JSON, export recipe and output hashes.
- No edits were made to ForgedAndSentFitness. Weighted variants, authoring UI,
  workout composition, cloud, Flutter and publication are outside this slice.

## Separate Heatsy probe

The historical `studio/probe_heatsy.py` tested the unmodified model from commit
`6cf6a0ae7c63bcffca1137ddcec14a31b7254a6d` in the same Blender. It is not part of
the normal build. Its original failure report and notices remain in outputs/heatsy-probe.
The source checkout is under work/heatsy.

The subsequent static compatibility milestone is reproduced with
`python studio/heatsy_build.py`. It uses a version/hash-checked process-local
importer patch and verifies values, topology, scale and effective skinning.
Its outputs are isolated in `outputs/heatsy-probe/compatibility/`.
The static comparison is at http://127.0.0.1:8765/studio/heatsy/ when the local
HTTP server is running. See [HEATSY_COMPATIBILITY_REVIEW.md](../docs/HEATSY_COMPATIBILITY_REVIEW.md)
for exact commands, representation changes, evidence and limitations.
This does not establish animated deformation or retargeting compatibility.

## First animated Heatsy diagnostic

The historical diagnostic is retained in `outputs/heatsy-squat/`, with result
`BLOCKED_DEFORMATION`: technical preservation/playback checks passed, but
upper-body stretching was unacceptable. Its prior-revision report is retained as
[HEATSY_SQUAT_REVIEW.md](../docs/HEATSY_SQUAT_REVIEW.md). Current reproduction
commands and the viewer now target the Milestone 3 bundle described below.

## Milestone 3: animated Heatsy bodyweight

Milestone 3 extends the existing animated diagnostic and comparison viewer.
Run `python studio/heatsy_squat_build.py`; current outputs now go separately to
`outputs/heatsy-bodyweight/`, with the historical `outputs/heatsy-squat/` retained.
The viewer remains http://127.0.0.1:8765/studio/heatsy-squat/ . It now synchronizes
the actual keyed motion intervals and adds a 320-pixel Quick Peek mode.
The result is **PARTIAL**, with expected exit code 2 for the documented deformation
obstacle. See [HEATSY_BODYWEIGHT_REVIEW.md](../docs/HEATSY_BODYWEIGHT_REVIEW.md)
for Blender/browser parity, sole measurements, visual limitations and all outputs.

## Autonomous deformation repair

The subsequent autonomous deformation repair is isolated in `outputs/heatsy-repair/`.
Run `python studio/heatsy_repair_build.py` (expected exit 2 while compression and
the documented native Blender precision-gate failure remain).
View `/studio/heatsy-squat/?repair=final` or add `&compare=before` for the preserved
broken Heatsy comparison. See [HEATSY_DEFORMATION_REPAIR.md](../docs/HEATSY_DEFORMATION_REPAIR.md)
for the explicit weight derivative, controlled diagnostics, before/after evidence,
renderer profiling and remaining limitations. Earlier output bundles are retained.

## Input needed after technical review

Supply a controlled full-body squat capture or existing skeletal motion with a
written grant covering footage, performer consent, processing/derivatives and
redistribution of resulting motion, animated GLB and rendered previews (including
commercial reuse if intended). Prefer a clean side view with feet and hands
visible through standing, descent, bottom, ascent and return; a matching front
view helps evaluate knee tracking. A named movement/anatomy reviewer and an
appearance reference are also needed. The next smallest task is one reviewed
bodyweight capture through this same pipeline, with no weighted variation work.
