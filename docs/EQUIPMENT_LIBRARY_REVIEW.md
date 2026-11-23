# Equipment library and bounded grip refinement

2026-11-23 · continuation of `ad14fa7ebbf16f692ca14312b3a1d19323985bfe`
on local branch `codex/equipment-library-grip`.
Tested implementation commit: `6c9a4a568dbf1ac18de14cdc8944c3312a3ac142`.

**Technical PASS. Visual PARTIAL. Movement and human approval UNAPPROVED.**
The three-item equipment catalog and existing MPFB goblet interaction work together.
Finger contours improved; thumb placement/web deformation remains unresolved.
This is an experimental technical demonstration, not approved exercise instruction.
The Heatsy deformation milestone remains independent and unchanged.

## What changed

The existing procedural dumbbell, kettlebell and barbell now have standalone
GLBs, 320×240 WebP thumbnails, measured dimensions, inspection configuration,
nominal handle targets, explicit compatible variation IDs and MIT provenance.
The gallery loads thumbnails without requesting any GLB. Selecting an item loads
its static asset; only the dumbbell offers the experimental goblet demonstration.
Changing equipment does not build, modify or imply a new exercise technique.

The existing viewer now bounds ownership to two cached assets and one active
animation mixer. Superseded loads, evictions and page teardown release their
resources, including a model that finishes loading after teardown. Framing adapts
to each implement. The separate Quick Peek page remains video-only.

The grip correction preserves inherited wrist/finger roll and bounds each aiming
step for fingers two through five to 90°/85°/65°. These are procedural swing
bounds, **not certified anatomical joint limits**. Thumb matrices, palm anchors,
equipment dimensions, mesh proportions, skin weights, bind matrices and the
remaining motion stay unchanged. The adapter records the selected recipe in the
variation metadata rather than relying on an undocumented pose substitution.

Architecture: [equipment components and lifecycle](architecture/EQUIPMENT-USE.md).
The original proof remains documented in [EQUIPMENT_USE_REVIEW](EQUIPMENT_USE_REVIEW.md).

## Baseline evaluation and grip decisions

Before editing the pose, the checkpoint contact validator reproduced PASS at 181
samples, the opposing-hand check found zero crossings at three poses, both GLBs
passed glTF validation, joint QA passed and all 77 existing tests passed. Its 2,132
preserved browser-node samples were re-evaluated against the unchanged GLB, with
maximum component error 0.144 µm. The actual grip screenshot and decoded MP4
contact sheet showed pointed knuckles, abrupt folded finger segments and pinched
thumb webs, while the implement remained synchronized with the squat.

The investigation identified two pose defects: aiming from world rest axes lost
the wrist's inherited roll, and circular targeting could nearly reverse phalanges.
Correcting fingers improved the same unchanged mesh; hand proportion changes or
a character remodel were not needed for that improvement. The remaining thumb
web is strongly coupled to metacarpal and thumb weights. One failing web vertex
had approximately 62% metacarpal, 23% middle-thumb and 15% proximal-thumb influence.
This does not prove that MPFB cannot produce a convincing grip; it establishes a
limitation of this bounded pose correction with the existing mesh and skinning.

| Controlled candidate | Contact result | Decision |
| --- | --- | --- |
| Preserve inherited roll on every digit | 6.627 mm penetration; FAIL | Reject; visible pinching also remains |
| Preserve roll and bound every digit | 8.657 mm penetration; FAIL | Reject despite smoother finger contours |
| Bound fingers two–five; retain baseline thumbs | 2.392 mm penetration; PASS | Selected |
| Selected fingers plus 10% thumb correction, capped at 5° per segment | 2.392 mm penetration; PASS | Reject: no convincing visible thumb benefit; one distortion count worsens |

The selected pose reduces finger-region edges exceeding twice their rest length
from **584 to 95**, and triangles below one tenth of rest area from **458 to 38**.
These are exported standing-mesh diagnostics, not physiological strain or anatomy
approval. Edges shorter than 0.5 mm and effectively zero-area rest triangles are
excluded. Thumb deformation is not claimed to improve.

The final browser images were inspected at detail size and 320-pixel width. Fingers
are less folded and their contour is more continuous. Residual thumb-web pinching,
coarse palm shape and small protrusions remain visible. The selected candidate
and final rebuild produce the same GLB hash. Rejected artifacts and measurements
remain under `outputs/equipment-library/grip-experiments/`; the decision record is
[grip-review.json](../outputs/equipment-library/grip-review.json).

## Executed validation

The complete `python studio/equipment_build.py` pipeline exited **0**.
No contact tolerance was loosened. Independent source review identified and
corrected output-path protection and stale catalog-report gaps before the final
run. Final read-only review found no high-confidence defects; it did not confer
visual or movement approval.

