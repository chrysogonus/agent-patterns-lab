# agent-patterns-lab Constitution

## Core Principles

### I. Identical Conditions
Within a problem, every architecture MUST run with the same model, temperature, base prompt, tool
descriptions and step budget. The base prompt and tool descriptions are the problem's; the model
settings come from one shared configuration (`APL_MODEL` and the run settings). An architecture
MUST NOT override them.
Rationale: any difference in results must come from the architecture alone.

### II. Tool-Only World Access
Architectures MUST perceive and act on a problem only through that problem's tools: the dungeon's
`look`, `move`, `take` and `use`; the survey field's `look`, `move` and `submit`; the signal
trace's `look`, `probe` and `submit`; the rune floor's `look` and `move`; the workshop's `look`,
`inspect`, `gather` and `craft`. They MUST NOT import, call or read environment internals,
generators, solvers or reference walks. That includes the shortest solution, the full map, the
reference walk, the true deposit count, the broken segment, the reference probes, the rune floor's
rule, its trap tiles and its reference path, and the workshop's recipes (except through
`inspect`), its reference plan and its stuck check. Plain-code
nodes (for example A6) are bound by the same rule: they can work only with what earlier tool
results revealed.
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

- **Dungeon**: dungeons are generated from a seed and are solvable by construction. A BFS solver
  over (room, keys held, doors opened) verifies each one and records `optimal_steps`. The step
  budget is 6× `optimal_steps` (3× until v1.1.0: too tight for a small local model). Levels L1–L3
  are defined in plan.md §2.
- **Survey field**: fields are generated from a seed, with every cell reachable by construction.
  Code computes a reference walk that enters every cell; it is the shortest on open levels and is
  marked as a reference, not an optimum, on walled ones. The step budget is 3× the reference
  steps (the walk plus the submission). Levels S1–S3 are defined in plan.md.
- **Signal trace**: pipes of numbered segments are generated from a seed; each segment is fed from
  the source S or from one other segment, and exactly one segment is broken. A probe answer is
  always true, and the layout is given free at the start. Code computes a reference: the
  worst-case probes of code's own probe strategy on that layout, plus one submission. On straight
  levels the strategy is bisection, the optimum there; elsewhere the reference is marked as a
  reference, not an optimum. The step budget is the larger of 3× the reference and a full
  probe-by-probe scan (every segment but one probed, plus one submission). Levels T1–T3 are
  defined in plan.md.
- **Rune floor**: floors of colored tiles are generated from a seed, with a start S, a goal G and
  a hidden rule that decides which steps are safe. Every floor has a safe path from S to G, and the
  shortest route that ignores the rule springs a trap. The colors are given free at the start. A
  trap sends the agent back to S; it is a result, not an error, and no result states the rule.
  Code computes a reference: the moves on the shortest safe path. The step budget is 4× the
  reference. Levels R0–R3 are defined in plan.md.
- **Workshop**: workshops are generated from a seed: a goal item, craftable items with one or two
  recipes each, and raw materials with a stock count each, some scarce. Every workshop is
  solvable; on levels with conflicts, always taking an item's first-listed recipe gets stuck. The
  goal and the stock are given free at the start; a recipe is seen only through `inspect`. The
  episode ends as stuck once the goal can no longer be made from the inventory and the stock.
  Code computes a reference: the steps of the shortest plan that inspects every craftable item it
  uses, gathers its raw materials and crafts the goal. The step budget is 3× the reference.
  Levels W1–W3 are defined in plan.md.
- **Attempts**: an architecture registered as retrying (A4) may restart the world up to 3
  attempts per episode. A restart puts the world back in its start state and costs no step; every
  tool call of every attempt counts toward the one budget. On the survey field a wrong total, on
  the signal trace a wrong submitted segment, on the rune floor a trap, and on the workshop getting
  stuck ends such an architecture's attempt while attempts are left, with a result that says only
  that it was wrong (on the rune floor, that it was a trap and where; on the workshop, that the goal
  can no longer be made). Every other architecture has one attempt.
- A per-run token cap stops an episode that loops.
- Changing a level definition or the seed split invalidates earlier results for comparison.
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
Complexity Tracking table with a justification. Results from different problems MUST NOT be
combined in one comparison.

**Version**: 2.4.0 | **Ratified**: 2026-10-28 | **Last Amended**: 2026-11-02
