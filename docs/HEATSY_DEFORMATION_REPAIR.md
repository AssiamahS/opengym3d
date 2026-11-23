# Heatsy autonomous deformation repair

**Result: PARTIAL.** Extreme tearing is substantially reduced by an explicitly
tracked skin-weight derivative. The original mesh, anatomical data, skeleton,
inverse binds and squat animation remain unchanged. Residual compression,
intersections and anatomical attachment quality prevent a deformation PASS.
Exit code **2** remains meaningful. No movement, anatomy or public-use approval
is asserted, and no assets have been published.

## Reproduce and inspect

```powershell
Set-Location C:\ws_c\ForgedMotionStudio
# Only if the existing environment lacks the recorded dependencies:
python -m pip install -r studio/requirements-repair.txt
python studio/heatsy_repair_build.py
python -m http.server 8765 --bind 127.0.0.1
```

Expected build exit: **2**, because deformation is still incomplete and native
Blender position parity narrowly fails its unchanged tolerance. The final
`technical_pass` is **false**, not a blanket technical PASS. Unexpected exceptions
write `FAIL` and exit 1. Reuse an existing server on
8765 rather than starting a second one.

- Updated MPFB comparison: http://127.0.0.1:8765/studio/heatsy-squat/?repair=final
- Before/after Heatsy: http://127.0.0.1:8765/studio/heatsy-squat/?repair=final&compare=before
- Preserved broken baseline: http://127.0.0.1:8765/studio/heatsy-squat/

All new outputs are in **C:\ws_c\ForgedMotionStudio\outputs\heatsy-repair\**.
The final complete rebuild took **196.6 seconds**, including **52.8 seconds** for
the rest-space weight correction/export, **21.1 seconds** for sampled validation,
**29.9 seconds** for tests, **19.3 seconds** for intersections, **39.7 seconds**
for browser captures and **2.9 seconds** for MP4 encoding. Detailed stage timing
is in `build-timing.json`; separate performance experiments are excluded.
The build process actually returned **exit code 2**. Repeated deterministic builds
produced the same final GLB hash. Existing pinned Blender 4.5.11 and the Node
dependencies from `package-lock.json` are reused from the prior milestones.
The original source, static compatibility results, canonical MPFB bundle, previous
Heatsy animations, motion JSON and notices are protected by the checkpoint hash
manifest. Operational HTTP logs are excluded because serving the viewer appends
to them. The initial worktree and source archive are under `checkpoints/`.
No unrelated work was committed, reset or edited. ForgedAndSentFitness was not
accessed or modified.

All **650 protected baseline files** remain byte-identical. Meaningful local
checkpoints are `checkpoints/before-repair-source.zip`, the original worktree
listing/hash manifest, and `checkpoints/accepted-source.zip`; `provenance.json`
records exact current code and asset hashes. The resulting GLB SHA-256 is
`0d493881425b70291727909709f0e2234d32f80b8e6af31b9587255c79b0124b`.

## Confirmed causes and limits of the diagnosis

**Abrupt source weight gradients are the main confirmed cause of tearing.**
The bind pose is consistent within 5.98 micrometres at matrix translation scale;
weight sums differ from one by at most 9.69e-8. Posed joint transforms remain
rigid. There is no global coordinate conversion, root scaling or parent-transform
failure explaining the centimetre-scale damage.

The exact linear-skinning edge vector was decomposed into a geometric term
(average weights acting on the rest edge) and a term due to differing endpoint
weights. Vector magnitudes do not add arithmetically; their vector sum gives
the actual posed edge.

| Region / actual worst part | Rest edge | Posed edge | Geometric term | Weight-gradient term |
| --- | ---: | ---: | ---: | ---: |
| Back: right latissimus | 1.407 mm | 46.841 mm | 1.395 mm | 46.650 mm |
| Hips: right tensor fasciae latae | 1.393 mm | 6.898 mm | 1.100 mm | 7.393 mm |
| Knee-crossing muscles: left vastus lateralis | 3.961 mm | 36.066 mm | 2.795 mm | 33.663 mm |