| Check | Final observed result |
| --- | --- |
| Unit suite | **90 PASS**, no skips; 27.336 s test runtime |
| Four GLBs | Zero glTF errors; static GLBs have zero warnings; animated GLB retains the documented skinned-non-root warning |
| Joint QA | PASS, 46 samples across 3 seconds |
| Exported contact | PASS at 181 poses; maximum shaft gap 0.0364 mm, gate 5 mm |
| Hand/equipment penetration | 2.3921 mm maximum, unchanged 3 mm gate; baseline was 1.7012 mm |
| Other body/equipment vertex penetration | 0 mm in the sampled analytic-envelope test |
| Opposing hands | Zero proper crossings at standing, mid-descent and bottom |
| Synchronization | Relative chest/equipment matrix-component drift 1.0034e-5; mesh loop seam 0 m |
| Grip orientation | Minimum wrist/shaft angle 86.423°; minimum palm-plane alignment 0.99666 |
| Pose-only preservation | Rest positions, normals, topology, weights, joint indices and inverse binds identical; 401 non-finger tracks unchanged within 1e-7 |
| Source lower body | Maximum position-component difference 1.281 µm |
| Browser/export parity | 2,132 node comparisons; maximum component difference 0.144 µm |
| Catalog | Three standalone static assets; decoded bounds/dimensions, analytic handle targets, hashes and license files pass |
| Resource lifecycle | Four full selection cycles stable at 8 geometries, 1 texture, 4 programs; at most 2 cached assets and 1 mixer |
| Teardown | Zero cached assets, mixers, geometries, textures and programs; late in-flight load also disposed |
| Raster regression | 9,628 changed detailed pixels and 1,387 changed 320px pixels, **zero outside the fixed grip region** |
| Media | Front/side 640×640, 90 frames, 30 fps, 3 s; decoded-source PSNR 50.990/51.304 dB |
| Quick Peek | Front/side 320×320 decode and loop; no GLB or Three.js requests |
| Preservation | All **1,139** protected baseline files and **243** checkpoint equipment files byte-identical |

The raster test localizes the change; it does not certify that the hand looks
correct. Unit regressions reject inherited-roll loss, unbounded reversals, mesh
or unrelated-motion changes, missing/stale catalog evidence, illegal output paths,
unreviewed equipment substitution and invalid dimensions/contact coordinates.
Browser checks exercise gallery selection, independent orbit/configuration,
goblet setup/play/pause/scrub/orbit, actual Quick Peek navigation, browser back,
and selection of a different implement without changing the goblet file.

Collision scope remains the original one: body vertices against analytic
generator envelopes at 181 poses, plus opposing-hand triangle crossings at three
poses. This is not exhaustive triangle-only equipment collision, all-body
self-collision or physical grip-force validation.

## Performance and asset sizes

Measurements are local Chromium 145.0.7632.6 with ANGLE/D3D11 on the NVIDIA RTX
2070 Max-Q. Cold gallery readiness was **452.3 ms**, transferring **1,527,915 bytes**
including the Three.js modules, and requesting **zero GLBs**. The 3 thumbnails
total **3,902 bytes**. The gallery still loads its 3D JavaScript module at startup;
only the detailed model assets are deferred.

| Asset | Static GLB bytes | Thumbnail bytes | Selection/setup measurement |
| --- | ---: | ---: | --- |
| Dumbbell | 17,688 | 1,458 | 2.9 ms, cache hit |
| Kettlebell | 44,192 | 1,414 | 18.9 ms, uncached |
| Barbell | 27,992 | 1,030 | 18.1 ms, uncached |

Selection times cover parsing, scene setup and first render submission, excluding
GPU completion. After eight warmup frames, 60 headless frame intervals measured
**16.7 ms median / 16.9 ms p95**. These are not displayed-device FPS or mobile
performance claims. Whole pipeline stages total **171.4 s** on this
run, including 70.8 s goblet build, 17.7 s contact validation, 29.3 s unit-test
process, 24.5 s frame capture and 8.3 s catalog browser checks.

The standalone catalog command took 4.28 s including thumbnail renders and reused
all three GLBs. Its implementation never invokes the exercise builder. Final
front/side videos are 144,069/137,367 bytes; Quick Peek front/side files are
39,393/37,839 bytes.

## Open and reproduce

The existing local server was checked successfully at port 8765:

