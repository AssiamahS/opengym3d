# Heatsy static compatibility and appearance proof

This bounded milestone stays in ForgedMotionStudio. The synthetic MPFB squat
remains the working technical baseline; its movement, anatomy and public
readiness remain unapproved. No publication, retargeting, rig reconstruction,
weighted exercises, general editor, cloud or Flutter work is included.

## Reproduce and review

```powershell
Set-Location C:\ws_c\ForgedMotionStudio
python studio/heatsy_build.py
python -m http.server 8765 --bind 127.0.0.1
```

Open **http://127.0.0.1:8765/studio/heatsy/**. Drag either model to orbit both;
front, side, three-quarter and rear presets share cameras and lighting. The
selector offers model-group and individual muscle selections by anatomical side.

Prerequisites: the existing `studio/setup.py` toolchain (Blender 4.5.11,
MPFB 2.0.16, Three.js r170, Playwright 1.58.2 / Chromium 145), Node and Python.
This run used Python 3.13 and NumPy 2.3.5. If NumPy is absent:
`python -m pip install numpy==2.3.5`. The driver does not download or publish.

The existing `work/heatsy` checkout must be at commit
`6cf6a0ae7c63bcffca1137ddcec14a31b7254a6d`. Source:
`work/heatsy/model/body_superficial.app5m.glb`, SHA-256
`ce9859de013c2ee9713dbe3158275208b57be1b4ff31957eca87195b991c0ab1`.
The original side of the viewer reads that exact file. Repository:
https://github.com/heatsy-app/heatsy-body-model.

