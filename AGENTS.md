# Forged Motion Studio: agent working agreement

This is a standalone, open-source-derived exercise-animation authoring project. It is **not** the Forged & Sent Flutter app. The existing OpenGym3D pipeline and model lanes are valuable baselines, not disposable scaffolding.

## Start here
1. Inspect the branch, HEAD and working tree; preserve existing user changes.
2. Read [the knowledge index](docs/knowledge/INDEX.md), your row in [WORK](docs/knowledge/WORK.md), and the relevant [system architecture](docs/architecture/SYSTEM.md) / ADR.
3. Read the specific milestone report and source/tests for your task. Reference exact input, model, output and tool revisions.
4. Work in one focused branch or isolated worktree. Run actual applicable tests and report PASS, PARTIAL, BLOCKED or NOT VERIFIED precisely.
5. Update the relevant architecture/plan note in the same PR as code changes, without duplicating historical experiment reports.

## Hard boundaries
- Never modify ForgedAndSentFitness. Never replace original OpenGym/MPFB/Heatsy assets or erase old evidence.
- Reuse the normalized motion, rig adapter, Blender export, validators and viewer before adding new frameworks.
- Keep experimental source motion and unfinished anatomical models **unapproved**. Human review is required for movement accuracy, anatomy and public-use readiness.
- Do not bypass the fail-closed checks or reinterpret the repair build's expected exit code **2** as full success. The current derivative improves tearing but fails deformation acceptance and the strict native Blender parity gate.
- Heatsy-derived anatomy must retain CC BY-SA 4.0 notices and provenance. Never assume that public video, Mixamo or other third-party motion may be redistributed.
- Do not push directly to main, merge, deploy, publish assets, or change GitHub protections without explicit authorization.
- Do not commit generated `outputs/`, downloaded `work/`, `node_modules/`, credentials, private motion or personal Obsidian settings.
- Do not implement an editor, additional exercises, cloud infrastructure or Flutter integration just to make progress on a deformation-specific task.

## Documentation hierarchy
- Code, tests and output reports establish **what is implemented and observed**.
- Accepted ADRs record intended decisions; proposed ADRs are **not** approvals.
- [WORK](docs/knowledge/WORK.md) tracks current tasks and next actions; [ROADMAP](docs/plans/ROADMAP.md) is sequencing, not live CI.
- Dated milestone reports under `docs/HEATSY_*.md` are evidence snapshots. Link them rather than rewriting their numbers into several documents.
- The PR description is normally the handoff. Use [the handoff template](docs/knowledge/handoffs/TEMPLATE.md) only for work paused before a PR exists.

## Minimal checks
- Run `python -m unittest discover -s tests -v` for code changes when dependencies are present.
- Run the relevant selected build, glTF validation and browser checks for animation/model changes; name any unavailable tools.
- The current repair entrypoint is `python studio/heatsy_repair_build.py`. A documented exit **2** means an honest PARTIAL, not a green acceptance gate.
- Doc-only edits need readable relative Markdown links and a consistency check against the current repository. No extra CI framework is required.

Obsidian is a human-friendly Markdown interface; Git remains the source of truth. Start at [docs/HOME.md](docs/HOME.md).
