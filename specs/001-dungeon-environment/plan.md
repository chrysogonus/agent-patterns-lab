# Implementation Plan: Dungeon Generator, Environment, Tools and Solver

**Branch**: `001-dungeon-environment` (spec directory; work happens on `main`) | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-dungeon-environment/spec.md`

## Summary

M1 builds the simulated world every architecture will play in, with no model involved:

- **Generator:** a seeded generator for L1–L3 that constructs each dungeon so it is solvable and
  meets the level rules.
- **Solver:** a BFS solver that gives the true shortest solution.
- **Environment and tools:** the four agent-facing tools, with structured results, step
  counting, a budget, and an outcome record with the full call log.
- **Drawing:** routes are replayed into frames, and those frames drive a text map with a route
  overlay and a self-contained HTML picture that animates the route.

Everything is pure Python 3.12 with the standard library only, behind a minimal `apl dungeon
show` command. The key design choices are:

- **Generation:** build by construction, then check, then retry (research R2).
- **Agent boundary:** enforced by an import test and a test on result contents (R5).
- **One source for all drawing:** frames come from replaying through the real environment, so
  the text map, the picture and the animation can't disagree with it (R7).

## Technical Context

**Language/Version**: Python 3.12 (pinned in `.python-version` and `requires-python`)

**Primary Dependencies**: Standard library only (`random`, `dataclasses`, `enum`, `json`,
`html`, `argparse`, `importlib.resources`). No LangGraph or LangChain in M1.

**Storage**: None. Route files and outcome records are JSON files the user passes in or writes.

**Testing**: pytest, ruff, mypy (strict), all already set up in `pyproject.toml`.

**Target Platform**: Linux, macOS and Windows terminals; any current web browser for the HTML
output, offline.

**Project Type**: Python library with a small CLI (`apl`).

**Performance Goals**: Generating and solving all dev and test seed sets (90 dungeons) in under
10 s (SC-006). The expected time is well under 1 s.

**Constraints**:

- Generation is deterministic across runs and machines (FR-009).
- The HTML output is byte-identical for the same input, and needs no network (FR-026).
- No paid calls (Constitution VI).

**Scale/Scope**: Grids up to 5×5, at most 2 locks, routes up to about 3 × 40 steps. Roughly
10 source modules and 10 test modules.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies | Status |
| --- | --- | --- |
| I. Identical Conditions | The budget is computed by the environment from the dungeon (`3 × optimal`); no caller can set it. Tool descriptions for the model are deferred to M2 (research R12) | PASS |
| II. Tool-Only World Access | Architectures get only `AgentTools` and the result types; an `ast` test forbids every other `apl.dungeon` import from `src/apl/arch/`; results contain only the current room (R5, SC-007); labels reveal no position (R3) | PASS |
| III. Only the Graph Varies | One step counter per episode counts every tool call, including invalid ones. There is no reset, so a retry (A4, in M4) cannot get a fresh budget from M1 code | PASS |
| IV. Structured, Code-Scored Results | Frozen dataclasses with fixed `to_dict()` shapes, error codes and end reasons as enums, and an outcome record with the raw numbers (contracts/tools.md, contracts/outcome.md). No LLM judge | PASS |
| V. Honest Reporting | Fixed, disjoint dev and test seed sets, checked by a test (R11) | PASS |
| VI. No Paid Call Without `--execute` | No model dependency or call anywhere in M1 | PASS |
| Experiment Setup | Solvable by construction and checked by the BFS solver over (room, keys, doors); budget 3 × optimal; levels as in plan.md §2 | PASS |
| Development Workflow | Nothing is written in `src/apl/arch/`; pytest, ruff and mypy are the done gate | PASS |

**Post-design re-check (after Phase 1)**: PASS. The data model and contracts add no way around
the tools: frames, the solver and the layout live in modules that the boundary test keeps away
from architectures. Nothing goes in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/001-dungeon-environment/
├── spec.md
├── plan.md              # this file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── tools.md         # agent-facing tools and result shapes
│   ├── outcome.md       # outcome record and log
│   └── cli.md           # apl dungeon show, text map, HTML
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2, written by /speckit-tasks
```

### Source Code (repository root)

```text
src/apl/
├── __init__.py
├── cli.py                    # `apl` entry point (argparse): `apl dungeon show`
└── dungeon/
    ├── __init__.py           # public runner-side API: generate, solve, start_episode, ...
    ├── model.py              # Direction, Level, LEVELS, Edge, Layout, Dungeon, Action, Solution
    ├── rules.py              # check_level_rules (FR-001–FR-008), shared by generator and tests
    ├── generator.py          # generate(level, seed) (research R1–R3)
    ├── solver.py             # solve(layout) (R4)
    ├── results.py            # agent-facing result types and enums (contracts/tools.md)
    ├── env.py                # Episode, LogEntry, Outcome, start_episode
    ├── tools.py              # AgentTools: look, move, take, use (the only agent surface)
    ├── seeds.py              # DEV_SEEDS, TEST_SEEDS
    ├── frames.py             # Frame, build_frames (R7)
    ├── render_text.py        # text map + route overlay (R8)
    ├── render_html.py        # SVG picture + embedded frames (R9)
    └── assets/
        └── player.html       # player template: inline CSS and JS

tests/
├── __init__.py
├── test_package.py           # exists
└── dungeon/
    ├── __init__.py
    ├── reference.py          # hand-built reference Layouts with known answers
    ├── test_model.py         # Layout validation, Edge, LEVELS, budget, from_layout
    ├── test_rules.py         # check_level_rules reports each broken rule
    ├── test_generator.py     # level rules, determinism, golden fingerprints, variety, timing
    ├── test_labels.py        # SC-009
    ├── test_solver.py        # reference dungeons with known answers, unsolvable case
    ├── test_replay.py        # solution replay for every dev and test dungeon (SC-002)
    ├── test_env.py           # every error code, step counting, budget, end reasons, log
    ├── test_boundary.py      # result shapes (SC-007), import boundary for src/apl/arch/
    ├── test_seeds.py         # disjoint seed sets
    ├── test_frames.py        # frames vs. environment state (SC-012), log replay check
    ├── test_render.py        # map/picture content, determinism, no external refs
    └── test_cli.py           # `apl dungeon show` smoke tests and exit codes
```

**Structure Decision**: A single library package under the existing `src/apl/`, with the dungeon
in `src/apl/dungeon/` as `plan.md` and the README lay out, and tests mirroring it under
`tests/dungeon/`. `pyproject.toml` gains `[project.scripts] apl = "apl.cli:main"`. The package data
(`assets/player.html`) lives inside the module directory, where `uv_build` picks up files. A
test loads it through `importlib.resources`, and one task checks that a built wheel contains
it.

## Complexity Tracking

No constitution violations, so nothing to justify.
