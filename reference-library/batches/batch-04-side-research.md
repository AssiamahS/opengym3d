# Batch 04 — dumbbell goblet side-view investigation

2026-11-23 · `codex/visual-reference-library` · base `8ea29c8dab459c306cbc5d20110ffad7584e5417` · **PARTIAL research; human unreviewed**.

Scope: investigate the remaining dumbbell head-support side-cycle gap from [batch 03](batch-03-review.md). This note changes no catalog data or approval flags. Existing working-tree changes were preserved.

## Primary source inspected

- [Dumbbell Goblet Squat (Side View)](https://www.youtube.com/watch?v=XZS7dkzDXX8), published on [Simon Paige's channel, @S1zemon](https://www.youtube.com/@S1zemon). The YouTube watch page visibly identifies Simon Paige as uploader and shows a 21-second player. This verifies the uploader, not professional credentials, performer identity, original authorship, or redistribution permission.
- Watch-page description explicitly identifies videos on the channel as reference material and says they do not replace professional advice. No generalized training or clinical claims are adopted here.
- Actual player pixels were inspected through Chrome/CUA, not inferred from the title. A person in a blue shirt and dark shorts faces left on green gym flooring, holding one vertically oriented dumbbell close to the upper chest. The visible near hand cups the upper head; the lower head hangs below it. This is a dumbbell source, not a kettlebell substitute.
- The source provides a side-oblique view. Both feet can be distinguished and some anterior torso/arm surfaces are visible; do not upgrade it to a calibrated exact sagittal view. Hidden far-hand and thumb contacts remain unresolved.

## Samples and reliability limit

The browser produced a standing image with visible `0:00 / 0:21`, and a lowered image with visible `0:03 / 0:21`, using the same person, equipment, camera and gym setting. These are useful visual observations, but not yet reliable exact frame locators for catalog promotion. Tentative review entry points are [start](https://www.youtube.com/watch?v=XZS7dkzDXX8&t=0s) and [lowered vicinity](https://www.youtube.com/watch?v=XZS7dkzDXX8&t=3s).

Seeking revealed a concrete reliability problem: the displayed time, accessibility seek-slider value and rendered pose did not always agree. Immediately after Home, the accessibility time read zero while the screenshot still displayed six seconds. Subsequent separate screenshot calls and page reframing improved some samples, but repeated seeks around four and five seconds produced inconsistent apparent poses. After a play/pause refresh, accessibility exposed slider value seven while the time button read eleven seconds. These conflicts prevent an honest exact standing–bottom–return assertion. A low frame near three seconds is not proven to be the deepest frame or reversal point.

The first standing and lowered observations share a visual setup; an uncut same-take complete repetition has **not** been verified. A matched standing return endpoint has **not** been established. This is a source lead with visually inspected equipment/view identity, not resolved side-cycle evidence. Keep `full_cycle_reviewed: false` and retain the existing complete-cycle gap. Do not infer timing, joint angles, force, palm pressure or hidden digit positions from these samples.

## Method and next action

Read-only browser work used visible YouTube play/pause, seek-slider keyboard shortcuts and frame-step keys; no hidden application state, media extraction or downloads were used. No screenshots or third-party media were added to the repository. E3's inaccessible Vimeo player, M&S front-oblique footage and MCM photographs were not retried.

The next useful action is to review this short source in a player session with stable seek-to-frame synchronization, then record visible timestamps for one standing–lowest–standing sequence and inspect uninterrupted playback separately. Do not broaden search solely to increase source counts. Public availability supplies no redistribution grant, anatomical approval or movement approval.

**Checks:** source uploader/title/player and dumbbell/view identity inspected; exact phase timing and same-take return **NOT VERIFIED**; continuous-cycle review **NOT VERIFIED**. Documentation-only note; no code/model/build change or test run.
