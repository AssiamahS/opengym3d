# ROADMAP — OpenGym3D vs the masters

Benchmarked 2026-07-17 against the three reference players:
**gym-animations.com** (7,000+ hand-keyed MP4s, 10-person motion team),
**MuscleWiki** (1,900+ filmed exercises, API + first-party MCP),
**Exercise Animatic** (studio 3D fitness animation, storyboard → anatomist → 4K).

## Scorecard (10 = best in class)

| Axis                | Us | GA | MW | EA | Notes |
|---------------------|----|----|----|----|-------|
| Render style        | 8  | 9  | –  | 9  | genre-correct; v0.21 adds procedural muscle-fibre striation |
| Motion quality      | 5  | 9  | 8* | 9  | keyframed + life-noise vs hand-keyed polish (*MW films humans) |
| Equipment shown     | 7  | 9  | 9  | 9  | v0.18+: procedural DB/BB, measured grip; no machines/benches |
| Form guidance       | 8  | 3  | 9  | 5  | v0.18+: steps on every exercise; MW adds grips/difficulty UX |
| Camera angles       | 4  | 7  | 9  | 8  | one anatomy-driven 3/4 view; MW ships front+side, both sexes |
| Model variants      | 2  | 5  | 9  | 6  | one male model; MW has male+female everywhere |
| Coverage            | 3  | 10 | 9  | 7  | 24 vs 1,900–7,000 |
| Delivery formats    | 8  | 6  | 7  | 6  | GLB + PNG + GIF + MP4 per exercise, free |
| Interactivity       | 10 | 2  | 3  | 2  | orbitable, scrubbable 3D in-browser — nobody else has this |
| AI/API access       | 8  | 1  | 9  | 1  | our MCP (mcp/server.py) matches MW's move; no REST API yet |
| Cost / licensing    | 10 | 4  | 6  | 3  | open source, $0, CI-rendered |
| Marginal cost/exercise | 10 | 2 | 3 | 2  | one JSON + a CI run vs animator-days |

## Backlog, ranked by score impact

1. **Coverage** (2→): keep authoring specs from verified templates only
   (v0.21 adds deadlift, hammer curl, DB shoulder press, reverse lunge,
   wall sit, superman → 24). Every new pose inherits a rendered-correct
   template or uses aim_world; genuinely new geometry waits for thumbnail
   evidence before layering more on top.
2. **Model variants** (2→): MPFB gender is a parameter we already set
   (`gender: 1.0`) — a female model is nearly free. Render `<id>_f.*`
   variants, site toggle. Doubles CI time; consider splitting the matrix.
3. **Camera angles** (4→): second render lane (front+side) per exercise,
   MuscleWiki-style. Also ~2× render time; do after variants decision.
4. **Motion quality** (5→): per-phase easing asymmetry (slow eccentric /
   fast concentric), foot-plant polish, wrist roll during curls.
5. **Machines/benches**: procedural bench + rack props unlock presses,
   hip thrusts, split squats. Bigger modelling lift.

## Anatomy datasets (researched 2026-07-17 — for the ecorché experiment)

The artist route to a true ecorché (visible individual muscles) is a real
anatomy dataset, not sculpting from scratch:

- **Z-Anatomy** (github.com/Z-Anatomy/Models-of-human-anatomy) — libre 3D
  atlas, Blender-native .blend, organised by Terminologia Anatomica (TA2),
  derived from **BodyParts3D** (Database Center for Life Science).
  Also on Zenodo (record 4953712, ~130 MB).
- **Licence: CC-BY-SA 4.0** (BodyParts3D: CC-BY-SA 2.1 Japan). Attribution
  **and share-alike**: any derivative must ship under the same licence.
  That is viral onto whatever we distribute the models inside — decide
  deliberately before importing, since this repo is currently MIT-style.

**Why we haven't imported it:** NOTES records that separate muscle-overlay
meshes were already tried and failed here — rigid-skinned eggs poke through
the skin at joints. A static atlas mesh has the same problem: it isn't
weighted to our MakeHuman rig, so it would need a full transfer-weights
pass before it could survive a squat. That's the experiment, not a quick win.

**What we did instead (v0.21):** material-level fibre striation — a Wave
texture driving a Bump on the highlighted muscle materials, which is the
technique the BlenderArtists anatomy thread lands on ("bake a parametric
material") and Blender Base Camp's muscle guide teaches (Draw Sharp for
fibre direction). No new geometry, no licence entanglement, no joint
poke-through.

## Hosting / cost

GitHub Actions is **free with unlimited minutes for public repositories** on
standard runners, and this repo is public — every render costs $0. That is
the whole economic argument vs the studios: their marginal cost per exercise
is an animator-day, ours is a JSON file and free CI time.

## Standing rules (learned the hard way — see NOTES.md)

- Never push while a render run is in flight — it cancels the deploy
  (v0.18 and v0.19 died this way on 2026-07-17). `[skip ci]` for docs/specs;
  version pushes only after the previous run is verified live.
- No eyeballed poses. World-space `aim_world` for anything gravity-driven;
  solved chains for legs; thumbnail evidence before trusting a new pose.
