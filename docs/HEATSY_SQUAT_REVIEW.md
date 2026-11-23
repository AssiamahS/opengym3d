# First animated Heatsy squat: deformation blocked

The diagnostic animation is built, but it is **not ready for movement or anatomy approval**. Technical preservation and playback checks pass. Severe upper-body stretching fails the deformation gate. Work stops here without editing skin weights, repairing topology, changing the synthetic motion, or publishing anything.

## Review locally

With the repository HTTP server running, open:

http://127.0.0.1:8765/studio/heatsy-squat/

The left panel is the unchanged MPFB baseline; the right panel is the diagnostic Heatsy animation. Playback and scrubbing synchronize normalized phase: the existing MPFB clip lasts 3.033333 seconds and the new Heatsy clip lasts 3 seconds. Neither source clip is rewritten for synchronization. Orbit, front/side/three-quarter/rear views, speed, and actual model-ID muscle highlighting are available. A visible failure banner distinguishes this diagnostic from an approved result.

All new outputs are under `outputs/heatsy-squat/`:

- `heatsy-squat.glb`: the single animated candidate.
- `front.mp4`, `side.mp4`: 640 x 640, 30 fps, 90 frames, 3-second diagnostic loops. Looping is a player setting.
- `poster.png`: bottom-pose three-quarter image.
- `poses/{standing,descent,bottom,ascent,return}-{front,side,three}.png`: synchronized comparisons.
- `poses/{descent,bottom,ascent}-normals.png`: normal-direction shading checks.
- `poses/{standing,descent,bottom,ascent}-latissimus-detail.png`: highlighted failure region.
- `poses/bottom-{quads-L,quads-R,glutes-L,glutes-R}.png`: separate left/right selections.
- `front-decoded-all-frames.png`, `side-decoded-all-frames.png`: all decoded video frames.
- `milestone.json`, `validation.json`, `preservation.json`, `animated-parity.json`, `deformation-diagnosis.json`, `viewer.json`, `media.json`, `provenance.json`: machine-readable evidence.
- `LICENSE`, `NOTICE.md`, `IMPORTER-NOTICE.md`, `MOTION-CODE-MIT.txt`, `DERIVATION.md`: accompanying attribution and license notices.

There are 26 comparison/diagnosis screenshots plus the poster. Gluteus minimus and vastus intermedius still have no corresponding geometry; no replacement geometry or invented IDs were added. Selection checks cover 19 options at descent, bottom and ascent, including the diagnostic latissimus selections.

## Exact failure and focused diagnosis

The same right latissimus dorsi edge fails at every representative pose. Both endpoints have actual `_PART_ID=58`. The exported vertex records are 51179 and 51848; the existing verified correspondence maps them to original source records 51164 and 51833. Its rest length is 1.407101 mm.

| Pose | Time (s) | Deformed edge (mm) | Rest-length multiple |
| --- | ---: | ---: | ---: |
| Standing, arms forward | 0 | 38.776169 | 27.5575 |
| Descent | 0.75 | 43.063984 | 30.6047 |
| Bottom | 1.5 | 46.840740 | 33.2888 |
| Ascent | 2.25 | 43.063984 | 30.6047 |
| Return | 3 | 38.776169 | 27.5575 |

See `poses/bottom-latissimus-detail.png`. At the bottom pose, 19,595 measured edges exceed twice their rest length. Measurements exclude rest edges shorter than 1 mm, so this finding does not depend on tiny or degenerate source triangles.

The preserved weights differ sharply across this edge: upperarm.R contributes 0.623529 and 0.843137; spine_02 contributes 0.258824 and 0.113725. The remaining influences are spine_03 and scapula.R. A diagnostic ablation removing clavicle/scapula follow still stretches the bottom edge to 44.797069 mm. A control retaining pelvis and leg motion while leaving the upper body at rest retains its 1.407102 mm length. These controls are evaluated in memory; no alternate animation assets are delivered.

The evidence points to the existing weight transition under the required arm elevation as the dominant cause for this region. It does not establish a general rig diagnosis or prove that all shoulder rotation/twist choices are anatomically correct. The current direction-only source supplies no independent forearm pronation target; the visible hand orientation also remains unapproved. Resolving the distortion would require a separately scoped shoulder/skin-deformation investigation. No weight edits, corrective shapes, pose-specific motion changes, or general mesh repair were attempted.

