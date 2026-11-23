# Milestone 3 — animated Heatsy bodyweight squat

**Result: PARTIAL.** The exported squat, anatomical attributes, synchronized
viewer and reproducible evidence pipeline work. Convincing anatomical deformation
is not established: the preserved skin has severe upper-body stretching and
visible pinching around the hips and knees. Technical validation is distinct
from movement, anatomy, appearance and public-use approval; all remain unapproved.
This is the end of this bounded milestone, pending human review.

## Reproduce and inspect

From the existing prepared environment (Python/NumPy, Node dependencies,
Playwright Chromium, pinned Blender 4.5.11, FFmpeg and ffprobe):

```powershell
Set-Location C:\ws_c\ForgedMotionStudio
python studio/heatsy_squat_build.py
python -m http.server 8765 --bind 127.0.0.1
```

The build deliberately returns **2** after delivering a technically validated
but deformation-blocked result. An exception instead writes `FAIL` and exits 1.
Open **http://127.0.0.1:8765/studio/heatsy-squat/**. This extends the existing
comparison viewer, with play/pause, automatic looping, scrub, 0.5/1/2x speeds,
synchronized orbit, front/side/three-quarter/rear presets, individual and grouped
muscle highlighting, and a **Quick Peek · 320 px** button. Muscle highlighting
identifies geometry; it is not an activation measurement.

All generated files for this run are in
**C:\ws_c\ForgedMotionStudio\outputs\heatsy-bodyweight\**. The earlier
`outputs/heatsy-squat/` diagnostic, static compatibility bundle and canonical
MPFB outputs are protected by a before/after hash manifest. No fitness app,
cloud service, publication or additional exercise is involved.

## Reused implementation and changes

The existing `heatsy_squat.py` target-specific adapter, normal restoration,
attribute/correspondence validator, independent GLB FK/LBS, diagnostic ablations,
capture and media pipeline were reused. No rig, weights, anatomy geometry or
general retargeting framework was rebuilt. New work adds source-derived timing,
correct MPFB keyed-interval synchronization, explicit hierarchy/fallback metadata,
fixed-sole contact measurements, regional edge measurements, Blender evaluation,
Quick Peek, speed/pause checks, individual-muscle evidence and build/performance
measurements. The build now writes only the requested new output directory.

The source is the exact unchanged `motions/synthetic/squat.json`, format
`opengym3d-motion/1`, SHA-256
`8707ffd2547de40629f193c9667136485ba51a59b99b9212a44bcefb47c13ad9`.
Its **91 samples at 30 fps span 90 intervals = 3.000 seconds**. This is derived
from the file, not a fixed-duration assumption; a regression also checks 24 fps.
MPFB's existing keys span 0.0333333–3.0333333 seconds. The viewer synchronizes
each model's **first-to-last keyed interval**, preserving both assets and avoiding
the earlier phase offset caused by dividing by total clip duration. The source
cosine path supplies standing, descent, bottom, ascent and return; there are no
manually edited frames. The duplicate closing key is omitted from video frames.

## Rig and preservation contract

`retarget.json` contains every node's parent and the complete correspondence.
OpenGym uses metres, +Z up and -Y forward; glTF uses metres, +Y up and +Z forward.
Conversion is `(x,y,z) → (x,z,-y)`. Limb directions are calibrated to the target
rest geometry, then converted from desired world rotations to parent-relative
quaternions. Pelvis orientation uses the source pelvis basis. Root travel is
scaled by target/canonical leg length, **0.92580820997**, with one constant
standing-floor offset of **-2.304830 mm**. Only pelvis translation is animated.

`spine_01` and `spine_02` follow canonical spine world delta; `spine_03` follows
chest. This does not apply the same local rotation twice. Clavicle/scapula retain
the existing small arm-elevation follow policy. Thigh, shin, foot, upper arm,
forearm, hand, neck and head are explicitly mapped. Forearm twist, fingers and
toes inherit animated parents with their local rest transforms. There is no
source twist reference in this fixture; none is invented. New inputs with twist
targets are rejected pending review. Shortest-arc arm aiming leaves palm
orientation unresolved; the visible palms differ from MPFB.
The fixture's pelvis basis is constant, so there is no independently captured
pelvic tilt or bottom-position tuck. Torso lean comes from the source spine
directions. This limits any claim about realistic pelvic articulation.

The whole static binary prefix and the original meshes, nodes, materials, skins,
inverse binds and existing accessors remain unchanged. The animated GLB retains
**149,030 triangles, 79,674 vertex records and 56 skin joints**. The existing 16
representational vertex splits are preserved. No new splits or weight edits.
All decoded `_PART_ID`, `_FIBER` and `_TENDON` values are unchanged FLOAT32 with
`normalized=false`. Fiber vectors are not renormalized and original position or
attribute quantization scales are not applied again. Existing explicit source
normal restoration is rerun in isolation and must reproduce the static baseline.