The latissimus edge changes upper-arm influence by about 22 percentage points
over 1.4 mm; the knee example changes shin influence by about 45 points over
4 mm. These are much larger than one 8-bit quantization step. They occur on
ordinary edges, independently of tiny/degenerate source edges.

**Rotation choices are not proven anatomically optimal**, but changing them did
not resolve the defect. In the tested bottom pose, the left thigh and shin local
rotation axes expressed in rest-world coordinates align closely with sagittal
X (absolute X component >0.9997). Their rest-relative rotations are about 82.04°
and 111.70°. Spine_01 carries 25° of lean; spine_02/03 have no additional local
lean. This is a concentrated distribution, not accidental repeated accumulation.
The source pelvis basis is constant. Shoulder swing has no independent source
twist target; palm orientation remains unresolved. `joint-axes.json` stores rest,
local and world matrices; axis screenshots accompany the experiments.

**Additional confirmed experimental failure:** unrestricted Euclidean smoothing
mixed nearby rest-pose hand/forearm and thigh/torso influences. For example,
switching a hand vertex's fourth influence to thigh produced new tearing.
That trial was rejected. The accepted correction restricts each muscle part and
each connected unlabeled component to bones already present in its original
support. It does not change or merge anatomical labels.

**Additional confirmed representation hazard:** abruptly retaining only the four
largest weights introduces a discontinuity when the fourth and fifth exchange
rank. The accepted method fades the discarded influence continuously before
normalization. A synthetic adjacent-surface test and a rank-swap test cover these
two defects separately.

## Controlled experiments

All diagnostics evaluate cached rig/mesh arrays in memory; a GLB is not rebuilt
for every pose. Neutral, isolated hip flexion, knee flexion, shoulder swing,
shoulder plus girdle, torso articulation, standing, descent and squat bottom are
recorded in `controlled-baseline.json` and `controlled-after.json`.

| Baseline controlled pose | Maximum ordinary-edge stretch |
| --- | ---: |
| Neutral rest | 1.000× |
| Arms-forward standing | 27.557× |
| Isolated hip flexion | 6.115× |
| Isolated knee flexion | 9.105× |
| Isolated shoulder swing | 25.339× |
| Shoulder plus girdle | 27.557× |
| Torso articulation | 5.323× |
| Squat bottom | 33.289× |

Arm roll ±45°/±90°, doubled/removed girdle follow, and distributed spine lean
were tested without lowering the source arm direction. Bottom torso maximum
remained 31.21–35.93×. None was accepted as a fix. Screened graph diffusion,
per-part spatial smoothing, unrestricted coherent smoothing and guarded coherent
smoothing are preserved as separate experiment reports and candidate GLBs.

Per-part smoothing reduced stretch but produced attachment mismatches between
neighboring muscles. A shared field improves their relative behavior, while the
original-support guard avoids transferring motion between nearby unrelated limbs.
The final continuous four-influence reduction slightly increases maximum stretch
versus the abrupt guarded trial (3.529× versus 3.495×), in exchange for eliminating
the rank-switch discontinuity. This tradeoff is explicit.

The same rotation experiments were repeated **after** the weight correction.
Distributing spine lean reduces torso maximum 3.057→2.951× and compressed edges
733→600, but increases nearly collapsed triangles across the mesh 71→74. Removing
girdle follow reduces torso stretch slightly but increases torso compressed edges
733→1,117. Negative arm-roll trials increase nearly collapsed triangles to
428–465. These are not uniform fixes; none was accepted as an additional motion
change. `transform-experiments-after.json` retains all three tested phases.

## Accepted correction

`recipe.json` specifies the complete deterministic method:

1. Compute rest-triangle area weights, so dense or tiny triangles do not dominate.
2. Average original skin influences with a 35 mm Gaussian in rest space, truncated
   at three sigma. No animation pose or frame participates in fitting.
