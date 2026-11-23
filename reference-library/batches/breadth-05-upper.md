# Breadth 05: upper-body research

2026-11-23. **PARTIAL, human unreviewed.** Baseline branch `codex/visual-reference-library`, HEAD `8ea29c8dab459c306cbc5d20110ffad7584e5417`; [existing catalog](../data/exercise-variations.json). [Batch JSON](breadth-05-upper.json) adds 20 variations across 18 previously absent families. Chest fly and lateral raise have dumbbell/cable counterparts.

Method: followed the [publisher directory](https://www.strengthlog.com/exercise-directory/) to exercise pages, read instructions and followed demonstration image links to recover actual URLs. No guessed media URLs or downloads. Web image responses supplied metadata only. Chrome screenshots separately established three untimed single-frame observations; all full-cycle flags remain false. Seventeen other visuals are linked but uninspected. Wrist-extension media fetch timed out after exposing the exact link. Direct Python network failed DNS; web/browser tools supplied evidence.

| Primary source | Source-derived motion/contact | Evidence |
| --- | --- | --- |
| [Dumbbell chest fly](https://www.strengthlog.com/dumbbell-chest-fly/) | Open arms to sides with slight elbow bend; Bring weights together above chest. One dumbbell handle per hand. | Actual single-frame screenshot |
| [Dumbbell pullover](https://www.strengthlog.com/dumbbell-pullover/) | Lower dumbbell behind head with nearly straight arms; Lift weight above torso. Hands hold dumbbell; exact head/shaft support unresolved. | Text and linked GIF; pixels uninspected |
| [Band external shoulder rotation](https://www.strengthlog.com/band-external-shoulder-rotation/) | Rotate forearm away from trunk with upper arm near side; Rotate inward to setup. Far-side hand holds band; closure uninspected. | Text and linked GIF; pixels uninspected |
| [Cable internal shoulder rotation](https://www.strengthlog.com/internal-shoulder-rotations/) | Rotate forearm inward with upper arm near side; Rotate outward to setup. Near-side hand holds cable handle. | Text and linked GIF; pixels uninspected |
| [Band pull-apart](https://www.strengthlog.com/band-pull-apart/) | Spread arms apart; Bring hands forward together. One band segment in each hand. | Text and linked GIF; pixels uninspected |
| [Barbell upright row](https://www.strengthlog.com/barbell-upright-row/) | Raise bar along torso; Lower bar toward thighs. Overhand bar grip; exact closure uninspected. | Text and linked GIF; pixels uninspected |
| [Dumbbell front raise](https://www.strengthlog.com/dumbbell-front-raise/) | Lift weights forward; Lower weights in front. One handle in each hand; fine grip uninspected. | Text and linked GIF; pixels uninspected |
| [Dumbbell lateral raise](https://www.strengthlog.com/dumbbell-lateral-raise/) | Raise arms outward; Lower weights to sides. One handle in each hand; fine grip uninspected. | Text and linked GIF; pixels uninspected |
| [Cable rope face pull](https://www.strengthlog.com/face-pull/) | Pull rope toward face, elbows outward; Extend arms forward. Both hands hold rope branches; thumb detail unresolved. | Actual single-frame screenshot |
| [Kneeling two-hand landmine press](https://www.strengthlog.com/landmine-press/) | Press bar end upward and forward; Lower end toward chest. Both hands clustered at bar end; contact surfaces unresolved. | Actual single-frame screenshot |
| [Reverse dumbbell fly](https://www.strengthlog.com/reverse-dumbbell-flyes/) | Lift arms outward with small elbow bend; Lower weights beneath torso. One dumbbell handle per hand. | Text and linked GIF; pixels uninspected |
| [Dumbbell lying triceps extension](https://www.strengthlog.com/dumbbell-lying-triceps-extension/) | Bend elbows to lower weights behind head; Straighten arms upward. One dumbbell handle per hand. | Text and linked GIF; pixels uninspected |
| [Cable bar triceps pushdown](https://www.strengthlog.com/tricep-pushdown-with-bar/) | Extend elbows pressing bar down; Let bar rise with elbow flexion. Overhand grip on cable bar; attachment catalog gap. | Text and linked GIF; pixels uninspected |
| [Dumbbell shrug](https://www.strengthlog.com/dumbbell-shrug/) | Elevate shoulders; Lower shoulders. One dumbbell handle per hand. | Text and linked GIF; pixels uninspected |
| [Scapular pull-up](https://www.strengthlog.com/scap-pull-up/) | Draw shoulder blades down and together; Allow shoulder blades to rise. Overhand grip slightly wider than shoulders per text. | Text and linked GIF; pixels uninspected |
| [Dumbbell wrist curl](https://www.strengthlog.com/dumbbell-wrist-curl/) | Lower hand and allow weight toward fingers; Close grip and curl wrist upward. Underhand grip includes described finger roll. | Text and linked GIF; pixels uninspected |
| [Dumbbell wrist extension](https://www.strengthlog.com/dumbbell-wrist-extension/) | Lower hand; Extend wrist upward. Overhand dumbbell grip. | Text and linked GIF; pixels uninspected |
| [Two-hand bar hang](https://www.strengthlog.com/bar-hang/) | Suspend body from bar; Dismount not described or inspected. Both hands on bar; grip orientation unresolved. | Text and linked GIF; pixels uninspected |
| [Standing cable chest fly](https://www.strengthlog.com/standing-cable-chest-fly/) | Bring slightly bent arms together in front; Let arms open under control. One high-pulley handle per hand. | Text and linked GIF; pixels uninspected |
| [Single-arm cable lateral raise](https://www.strengthlog.com/cable-lateral-raise/) | Raise arm outward; Lower handle toward hip. Far hand on low-pulley handle; other hand contact unknown. | Text and linked GIF; pixels uninspected |

Actual observations: chest fly shows a supine performer with planted feet, two dumbbells and spread arms. Landmine press shows both knees on a mat, hands near the chest-level bar end and the other end meeting a floor plate. Face pull shows a standing performer holding rope branches with arms forward. Timing, forces, hidden finger contacts and full cycle remain unverified. Exact media links and observation limits are in each JSON reference.

Conflicts: [upright row](https://www.strengthlog.com/barbell-upright-row/) gives chin-height instructions but also discusses limiting upper-arm elevation; endpoint remains unresolved. [Internal rotation](https://www.strengthlog.com/internal-shoulder-rotations/) has cable instructions and band commentary; entry follows cable setup with visual confirmation pending. [Landmine press](https://www.strengthlog.com/landmine-press/) permits standing/kneeling; only sampled kneeling is included. Wrist support choice and hang shoulder activity remain unresolved.

Equipment gaps: dedicated landmine anchor and straight cable-bar attachment need catalog configurations. Generic grip IDs on band/pullover/landmine records are lookup placeholders; contact text governs interpretation. Counterparts are grouping candidates, not equivalent motion prescriptions. Scapular push-up was not added; scapular pull-up supplies a distinct sourced scapular family.

Rights: links only. The publisher directory describes conditional noncommercial attribution-based reuse; this research grants no license and copies no media. Movement, anatomy and public-use approval remain unreviewed.

Checks: JSON parsed, 20 unique IDs, 18 families, no overlap with baseline IDs/families; 20 source-linked GIFs; 3 single-frame visual inspections; no full-cycle claims. Shared data/build files untouched by this worker; integration tests remain coordinator-owned.
