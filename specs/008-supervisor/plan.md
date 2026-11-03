# Implementation Plan: A5 Supervisor

**Branch**: `008-supervisor` (spec directory; work happens on `main`) | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/008-supervisor/spec.md`

## Summary

A5 needs nothing below the architecture: no problem, kit, prompt or viewer change.

- **A5** (`src/apl/arch/supervisor.py`), written by the agent: a `supervisor` node that answers
  with one JSON handoff and routes with `Command(goto=...)`; two helpers, `navigator` (`look`,
  `move`) and `inventory` (`take`, `use`), each a compiled `StateGraph` added as a node of the
  parent graph and sharing its state; one A2 map for all three (research R1–R6).
- **Runner**: `supervisor` registered for the dungeon only; `"supervisor"` in the meter's
  `LEAD_ROLES`; `supervisor → mapstate` in the comparison's references (R7).
- **Viewer**: nothing new; it offers registered architectures per problem and shows roles on
  every model-call card already (R8).
- **Docs**: plan.md and README list A5 as built on the dungeon.

## Technical Context

**Language/Version**: Python 3.12.

**Primary Dependencies**: unchanged (`langgraph` 1.2.x: `StateGraph`, compiled subgraphs as
nodes, `langgraph.types.Command`).

**Storage**: none new.

**Testing**: pytest, ruff, mypy (strict), the scripted model; research R9 lists the tests.

**Target Platform**: the experimenter's WSL2 machine. No experiment run in this feature.

**Project Type**: Python library with a CLI and a local web page.

**Performance Goals**: none new.

**Constraints**: constitution I–VI; byte-identical outputs for every other architecture; every A5
loop bounded by constants or the budget.

**Scale/Scope**: one architecture module, registry, meter, compare, tests, docs.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
| --- | --- | --- |
| I. Identical Conditions | Same model, temperature, base prompt, tool schemas and budget as A2. Each helper is bound to a subset of `kit.tools`, unchanged; the fingerprint is the kit's. | ✅ |
| II. Tool-Only World Access | All three jobs see tool results, the reports and A5's own counters. The refusal text for an off-role call names only whose tool it is. | ✅ |
| III. Only the Graph Varies | Only the graph differs: nodes, edges, state and what each node is told (which tools it is offered). Every call that reaches the dungeon counts toward the one budget. | ✅ |
| IV. Structured, Code-Scored Results | Unchanged; A5 adds no result field. | ✅ |
| V. Honest Reporting | No run; the limits may be tuned on dev seeds only. | ✅ |
| VI. No Paid Call Without `--execute` | Tests use the scripted model; a dry-run test checks that no model is built. | ✅ |
| Development Workflow (agents do not write graphs) | The experimenter asked the agent to write A5 (spec Clarifications). | ✅ |

Re-check after Phase 1: unchanged, all ✅.

## Project Structure

### Documentation (this feature)

```text
specs/008-supervisor/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── supervisor.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
src/apl/arch/supervisor.py         # new: A5
src/apl/runner/registry.py         # ARCHITECTURES, SUPPORTS (dungeon)
src/apl/runner/meter.py            # LEAD_ROLES += supervisor
src/apl/runner/compare.py          # REFERENCES supervisor → mapstate
tests/arch/test_supervisor.py      # new
tests/runner/test_supervisor_runs.py  # new
tests/viewer/test_supervisor.py    # new
tests/runner/test_cli_run.py, tests/runner/test_spec.py  # registered-name lists
plan.md, README.md
```

**Structure Decision**: one new module in `src/apl/arch/`, following `plan_execute.py`; the
runner learns the name in the three tables that every architecture uses.

## Complexity Tracking

None.
