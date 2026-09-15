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

## v0.23 research — the 3D character pipeline decision (2026-07-27)

- Z-Anatomy IS usable: 731 muscle meshes, 2.14M tris, every exercise muscle
  key resolves, all TA2-named (`Rectus femoris muscle.l`). CC-BY-SA 4.0 =
  share-alike, so exported assets can NOT be MIT — code stays MIT, renders
  don't. Collection is `4: Muscular system` (numeric prefix; the addon
  renames to dot-prefixed at runtime — match on suffix, never a literal).
- **Appended objects have identity matrix_world until `view_layer.update()`.**
  Cost a full probe round: the census reported the whole body spanning 0.66
  units with left/right sharing a bbox. After the update Frontalis sits at
  z=1.64 — a correctly scaled human all along. Any census that reads
  matrix_world straight after `libraries.load` is reading a lie.
- Character Creator 5 is **Windows-only** (Win 10/11, NVIDIA GTX 10+, 8 GB
  VRAM, 30 GB install + 200 GB DDS cache). Not an option from the Mac.
- **RealityKit collapses a multi-animation USDZ into one clip** (SO 79907762,
  Mar 2026; Apple forum 131463). Ship one USDZ per exercise — which is what
  this repo already does per GLB, so the layout survives the port.
- ActorCore is the wrong store for this: 2,200 motions, themed around city
  life / stunts / parkour, no fitness library. Unity Asset Store has real
  gym mocap in FBX for $10-20 a pack.

## 2026-07-27 — site restore + écorché diagnosis
- github-pages environment only allows `main` deploys: a workflow_dispatch from a
  tag renders fine then dies at deploy. Added v0.22.0 as an allowed tag via
  `gh api .../deployment-branch-policies -f type=tag`. Remember for future tag deploys.
- The écorché blank-render bug: the Z-Anatomy figure exports LYING ON ITS BACK
  (atlas Z-up vs pipeline Y-up), so the standing-figure camera frames empty air.
  Confirmed by loading the spike GLB in three.js. Also: the atlas's text-label
  meshes (FASCIAE etc.) leak into the export — strip them pre-export.
- 2026-07-30: github-pages CI artifacts expire in days — to recover built GLBs without re-running Blender CI, pull them straight off the live Pages site via exercises.json manifest URLs.
- 2026-07-30 écorché UNBLOCKED (4 bugs, one spike each): (1) join() keeps the ACTIVE object's transform — parent_clear keep-transform + transform_apply after join or the camera frames the local bbox of a head-origined muscle; (2) the atlas hides itself at the COLLECTION level too (collection.hide_render + view-layer exclude), object flags were only half; (3) the ".g" labels are FONT/CURVE objects — a mesh-only sweep misses them, the exporter meshes them on the way out; (4) Bone Heat "failed to find solution" is a WARNING with 0 verts weighted, not an exception — census the weights, fall back to nearest-bone inverse-square blend. Figure now renders posed + skinned (skins=1). Remaining: exposure washes the muscle red to pink, squat pose hunches forward, hand meshes spike. FITX_ECORCHE still pinned 0 in render.yml — flip after pose/color polish.
- 2026-07-30 the pink écorché was never an exposure bug. Measured the render instead of adjusting lights: 0% of figure pixels near-clipped, brightest 244 — nothing blown. But saturation read 0.336 against a 0.71 material. Neutral light takes S=(max-min)/max to (max-min)/(max+Δ), so that ratio alone pins Δ≈1.1·max: the 14 m albedo-0.92 cyclorama was bouncing MORE onto the figure than the key light. `backdrop.visible_diffuse=False` keeps it white to camera and removes the fill entirely → sat 0.345 → 0.719 measured. Lesson holds: when something looks wrong twice, measure the output, don't tune the input. A white studio sweep is a saturation solvent.
- 2026-07-30 skin weights: 4 influences (glTF's limit) beats 2, and inverse DISTANCE beats inverse square — squared falloff gives the nearest bone ~all the weight, which creases a joint instead of bending it. Relative cutoff (2x nearest + 2cm) stops the far leg bleeding in.
- 2026-07-30 spike.yml only watched pipeline/ecorche.py, so look changes in build_exercise.py and pose changes in exercises/ rendered nothing. Widened. If a spike "passes" instantly, check it actually ran.

## 2026-09-09 — the hand-keyed era ends (r/threejs: "brother these are so bad")
- Every hand-keyed rep read robotic and the thread said so in 11 comments. The
  fix was never another pose tweak: it was real capture. Mixamo has a proper
  fitness set (Air Squat, Push Up, Jumping Jacks, Plank, Situps, Bicycle Crunch,
  Bicep Curl, Front Raises, Burpee, Kettlebell Swing, Back/Overhead Squat,
  Pistol, Snatch, Clean And Jerk, Sumo High Pull, Jump Push Up + fitness idle
  and start/end transitions). No Mixamo clip exists for lunges, RDL/deadlift,
  rows, lateral raises, calf raises, bridges, good mornings, hammer curls,
  tricep extensions, wall sits, supermans or high knees — those specs are
  drafts until we capture them (v2 phone mocap) or buy a pack.
- Mixamo export API (logged-in browser session, Bearer token from
  localStorage `access_token`, header `X-Api-Key: mixamo2`): GET
  /api/v1/products/<id>?similar=0&character_id=<char> → details.gms_hash; POST
  /api/v1/animations/export with the WHOLE gms_hash object (params joined as
  a string, "0" not "0.0"), preferences {format:"fbx7", skin:"false",
  fps:"30", reducekf:"0"}; then GET /api/v1/characters/<char>/monitor until
  status=completed → job_result is the FBX URL. "Unknown error while
  generating motion" = a malformed gms_hash (dropped keys / float params /
  fbx7_2019). The monitor endpoint LONG-POLLS: never fire several in
  parallel from one tab or the connection pool jams and every fetch hangs.
