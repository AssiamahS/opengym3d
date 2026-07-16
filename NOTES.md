# NOTES

- Metaball bodies: elements only fuse when fields overlap — chain a ball every ~3.5cm along each bone, and remember the iso-surface sits well INSIDE the element radius at the default threshold (scale radii ~1.45x + threshold 0.45, or the figure comes out starved). Separate muscle-overlay meshes were a dead end (rigid-skinned eggs poke out at joints); painting face materials by bone territory on the one fused mesh is the right architecture.

- Blender exits 0 even when a `-P` script raises — always pass `--python-exit-code 1` in CI or failures deploy empty sites silently.
- Bone euler signs on this rig (roll=0), settled by A/B thumbnails: up-pointing torso bones lean FORWARD with **positive rx**; down-pointing legs swing forward with **negative rx**; knee/shin flexion is **positive rx**; arm forward-swing from T-pose is **negative rz** on `.L` (the `.*` mirror expansion `[rx,-ry,-rz]` handles `.R`). Beware misreading the 3/4-view thumbnail — flip the sign and compare two renders before trusting your eyes.
- FK squats need the chain SOLVED, not eyeballed: pick thigh angle, then shin angle + pelvis drop follow from "ankle returns to its rest point" (shin ≈ +130 for thigh −75, pelvis −0.51).
- The mid-rep Cycles thumbnail doubles as the pose-debugging tool: tune JSON → push → look at the PNG. No local Blender needed.
- GitHub Pages must be enabled with `build_type=workflow` (`gh api -X POST repos/.../pages -f build_type=workflow`) before the first deploy-pages run.
