# Contract: Runner, report and viewer changes

Small, additive changes outside `src/apl/arch/` (research R7, R8).

## Registry (`src/apl/runner/registry.py`)

- `ARCHITECTURES["plan_execute"] = "apl.arch.plan_execute"`.
- `SUPPORTS["plan_execute"] = {"dungeon", "survey"}`.

`apl run --arch plan_execute …`, `apl continue` and `apl serve` pick it up from there. A dry run
lists it like the others and calls no model.

## Meter (`src/apl/runner/meter.py`)

- `LEAD_ROLES = frozenset({"orchestrator", "planner", "replanner"})`.
- `orchestrator_calls` counts calls whose metadata role is in `LEAD_ROLES` (was: equal to
  `"orchestrator"`). For A1, A2, A2r, A6–A9 the count is unchanged.

The results schema does not change: `orchestrator_calls` keeps its name and type.

## Comparison (`src/apl/runner/compare.py`)

- `REFERENCES["plan_execute"] = "mapstate"`.
- The "Calls: orch / scouts" column shows, for A3, planner + replanner calls / executor calls.

## Dry-run estimate (`src/apl/runner/spec.py`)

Unchanged: model calls are estimated as budget + 1 per episode; tokens and cost are hard bounds
through the token cap (spec FR-013).

## Viewer

No code change expected: the architecture list comes from the registry, and each model-call card
shows its role (`planner`, `replanner`, `executor (subgoal N)`). A test checks that
`plan_execute` is offered for both problems and that a scripted A3 episode's events carry the
three roles in order and replay the same.
