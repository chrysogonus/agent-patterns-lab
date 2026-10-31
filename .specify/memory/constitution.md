# agent-patterns-lab Constitution

## Core Principles

### I. Identical Conditions
Every architecture MUST run with the same model, temperature, base prompt, tool descriptions
and step budget. These values come from one shared configuration (`APL_MODEL` and the run
settings). An architecture MUST NOT override them.
Rationale: any difference in results must come from the architecture alone.

### II. Tool-Only World Access
Architectures MUST perceive and act on the dungeon only through `look`, `move`, `take` and
`use`. They MUST NOT import, call or read environment internals, the generator or the solver.
That includes the shortest solution and the full map. Plain-code nodes (for example A6) are
bound by the same rule: they can work only with what earlier tool results revealed.
Rationale: an architecture that peeks is not solving the task being measured.

### III. Only the Graph Varies
The only thing an architecture may change is its graph: nodes, edges, state schema, and the
node-specific instructions added on top of the shared base prompt. Every tool call by any
node or subgraph counts toward the episode's single step budget, invalid calls included. For
retrying architectures such as A4, all attempts count toward that budget.
Rationale: this keeps the comparison about structure, not about extra resources.

### IV. Structured, Code-Scored Results
Tool results, errors and episode outcomes MUST be structured data with a fixed schema, not free
text. Scoring MUST be computed by code from those records (success, steps vs. optimal, invalid
actions, budget hit, calls, tokens, latency). No LLM judge is used.
Rationale: exact scoring makes results reproducible and comparable.

### V. Honest Reporting
Development and tuning MUST use dev seeds only. Reported results MUST use test seeds only and
include repeats per seed and the spread across them. Test seeds MUST NOT feed back into prompt,
graph or parameter tuning.
Rationale: tuning on reported seeds would inflate results.

### VI. No Paid Call Without `--execute`
No code path may make a paid model call unless the user passed `--execute` explicitly.
Without it, the runner MUST only print the planned matrix and an estimate of model calls.
Tests MUST NOT make paid calls.
Rationale: runs cost money, and dry runs must be safe by default.

## Experiment Setup

- Dungeons are generated from a seed and are solvable by construction. A BFS solver over
  (room, keys held, doors opened) verifies each one and records `optimal_steps`.
- The step budget is 6× `optimal_steps` (3× until v1.1.0: too tight for a small local model). A per-run token cap stops an episode that loops.
- Levels L1–L3 are defined in plan.md §2. Changing a level definition or the seed split
  invalidates earlier results for comparison.
- Stack: Python 3.12, uv, LangGraph 1.2.x, LangChain `init_chat_model`, pytest, ruff, mypy.

## Development Workflow

- Each milestone after M0 is one Spec Kit feature, `/speckit-specify` through
  `/speckit-implement`.
- The user builds the architecture graphs by hand with `StateGraph`. Agents MUST NOT write the
  graph logic in `src/apl/arch/` unless the user asks for it.
- Every `/speckit-plan` MUST pass the Constitution Check against Principles I–VI before tasks
  are generated.
- pytest, ruff and mypy MUST pass before a feature counts as done.

## Governance

This constitution overrides other project guidance where they conflict. Amendments are made with
`/speckit-constitution`, recorded in this file, and checked for their effect on existing
specs. Versioning is semantic: MAJOR for removing or redefining a principle, MINOR for adding a
principle or section or materially expanding one, PATCH for clarifications. Each feature's plan
and review MUST check compliance. An unavoidable violation MUST be recorded in that plan's
Complexity Tracking table with a justification.

**Version**: 1.1.0 | **Ratified**: 2026-10-28 | **Last Amended**: 2026-10-31
