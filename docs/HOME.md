# Forged Motion Studio | Home

> **Current focus:** Make one Heatsy bodyweight squat deform convincingly **before** building weighted variations or a general editor. [Open the one work board](knowledge/WORK.md).

## Do this next

**FMS-01: Attachment-aware deformation investigation.** [Plan and stopping criteria](plans/NEXT-SLICE.md).

The last published code checkpoint is [PR #1](https://github.com/Forged-Sent/ForgedMotionStudio/pull/1). The latest repair is **PARTIAL**, not anatomical or movement approval. Ordinary-edge bottom-pose maximum stretch improved from 33.289× to 3.529×, but ordinary edges compressed below half length rose from 1,292 to 3,139; native Blender parity narrowly fails the fixed tolerance. [Original evidence and measurements](HEATSY_DEFORMATION_REPAIR.md).

> These are checkpoint observations, not live branch, CI or review status. Use [GitHub PRs](https://github.com/Forged-Sent/ForgedMotionStudio/pulls) for live state.

## Navigate

| Need | Note |
| --- | --- |
| Pick or resume a task | [WORK: single work board](knowledge/WORK.md) |
| Understand what is implemented | [System and boundaries](architecture/SYSTEM.md) |
| See why decisions were made | [Decision index](architecture/DECISIONS.md) |
| Know what comes after deformation | [Roadmap](plans/ROADMAP.md) |
| Understand risks | [Risks and release gates](architecture/RISKS.md) |
| Reproduce current outputs | [Studio setup and commands](../studio/README.md) |
| Inspect the full repair evidence | [Deformation repair report](HEATSY_DEFORMATION_REPAIR.md) |
| Prepare a paused Codex handoff | [Handoff template](knowledge/handoffs/TEMPLATE.md) |
| Set up the vault | [Obsidian setup](knowledge/OBSIDIAN-SETUP.md) |
| Find docs as an agent | [Knowledge index](knowledge/INDEX.md) |

## Local inspection

From the existing prepared Windows checkout:

```powershell
Set-Location C:\ws_c\ForgedMotionStudio
python -m http.server 8765 --bind 127.0.0.1
```

Open [the local before/after viewer](http://127.0.0.1:8765/studio/heatsy-squat/?repair=final&compare=before). The link works only when that computer is serving the files and the generated output bundles exist.

**Do not confuse a good-looking neutral anatomical model with a verified moving model.** The current source squat is synthetic and the anatomy remains unapproved.
