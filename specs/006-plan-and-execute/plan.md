# Implementation Plan: A3 Plan-and-Execute

**Branch**: `006-plan-and-execute` (spec directory; work happens on `main`) | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-plan-and-execute/spec.md`

## Summary

A3 adds planning to A2. One new module, `src/apl/arch/plan_execute.py`, holds a `StateGraph` with
four nodes: a `planner` that writes 1–8 subgoals as JSON, an `executor` that is A2's map-state
turn with a `Your subgoal:` line, `act` that applies its tool calls to the map, and a `replanner`
that reads each subgoal's report and the map and answers with the remaining plan or
`{"done": true}`. Constants bound every loop (R5). Outside `src/apl/arch/` the feature registers
the architecture for both problems, sets `mapstate` as its comparison reference, and lets the
meter count planner and replanner calls as orchestrator calls (R7, R8). The viewer, results
schema, dry-run estimate and both problems stay as they are.

## Technical Context

**Language/Version**: Python 3.12 (pinned).

**Primary Dependencies**: as in M5: `langgraph` 1.2.x, `langchain` 1.4.x, `langchain-core`.
Nothing new in `pyproject.toml`.

**Storage**: run folders under `results/` and viewer episodes under `results/viewer/`, schema
unchanged ([data-model.md](data-model.md)).

**Testing**: pytest, ruff, mypy (strict), with the scripted chat model and helpers from M2–M5
(`tests/runner/scripted.py`, `tests/arch/orchestrated.py`). Research R10 lists the tests.

**Target Platform**: the experimenter's WSL2 machine. This feature makes no paid or local
experiment run.

**Project Type**: Python library with a CLI (`apl`) and a local web page.

**Performance Goals**: none beyond the existing ones; A3 adds at most one planning call per 20
executor turns plus retries.

**Constraints**: constitution I–VI; the import boundary for `src/apl/arch/`; every A3 loop bounded
by a constant, none derived from the step budget (R5).

**Scale/Scope**: one architecture module (about 200 lines), four one-line runner changes, one
test module, docs.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
| --- | --- | --- |
| I. Identical Conditions | A3 uses `kit.model`, `kit.base_prompt`, `kit.tools` and the problem's budget; it adds node instructions only after the base prompt. A test compares its prompt fingerprint, tool schemas and budget with A2's. | ✅ |
| II. Tool-Only World Access | Planner, replanner and executor see only tool results (the map), the executor's reports and A3's own counters. A3 imports only the kit, `apl.arch.*` and the problems' public tools and results (boundary test). The limits are constants, not budget-derived. | ✅ |
| III. Only the Graph Varies | Only the graph and node instructions differ from A2. Every executor tool call goes through `kit.tool_node` and counts toward the one budget; planner calls make none. | ✅ |
| IV. Structured, Code-Scored Results | Scoring is unchanged; plans are parsed from JSON by code; no LLM judge. | ✅ |
| V. Honest Reporting | No run in this feature; any tuning of the limits is on dev seeds only. | ✅ |
| VI. No Paid Call Without `--execute` | No new code path calls a model outside an episode; tests use the scripted model. | ✅ |
| Workflow: graphs by the user | The experimenter asked the agent to write A3 (spec Clarifications); they review it afterwards. | ✅ |

**Post-design re-check (after Phase 1)**: unchanged, all pass. The meter change (R7) touches
how calls are counted, not what an architecture can see or do.

## Project Structure

### Documentation (this feature)

```text
specs/006-plan-and-execute/
├── plan.md              # this file
├── research.md          # Phase 0: decisions R1–R10
├── data-model.md        # Phase 1: graph state, transitions, roles
├── quickstart.md        # Phase 1: validation steps
├── contracts/
│   ├── plan-execute.md  # the architecture
│   └── runner-viewer.md # registry, meter, comparison, viewer
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
src/apl/
├── arch/
│   └── plan_execute.py      # new: A3 (agent-written, at the experimenter's request)
└── runner/
    ├── registry.py          # + plan_execute, both problems
    ├── meter.py             # LEAD_ROLES counted as orchestrator calls
    └── compare.py           # + plan_execute → mapstate

tests/
├── arch/test_plan_execute.py    # new
└── runner/
    ├── test_meter.py            # + planner/replanner roles
    └── test_compare.py          # + A3 with its reference

plan.md, README.md               # A3 built, on both problems
```

**Structure Decision**: the existing single-package layout. A3 reuses `apl.arch.dungeon_map`,
`apl.arch.field_map`, A2's instruction texts from `apl.arch.mapstate`, `read_answer` from
`apl.arch.scouts` and `MAX_MISSES` from `apl.arch.hybrid`.

## Complexity Tracking

No constitution violations.