- Mixamo terms: use inside a project yes, redistribute files no. FBX lives in
  the private opengym3d-mocap repo (CI checkout via MOCAP_TOKEN); the Gumroad
  pack stays the original hand-keyed v1 set.
- Retarget: driver pelvis gets the Hips delta rotation (world space, via the
  armature's matrix_world — the FBX importer leaves the cm→m scale on the
  object), root offset = Hips travel × (MH root height / Hips rest height),
  every other driver bone is an override direction into transfer_pose. Same
  aim machinery as the JSON lane, so the shoulder-girdle rhythm and grip code
  come for free. Sampled every frame, LINEAR, no life-noise.
- 2026-09-09 polish pass (branch polish): the second thing a thread laughs at
  after robotic motion is the mime — "Barbell Snatch" with empty hands. Props
  were OFF (SHOW_PROPS=False) the whole time. Kettlebell prop hangs along the
  forearm line, not gravity, or it dangles mid-swing. Thumbnail = the frame
  furthest from frame 1 at hands/head/hips (peak_frame), never the mid frame.
  One subdivision level (export_apply) turns the stairstep highlight borders
  into gradients; GLBs grow 2.7 -> 5.8 MB, acceptable. "camera": "front" on
  every live spec — the posterior rule shot the kettlebell swing from behind.

## 2026-09-11 — grade the GLB, not the thumbnail (rig inspector + QA gate)
- The export already ships every MakeHuman bone as a node plus the baked
  clip, so joint QA runs on the artefact the viewer plays, in 0.2 s, with no
  Blender: pipeline/qa_glb.py rebuilds joint world positions per sample and
  checks length drift, hinge range, roll flips, pops, foot slide, implement
  contact, loop closure. website/inspect.html draws the same skeleton with
  the same verdicts. Run it on the live assets before theorising.
- What the numbers said about the "disconnected arms": bone lengths 0.0%
  drift, hinges in range, bar on the hands, on all 17. The failure was ROLL:
  rotation_difference is the shortest arc, and once a limb passes near its
  rest direction's antipode the roll flips up to 177 deg between adjacent
  frames (bicycle crunch 8 bones, sit-up forearm 135 deg). Fix = carry each
  Mixamo bone's rest roll reference through its posed rotation and roll the
  MH bone about its aim to match (aim_bone twist=). TWIST MISS in the log
  means the sign convention is off — measure, don't flip signs blind.
- Elbow hyperextension cannot be judged against a body axis: a sumo high
  pull's flared elbows read "backwards" against the shoulder line while
  being sound. Knees are fine against the hip line. Elbows = range only
  until the humeral roll is read from the GLB rotations.
- Position "pops" at 15 Hz are indistinguishable from jump landings (burpee,
  jump push-up, split jerk all trip a 6 cm second-difference); root-relative
  and a warning, never the gate. The retarget's real pops are direction
  flips and those land in the twist check.
- GLTFLoader strips "." from node names (wrist.L -> wristL): look up both.
- A dead-side camera puts a barbell's near plate end-on over the hands;
  "side" is 25 deg toward the front.

## 2026-09-15 — stop buying motion: the asset library + two free lanes
- The "buy the Unity pack" plan was the wrong shape. Motion is an asset
  lookup, and licensing is data: assets/ASSET_LIBRARY.json holds every
  human/motion/implement with its licence, make_manifest.py stamps
  `license.pack` per exercise from it, tests fail on a motion the library
  doesn't know. Mixamo and CMU are the same licence class ("use in a product
  yes, redistribute even converted no") — app-only forever. CC0 (Mesh2Motion
  = Quaternius retargets, 162 human clips) and your own phone captures are
  the only things that can go in the sold pack.
- Mesh2Motion's human packs are Y-up glTF, UE-mannequin bone names, T-pose,
  1.64 m; one GLB holds 75-87 actions. After import_scene.gltf, pick the
  action by name and mute the NLA tracks. Directions come from bone HEAD to
  child HEAD (M2M_MAP names the child) — never trust the importer's tail
  heuristic for a leaf like hand_l with five finger children.
- Video lane: MediaPipe Pose 1.0.1 aborts on macOS Metal
  ("DrishtiMetalHelper ... Service is unavailable"); 0.10.21 + CPU delegate
  works, ~25 fps on M-series. World landmarks are hip-centred, so vertical
  travel is recovered as hip height above the lowest foot point; horizontal
  travel is dropped (in-place render). No axial rotation exists in a
  monocular estimate — twists are the body's forward carried through the
  pelvis/torso frame, which is exactly twist_ref's rule for the rest pose.
  Side view beats front: a 3/4 squat read the two knees 28 deg apart, the
  side-view lunge 8 deg.
- auto-rep: walk out from the DEEPEST frame to the last standing frame
  before and the first after. Scanning forward from frame 0 grabbed 13 s
  of a coach talking because his hips wobbled past the threshold.
- zsh does not word-split `$var` in `for spec in "a b c"; set -- $spec` —
  use `${=spec}` or separate commands.
