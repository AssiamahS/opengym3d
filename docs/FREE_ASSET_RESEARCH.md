# Free asset research — 2026-09-15

Question asked: with the pipeline working (MPFB2 human → Mixamo mocap →
GLB → QA → Pages, 17 exercises live), 18 specs sat as drafts because
Mixamo has no clip for them and the only plan on the board was a $40 Unity
pack. What can replace that for $0, and what may actually be *shipped*?

Everything below was checked against the actual files or licence text, not
a product page. Costs: $0 software, $0 API, $0 GPU, $0 assets.

## Verdict

| Need | Pick | Why |
|---|---|---|
| Human | **MPFB2 (already in use since July)** | CC0 base mesh + rig, generated headless in CI, 163-bone rig the QA gate already reads. Nothing free is better; nothing paid is needed. |
| Motion, redistributable | **Mesh2Motion CC0 human packs** (162 clips) | genuinely CC0, GLB, one skeleton, vendored in `motions/cc0/`. Covers push-up, jumping jacks, jog, run, walk, bear crawl, meditation. |
| Motion, the 18 drafts | **Own phone video → MediaPipe → `video_mocap.py`** | the only $0 source that covers lunges, RDL, rows, raises, curls, bridges, wall sits, supermans, high knees. You own the result. |
| Motion, app-only | Mixamo (kept), CMU (not wired) | both forbid redistributing files even converted, so they can drive the viewer but never the pack. |
| Anatomy reference | Z-Anatomy (already researched) | CC-BY-SA: share-alike is viral, stays behind `FITX_ECORCHE=0`. |

## Humans

| Source | Quality | Rig | Licence | Commercial | Local | CI | Verdict |
|---|---|---|---|---|---|---|---|
| MPFB2 2.0.16 (MakeHuman for Blender) | anatomical, muscle slider, proportions editable | MakeHuman default (163 bones) / Rigify / game rigs | mesh + assets CC0, add-on GPL (no obligation on output) | yes | Blender | yes, cached zip | **in use** |
| MB-Lab | similar | own | AGPL, archived | murky | Blender | — | rejected (archived, viral) |
| Mesh2Motion / Quaternius mannequin | stylised low-poly | UE-style 66 bones | CC0 | yes | any | yes | motion skeleton only; not the visual |
| Z-Anatomy / BodyParts3D | full atlas | none (needs volumetric skinning) | CC-BY-SA 4.0 | yes, share-alike | Blender | cached | reference + écorché lane |
| Character Creator / ActorCore / MetaHuman / Daz | high | proprietary | paid / EULA | restricted | — | — | rejected: cost and licence |
| Ready Player Me | game avatars | own | terms, hosted | app-tied | — | — | rejected: hosted service |

## Motion

| Source | Fitness content | Format | Licence | Redistribute? | Verdict |
|---|---|---|---|---|---|
| **Mesh2Motion human packs** (github.com/Mesh2Motion/mesh2motion-app, `static/animations/*.glb`) | Pushup, Jumping Jacks, Crawl, Meditate, Jog, Sprint, Walk, Chest_Open, Jump_*, Crouch_Idle, Roll, Swim_Fwd (+150 game clips) | GLB, UE-style mannequin | CC0-1.0 (LICENSE-CC0.MD) | yes | **wired** (`cc0/` lane, `M2M_MAP`) |
| Quaternius Universal Animation Library | same clips (M2M's packs are Quaternius retargets) | FBX/GLB, itch.io (Cloudflare-walled to scripts) | CC0 | yes | covered via Mesh2Motion |
| **Own video → MediaPipe Pose** | anything you can film | `opengym3d-motion/1` JSON | yours | yes | **wired** (`video/` lane, `animate_video`) |
| Mixamo | 21 fitness clips already used | FBX | Adobe terms: use yes, redistribute no | no | kept, app-only |
| CMU Graphics Lab (mocap.cs.cmu.edu) | squats inside compound trials 13_29/30, 14_06/14, 22_14, 23_14, 86_02/08 | ASF/AMC, C3D, BVH (cgspeed) | "may include in commercial products, may not resell even in converted form" | no | app-only; not wired (needs ASF importer + trimming) |
| Mesh2Motion's `CarnegieMellonAnimations/91_*.fbx` | walking | FBX | CMU | no | ignore |
| AMASS / HumanML3D / Motion-X | large | SMPL | research, non-commercial | no | rejected |
| Bandai Namco motion dataset | large, stylised | BVH | CC BY-NC-ND | no | rejected |
| LAFAN1 (Ubisoft) | locomotion | BVH | CC BY-NC-ND | no | rejected |
| Unity Asset Store gym packs | 150+ gym motions | FBX | per-seat, no redistribution of source | no for the pack | rejected: $40 for app-only rights |
| FreeMoCap | your recordings, multi-camera | BVH/CSV | AGPL tool, data yours | yes | upgrade path for depth |
| BlendArMocap | same estimator as our lane, inside Blender UI | Blender | GPL tool | yes | not needed headless |

## What the video lane measured on the first two captures

Local, M-series Mac, CPU, `mediapipe==0.10.21` (`1.0.1` aborts in
`TensorsToDetectionsCalculator` with a Metal "Service is unavailable";
the CPU delegate on 0.10.21 is the working combination).

| Clip | View | Detected | Rep found | Hip drop | Knee at bottom | Loop gap |
|---|---|---|---|---|---|---|
| air squat demo (public YouTube), s 26–44 | 3/4 | 539/539 frames | 52 frames, 1.73 s | 77 → 46 cm | L 106° / R 78° | 18 cm |
| forward lunge demo (public YouTube), s 4–14 | side | 232/300 frames | 87 frames, 2.90 s | 78 → 49 cm | L 99° / R 91° | 25 cm |

Reading: depth is the weak axis of a single camera — the two knees disagree
by 28° on a front-loaded squat because one leg is further from the lens.
A side view (the lunge) lands both knees within 8°. The loop gap is the mean
landmark distance between first and last frame; lunges are asymmetric by
nature (the returning foot lands elsewhere), squats close within ~18 cm at
the smoothing used. Both are inside the QA gate's tolerances; whether they
*look* right is what the spike strip and inspect.html decide.

These two files are labelled `video-demo` in the library and stay out of
the pack. They exist to prove the lane end-to-end; the shipping captures
are the ones you record.

## Rejected paid options, and what replaced each

| Paid | Replaced by |
|---|---|
| Unity gym mocap pack ($40) | video lane for the 18 drafts; CC0 packs for cardio |
| Character Creator 5 / ActorCore | MPFB2 (in use) + CC0 / own motion |
| MetaHuman | not needed for a grey studio figure |
| Rokoko / Move.ai / DeepMotion subscriptions | MediaPipe on-device now, FreeMoCap multi-camera later |
| Marketplace characters (CGTrader / TurboSquid / Sketchfab paid) | MPFB2 |
| Cloud GPU | GLB export is CPU; GitHub Actions is the render farm |
