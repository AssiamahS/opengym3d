# Bounded attachment and compression investigation

**Result: PARTIAL. No new anatomical correction is accepted.** The previous
35 mm weight derivative remains the baseline. A new, explicitly unapproved
candidate reduces several aggregate defects but increases worst stretch and
isolated knee compression. It is retained as evidence, not promoted as a fix.
No threshold, original asset, anatomical label, motion or inverse bind was changed.

This continues [the earlier repair](HEATSY_DEFORMATION_REPAIR.md), rather than
repeating the older 33.29x baseline milestone. Work started from commit
`14a218657d3aa6e9dcb567bdbe84e37f01e89ad7` on local branch
`codex/deformation-attachment-investigation`. The five pre-existing modified
files were left untouched. Nothing was pushed, merged or published.

## Inputs and reproducibility

- Heatsy source SHA-256: `ce9859de013c2ee9713dbe3158275208b57be1b4ff31957eca87195b991c0ab1`.
- Previous repaired GLB: `0d493881425b70291727909709f0e2234d32f80b8e6af31b9587255c79b0124b`.
- Synthetic squat: `8707ffd2547de40629f193c9667136485ba51a59b99b9212a44bcefb47c13ad9`.
- Same 91 source samples, 3-second cycle, 79,674 vertices, 149,030 triangles,
  56 skin joints and source anatomical attributes. The derivative retains the
  original binary prefix and appends only skin influence accessors.
- Exact candidate and implementation hashes are in
  [experiments.json](../outputs/heatsy-attachment/experiments.json) and
  [milestone.json](../outputs/heatsy-attachment/milestone.json).
- `protected.json` hashes 1,071 files across prior outputs, source model and
  motions. Operational HTTP logs are excluded. Old outputs remain in place.

Run from the prepared repository environment:

```powershell
Set-Location C:\ws_c\ForgedMotionStudio
python studio/heatsy_attachment.py
# Expected exit 2: experiments, not an accepted repair.
$env:PLAYWRIGHT_BROWSERS_PATH='C:/Users/Cornw/AppData/Local/ms-playwright'
python studio/heatsy_attachment_verify.py
# Expected exit 2 when verification completes: deformation remains PARTIAL.
$env:FMS_HEATSY_OUTPUT='outputs/heatsy-attachment'
$env:FMS_HEATSY_QUERY='repair=attachment-05'
node studio/heatsy_repair_profile.mjs
python -m http.server 8765 --bind 127.0.0.1
```

