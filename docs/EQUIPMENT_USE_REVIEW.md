# Experimental MPFB dumbbell goblet squat

This proof is independent of unresolved Heatsy deformation. It demonstrates
equipment inspection, a variation-specific character/equipment relationship and
separate guidance/preview presentation. It is **not approved exercise instruction**.
MPFB's existing painted muscle regions are approximate editorial highlights,
not isolated anatomical muscle geometry or activation measurements.

**Technical PASS; visual PARTIAL; movement and human approval UNAPPROVED.**
The requested three-level flow is functional. The finger contours remain coarse
and need visual refinement; the vertical two-hand shaft grip is a technical
fixture, not a certified goblet-squat technique.

## Inspect locally

Serve the repository using `python -m http.server 8765 --bind 127.0.0.1`, or reuse
an existing local server. Open [equipment catalog](http://127.0.0.1:8765/studio/equipment/).
Choose the dumbbell, rotate it, inspect its configuration and contact locations,
then choose the experimental goblet squat. Setup, front/side cameras, orbit and
playback expose the hold and the complete repetition. The standalone inspection
configuration is separate from the fixed demonstration configuration.

The [lightweight preview](http://127.0.0.1:8765/studio/equipment/preview.html)
is a video-only page: no Three.js module or anatomical GLB is required.

## Independent components

See [equipment-use architecture](architecture/EQUIPMENT-USE.md) for ownership
and future machine constraints. Equipment geometry/contact metadata, the source
squat, goblet posture/attachment recipe and instructional overlays are separate.
Changing exercise does not inherently require regenerating equipment geometry.
Changing an implement or its dimensions does require a compatible variation and
new reach/contact validation; it does not imply the same technique.

This proof begins from the standing held setup. It does not synthesize a pickup
from the floor. Future cables, leg presses, benches and Smith machines need
explicit moving components, support contacts and synchronized kinematic
relationships; no general machine physics engine is implemented here.

## Provenance and preservation

Implementation starts from `bd93190ccd1bb8f6f755119b175b6a5d70a7a18a`, on
`codex/equipment-use-proof`. The existing synthetic squat, MPFB character and
procedural dumbbell generator are reused. Original bodyweight and Heatsy outputs
remain in place. `outputs/equipment-use/protected.json` records 1,139 protected
files from those baselines and source motion before the experiment.

Generated artifacts live only in `outputs/equipment-use/`; they are not committed
or published. Existing unrelated user changes are preserved. MPFB/MakeHuman core
assets are CC0; the MPFB add-on license is separate, and OpenGym-derived code
retains its MIT notice. No Heatsy geometry is used in this proof.

## Reproduce

Use the existing prepared Python/NumPy, Node dependencies, pinned Blender 4.5.11,
Playwright Chromium and FFmpeg/ffprobe installation:

```powershell
Set-Location C:\ws_c\ForgedMotionStudio
$env:PLAYWRIGHT_BROWSERS_PATH='C:/Users/Cornw/AppData/Local/ms-playwright'
python studio/equipment_build.py
```

The isolated orchestrator runs generation, exported-mesh contact validation,
hand-to-hand surface checks, glTF validation, joint QA, unit tests, actual-browser
capture, video encoding, video-only-page checks and independent node parity.
Exit 0 means the selected technical checks pass; human/movement approval stays
absent. Exit 2 preserves an unresolved contact/intersection limitation; unexpected
pipeline errors exit 1 and invalidate the previous milestone status.

The standalone equipment asset is cached by generator and asset hashes. A new
variation can reuse that asset. The generator does not create another anatomy
model or modify the MPFB source. The animated proof explicitly reposes arms,
wrists and fingers, while retaining source lower-body joint motion and the full
three-second cycle. Inspection contact sites are nominal surface points, not a
claim of exact human anatomical anchors.

## Validation scope

The contact validator independently evaluates the decoded exported GLB at 181
times, including off-key samples. It measures actual weighted hand vertices
against the known procedural handle/head surfaces, not just markers attached to
the same transform. Signed-distance checks use the actual generator's cylinder
dimensions; circular head envelopes conservatively enclose the polygonal mesh.
Handle gap must stay below 5 mm, hand and nonhand penetration below 3 mm. Wrist
direction must remain transverse to the shaft; the measured palm plane uses
wrist/index/pinky landmarks and the palm midpoint. Equipment/chest relative
transforms, mesh loop closure and source lower-body joint agreement are checked
independently. Thresholds are engineering tolerances, not exercise approval.

Additional BVH candidate pairs and exact segment/triangle tests examine opposing
hand surfaces at standing, mid-descent and bottom. Shared-edge touches and
coplanar contacts are excluded; crossings with >0.1 mm plane margin are retained.
Vertex-distance tests alone cannot certify absence of triangle-only collisions,
and this is not exhaustive full-body self-collision or a physical grip-force
simulation. The model begins already holding the implement; no pickup is claimed.

Browser parity requires equipment, wrists, finger landmarks and feet at named
poses and off-key phases, rejecting nonfinite coordinates and missing samples.
Reports are tied to artifact hashes. Quick Peek tests check actual 320x320 video
dimensions, playback and looping, and reject any GLB/Three.js network request.

## Executed results

The complete `python studio/equipment_build.py` run exited 0; finalization retained
the separate visual limitation. A repeated build produced the same animated GLB
SHA-256 `bc437c52ac000263e96af13816075b63ef4caf6c12512bbcb95c4c58f021e077`.
Standalone geometry SHA-256 is
`eadc1cd47bead9993cce7cee306a25cd92653b418ad7ff4760c636720295ae4d`.
Blender 4.5.11, Three.js 0.170.0 and Chromium 145.0.7632.6 were used.

| Check | Observed result |
| --- | --- |
| Unit suite | 77 tests PASS, no skips |
| Both GLBs | Zero glTF errors; animated GLB retains one skinned-non-root hierarchy warning |
| Existing joint QA | PASS, 46 samples over 3 seconds; separate from contact acceptance |
| Actual hand-to-handle gap, 181 poses | Maximum 0.0364 mm; gate 5 mm |
| Hand/equipment penetration | Maximum 1.7012 mm; gate 3 mm |
| Nonhand body/equipment vertex penetration | 0 mm in sampled analytic-envelope test |
| Opposing hand surfaces | Zero proper crossings at standing, mid-descent and bottom |
| Wrist direction relative shaft | Minimum 86.423 degrees, transverse rather than aligned along the shaft |
| Palm plane alignment | Minimum absolute dot 0.99666 with inward direction from measured palm center |
| Equipment/chest stability | Maximum relative matrix component difference 1.0034e-5 |
| Mesh loop seam | 0 m |
| Source lower-body joint agreement | Maximum component difference1.281 micrometres after source-time-offset correction |
| Browser/Python exported-node parity | 2,132 comparisons, maximum 0.144 micrometres, including equipment and off-key poses |
| Catalog/UI | Selection, standalone orbit/configuration, demo playback/scrub/orbit, setup/grip cameras and guidance toggles PASS |
| Media | Front/side 640x640, 90 frames at 30 fps, 3 seconds; decoded source-frame PSNR 51.077/51.400 dB |
| Lightweight preview | Actual 320x320 front/side videos, 39,608/37,104 bytes; playback/loop/no 3D-asset network checks PASS |
| Preserved baselines | 1,139 protected files byte-identical |

Initial investigation caught and corrected the wrong assumed MPFB palm axis,
finger paths aimed at the wrist rather than the shaft, deep thumb-web penetration
and opposing-hand interleaving. Corrections use the measured knuckle plane,
bone-length-preserving reach and bounded finger poses. No mesh/weight edits or
equipment resizing were used to hide these failures. Tests include the actual
palm-plane regression and rejection of unreachable hand targets.

Complete side/front decoded contact sheets and final grip screenshots were
visually inspected. Equipment travels with the held posture through descent,
bottom and ascent. The bodyweight arms-forward posture is visibly replaced by
bent elbows and the vertical hold. The coarse thumb/finger silhouette is retained
as a visible limitation, not marked visually approved.

## Artifacts and implementation

- [Animated GLB](../outputs/equipment-use/goblet.glb) and [standalone dumbbell](../outputs/equipment-use/dumbbell.glb).
- [Front MP4](../outputs/equipment-use/front.mp4), [side MP4](../outputs/equipment-use/side.mp4), [320px side loop](../outputs/equipment-use/quick-peek.mp4).
- [Grip detail](../outputs/equipment-use/grip-detail.png), [inspection](../outputs/equipment-use/inspection.png), [Quick Peek](../outputs/equipment-use/quick-peek.png).
- [Final statuses](../outputs/equipment-use/milestone.json), [contact report](../outputs/equipment-use/contact-validation.json), [integration](../outputs/equipment-use/integration.json), [media](../outputs/equipment-use/media.json).

New implementation: `studio/goblet_build.py`, `goblet_validate.py`,
`equipment_build.py`, `equipment_capture.mjs`, `equipment_media.py`,
`equipment_verify.py`, and `studio/equipment/{index.html,style.css,viewer.js,preview.html}`.
Tests: `tests/test_goblet.py`, `tests/test_equipment_validation.py`.
The existing Studio landing page links the catalog. Architecture/work notes
record the independent scope. The original pipelines and all Heatsy code are unchanged.

Next milestone: refine the MPFB finger/hand silhouette and review the specific
two-hand grip and squat movement before any instructional approval or broader
equipment technique catalog. Machine contacts and movable components remain
documented future capabilities, not implemented physics.
