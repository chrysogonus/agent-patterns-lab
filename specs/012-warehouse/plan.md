# Implementation Plan: The Warehouse

**Branch**: `012-warehouse` (spec directory; work happens on git branch `m12-warehouse`) | **Date**: 2026-11-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/012-warehouse/spec.md`

## Summary

The lab gets a sixth problem, the warehouse: robots find hidden packages in the aisles of a known
floor and carry them to a drop zone, one at a time. It is built so that adapting a split of the
work is what differs: packages are spread unevenly, so a split decided before anyone has looked
leaves a robot idle. It plugs into the problem table without changing the other five problems.

- **Constitution 2.5.0** (done before this plan): principle II names `look`, `move`, `pick`,
  `drop` and forbids reading package positions except through the robots' views, and the
  reference; the Experiment Setup describes the warehouse.
- **The problem**: a new package `apl.warehouse`, shaped like `apl.survey` with its scouts (R1).
  Floors of 3 or 5 aisles between single shelf rows, two cross corridors, the dock and D off the
  aisles (R2). A robot sees the packages of the corridors it stands in (R3), carries one, picks and
  drops with no arguments (R4). Package names are shuffled; the count is free (R5).
- **Reference and budget** (R6): a single robot clearing the aisles north to south; budget 3×.
  P2 and P3 draws are accepted only if a blind split idles a robot and a replanning split is faster
  in parallel turns (R7).
- **Scoring**: success is every package delivered; rows add `delivered`, `packages`,
  `idle_robot_turns`, with the shared `parallel_turns` and `scouts` (R8, R9).
- **Viewer**: `/api/warehouse`, the floor as an SVG with corridor-based fog, packages on cells or on
  their robots, warehouse stats rows; `apl warehouse show` prints a floor (R14, R15).
- **Architectures**, written by the agent (FR-024): A1 unchanged; a `FloorMap` for A2 and the
  scouts; warehouse texts for A7–A9, with a warehouse-only claim pattern for A9 (R12, R13). The
  About card covers the five pairs (R17).

## Technical Context

**Language/Version**: Python 3.12 (pinned). The viewer page is plain HTML, CSS and JavaScript.

**Primary Dependencies**: as in M11. Nothing new in `pyproject.toml`.

**Storage**: run folders under `results/` and viewer episodes under `results/viewer/`
(gitignored), with the additive row fields of [contracts/results.md](contracts/results.md).

**Testing**: pytest, ruff and mypy (strict), with the scripted chat model. The tests:

- pin the workshop's outputs before any change (fingerprint and dry-run plan); the other pins stay
  (SC-001);
- generate every warehouse level and every dev and test seed: determinism, geometry, the level's
  spread, distinct package cells, every package reachable, budget 3× the reference (SC-002);
- check the reference and the scripted agents of R7 through the environment: the reference
  delivers everything in exactly its steps (SC-003); on P2 and P3 the blind split idles a robot and
  the replanning split takes fewer parallel turns (SC-004);
- check the environment and tools: every view, result and error of the contract, sight by
  corridor, robots added up to 4, calls in robot order, parallel turns and idle robot-turns rebuilt
  from saved steps (SC-006), the boundary test (R16, FR-019);
- play scripted architectures on the warehouse: A1, A2 (the floor map against an oracle built from
  the episode), A7, A8, A9 (claims), and the dungeon and survey field behaviour of A7–A9 unchanged;
- plan, refuse, interrupt, continue and report scripted warehouse runs (US3);
- the viewer API, a scripted episode's events and frames, replay, and the About card pairs (US1,
  SC-005).

The page is checked with the headless browser and by hand (quickstart 5–6).

**Target Platform**: the experimenter's WSL2 machine. This feature makes no paid or local
experiment run.

**Project Type**: Python library with a CLI (`apl`) and a local web page.

**Performance Goals**: generating a warehouse (a few draws, each with three scripted plays on a
floor of at most 99 cells) takes well under a second.

**Constraints**: no change to the other five problems' behaviour, results or command output
(FR-020). No paid call without `--execute` (VI). Architectures import only `apl.kit`, `apl.arch`
and each problem's `tools` and `results`.

**Scale/Scope**: 6 problems; 3 warehouse levels; 10 dev and 20 test seeds; 5 architectures on the
warehouse; up to 4 robots.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against v2.5.0, amended for this feature before planning.

| Principle | How this plan complies |
| --- | --- |
| I. Identical Conditions | Every architecture on the warehouse gets its one base prompt, tool schemas and budget from `apl.problems`; the prompt explains the floor and the tools, never how to split the work ([contracts/warehouse-tools.md](contracts/warehouse-tools.md)). |
| II. Tool-Only World Access | Architectures get the four tools and the free start view (floor plan, package count, first view). The floor map and A9's board come from tool results only. The import test forbids `generator`, `env`, `plans` and `model` (R16). |
| III. Only the Graph Varies | Every call of every robot costs a step from one budget; more robots buy no steps. The orchestrators' warehouse texts are node instructions. |
| IV. Structured, Code-Scored Results | Same envelope; success, delivered, parallel turns, idle robot-turns and the reference are computed by code (R6, R8). |
| V. Honest Reporting | Dev 1000–1009 and test 2000–2019, keyed by the problem name; the viewer refuses test seeds. |
| VI. No Paid Call Without `--execute` | `--problem warehouse` changes only what is planned; dry runs and tests call no model. |
| Workflow: user writes graphs | The experimenter asked the agent to write the warehouse versions of A1, A2 and A7–A9 (FR-024) and reviews them. |

**Post-design re-check** (after Phase 1): passes. The package count is free, which tells an agent
how many to find but never where; the views never show a package outside the robot's corridors.

## Project Structure

### Documentation (this feature)

```text
specs/012-warehouse/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R18
├── data-model.md        # Phase 1: entities and transitions
├── quickstart.md        # Phase 1: how to check the feature end to end
├── contracts/
│   ├── problems.md      # the problem table entry and the kit
│   ├── warehouse-tools.md  # base prompt, tools, results, errors
│   ├── architectures.md # FloorMap, SharedMap, A2, A7–A9, About card
│   ├── cli.md           # apl run --problem warehouse, apl warehouse show
│   ├── results.md       # row fields, report and comparison
│   └── viewer.md        # /api/warehouse, frames, the page
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
src/apl/
├── problems.py          # PROBLEMS["warehouse"]
├── kit.py               # docstring: the allowed imports
├── warehouse/           # new package (R1–R8)
│   ├── __init__.py
│   ├── model.py         # WarehouseLevel, LEVELS P1–P3, Floor, Action, cell names
│   ├── seeds.py         # DEV_SEEDS, TEST_SEEDS
│   ├── plans.py         # shortest paths, reference_calls, blind and replanning splits
│   ├── generator.py     # generate(level, seed): packages, spread, acceptance (R2, R7)
│   ├── env.py           # Episode, LogEntry, Outcome, MAX_SCOUTS, MAX_ATTEMPTS
│   ├── results.py       # agent-facing views and errors (architectures may import)
│   ├── tools.py         # AgentTools: start, look, move, pick, drop (architectures may import)
│   ├── prompt.py        # BASE_PROMPT, TOOL_SCHEMAS, prompt_fingerprint
│   ├── kit.py           # build_kit with add_scout
│   ├── frames.py        # the viewer's frames and reference frames
│   ├── render_text.py   # `apl warehouse show`
│   └── render_svg.py    # the viewer's floor
├── arch/
│   ├── floor_map.py     # new: the floor map (R12)
│   ├── mapstate.py      # picks FloorMap on warehouse
│   ├── scouts.py        # SharedMap with FloorMap; robot texts; warehouse claim pattern
│   ├── fanout.py        # warehouse texts; no collect step
│   ├── rounds.py        # warehouse texts
│   ├── blackboard.py    # warehouse task
│   └── react.py         # unchanged
├── runner/
│   ├── registry.py      # SUPPORTS gains "warehouse"
│   ├── results.py       # warehouse row fields, end reason "delivered"
│   ├── report.py        # the warehouse table and spread
│   └── compare.py       # the parallel-turns comparison on the warehouse
├── viewer/
│   ├── about.py         # warehouse texts
│   ├── app.py           # /api/warehouse, frames, start event, episode-id pattern
│   ├── server.py        # the /api/warehouse route
│   └── assets/index.html  # floor, fog by `seen`, packages, stats
└── cli.py               # `apl warehouse show`
tests/
├── warehouse/           # new: model, plans, generator, agents, env, boundary, render, kit
├── arch/                # floor_map; scripted warehouse episodes for A1, A2, A7–A9
├── runner/              # warehouse plan/run/continue/report; workshop outputs pinned
└── viewer/              # warehouse API, episode events, replay, About pairs
AGENTS.md                # allowed imports, tools and commands gain the warehouse's
plan.md, README.md       # §2f warehouse, §4 problems column, §7 M12
```

**Structure Decision**: the warehouse mirrors `apl.survey` module by module (several bodies, turn
source, the frame shape), with `plans` holding the reference and the scripted splits. No
architecture changes structure: A7–A9 gain warehouse texts and the shared map gains a third map
type.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Warehouse result types repeat the other problems' envelope classes | Each problem's `results` module stays self-contained, as decided in M5 | A shared base module would change five problems' import surface. |
| The generator plays scripted splits to accept a draw | SC-004 must hold on every seed by construction | Hand-picked layouts would not cover 30 seeds per level. |