- [Equipment gallery](http://127.0.0.1:8765/studio/equipment/)
- [Goblet demonstration](http://127.0.0.1:8765/studio/equipment/?demo)
- [Video-only Quick Peek](http://127.0.0.1:8765/studio/equipment/preview.html)
- [Preserved checkpoint demonstration](http://127.0.0.1:8765/studio/equipment/?baseline&demo)

Full rebuild uses the existing prepared toolchain and checkpoint assets:

```powershell
Set-Location C:\ws_c\ForgedMotionStudio
$env:PLAYWRIGHT_BROWSERS_PATH='C:/Users/Cornw/AppData/Local/ms-playwright'
python studio/equipment_build.py
python -m unittest discover -s tests -v
# Reuse the existing server, or start one when port 8765 is free:
python -m http.server 8765 --bind 127.0.0.1
```

Standalone catalog regeneration and checks, without building an exercise:

```powershell
& .\work\toolchain\blender-4.5.11-windows-x64\blender.exe -b --factory-startup --python-exit-code 1 -P studio/equipment_catalog.py
foreach ($item in 'dumbbell','kettlebell','barbell') {
    node studio/validate_gltf.mjs "outputs/equipment-library/$item.glb"
}
python studio/equipment_catalog_validate.py
```

Continuation writes are guarded to `outputs/equipment-library/`. `FMS_EQUIPMENT_OUTPUT`
can select a child directory for individual investigative scripts, but cannot
target the preserved proof or other baselines. The full browser pipeline uses
the standard library directory. The legacy and rejected grip modes are explicit
reproduction options for investigation; the default is `bounded-fingers`.

Tool revisions: Blender **4.5.11 LTS / 4db51e9d1e1e**, Three.js **0.170.0**,
Playwright **1.58.2**, glTF validator **2.0.0-dev.3.10**, NumPy **2.3.5**, Pillow
**11.3.0**. Procedural source SHA-256:
`14640189bbeebd649c5d6ac8a1805c0dedc6a4bb70d1f206c179374febad9033`.
MPFB input SHA-256:
`d5338f85672114c0b0d40dfb07f4249009e8e97990800dd657775594dfc43ca7`.
Final goblet SHA-256:
`98785f00eb2a925a945b8538cf513bf62268097a885fa8f7304233a9264fd6da`.
The standalone dumbbell is byte-identical to the checkpoint.

## Review artifacts

- Grip detail: [before](../outputs/equipment-library/grip-before.png) · [after](../outputs/equipment-library/grip-after.png).
- Grip at 320px: [before](../outputs/equipment-library/grip-before-320.png) · [after](../outputs/equipment-library/grip-after-320.png). The screenshot wrapper adds a one-pixel border; video media is exactly 320×320.
- Gallery screenshots: [overview](../outputs/equipment-library/gallery.png) · [dumbbell](../outputs/equipment-library/catalog-dumbbell.png) · [kettlebell](../outputs/equipment-library/catalog-kettlebell.png) · [barbell](../outputs/equipment-library/catalog-barbell.png).
- [Animated goblet GLB](../outputs/equipment-library/goblet.glb), [front MP4](../outputs/equipment-library/front.mp4), [side MP4](../outputs/equipment-library/side.mp4), [320px loop](../outputs/equipment-library/quick-peek.mp4).
- Standalone GLBs: [dumbbell](../outputs/equipment-library/dumbbell.glb) · [kettlebell](../outputs/equipment-library/kettlebell.glb) · [barbell](../outputs/equipment-library/barbell.glb).
- Evidence: [milestone](../outputs/equipment-library/milestone.json) · [contacts](../outputs/equipment-library/contact-validation.json) · [catalog/browser/performance](../outputs/equipment-library/catalog-check.json) · [raster regression](../outputs/equipment-library/visual-regression.json) · [integration](../outputs/equipment-library/integration.json) · [media](../outputs/equipment-library/media.json) · [timings](../outputs/equipment-library/timings.json).

## Remaining limitations and next milestone

Thumb-web pinching and coarse hand shape remain; the thumb correction was not
promoted. The two-hand shaft hold is a technical fixture, not a certified goblet
technique. This begins already holding the implement and does not demonstrate a
pickup. MPFB muscle colors are approximate editorial regions, not separated
anatomical geometry or activation measurements. Kettlebell and barbell have no
implemented or approved exercise variations. Inspection scale/finish has no
validated load or technique meaning. The retained glTF hierarchy warning requires
separate validation in other consumers. Heatsy deformation remains unresolved.

The next recommended milestone is a focused thumb/opposition and web-skinning
investigation with representative hand references and human review, preserving
the current contact and deformation baselines. Review the specific grip and squat
before considering instructional use or another equipment technique. Cables,
moving carriages, benches, Smith-machine constraints and general machine physics
remain future capabilities, as documented in the architecture.

The requested delegation policy was followed with bounded independent ownership
for grip investigation, catalog UI and read-only review, and coordinator-owned
integration and validation. No reliable cheaper-model capability/price comparison
was available for these geometry/lifecycle tasks, so inherited strong models were
used without a cost-saving claim. No push, merge, deployment or publication was
performed; generated artifacts remain ignored local outputs.