All new generated artifacts are under **outputs/heatsy-probe/compatibility/**.
The earlier parent-directory `probe.json`, `LICENSE` and `NOTICE.md` remain intact.
The driver marks `milestone.json` BUILDING before work and FAIL on any required
failure. PASS requires all gates, including hashes, fixtures and browser checks.

## Reproduced failure and narrow fix

The bundled glTF add-on is **4.5.51**, in Blender **4.5.11**. Its `imp/mesh.py`
SHA-256 is `7c8204165da0b3cf0caf24af665642a7f29572cb4e056939ffca48ee1fb09b93`.

Two independent defects were demonstrated:

1. The importer appends arrays to `attribute_data` in discovery order but stores
   names in a set. Later enumeration indexes the arrays in set order. This can
   concatenate a scalar onto a VEC3 array, reproducing the recorded dimension
   mismatch. A one-triangle fixture with only **two float custom attributes**,
   inserted opposite their set order, isolates this from type conversion.
   Replacing the set with an insertion-ordered dictionary fixes this fixture.
2. `BinaryData` decodes normalized integers to float32, but mesh storage is chosen
   from the original integer type. An isolated normalized INT8 VEC3 `_FIBER`
   silently disappears because `get_attribute_type` has no match. An isolated
   normalized UINT8 SCALAR `_TENDON` is assigned to INT storage and fails
   `foreach_set`. The patch selects float storage for already-decoded normalized
   data. Non-normalized `_PART_ID` remains integer-valued in Blender.

`heatsy_patch.py` checks Blender version, add-on version, file hash and replacement
contexts, then changes the module **in process memory only**. It does not edit
the installed importer or input asset. Vertex merging is disabled because the
importer can merge custom data arbitrarily. Bone-shape helpers are disabled;
the source rig is retained and no bone is posed.

`original-traceback.txt` retains the exact concatenation failure. Fresh Blender
processes can encounter the normalized-type failure first due to set order.
Every attempt is retained as `original-traceback-attempt-*.txt`; the driver
requires the original dimension failure within eight fresh attempts. The minimal
ordering fixture is deterministic within each process, independent of hash seed.

The Blender regression harness tests all six permutations of the three required
attributes, the minimal float fixture, an isolated normalized vector and an
isolated normalized scalar. **All nine pass with the full patch**, including
exported values. Stock and ordering-only failures are retained in
`fixture-stock.json`, `fixture-order.json`, and `fixture-fixed.json`.
See `fixed-importer.patch` and `IMPORTER-NOTICE.md` for the patch and attribution.

## Representation changes and preservation

| Attribute | Source | Final roundtrip | Value check |
|---|---|---|---|
| `_PART_ID` | UINT8 SCALAR | FLOAT32 SCALAR | Exact integer values and side codes |
| `_FIBER` | normalized INT8 VEC3 | FLOAT32 VEC3 | `max(raw/127,-1)`, all components |
| `_TENDON` | normalized UINT8 SCALAR | FLOAT32 SCALAR | `raw/255`, including fractions |
| `POSITION` | INT16 VEC3; 0.0001 m scaling in inverse binds | FLOAT32 VEC3 in metres | Full skinning and per-joint contributions |
| `NORMAL` | normalized INT8 VEC3 | unit FLOAT32 VEC3 | Source direction at every corner |
| `JOINTS_0` | UINT8 VEC4 | UINT8 VEC4 | Same named nonzero influences |
| `WEIGHTS_0` | normalized UINT8 VEC4 | FLOAT32 VEC4 | Effective weights by joint name |

All final FLOAT32 accessors have `normalized=false`. Anatomical fiber vectors
are **not** normalized to unit length: decoded component values are preserved.
The integer part IDs fit float32 exactly. The original top-level
`extras.app_model.position_unit_m` is not carried onto the metre-based export;
it must not be reapplied. Quantization is absorbed into mesh coordinates and
inverse binds. Every accessor type/flag, node transform, hierarchy, material
factor and asset-extra change is recorded in `validation.json`.

Raw Blender export changed 38 shading-normal directions by over 0.1°, with a
maximum of 84.514°. Many large discrepancies occur beside collapsed source
triangles; 131 source triangles have area below 1e-12 m². The raw normal path is
therefore **not itself appearance-preserving**. `blender-raw.glb` and
`normal-diagnostic-raw.json` retain this evidence.

`heatsy_normals.py` explicitly restores source normal directions after export.
It matches oriented triangles by geometry, anatomical identity and skin weights,
then retains every normal-bearing source corner, including coincident/degenerate
corners. The final topology check includes normals. Lossless corner splits are
supported, but this asset required **zero additional splits** at this step.
Positions, anatomical values, skin data and triangles are unchanged by it.
Raw/final hashes and the operation are recorded in `normal-preservation.json`.
This is a disclosed compatibility pipeline, not an unpatched-Blender success.

## Validation results

| Check | Observed result |
|---|---|
| Source / installed importer | Original SHA-256 values unchanged |
| Required anatomy | All three attributes present and verified |
| Part-ID error | Exactly zero; left/right swaps rejected by tests |
| Maximum fiber component error | 2.9568e-8; tolerance 1e-7 |
| Maximum tendon error | 2.9685e-8; tolerance 1e-7 |
| Maximum weight error | 5.9254e-8; tolerance 2e-7 |
| Vertex records | 79,658 → 79,674; 16 representational splits |
| Triangles | 149,030 in both; oriented corner multiset preserved |
| Mesh / skeleton | One mesh, same 56 named joints and parent hierarchy |
| Maximum rest-position component error | 5.9242e-6 m (0.00593 mm) |
| Maximum per-joint bind contribution error | 5.9242e-6 m |
| Maximum joint world-matrix element difference | 9.9684e-6 |
| Final normal direction error | 0.000002832° maximum |
| Height | Approximately 1.7040 m in both |
| Python/browser source parity | All 79,658 vertices; maximum 6.67e-16 m |
| Python/browser roundtrip parity | All 79,674 vertices; maximum 1.526e-7 m |
| Application suite | 53 tests pass, including existing bodyweight tests |
| Blender fixture cases | 9/9 pass with patch |
| Fresh MPFB export | Byte-identical to canonical bodyweight GLB |
| Canonical bodyweight outputs | All 38 file hashes unchanged |
| Browser | 16 selections, matched views, synchronized orbit, baseline scrub pass |

The 10 micrometre geometry tolerance is one tenth of source position quantization.
Anatomical tolerance is approximately one float32 ULP over [-1,1], far smaller
than an 8-bit quantization step. IDs have zero tolerance. Matrix elements use a
1e-5 bound (translation in metres, rotation/scale dimensionless), supplemented
by per-joint position-action checks in metres. These tolerances establish
numerical compatibility, not anatomical or movement quality.

Matching never assumes array-index correspondence. Position-grid buckets locate
candidates; numerical checks verify positions, attributes and named weights.
Complete oriented triangle multisets then verify corner identities, including
normals. Individual joint contributions are checked separately so compensating
weighted errors cannot hide a bind error. Tests shuffle vertices, add a valid
split, and deliberately corrupt IDs, fibers, tendons, weights, positions, binds
and winding to verify rejection.

Untruncated Khronos validation: source **zero errors / 5,639 warnings** (5,638
nonzero indices in exactly zero-weight slots, plus one non-root skinned mesh).
Derived GLB: **zero errors / one warning**, `NODE_SKINNED_MESH_NON_ROOT`.
Unused slots contribute nothing; Blender resets them without changing effective
weights. The non-root hierarchy is retained; this viewer never changes parent
transforms. Other consumers are untested. Full results/dispositions are in
`source-gltf.json`, `roundtrip-gltf.json` and `mpfb-gltf.json`.

## Appearance review and actual muscle IDs

Neutral comparisons: `screenshots/neutral-front.png`, `neutral-side.png`,
`neutral-three.png`, and `neutral-rear.png` (all under the same screenshots folder).
Separate-side comparisons: `screenshots/select-quads-L-front.png`,
`select-quads-R-front.png`, `select-glutes-L-rear.png`, and
`select-glutes-R-rear.png`. **viewer.json** lists all 20 current screenshots and
their selection checks. Individual selections are captured facing the chosen side.

| Available geometry | Left / right part IDs |
|---|---|
| Gluteus maximus | 97 / 98 |
| Gluteus medius | 99 / 100 |
| Tensor fasciae latae (source glutes group) | 103 / 104 |
| Rectus femoris | 117 / 118 |
| Vastus lateralis | 119 / 120 |
| Vastus medialis | 121 / 122 |

The source formula is `1 + 2*part_index + side`, where side 0=L, 1=R.
**Gluteus minimus and vastus intermedius have no geometry on either side.** Other
absent source-glutes-group leaves: piriformis, gemellus superior, obturator
internus, gemellus inferior, obturator externus and quadratus femoris. The UI
lists absent parts and never substitutes another region.

Tests inspect actual vertex colors against `_PART_ID`, require only intended
codes to change, check source vertex counts, and verify positive-X anatomical
left / negative-X right with a small midline tolerance. Both models retain the
gray anatomical surfaces, exposed tendinous areas and simplified mannequin
head/hands/feet. Saved views show consistent silhouettes and muscle locations.
This is an appearance-review artifact, not human anatomical approval.

## Changed files, attribution and limits

New files in `studio/`: `heatsy_build.py` (orchestration), `heatsy_repro.py` and
`heatsy_fixture_test.py` (reproduction), `heatsy_patch.py` (guarded patch),
`heatsy_gltf.py` (independent decoder), `heatsy_roundtrip.py` (export/notices),
`heatsy_normals.py` (normal preservation), `heatsy_validate.py` and
`heatsy_finish.py` (verification), `heatsy_check_gltf.mjs` (Khronos validation),
`heatsy_capture.mjs` (browser checks), and `heatsy/index.html` / `heatsy/viewer.js`.
Also added `tests/test_heatsy.py` and this review; `studio/README.md` links it.
Existing bodyweight source and canonical outputs were not edited. Pre-existing
uncommitted work remains preserved; no commit or push was made.

`LICENSE` and `NOTICE.md` are copied verbatim from the pinned source, with
`muscles.json`, `za_map.json`, and `DERIVATION.md` beside the outputs. Derived GLB
and screenshots retain **CC BY-SA 4.0** terms and credit Heatsy / DDDEV LTD,
Z-Anatomy and BodyParts3D. The viewer links these notices. Importer-code attribution
is separate in `IMPORTER-NOTICE.md`.

No claim is made about animated deformation, new poses, retargeting, movement
accuracy, clinical anatomy, mobile performance or other engines. Work stops here.

API references: [Blender 4.5 import](https://docs.blender.org/api/4.5/bpy.ops.import_scene.html),
[Blender 4.5 export](https://docs.blender.org/api/4.5/bpy.ops.export_scene.html),
[Three.js r170 BufferAttribute](https://github.com/mrdoob/three.js/blob/r170/docs/api/en/core/BufferAttribute.html).
