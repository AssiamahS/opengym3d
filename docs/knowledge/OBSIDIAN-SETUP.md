# Obsidian setup | Minimal

Obsidian is an optional interface for the Markdown already kept in Git. No plugin, generated view or special vault format is required.

## Open on Windows or Mac

1. Keep a normal local checkout of [ForgedMotionStudio](https://github.com/Forged-Sent/ForgedMotionStudio). Pull the branch you intend to read.
2. In Obsidian choose **Open folder as vault** and select the **repository root**, not a separately copied `docs/` folder.
3. Open `docs/HOME.md`. Bookmark it with Obsidian's built-in Bookmarks feature.
4. Optionally install **Homepage** and set the home note to `docs/HOME`. Core Graph, Search, Backlinks and Templates are optional, not requirements.
5. Make sure local `.obsidian/` settings remain Git-ignored. Do not enable Obsidian Git auto-commit/push; use normal branches and PRs.

## Five-minute daily workflow

- Open [HOME](../HOME.md) and read the one next action.
- Open [WORK](WORK.md) to see task states; edit that page, not a duplicate Kanban board.
- Read the linked [plan](../plans/NEXT-SLICE.md) and latest [evidence](../HEATSY_DEFORMATION_REPAIR.md) only for the chosen task.
- If Codex work pauses before a PR, copy the [handoff template](handoffs/TEMPLATE.md) into a task-specific note.
- Review changes in a branch/PR; update your reading checkout after merge.

## Sharing and privacy

Git is authoritative. Only commit team-relevant Markdown; keep personal notes, local plugin state, source videos without rights, credentials and machine-specific caches out of the repo.

On GitHub, normal relative Markdown links should remain readable even without Obsidian. No vault plugin is needed to read these notes.
