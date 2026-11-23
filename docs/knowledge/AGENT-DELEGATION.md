# Cost-aware agent delegation

**Status:** Agent operating policy. [AGENTS.md](../../AGENTS.md) is the mandatory entrypoint. This note defines decision rules; it does **not** automatically configure or install subagents, model selection, permissions or billing.

## Objective

Reduce **total execution cost** without reducing correctness, safety, reproducibility or architecture quality.

**Pick the cheapest _actually available_ subagent model that is comfortably overqualified for the given job.** Comfortably overqualified means credible evidence that the model handles both the assigned task class and meaningfully harder neighboring tasks reliably, with sufficient context and required tool access. A model that might just manage is unacceptable.

If that headroom cannot be demonstrated, keep the work with the stronger coordinator. Never guess relative prices, available models, token savings, capabilities or reason about cost solely from a model's name.

## Decision sequence

1. **Define one bounded deliverable.** Specify files, source versions, access level, expected output, tests and a stop condition. Keep ambiguous or tightly coupled work with the coordinator.
2. **Check delegation value.** A small sequential task may cost *more* when handed off. Only spawn when independent work, context isolation or parallel progress justifies dispatch and review.
3. **Check actual available choices.** Use a lower-cost model only if the session/runtime supports explicitly choosing it and prior evidence or reliable model documentation supports substantial capability margin. Otherwise do the task with the stronger available model.
4. **Restrict the scope.** Default to read-only inspection. For editing, give exclusive ownership of named files or a separate worktree. Never let agents simultaneously edit the same file or shared mutable outputs.
5. **Require a verifiable result.** Demand specific file paths, test commands/results, sources, differences, unresolved issues and NOT VERIFIED statements.
6. **Integrate and review.** The stronger coordinating agent inspects the work, confirms evidence, runs applicable checks and retains accountability. Independent review of risky changes must not be performed solely by their author.
7. **Escalate after a capability gap.** Stop retrying a marginal cheap model after a substantive failure, inability to explain a result, unexpected complexity or unclear constraints. Bring in a stronger model or the human owner.

## Model-routing examples

| Task and risk | Default owner | Examples |
| --- | --- | --- |
| Trivial sequential operation | Coordinator, no subagent | One typo, one known-file command, a short follow-up |
| Routine bounded/read-only work | Less-expensive **overqualified** subagent when worthwhile | Check Markdown links, inventory equipment IDs, extract benchmark numbers from a supplied report, identify stale file paths |
| Small deterministic edits | Overqualified lower-cost agent only with evidence and focused review | Write an isolated JSON-schema negative test, populate a clearly specified equipment catalog fixture, fix one self-contained documentation link |
| Cross-component/ambiguous engineering | Strong coordinator or proven specialist | Equipment grip and attachment contracts, interface architecture, new asset schemas, viewer lifecycle, cross-file changes |
| High-consequence work | Strongest suitable model plus review | 56-joint retargeting, transform math, skin-weight and volume correction, glTF export, biomechanics, licensing/attribution, security, branch/release protections |
| Final approval | Human owner/reviewer, supported by coordinator | Anatomical accuracy, movement instruction, redistribution and public-release readiness |

A lower-cost agent can **inventory** existing dumbbell, kettlebell and barbell geometries. It must not decide that a goblet squat hand placement is correct or that equipment/limb intersections are anatomically acceptable. It may draft a deterministic parity test, but must not loosen the 10 µm threshold merely to get a green result.

## Each delegated task needs a contract

> **Goal:** one measurable outcome.  
> **Inputs:** exact paths, branch/commit and authoritative docs.  
> **Model:** actual selected model and justification for *extra* capability headroom, when supported.  
> **Permissions:** read-only or exclusive edit scope; no push, merge or publication.  
> **Acceptance:** required tests, artifacts and explicit NOT VERIFIED gaps.  
> **Escalation:** unknown requirements, failed tests, rights ambiguity, unexpected diff or repeated poor output.  
> **Handoff:** concise evidence, file paths, what changed, test results and next action.

The coordinator should not delegate the final approval of a change back to the same agent that wrote it. Subagents' output is advisory until independently verified.

## Cost and quality safeguards

- **Measure total work**, including orchestration, context duplication, tool calls, review, retries and rework. The cheapest per-token model is not always the cheapest successful solution.
- Start with one independent subagent. Add parallel workers only for disjoint investigations or nonoverlapping files. Avoid parallel agents for a single ordered Blender render or shared worktree edits.
- Record observed model/tier, task, verification and escalation when those details are available; never invent billing or telemetry.
- If per-subagent model selection is not supported, this policy cannot enforce lower-cost workers. Continue with capable available models and do not claim savings.
- Maintain existing fail-closed validation and partial statuses. In particular, the Heatsy repair exit code **2** is **PARTIAL**, not a passing anatomical result.
- All agents follow the original source and Heatsy licenses, provenance requirements, separation from ForgedAndSentFitness, and no-push/no-merge/no-publish restrictions in [AGENTS.md](../../AGENTS.md).

## Why this remains a policy, not a framework

Avoid adding agent registration, model names, TOML configuration, auto-routing scripts, extra CI or scheduled work just to satisfy this guideline. Introduce explicit configuration only after verifying what the installed agent runtime supports and measuring a practical benefit.

**References:** [OpenAI multi-agent guidance](https://developers.openai.com/api/docs/guides/agents-api/multi-agent) and [model configuration guidance](https://developers.openai.com/api/docs/guides/agents/models).