3. Restrict the resulting field to original per-part/component bone support.
4. Retain original foot weights below rest Y=0.10 m, with a smoothstep blend to
   the corrected field by Y=0.16 m. This is a rest-skin preservation constraint,
   not per-frame floor clamping or foot IK.
5. Subtract the fifth-largest influence, clamp at zero and normalize. At most
   four influences remain, with continuous behavior across ordinary rank swaps.
   An ambiguous all-equal support is rejected for review rather than silently
   assigned a bone.

Only new `JOINTS_0` and `WEIGHTS_0` accessors are appended and referenced. The
entire prior binary prefix remains intact. Mesh positions, normals, triangles,
149,030 faces, 79,674 vertex records, 56 joints, inverse binds and animation
channels are retained. `_PART_ID`, `_FIBER` and `_TENDON` values and semantics are
unchanged; no scales are reapplied and fibers are not renormalized. The source
motion still contains the same 91 samples spanning 3 seconds. There are no
recurring manual frame edits or new exercise variations.

`weight-change.json` records changed-vertex counts, magnitudes and per-part
changes. This is explicitly a **skin-weight derivative**, not a weight-preserving
roundtrip. Heatsy / DDDEV LTD, Z-Anatomy and BodyParts3D credit and CC BY-SA 4.0
remain with every derived asset. MIT motion/code notices are also included.

## Before/after deformation measurements

All ordinary-edge statistics below exclude rest edges shorter than 1 mm. Separate
bands below 0.1 mm and between 0.1–1 mm remain in every report. Region masks use
the source muscle vocabulary; “knees” means knee-crossing muscle groups, not
only a spatial box around the knee joint.

There are 221,662 ordinary edges, 7,005 effective-rest edges between 0.1–1 mm,
and 129 below 0.1 mm. **59 edges have exactly zero length in the source geometry**;
their stretch ratio is undefined and separately reported as `null`, with posed
separation in millimetres. The historical combined tiny-edge ratio can exceed
674,000× and must not be interpreted as a material strain measurement. The
33.289× ordinary-edge failure is independently real: its rest length is 1.407 mm.
The 59 zero-length source edges separate by at most 0.591 mm at baseline bottom,
versus 0 mm after correction. The other 70 source edges below 0.1 mm are reported
separately; their maximum absolute change falls 0.551→0.066 mm.

| Bottom pose | Maximum before → after | p99 before → after | Edges >2× before → after |
| --- | ---: | ---: | ---: |
| Whole mesh | 33.289 → 3.529× | 7.887 → 1.800× | 19,595 → 925 |
| Torso/shoulders | 33.289 → 3.057× | 10.804 → 1.890× | 11,755 → 379 |
| Hips | 4.952 → 1.865× | 3.022 → 1.704× | 1,356 → 0 |
| Knee-crossing muscles | 9.105 → 2.068× | 3.365 → 1.767× | 2,467 → 19 |
| Upper arms/forearms | 27.309 → 3.529× | 8.543 → 2.161× | 2,506 → 326 |

Remaining worst regional edges are also reported in absolute units: torso
4.589 → 14.028 mm (+9.439 mm), hips 5.239 → 9.770 mm (+4.530 mm), knees
2.867 → 5.930 mm (+3.063 mm). These are new worst edges, not the original ones.
The original failing endpoints are separately covered by regression tests.

Absolute change also matters: the final largest ordinary-edge length change is
**79.524 mm**, on right triceps long head, from **37.370 to 116.894 mm (3.128×)**.
The original mesh maximum absolute change was 165.078 mm. This remains severe
upper-arm attachment distortion despite the improved percentile statistics.
Every region now includes the worst edges sorted both by ratio and by absolute
length change. Whole-mesh p95 decreases 2.987→1.491×; p50 remains about 1.000×.

**Compression regression:** ordinary edges below half their rest length increase
from 1,292 to 3,139 (hips 232→811, knee groups 251→791). Triangles below one tenth
their rest area decrease from 106 to 71; no newly tiny triangles pass below the
recorded absolute area threshold. The correction trades severe tearing for a
more coherent but still compressed surface. This is why it remains PARTIAL.