Selections cover neutral, left/right quadriceps, gluteus maximus (97/98), gluteus
medius (99/100), and individual rectus femoris, vastus lateralis and vastus
medialis. Missing vastus intermedius and gluteus minimus remain absent. The glutes
group follows the source vocabulary and also includes tensor fasciae latae;
individual selections make this distinction explicit. Color/ID correspondence
is checked at descent, bottom and ascent, with skin-position samples distributed
across every present part ID.

## Measurements and their limits

The current source/export is sampled at **181 times, 60 Hz**, including endpoints.

| Measurement | Result |
| --- | ---: |
| Mesh loop closure | 0 m |
| Maximum ankle-joint drift | 0.322 mm |
| Maximum fixed-sole horizontal drift | 0.311 mm |
| Maximum skin/sole penetration | 0.115 mm |
| Maximum sole lift relative to standing | 0.120 mm |
| Highest lowest sole point, L / R | 0.119 / 0.219 mm |
| Bottom knee interior angle, both sides | 71.3596° |
| Maximum key-to-key rotation step | 3.8574° |
| Maximum normal step at 60 Hz | 1.0941° |
| Maximum source/target limb direction error | 0.000782° |
| Blender vs independent GLB position component error | 0.00985 mm maximum |

The sole sample uses fixed material vertices within 2 mm of each foot's standing
minimum: 14 left, 17 right. Reported maximum point height also includes the
initial 2 mm band, so it is not the same as lift. There is no IK/contact solver,
toe articulation, collision response or per-frame clamp. These contact results
apply to this synthetic fixture and target proportions only.

`animated-parity.json` records actual Three.js/Python and direct
**Blender/Three.js** maxima across 1,107 vertices at eight poses (five named poses
and three off-key phases). Blender imports the delivered GLB using the guarded
patch, verifies all rest positions, anatomy values and named weights through
spatial correspondence, then evaluates the armature modifier. The position gate
is 1e-5 m; observed Blender rest correspondence is within 0.00623 mm. This is
not index-assumption or a second export. Browser normal and joint-matrix gates
are 1e-5 per component. Blender's known custom-normal re-encoding limitation is
not claimed solved; final GLB source-restored normals are evaluated in Three.js.
Shaded and normal-direction images show continuous shading, including the
unacceptable distortions in the underlying geometry.

Khronos validation requires **zero errors**, an untruncated report and only the
retained `NODE_SKINNED_MESH_NON_ROOT` warning. Both mesh and `body_rig` are static
identity nodes; root motion belongs to pelvis. Posed positions and all 56 world
joint matrices agree in the tested consumers. This supports retaining the warning
for this animation; arbitrary parent scaling/animation and other engines remain
untested.

The unit suite has **60 passing tests**, including all prior static/bodyweight
tests and the source-timing regression. `baseline-before.json` protects **386
files** across source inputs and earlier output bundles. Media verification
decodes all 90 frames of each 640×640, 30 fps MP4 and compares them with the
exported-GLB renderer frames (PSNR gate >35 dB). Exact PSNR, file hashes, browser
timings and stage durations are in `media.json`, `viewer.json`, `provenance.json`
and `build-timing.json`. CPU seek/render-submission timings are not GPU completion
times, sustained device fps or mobile benchmarks.

The completed build took **257.21 seconds**: retarget/export 0.96 s, preservation
and animation validation 24.81 s, Blender comparison 6.64 s, browser checks/capture
161.93 s, and video encoding/verification 3.69 s (other time is preparation/tests).
Direct Blender/Three.js maximum position component difference is **0.009838 mm**;
Three.js/Python is **0.000156 mm**. All 38 screenshots, 57 selection checks,
pause, loop, scrub, speed and orbit checks passed without browser errors.
Front/side decoded PSNR is **49.918 / 49.414 dB**. Both complete decoded contact
sheets were visually inspected; descent/ascent are continuous and the upper-body
defect persists through the loop.

In Windows Headless Chromium 145, both-model median CPU seek/render submission
was **1.8 ms**. Actual median animation-frame intervals were **221.9 ms** at
588×580 per panel and **186.3 ms** at 320×320 (about **4.5 / 5.4 fps** respectively;
p95 intervals 234.4 / 193.6 ms). This is slow interactive frame delivery in the
tested environment, despite correct phase/speed advancement. It must not be
reported as smooth 60 fps or inferred from CPU submission time. The offline
videos contain every frame at 30 fps. GPU backend attribution and representative
hardware/mobile performance require a separate measured review; no mesh
simplification was introduced to disguise this limit.