Reuse an existing local server if present. Inspect
[previous repair versus candidate](http://127.0.0.1:8765/studio/heatsy-squat/?repair=attachment-05&compare=before),
or omit `compare=before` for the existing MPFB comparison. The original viewer
and `repair=final` routes retain their previous assets. The browser's normal
playback, scrubbing, orbit and muscle selection remain available.

The sandbox initially could not locate its browser cache and then could not
launch Chromium. The installed cache path and approved local execution outside
the sandbox resolved this; no browser download or system setting change was needed.

## Confirmed causes versus hypotheses

The [previous decomposition](HEATSY_DEFORMATION_REPAIR.md) established abrupt
source weight gradients as the principal cause of centimetre-scale tearing.
Rest/bind and normalization discrepancies were micrometre-scale; changing arm
roll, girdle follow and spine distribution did not remove the original tears.
Those conclusions remain applicable; this investigation does not relabel a
native-import precision issue as the cause of gross anatomical damage.

The new edge diagnostic separates the exact posed edge vector into:

1. The rest edge transformed by the average of its endpoint skin operators.
2. A vector caused by the difference between endpoint weights, acting at the
   rest-edge midpoint.

The vectors sum exactly, checked against delivered-GLB positions to 1e-12 m.
Their magnitudes must not be added as scalars. Singular values describe only
the constant-weight operator, not the full spatial deformation gradient or
physiological volume. Ten most compressed and ten largest absolute-change
ordinary edges per region are retained with weights, part IDs and vectors.

| Representative compressed edge | Actual/rest | Constant-weight term/rest | Smallest operator singular value |
| --- | ---: | ---: | ---: |
| Serratus anterior, 69228–69230 | 0.174 | 0.653 | 0.643 |
| Sartorius, 62895–63075 | 0.206 | 0.756 | 0.751 |
| Semitendinosus, 66393–66396 | 0.075 | 0.566 | 0.566 |
| Biceps short head, 71037–71083 | 0.253 | 0.613 | 0.589 |

**Confirmed:** both blended-rotation contraction and spatial influence
transitions contribute; these deepest folds cannot be explained by uniform
linear-blend contraction alone. **Not established:** correct physiological
attachments, independent axial twist, or an anatomically valid alternative
weight field. No manual weight painting, retopology or simulation was introduced.

## Six controlled candidate experiments

Three power transforms `w^p`, normalized, strengthen dominant influences.
Three rational transforms `w/(1+k*w)`, normalized, reduce influence contrast
with a bounded derivative at zero. Both retain exact zero support, at most four
influences, and the existing smooth rest-height sole preservation constraint.
They do not fit animation frames or change source joint motion. Metrics below
come from decoded exported FLOAT32 weights, not a higher-precision proposal.

| Bottom pose candidate | Max stretch | Edges >2x | Edges <0.5x | Triangles <0.1x area | Max absolute edge change |
| --- | ---: | ---: | ---: | ---: | ---: |
| Previous repair | 3.529 | 925 | 3,140 | 71 | 79.524 mm |
| Power 1.1 | 3.634 | 1,323 | 3,380 | 75 | 82.923 mm |
| Power 1.25 | 3.792 | 2,640 | 3,509 | 107 | 86.874 mm |
| Power 1.5 | 4.301 | 6,087 | 3,512 | 206 | 90.841 mm |
| Rational k=0.5 | 3.683 | 724 | 2,764 | 57 | 75.875 mm |
| Rational k=1 | 3.858 | 720 | 2,621 | 54 | 75.550 mm |
| Rational k=2 | 4.011 | 780 | 2,433 | 57 | 82.199 mm |

All power candidates are rejected. Rational k=0.5 is the bounded visual proof,
**not accepted as a replacement**. Larger values increase knee compression
and/or other absolute distortions. No additional parameter search is justified
by these results. Ordinary edges have rest length at least 1 mm; shorter bands
and the 59 zero-length source edges remain separately reported with undefined
ratios for the latter. The newly recomputed previous-repair count is 3,140,
rather than the historical report's 3,139; all table comparisons use this run's
same decoded-artifact evaluator. The historical evidence has not been rewritten.

| Region, bottom | Maximum before → candidate | Compressed edges before → candidate | Max absolute change before → candidate |
| --- | ---: | ---: | ---: |
| Torso/shoulders | 3.057 → 2.939 | 734 → 616 | 42.254 → 40.666 mm |
| Hips | 1.865 → 1.759 | 811 → 721 | 22.448 → 23.477 mm |
| Knee-crossing muscles | 2.068 → 1.940 | 791 → 762 | 37.373 → 40.257 mm |
| Arms | 3.529 → 3.683 | 290 → 206 | 79.524 → 75.875 mm |

Regional percentiles, worst-edge rest/posed lengths, and the full nine-pose
experiments are in `experiments.json`. The same candidate worsens isolated knee
flexion: compressed edges rise **679 → 784**, despite bottom-pose improvement.
Standing nearly collapsed triangles rise **16 → 17**; shoulder-plus-girdle
triangles rise **16 → 18**. These are reasons to reject aggregate-only approval.
Neutral, isolated hips, knees, shoulders, shoulder/girdle, torso, standing,
mid-descent and bottom all have metrics and spatial strain images.

At bottom, proper non-coplanar crossing pairs fall **61,977 → 61,525**; those
with >0.1 mm plane margin fall **44,795 → 43,881**. Standing raw pairs increase
**59,925 → 59,988**, while margin-qualified pairs decrease **43,529 → 43,309**.
The source already intersects at rest. Coplanar contacts, containment and
physiological sliding remain outside this test; these counts are not anatomical
certification. See [intersections.json](../outputs/heatsy-attachment/intersections.json).

## Native Blender precision investigation

The unchanged previous repair reproduces **10.0187 µm** maximum error against
the **10 µm** gate. A read-only independent review found that ideal double-
precision importer rebinding accounts for only **0.214 µm** across all vertices.
The native probe then measured intended versus actual rest matrices: thigh/shin
component discrepancies reach **2.46e-5**. Intended thigh singular values are
approximately 0.9999998; native thigh maximum singular value is **1.0000261**.
This confirms a small native rest-reconstruction non-rigidity distinct from
the source rig and centimetre-scale tearing. Its exact Blender internal
numerical cause is still unresolved.

Direct edit-matrix reassignment still fails at **10.0038 µm**. A compensated
180-degree thigh display-roll change fails at **10.1677 µm**. The tested
TEMPERANCE setting reproduces the original discrepancy. None is adopted.
No source bind, selected sample, tolerance, native evaluated vertex or installed
Blender file was altered. Probe scripts, logs and matrices are retained under
`outputs/heatsy-attachment/parity-*`; the reusable verifier records native
rest reconstruction without applying any correction.

Blender remains pinned to **4.5.11 LTS**, build `4db51e9d1e1e`, glTF importer
4.5.51. The existing guarded compatibility patch is reused. Context7 supplied
[Blender 4.5 EditBone documentation](https://docs.blender.org/api/4.5/bpy.types.EditBone.html)
and [NumPy SVD documentation](https://numpy.org/doc/stable/reference/generated/numpy.linalg.svd.html);
the pinned installed importer source is authoritative for its reconstruction.

## Visual proof and validation

Artifacts are under `outputs/heatsy-attachment/`:

- [Candidate GLB](../outputs/heatsy-attachment/heatsy-squat.glb),
  [front MP4](../outputs/heatsy-attachment/front.mp4),
  [side MP4](../outputs/heatsy-attachment/side.mp4).
- Matched standing/descent/bottom back, shoulder, hip and knee comparisons in
  `details/`; nine controlled strain maps and bottom joint axes.
- Full-pose and individual-muscle images, 320-pixel Quick Peek, decoded complete
  90-frame video contact sheets and poster.
- `validation.json`, `viewer.json`, `blender-parity.json`, `milestone.json`,
  `intersections.json`, `media.json`, `performance-profile.json` and stage logs.

The previous front/side proofs remain under `outputs/heatsy-repair/`; the older
broken animation remains under `outputs/heatsy-bodyweight/`. Every derivative
retains Heatsy / DDDEV LTD, Z-Anatomy and BodyParts3D attribution and CC BY-SA 4.0.
The MIT synthetic motion/code notice is retained separately.

Visual inspection of the matched detail images, strain map, 320-pixel capture
and both complete decoded contact sheets confirms continuous playback and
readable quadriceps highlighting. Back/shoulder sheets, hip folds and thin knee
attachments remain visibly unacceptable. Reduced aggregate counts are not a
visually convincing repair. Small muscle boundaries still need the detailed view.

| Check | Result |
| --- | --- |
| Unit suite | **PASS**, 69 tests, no skips; includes exact gradient-collapse and constant-weight cancellation regressions |
| glTF | **PASS**, zero errors, retained `NODE_SKINNED_MESH_NON_ROOT` warning only |
| Geometry, attributes, binds, motion and protected artifacts | **PASS**, all 1,071 protected files unchanged |
| Sampled motion/contact | **PASS**, 181 samples; loop error 0, ankle drift 0.322 mm, sole horizontal drift 0.311 mm, penetration 0.115 mm, lift 0.120 mm |
| Normal continuity | **PASS**, maximum step 1.094 degrees at 60 Hz |
| Browser | **PASS**, eight parity poses, 1,107 vertices per pose, 57 selection checks, playback/speed/pause/scrub/orbit checks and no page errors |
| Three.js/Python | **PASS**, maximum position component difference 0.173 µm; normal 4.56e-7, joint matrix 4.45e-7 |
| Native Blender/Python | **FAIL**, 10.0138 µm against unchanged 10 µm gate |
| Native Blender/Three.js | **FAIL**, 10.0290 µm against unchanged 10 µm gate |
| Media | **PASS**, both 640x640 MP4s decode all 90 frames at 30 fps; source-frame PSNR front 50.413 dB / side 49.877 dB |
| Deformation and overall result | **PARTIAL**, candidate not accepted, `technical_pass=false`, verifier exits **2** |

Performance was reprofiled independently on the candidate with MPFB as the
second model. Chromium **145.0.7632.6** used eight warmup frames and 48 timed
`requestAnimationFrame`/seek/render iterations per case; no screenshots/readback
occur inside the timed interval. Both mixers still update in the single-visible
model control. Highlight changes are separately timed and occur on selection,
not every frame. Production views have no shadows; full-vertex bounds work is
initialization-only, with no per-frame CPU skinning loop. The source viewer
rendering path was not optimized or decimated in this investigation.

| Case | SwiftShader median interval | Intel D3D11 median interval |
| --- | ---: | ---: |
| Dual detailed | 224.3 ms | 6.0 ms |
| Single detailed | 113.2 ms | 4.2 ms |
| Single 320 px | 94.0 ms | 4.2 ms |
| Single unlit | 69.6 ms | 4.2 ms |
| Single rigid-shader control | 91.8 ms | 4.2 ms |
| Empty scene control | 16.7 ms | 4.2 ms |
| Dual without preserved drawing buffer | 174.8 ms | 5.0 ms |

Software renderer: ANGLE Vulkan / SwiftShader Device (Subzero). Hardware:
ANGLE Intel UHD Graphics `0x00009BC4` / Direct3D11, Playwright Chromium channel
with `--use-angle=d3d11`. Dual p95 intervals are **266.8 / 9.7 ms**; median CPU
submission is **1.0 / 1.0 ms**. Median selection update plus submission is
**7.8 / 2.9 ms**. These results reproduce the software-rendering explanation for
the earlier 4.5–5.4 FPS measurement. Lighting, multiple models, resolution and
skinning contribute to software cost. Headless intervals are **not displayed
device FPS**, and no mobile/device performance approval is claimed.

## Changed implementation and next milestone

New: `studio/heatsy_attachment.py`, `studio/heatsy_attachment_verify.py`,
`studio/heatsy_attachment_capture.mjs`, `tests/test_heatsy_attachment.py`.
Extended: `studio/heatsy-squat/viewer.js` with one allowlisted experimental
route; `studio/heatsy_repair_profile.mjs` with optional output/query parameters.
The existing retargeter, static importer, canonical MPFB path and acceptance
thresholds are unchanged. Knowledge-board, next-slice and architecture notes
link this result rather than duplicating its numerical tables.

**Recommended next milestone:** explicitly model a small set of anatomical
attachment constraints and establish portable corrective feasibility against
these isolated poses. Further global influence smoothing/sharpening is not
supported. Any pose-driven corrective must survive standard GLB export and
improve attachment shape, compression and intersections without hiding another
failure. If that requires extensive hand-painted weights or a rig redesign,
make that model/rig decision explicitly before proceeding. Keep native Blender
reconstruction work independent. Anatomy, movement and public use remain
unapproved; no additional exercise, editor or Flutter work is justified.