`surface-intersections.json` uses Blender BVH candidates followed by explicit
non-coplanar segment/triangle tests. Shared vertices and endpoint/edge touches
are excluded. Both raw crossing pairs and a separate >0.1 mm plane-margin count
are retained. The source already has extensive intersections at rest; absolute
pair counts are not an anatomical acceptance test. Coplanar contact, containment
and physiological sliding are not modeled. The final accepted-file hash binds
its measurements to the exported GLB.

| Pose | Raw crossing pairs before → after | Pairs with >0.1 mm margin before → after |
| --- | ---: | ---: |
| Neutral rest | 50,757 → 50,721 | 43,281 → 43,271 |
| Standing | 113,209 → 59,925 | 98,499 → 43,529 |
| Mid-descent | 128,491 → 60,510 | 112,722 → 43,861 |
| Bottom | 144,241 → 61,977 | 127,366 → 44,795 |

Tiny neutral differences arise from changed weights acting on the source's
slightly inexact inverse-bind/rest configuration; positions differ by at most
0.359 micrometres. No geometry was deleted to reduce intersection counts.

The Blender volume ablation uses identical poses and weights. At bottom,
dual-quaternion versus native linear skinning reduces edges below half length
**3,140→530** and nearly collapsed triangles **71→23**, but increases maximum
stretch **3.529→4.084×**, p99 **1.800→2.109×**. Thus linear blending contributes to
compression, while changing the skinning method alone is not a complete fix.
Native float arithmetic accounts for the one-edge threshold difference from the
Python count of 3,139. This experiment is not included in the exported GLB.

## Visual evidence

Each comparison below shows the preserved baseline on the left and the tracked
derivative on the right, at the same phase, with matching lighting and cameras.

![Bottom back and shoulders](../outputs/heatsy-repair/experiments/final-bottom-shoulder.png)

![Bottom hips](../outputs/heatsy-repair/experiments/final-bottom-hips.png)

[Knee close-up](../outputs/heatsy-repair/experiments/final-bottom-knees.png),
[standing shoulders](../outputs/heatsy-repair/experiments/final-standing-shoulder.png),
[mid-descent shoulders](../outputs/heatsy-repair/experiments/final-descent-shoulder.png),
[bottom strain map](../outputs/heatsy-repair/experiments/control-final-bottom-strain.png).
Standing/descent/bottom close-ups for all three regions are in `experiments/`.

Back surfaces are less ragged and movement is coherent across the repetition.
The superior shoulder/clavicle seams still lift, latissimus looks sheet-like,
deep hip folds remain compressed, and knee/upper-arm attachments still look
unnatural. The result is not anatomically acceptable merely because tearing is
reduced. At 320 px the squat silhouette and selected quadriceps remain readable;
fine attachments and tendons need the detailed view.

![320-pixel comparison](../outputs/heatsy-repair/poses/bottom-quick-peek.png)

Playable previews: [front MP4](../outputs/heatsy-repair/front.mp4),
[side MP4](../outputs/heatsy-repair/side.mp4). The complete decoded 90-frame contact
sheets were inspected; both videos are 640×640, 30 fps, 3 seconds. Encoding PSNR
against the exact browser frames is 50.39 dB front / 49.87 dB side. Earlier
broken videos remain under `outputs/heatsy-bodyweight/`.

## Export, browser and performance verification

`validation.json` retains the prior technical tolerances: 10 micrometre rest and
posed parity, 20 mm ankle drift, 5 mm floor penetration, closed mesh loop and
normal continuity. All joint transforms and animation channels are compared
directly with the broken baseline. Browser color/ID checks cover neutral,
individual muscles and both sides through the squat. No missing muscle receives
substitute geometry. Complete numerical results are in `validation.json`,
`animated-parity.json`, `blender-parity.json`, `viewer.json`, the full unit-test
log and the untruncated Khronos report.

