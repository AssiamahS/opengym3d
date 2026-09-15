# The exercise factory

An exercise is an input, not a project. `exercises/<id>.json` says what the
movement is; the factory finds motion for it, retargets it onto the one
human, grades the result three ways and publishes only what passes.

```
exercises/<id>.json ─┬─ "mocap": <ref> ──────────────► asset library (licence, lane)
                     └─ "movement": {"pattern": …} ─► anatomy rules
        │
        ▼  factory.py resolve      no motion?  → candidate clip on disk, or CAPTURE NEEDED
        ▼  factory.py ingest       phone clip  → video_mocap.py → motions/video/<id>.json, spec live, library entry
        ▼  CI render (Blender)     retarget onto the MPFB2 human, props gripped, camera per spec
        ▼  gate 1  qa_glb.py       joints: lengths, hinges, roll flips, foot slide, implement on hands
        ▼  gate 2  anatomy_qa.py   movement: depth, hinge vs squat, arm plane, press height, …
        ▼  gate 3  sheet_glb.py    two-view skeleton sheet + Blender strip + inspect.html for the eyes
        ▼  make_manifest.py        critical failure = not published; licence.pack stamped
```

## Skeleton first

Nothing needs Blender until the skeleton is right. Every motion source is
converted into one file format and played on one canonical skeleton in
pure Python:

```
Mesh2Motion GLB ─┐
CMU ASF/AMC ─────┼─ pipeline/motion.py adapters ─► opengym3d-motion/1 ─► canonical skeleton FK
phone video ─────┘   (Mixamo FBX: Blender only, CI spike)      │              (opengym3d_v1, 17 bones)
                                                              ▼
                                        anatomy gate + two-view skeleton sheet, in seconds
```

`python3 pipeline/factory.py verify <id>` runs that for every candidate
motion of an exercise and leaves `verify/<id>.json` plus a sheet per
candidate. States: CANDIDATE (found by name, unproven), EXERCISE_VERIFIED
(passes the movement rules on the skeleton), REJECTED (fails them, or a
human rejected the render — recorded on the spec as `mocap_rejected`),
PUBLISHED (rendered on main). A filename is never evidence: Mixamo
"lifting heavy object" was a candidate for deadlift and is REJECTED
because it squats.

## Commands

```sh
python3 pipeline/factory.py status                  # every spec: lane, licence, pattern, tier, what's next
python3 pipeline/factory.py resolve                 # all drafts: candidate clip or capture needed
python3 pipeline/factory.py ingest lunge --video ~/Downloads/lunge.mov
python3 pipeline/factory.py grade spike/lunge.glb   # gates 1+2 and the sheet, locally, in seconds
python3 pipeline/factory.py verify deadlift         # skeleton-first: candidates → FK → anatomy gate → verdict
python3 pipeline/motion.py cmu motions/cmu/13.asf motions/cmu/13_29.amc out.json --start 31.6 --end 34.6
python3 pipeline/motion.py show motions/video/lunge_demo.json     # skeleton sheet from any motion
python3 pipeline/anatomy_qa.py census site/assets/*.glb   # the numbers behind the bounds
```

## The spec

```json
{
  "id": "deadlift",
  "movement": {"pattern": "hinge", "qa": {"hands_forward_m": [null, 0.45]}},
  "mocap": "video/deadlift.json",
  "prop": {"type": "barbell"},
  "camera": "side"
}
```

`movement.pattern` is one of the patterns in `pipeline/anatomy_qa.py`
(squat, hinge, swing, lunge, press_vertical, curl, raise_lateral,
raise_front, row, tricep_overhead, calf_raise, wall_sit, plank, push_up,
prone_lift, supine_curl, bridge, locomotion, high_knees, jumping_jack,
crawl, olympic, plyometric, seated_hold). `movement.qa` tightens or loosens
a bound for this exercise only. A spec without a known pattern fails the
unit tests.

## Gate 2 — anatomy

The joint gate proves the skeleton is sound; it cannot tell a deadlift from
a squat. The anatomy gate measures the movement from the same joint
samples: hip drop, tightest knee, torso lean, hip flexion, arm elevation
and plane, wrist over head / shoulder, hands forward of the hips, foot
split and spread, head rise, floor contact. Each pattern bounds the metrics
that define it. Bounds were set from a census of the live, reviewed GLBs;
patterns with no live GLB yet are listed in `PROVISIONAL` and get refined
from the first capture's census, not from opinion.

Failures are critical: the exercise renders, gets a QA report and a sheet,
and is left out of the public manifest with the reason printed in CI.

## Gate 3 — eyes

Per exercise CI leaves `<id>.strip.png` (12 Blender frames, one camera),
`<id>.sheet.png` (skeleton, front over side, 12 frames, failing frames
boxed red) and `<id>.glb.qa.json`. `inspect.html` shows all of it with a
live skeleton you can orbit. Read the sheet before the strip: the strip
shows what one camera saw, the sheet shows what the joints did.

## Motion lanes, in licence order

1. `motions/cc0/` — Mesh2Motion packs (CC0). Pack-eligible.
2. `motions/video/` — your own phone capture (`own`). Pack-eligible.
3. `motions/cmu/` — CMU mocap database (free for all uses, not resellable
   even converted). App-only. `index.json` holds each trial's description,
   rep window and what it is a candidate for.
4. `mocap/mixamo/` — private clone, app-only, never in the sold pack.
5. `video-demo` captures from public footage — app-only, pipeline tests.

`resolve` searches all four by whole-word alias and never guesses from a
substring. When nothing matches it says CAPTURE NEEDED and gives the shot
list: phone on a tripod, side view, whole body including the feet, one
clean rep.
