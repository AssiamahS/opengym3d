# Batch 02 — squat visual evidence and equipment choices

2026-11-23 · base `8ea29c8dab459c306cbc5d20110ffad7584e5417` · **PARTIAL; human unreviewed**.

The priority was improving the eight existing squat entries, then expanding into barbell squat, hinge, bench and rack references. Twelve new barbell variations are in [expansion-02](expansion-02.json); three additional visually supported variations are in [visual-expansion-02](visual-expansion-02.json). Exact current totals are generated in [coverage](../COVERAGE.md).

## Corrected evidence assignments

- The [NASM goblet page](https://www.nasm.org/resource-center/exercise-library/goblet-squat) permits two implements in text, but its [video](https://www.youtube.com/watch?v=nfX7IFK9UNI) shows a kettlebell. Paused samples at 0:04, 0:09, 0:14 and 0:19 establish that identity; the video was removed from dumbbell visual evidence and assigned to kettlebell goblet.
- The [Cossack source](https://www.strengthlog.com/cossack-squat/) GIF shows a kettlebell. It now supports `kettlebell-cossack-squat`; `bodyweight-cossack-squat` retains its ID but is downgraded to `research_required` until an explicitly unloaded demonstration is found.
- [CrossFit's 2006 photo sequence](https://library.crossfit.com/free/pdf/49_06_Dumbbell_Squat.pdf#page=2) supplies distinct side-held, shoulder-held and overhead dumbbell examples. Level 1 resolves the missing side-held visual match. The Level 3 single-arm picture is excluded from the new two-dumbbell overhead entry.
- A source called “Rack Pull” demonstrates plate blocks in the inspected frame. The expansion uses `barbell-block-pull` and records the source-name mismatch rather than inventing rack support contact.

## What was actually inspected

| Existing entry | New visual evidence | Remaining limit |
| --- | --- | --- |
| Air squat | [ACE](https://www.acefitness.org/resources/everyone/exercise-library/135/bodyweight-squat/) side sequence: upright, shallow flexion, lower and deepest shown; two StrengthLog GIF samples | Source arm positions and depth cues differ; return playback incomplete |
| Chair squat | StrengthLog GIF upright and partially lowered side samples | Seat-contact instant not sampled; no contact-force or unloading inference |
| Dumbbell side-held squat | CrossFit Level 1 frontal standing/bottom pair | Handle close-up and side motion missing |
| Double dumbbell front squat | CrossFit Level 2 frontal standing/bottom pair; new grip text sources | Shoulder-support patch and thumb details missing |
| Double kettlebell front squat | Three GIF samples: partial squat, bottom and standing | Palm insertion and hidden fingers not resolved |
| Kettlebell goblet | NASM sampled video, StrongFirst grip collage, NSCA figures 1E/F | Hidden thumb contacts and continuous true-side cycle missing |
| Dumbbell goblet head support | ACE bottom photo; M&S sampled video; dedicated head-support close-up; E3 Rehab poster | Underside/reverse thumb view and complete true-side motion missing |
| Bodyweight Cossack | Linked media inspected and rejected as equipment mismatch | Explicit unloaded evidence still required |

All GIF and video observations are sampled frames, **not complete-cycle review**. Video samples retain locators in `observed_samples`; GIF snapshots are untimed. The E3 Rehab Vimeo player reported “Unable to play media,” so its standing poster is the only evidence recorded. No video was downloaded.

## Grip findings

The [StrongFirst collage](https://www.strongfirst.com/kettlebell-simple-sinister-tips-for-heavy-goblet-squats/) compares open fingers, curled grip and bottom squat. It supports coarse palm placement near the horn junction, not digit-level pressure or an exact wrist pose. Author: Pavel Macek.

The [Fit Women's Weekly close-up](https://fitwomensweekly.com/post/how-to-hold-a-dumbbell-for-goblet-squats/) shows palms beneath the upper head's outer corners and fingers rising along its sides. Thumb surfaces remain hidden. It is used only as first-party visual contact evidence; the page's generalized pain, loading and numerical wrist claims are excluded.

[Muscle & Strength](https://www.muscleandstrength.com/exercises/dumbbell-goblet-squat) supplies a head-supported demonstration and an optional thumbless text cue. Its staff comment about a two-hand vertical shaft hold remains weak evidence. No strong matched shaft demonstration was established; it remains separate from head support. See [grip-source findings](batch2-grip-research.md).

## Equipment alternatives

The user's requested equipment choices are represented by [explicit groups](../EQUIPMENT-ALTERNATIVES.md): goblet squat (dumbbell/kettlebell), front-loaded squat (dumbbell/kettlebell/barbell), and Romanian deadlift (dumbbell/barbell). These are candidate variations for a workout slot. Each retains distinct grips, configuration, contact evidence and unresolved issues; no equal-load conversion or automatic animation substitution is implied.

## Review outcome

Independent review corrected a misattributed StrongFirst author, inconsistent sample-object shape, stale video-inspection wording and an irrelevant shoulder-contact gap on the side-held variation. The normalization now preserves curated source conflicts, explicit inspection flags and research-required status. Validation rejects unresolved variants in equipment-alternative groups.

No exercise receives anatomical, movement or public-use approval. No original model, motion, viewer, acceptance gate or historical experiment report was changed. The prior ZIP remains intact; batch 02 is packaged separately.