The static metre baseline has 116 near-zero-area triangles at the recorded 1e-12 square-metre threshold (the original quantized source report counted 131 before representation rounding). These documented limitations remain separate from the new pose-induced stretching. No triangles with rest area above 1e-10 square metres fall below 1e-12 at the five measured poses, although some triangles lose substantial area; this does not make the deformation acceptable.

## Implementation and preservation

The target-specific adapter reuses `pipeline.motion` and `pipeline.qa_glb.Clip`. It reads the unchanged 91-frame, 30 fps synthetic squat. Absolute thigh/shin and arm/hand directions are calibrated to Heatsy's rest directions; spine and foot direction deltas preserve their target rest calibration. The existing small shoulder-girdle-follow policy is applied to Heatsy's clavicles and scapulae. Other joints retain their local rest transforms. Root travel is scaled by target/source leg length (0.9258082099678989), with one measured constant standing-floor offset applied to pelvis throughout the clip. There is no per-frame floor clamp, foot IK, or source-motion edit.

Preparation copies the audited raw Blender export into the new output directory and reruns the existing explicit normal-restoration stage. Its restored GLB must be byte-identical to the verified static Heatsy export. Animation accessors/channels are then appended while preserving the entire static binary prefix and all original node, mesh, skin, material and accessor definitions. This avoids another importer/exporter representation conversion.

- 79,674 vertex records, including the existing 16 valid representation splits; 149,030 triangles; 56 skin joints.
- Existing correspondence/oriented-triangle checks pass, with zero additional splits and zero attribute, position or weight difference from the preserved static asset. Byte-preservation checks are additional evidence, not a substitute for correspondence checks.
- `_PART_ID` remains FLOAT32 with exact integer IDs; `_FIBER` and `_TENDON` remain decoded FLOAT32 with `normalized=false`. Their stored values are unchanged. Fiber vectors are neither decoded again nor unit-normalized.
- Positions remain metres. The original 0.0001 quantization scale is not reapplied. Rest transforms, inverse binds, indices, joint order and weights are unchanged.
- Rest normals are restored before animation, then transformed during playback using the existing skinning behavior. Normal direction images and shaded descent/bottom/ascent screenshots are retained. Continuity/parity passes do not certify shading over the visibly distorted geometry as anatomically correct.

## Technical results and hierarchy warning

The full existing unit suite passes: **59 tests**, including six focused animation/preservation regressions. Existing static Heatsy fixture coverage remains in that suite. All 137 protected inputs/baseline files retain their hashes, including all 38 canonical MPFB deliverables and the static Heatsy bundle. This milestone does not rebuild or overwrite those baseline outputs.

The exported animation is evaluated at 181 times over the complete interval (60 Hz):

| Check | Result |
| --- | ---: |
| Mesh loop closure error | 0 m |
| Maximum foot-joint displacement | 0.322 mm |
| Maximum skin-floor penetration | 0.116 mm |
| Maximum sampled normal change per 1/60 second | 1.095 degrees or less |
| Maximum source/target limb-direction error at 91 keys | 0.000782 degrees |
| Bottom knee interior angle | 71.3596 degrees, both sides |
| Maximum adjacent quaternion step | 3.8574 degrees |

Khronos validation reports zero errors and the retained `NODE_SKINNED_MESH_NON_ROOT` warning. It is reevaluated against this animation: `body_rig` and the skinned mesh remain static identity transforms, and pelvis alone carries root translation. No parent transform is animated or rescaled. Three.js deformed vertex positions, transformed normals and all 56 joint world matrices are compared with independent Python FK/LBS at five named poses and three off-key phases (0.123, 0.337, 0.611). The acceptance tolerance is 1e-5 m for positions and 1e-5 for normal/matrix components, allowing float32 browser arithmetic while detecting material parent/root errors. Exact observed maxima are in `animated-parity.json`. The warning is retained, not suppressed; this demonstrates behavior in the exported local viewer, not in every glTF consumer.

Observed browser parity across 1,107 vertices per pose: maximum position component error 1.55803e-7 m (0.000156 mm), normal component error 4.55547e-7 and joint matrix component error 4.45179e-7. These include off-key interpolation.