- **66 unit tests pass, no skips**, including the existing 60 and six repair
  regression tests. `tests.log` contains the complete names/results.
- Khronos validation: **zero errors, one existing hierarchy warning**; no
  truncated issue list. All geometry/anatomical attribute preservation checks pass.
- **73,472 of 79,674 vertex records** receive changed weights; per-part counts
  and magnitudes are explicit in `weight-change.json`.
- 181 geometry/normal samples at 60 Hz: mesh and animation seam error **0**;
  maximum normal step **1.094°**. Fixed sole samples (14 left / 17 right) drift
  **0.311 mm**, penetrate at most **0.115 mm**, and lift **0.120 mm** from standing.
  Ankle joint drift is **0.322 mm**. These preserve the earlier contact approximation;
  they do not constitute a physical foot-contact solver.
- Browser: eight parity poses, including off-key times, **1,107 vertices/pose**,
  **57 selection checks**, no browser errors; play/pause, scrubbing, synchronized
  orbit, 0.5×/2× playback and Quick Peek pass. Three.js/Python position component
  error is **0.194 micrometres**, normal component error **4.56e-7**, joint-matrix
  component error **4.45e-7**.
- **Native Blender parity FAIL:** maximum position component error is
  **10.0187 micrometres** versus the unchanged **10 micrometre** gate.
  Blender/Three.js direct comparison is **10.0147 micrometres**, also a failure.
  Neither threshold nor sampled vertices were changed to produce a pass.

`blender-operator-diagnostic.json` isolates the small native-import discrepancy:
imported rest coordinates differ by up to 5.946 micrometres, and reconstructed
bone operators differ from the original glTF bind operators. Applying those
native operators to the imported coordinates predicts Blender's evaluated mesh
within **0.330 micrometres** over all vertices. The discrepancy is therefore in
native rest/pose reconstruction, not browser phase synchronization or centimetre-
scale tearing. Its precise importer normalization/rounding source remains a
hypothesis; the original binds are preserved and the strict gate stays failed.

The known `NODE_SKINNED_MESH_NON_ROOT` warning remains under the same constraints:
mesh and body_rig are static identity nodes, with pelvis carrying root travel.
Blender/Python/Three.js comparisons test the actual final derivative. A separate
Blender dual-quaternion volume experiment is diagnostic only; standard glTF
skinning does not encode Blender's preserve-volume modifier flag. Its results
must not be represented as an exported fix.

Performance was profiled independently using 8 warmup frames and 48 timed
requestAnimationFrame/seek/render samples per case, without screenshots/readback
inside the timed interval. Highlight updates were measured separately and occur
only when the selection changes. The playback path has no per-frame CPU vertex
deformation loop; its full-vertex bounds scan happens during initialization.

| Profile case | Default headless shell, median interval | Chromium D3D11, median interval |
| --- | ---: | ---: |
| Dual models, detailed | 199.2 ms | 6.1 ms |
| Single model, detailed | 122.1 ms | 4.1 ms |
| Single model, 320 px | 103.1 ms | 4.2 ms |
| Single model, unlit material | 79.5 ms | 4.1 ms |
| Single model, rigid shader control | 102.5 ms | 4.2 ms |
| Empty scene control | 16.6 ms | 4.2 ms |
| Dual, no preserved drawing buffer | 196.1 ms | 5.0 ms |

The default renderer was **ANGLE Vulkan / SwiftShader Device (Subzero)**, a
software renderer. The hardware run used **ANGLE / Intel UHD Graphics / D3D11**,
launched with Playwright's Chromium channel and `--use-angle=d3d11`. Browser
version, GPU strings, launch configuration, p95 values and submission/selection
costs are recorded in `performance-profile.json`.

