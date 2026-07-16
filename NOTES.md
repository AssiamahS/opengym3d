# NOTES

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