## Visual assessment and isolated obstacle

The repetition and foot placement are readable, movement is continuous, and
selected muscles follow their anatomical mesh regions. At 320 px the highlighted
quadriceps region remains identifiable, but small muscle boundaries are difficult
to inspect. Detailed views remain necessary for anatomical review.

The shoulder/back result is **unacceptable**: the latissimus forms a stretched,
ragged sheet into the elevated arm. The diagnosed right-latissimus edge grows
from **1.407101 mm** at rest to **46.840740 mm (33.2888×)** at the bottom. It is
already 27.5575× in the arms-forward standing pose. At bottom, **19,595** measured
edges exceed twice their rest length. Edges shorter than 1 mm are excluded.
Removing girdle follow retains the failure; leaving the upper body at rest while
retaining leg/pelvis motion removes that edge distortion. This implicates the
preserved weight transition under arm elevation, without proving every roll or
shoulder mapping choice optimal. Exact endpoint weights and source correspondence
are in `deformation-diagnosis.json`.

Hip close-ups also show angular folds/pinching at the glute/thigh junction; knee
close-ups show thin stretched attachment regions. Neither is certified free of
self-intersection. `validation.json` adds regional stretch counts and percentiles
for hips/glutes, knee-crossing muscles and shoulders/torso. These group aggregates
are not a spatial collision test or physiological strain metric. No exhaustive
self-collision or clinical anatomy analysis was performed. There are no newly
tiny triangles under the recorded area gate at the five measured poses, but that
does not negate visible distortion. The baseline's degenerate triangles remain
a separate, pre-existing issue.

At bottom, the hip/glute group has **4.95× maximum / 3.02× p99** edge stretch
(1,356 edges >2×); knee-crossing muscle groups have **9.10× / 3.36×**
(2,467 >2×); shoulder/torso groups have **33.29× / 10.80×** (11,755 >2×).
Also, 106 triangles shrink below one tenth their rest area. These results and
the close-ups rule out claiming that only a minor shoulder cosmetic issue remains.

Do not solve this by lowering the arms, editing the input, hiding failing muscles,
changing weights or replacing geometry within this milestone. The highest-impact
next milestone is a bounded shoulder/hip deformation investigation with an anatomy
reviewer: test whether rest-roll/shoulder calibration can resolve the failure
while retaining this source and skin. If it cannot, separately scope corrective
skinning or pose-space deformation and its license/preservation implications.
Motion/anatomy approval must follow acceptable deformation, before broader
exercise coverage or product integration.

## Delivered evidence and attribution

- `heatsy-squat.glb`, `front.mp4`, `side.mp4`, `poster.png`.
- `poses/{standing,descent,bottom,ascent,return}-{front,side,three}.png`.
- `poses/bottom-{hips,knees}-detail.png` and four latissimus close-ups.
- Individual-muscle and separate-side screenshots, normal-direction views and
  four 320-pixel comparison screenshots.
- `front-decoded-all-frames.png`, `side-decoded-all-frames.png`.
- `milestone.json`, `validation.json`, `preservation.json`, `retarget.json`,
  `heatsy-squat.glb.gltf.json`, `blender-parity.json`, `animated-parity.json`,
  `deformation-diagnosis.json`, `viewer.json`, `media.json`, `build-timing.json`,
  `provenance.json`, stage logs and source/baseline hash manifest.
- `LICENSE`, `NOTICE.md`, `DERIVATION.md`, `IMPORTER-NOTICE.md`,
  `MOTION-CODE-MIT.txt` and this review copied as `REVIEW.md`.

Heatsy / DDDEV LTD, Z-Anatomy and BodyParts3D attribution and **CC BY-SA 4.0**
remain with the animation and rendered derivatives. Source commit:
`6cf6a0ae7c63bcffca1137ddcec14a31b7254a6d`. Original asset SHA-256:
`ce9859de013c2ee9713dbe3158275208b57be1b4ff31957eca87195b991c0ab1`.
Synthetic motion/code are MIT. Nothing has been committed, pushed or published.

API references used for the added checks:
[Blender 4.5 evaluated dependency graph](https://docs.blender.org/api/4.5/bpy.types.Depsgraph.html),
[Three.js r170 SkinnedMesh](https://github.com/mrdoob/three.js/blob/r170/docs/api/en/objects/SkinnedMesh.html),
[Three.js r170 AnimationMixer](https://github.com/mrdoob/three.js/blob/r170/docs/api/en/animation/AnimationMixer.html).
