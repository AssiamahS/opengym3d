# Knowledge index

This is the lightweight counterpart of Forged & Sent's Git-and-Obsidian project notes. All essential pages are plain Markdown and work on GitHub without plugins.

## Reading order
1. [HOME](../HOME.md): what to focus on.
2. [WORK](WORK.md): the one task board.
3. [SYSTEM](../architecture/SYSTEM.md): actual code boundaries and future seams.
4. [ADRs](../architecture/DECISIONS.md): accepted versus proposed choices.
5. The single [next-slice plan](../plans/NEXT-SLICE.md) or the milestone report relevant to your task.

## Sources and authority

**Implementation:** source code and tests. **Measured evidence:** build-specific reports and generated artifacts, with source SHA and commands. **Approved intent:** accepted ADRs. **Plans:** WORK and roadmap. Never treat a proposed feature or an agent's claim as implemented.

Useful historical evidence:
- [MPFB bodyweight baseline](../MILESTONE_REVIEW.md)
- [Static Heatsy import and anatomy](../HEATSY_COMPATIBILITY_REVIEW.md)
- [Animated Heatsy squat investigation](../HEATSY_BODYWEIGHT_REVIEW.md)
- [Skin-weight deformation repair](../HEATSY_DEFORMATION_REPAIR.md)
- [Equipment library and MPFB grip refinement](../EQUIPMENT_LIBRARY_REVIEW.md)

## Working practice

For each small change, start with the current WORK row; verify the source and constraints, keep the change isolated, attach output evidence, then update that row and affected architecture note **in the same PR**. Use [a handoff note](handoffs/TEMPLATE.md) only when pausing before a PR.

This vault intentionally has **no generated dashboards, database, documentation CI or automatically synchronized boards**. Keep the index and links honest by hand.

## Model and subagent selection

See [Cost-aware agent delegation](AGENT-DELEGATION.md) for when to assign routine independent work to a lower-cost model with generous capability headroom, and when to keep work with the stronger coordinator. The policy does not create subagents or configure models automatically.
