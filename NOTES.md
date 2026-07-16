# NOTES

## The rule this project keeps proving

Every pose or mapping I eyeballed came out broken. Every one derived from real
data worked first try. Guessed and wrong: capsule figure, squat depth (3 tries),
push-up, bridge torso, bridge legs, lats (3 tries). Solved and right first time:
push-up geometry, bridge shoulder-pivot, leg IK, light exposure, camera side.
When something looks wrong twice, stop adjusting numbers and go measure.

- **The lats were never unpainted.** Three rounds of remapping bones chased a bug
  that didn't exist — the camera sat in front of the figure and a bent-over row's
  lats face away from it. A one-line census (`painted primary=214`) would have
  caught it immediately. Print what the code actually did before theorising about
  why it's wrong.
- **Camera side must follow the anatomy**: all-posterior primaries → shoot from
  behind, and flip the light rig + cyclorama with it or you light the subject from
  behind and render through the backdrop.
- **Exposure was 3 stops hot from v0.1 to v0.10** and I "fixed" the wash twice by
  making it worse (900W → 1400W key). Solve it: E ≈ P/(4π·d²), L = E·albedo/π,
  AgX mid-grey ≈ 0.2 → key ≈450 W at 4 m. Blown channels desaturate, which is why
  the muscle reds rendered pink no matter how saturated the base colour was.
- **Skin territory ≠ bone ownership on the torso.** Census: spine02 owns 306 verts
  with 2 posterior; spine01 owns the whole upper back. Pecs and abs share spine02's
  anterior skin, so no bone list can part them — torso regions need geometry (a
  fixed centreline at y=0.03 + a rest-pose height box). Limbs are fine per-bone.
- **Blender's `-P` script exits 0 on error** → `--python-exit-code 1` + assert the
  assets exist, or CI deploys an empty site. This caught the fabricated
  `AgX - Medium Contrast` enum (the real one is `AgX - Base Contrast`; the error
  message lists the valid set).

- MPFB2 headless (v0.4): install by unzipping the pinned sha256 zip from extensions.blender.org into `~/.config/blender/4.5/extensions/user_default/mpfb` + `addon_enable("bl_ext.user_default.mpfb")` — the site 403s python-urllib's UA, download with curl or a browser UA. API from official script_samples: `HumanService.create_human()`, `HumanObjectProperties.set_value("muscle", 1.0, entity_reference=...)` + `TargetService.reapply_macro_details()`, `HumanService.add_builtin_rig(mesh, "default")`.
- MPFB rests in A-POSE, not T-pose — retarget by AIMING each MakeHuman bone at the driver bone's posed world direction (shortest arc), and aim BOTH segments of split limbs (upperarm01+02 etc.) or the second segment keeps its A-pose bend.
- MakeHuman basemesh: strip HelperGeometry/JointCubes/eye.* vertices before export; when reading skin weights, ignore the meta groups (body/Left/Right/Mid) — they carry full weights everywhere and drown the bone territories.
- breast.L/R bones = the pec territory for muscle painting.

- Metaball bodies: elements only fuse when fields overlap — chain a ball every ~3.5cm along each bone, and remember the iso-surface sits well INSIDE the element radius at the default threshold (scale radii ~1.45x + threshold 0.45, or the figure comes out starved). Separate muscle-overlay meshes were a dead end (rigid-skinned eggs poke out at joints); painting face materials by bone territory on the one fused mesh is the right architecture.

- Blender exits 0 even when a `-P` script raises — always pass `--python-exit-code 1` in CI or failures deploy empty sites silently.
- Bone euler signs on this rig (roll=0), settled by A/B thumbnails: up-pointing torso bones lean FORWARD with **positive rx**; down-pointing legs swing forward with **negative rx**; knee/shin flexion is **positive rx**; arm forward-swing from T-pose is **negative rz** on `.L` (the `.*` mirror expansion `[rx,-ry,-rz]` handles `.R`). Beware misreading the 3/4-view thumbnail — flip the sign and compare two renders before trusting your eyes.
- FK squats need the chain SOLVED, not eyeballed: pick thigh angle, then shin angle + pelvis drop follow from "ankle returns to its rest point" (shin ≈ +130 for thigh −75, pelvis −0.51).
- The mid-rep Cycles thumbnail doubles as the pose-debugging tool: tune JSON → push → look at the PNG. No local Blender needed.
- GitHub Pages must be enabled with `build_type=workflow` (`gh api -X POST repos/.../pages -f build_type=workflow`) before the first deploy-pages run.