Playback, scrub, synchronized orbit and 57 muscle-selection checks pass. Videos are decoded and compared against all renderer frames; front/side PSNR exceeds 49 dB against a 35 dB gate. The decoded full-loop contact sheets and shaded/normal-direction pose images were visually inspected: they show the squat cycle and persistent upper-body distortion, without a sampled normal-flip discontinuity. These are technical checks, separate from the failed deformation gate and from movement/anatomical approval. `milestone.json` must say `BLOCKED_DEFORMATION`, `technical_pass=true`, `review_ready=false`; all approval flags remain false.

## Reproduction

Use the existing repository environment with Python/NumPy, Node dependencies/Playwright Chromium and FFmpeg/ffprobe already installed for the static and MPFB milestones. The verified static bundle and source checkout must be present.

```powershell
Set-Location C:\ws_c\ForgedMotionStudio
python studio/heatsy_squat_build.py
```

**Expected exit code: 2**, indicating that diagnostic outputs and technical checks completed but deformation is blocked. A technical exception produces `FAIL` and a different nonzero exit. The build runs preparation/normal restoration, retargeting, correspondence and animation validation, focused diagnosis, the complete test suite, Khronos validation, browser capture, encoding and final evidence checks. Per-stage logs are saved under the new output directory.

To serve the viewer, reuse the running server, or start one if needed:

```powershell
python -m http.server 8765 --bind 127.0.0.1
```

To rerun focused evidence without regenerating the GLB:

```powershell
python studio/heatsy_squat_validate.py
python studio/heatsy_squat_diagnose.py
python -m unittest discover -s tests -v
node studio/validate_gltf.mjs outputs/heatsy-squat/heatsy-squat.glb
node studio/heatsy_squat_capture.mjs
python studio/heatsy_squat_media.py
python studio/heatsy_squat_finish.py
```

The full build is the authoritative reproducible path because it also captures test logs and baseline hashes. No manual global Blender edits are used. The pinned, process-local importer fix remains in the untouched static route; this animation starts from its verified output.

## Files added or changed for this milestone

Added:

- `studio/heatsy_squat.py`: target retarget adapter and independent deformation sampling.
- `studio/heatsy_squat_prepare.py`: isolated preparation, normal restoration and notices.
- `studio/heatsy_squat_validate.py`: preservation, hierarchy and whole-interval measurements.
- `studio/heatsy_squat_diagnose.py`: focused failure evidence and ablations.
- `studio/heatsy_squat_capture.mjs`: viewer checks and captures.
- `studio/heatsy_squat_media.py`: encoding and decoded-video verification.
- `studio/heatsy_squat_finish.py`: final hash/parity gates and explicit blocked status.
- `studio/heatsy_squat_build.py`: bounded reproduction command.
- `studio/heatsy-squat/index.html`, `studio/heatsy-squat/viewer.js`: synchronized diagnostic viewer.
- `tests/test_heatsy_squat.py`: focused regression coverage.
- `docs/HEATSY_SQUAT_REVIEW.md`: this handoff, copied to the output bundle.

Changed: `studio/README.md` adds the diagnostic entry point. Existing dirty-worktree files from earlier milestones were preserved. Generated files are isolated under `outputs/heatsy-squat/` and remain gitignored.

## Provenance and remaining boundaries

Heatsy source commit: `6cf6a0ae7c63bcffca1137ddcec14a31b7254a6d`.
Original GLB SHA-256: `ce9859de013c2ee9713dbe3158275208b57be1b4ff31957eca87195b991c0ab1`.
Preserved static GLB: `fb093c017518b139ec8ee77c9e912977499d6466e75367c11f82bb999c125933`.
Unchanged synthetic motion: `8707ffd2547de40629f193c9667136485ba51a59b99b9212a44bcefb47c13ad9`.
Animated GLB: `d9c0a0f5ac058abb0cc41a053f56e8bee090b99e62e360c3178602ecac0f4f00`.

Heatsy attribution and CC BY-SA 4.0 notices accompany the derived animation and images; synthetic motion/code MIT notices are also retained. The original and static assets remain unchanged. Nothing was published or modified in ForgedAndSentFitness. Animation quality, anatomical accuracy, movement accuracy and public readiness remain unapproved. No weighted variations, general editor, new motion ingestion, cloud service, Flutter integration or general mesh repair were added.
