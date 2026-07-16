# NOTES

- Blender exits 0 even when a `-P` script raises — always pass `--python-exit-code 1` in CI or failures deploy empty sites silently.
- Bone euler signs on this rig (roll=0), learned empirically from thumbnails: up-pointing torso bones lean FORWARD with **negative rx**; down-pointing legs swing forward with **negative rx**; shin flexion is **positive rx**; arm forward-swing from T-pose is **negative rz** on `.L` (the `.*` mirror expansion `[rx,-ry,-rz]` handles `.R`).
- The mid-rep Cycles thumbnail doubles as the pose-debugging tool: tune JSON → push → look at the PNG. No local Blender needed.
- GitHub Pages must be enabled with `build_type=workflow` (`gh api -X POST repos/.../pages -f build_type=workflow`) before the first deploy-pages run.