These final-asset measurements use Chromium **145.0.7632.6**. Dual-model p95 is
207.7 ms software / 9.0 ms hardware; median CPU submission is 1.4 / 1.1 ms.
Selection update plus submission costs 9.8 / 3.4 ms in the dual case, and happens
only on selection changes. The final profile is hash-bound to the delivered GLB;
the earlier same-topology candidate run remains `performance-profile-spatial30.json`.

Thus the earlier 4.5–5.4 fps result was primarily a software-rendering environment
limitation. Multiple models, fragment lighting and resolution add cost there;
skinning also contributes, but is not the dominant explanation. Shadows were
disabled in every production-view case. Hardware headless requestAnimationFrame
intervals are **not displayed-device fps or mobile performance certification**.
No decimation, major renderer rewrite or global browser setting change was made.

## Deliverables, changed files and next work

Primary proof: `heatsy-squat.glb`, `front.mp4`, `side.mp4`, `poster.png`,
`poses/`, complete decoded-video contact sheets, and `experiments/final-*` before/
after close-ups of standing, descent and bottom. Strain heatmaps show spatial
concentration at each controlled pose; gray approaches no edge strain and red
means a large absolute log length ratio, for edges ≥1 mm. They show compression
as well as stretch and are not muscle-activation maps.

New source files:

- `studio/heatsy_repair.py`: rig diagnostics, controlled experiments, weight
  corrections and append-only derivative export.
- `studio/heatsy_repair_validate.py`, `heatsy_repair_blender.py`,
  `heatsy_repair_intersections.py`, `heatsy_repair_finish.py`: technical and
  deformation evidence, explicit partial status.
- `studio/heatsy_repair_build.py`: isolated reproduction command.
- `studio/heatsy_repair_capture.mjs`, `heatsy_repair_profile.mjs`: before/after
  images, axes/strain evidence and renderer profiling.
- `studio/requirements-repair.txt`, `tests/test_heatsy_repair.py`, this report.

Existing files extended: `studio/heatsy-squat/viewer.js` (query-selected repair
comparison and diagnostic controls), `studio/heatsy_squat_capture.mjs` (optional
output/query/GPU configuration; unchanged default route), and `studio/README.md`.
The existing retargeter, MPFB build, static importer patch and anatomy validator
are reused. No changes were made to their source logic.

Comparison against the initial source archive confirms that exactly those three
pre-existing source files changed; no archived source file was removed.

Optional detailed experiment reproduction:

```powershell
python studio/heatsy_repair.py diagnose
python studio/heatsy_repair.py transforms
python studio/heatsy_repair.py transforms_after
python studio/heatsy_repair.py weights
python studio/heatsy_repair.py spatial
python studio/heatsy_repair.py candidates
python studio/heatsy_repair.py coherent
python studio/heatsy_repair.py guarded
python studio/heatsy_repair.py continuous
node studio/heatsy_repair_profile.mjs
```

**Next recommended milestone:** attachment-aware, volume-preserving deformation
for the same squat, informed by the diagnostic volume experiment and an anatomy
reviewer. Evaluate a small number of explicitly scoped joint correctives or a
portable volume-preserving representation before committing to weight painting
or a rig redesign. Residual compression, natural joint articulation and palm
orientation remain higher priorities than new exercises or product integration.

Remaining issues, in impact order:

1. Severe remaining arm/shoulder attachment stretch and hip/knee compression.
   Additional indiscriminate smoothing is not justified: it can trade tears for
   volume loss or create cross-limb influence. The next useful correction needs
   attachment/volume constraints or a small, anatomically informed corrective.
2. Native Blender import reconstruction narrowly misses strict posed parity.
   Isolate its rest-coordinate/bone reconstruction rounding without changing
   original inverse binds or relaxing the gate.
3. Synthetic motion supplies no independent axial-twist or pelvic-tilt targets;
   movement accuracy and anatomical appearance remain unapproved.
4. Real displayed-browser/mobile performance remains unmeasured. The software
   headless result does not establish a production-device limitation.

The bounded repair proof stops here. No weight painting, rig redesign, complex
simulation, new exercise variation, editor or application integration was begun.
