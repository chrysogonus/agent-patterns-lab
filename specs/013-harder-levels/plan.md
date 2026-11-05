# Implementation Plan: Harder Top Levels for the Signal Trace and the Workshop

**Branch**: `013-harder-levels` (spec directory; git branch `m13-harder-levels`) | **Date**:
2026-11-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/013-harder-levels/spec.md`

## Summary

Add one level at the top of two ladders, built by the generators that already exist: T4 on the
signal trace (256 segments, a tree with 8 pipe ends, runs of at least 4) and W4 on the workshop
(12 craftables, depth 5, 3 conflicts). Both sizes were checked against the current generators and
property tests for all 30 dev and test seeds before planning (research R1, R3). The work is two
table entries, a wider row for long pipes in the signal drawing, the `show` commands reading
`LEVELS`, tests that pin the old levels before the change, the tests that list levels, and the
docs and constitution text that name the level ranges. No tool, prompt or architecture changes.

## Technical Context

**Language/Version**: Python 3.12 (uv)

**Primary Dependencies**: unchanged (LangGraph 1.2, LangChain `init_chat_model`; the viewer's
standard-library HTTP server and one HTML page)

**Storage**: run directories under `results/` (unchanged format)

**Testing**: pytest, ruff (lint and format), mypy (strict); scripted models only, no paid call

**Target Platform**: Linux (WSL2), local

**Project Type**: CLI and local web viewer (single project)

**Performance Goals**: T4 generation about 50 ms a pipe; the test suite grows by about 10 s
(research R10)

**Constraints**: T1–T3 and W1–W3 byte-identical for every seed; saved runs unchanged

**Scale/Scope**: 2 level entries, 1 drawing rule (row width and label column), 2 CLI argument lists, about 10 test files,
3 docs (plan.md, README.md, the constitution)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against v2.5.0; the level ranges it names are amended to T1–T4 and W1–W4 as v2.5.1
(research R11).

| Principle | How this plan complies |
| --- | --- |
| I. Identical Conditions | Every architecture gets the new level's one prompt, tool schemas and budget from `apl.problems`, as on the existing levels; the budget rules are unchanged. |
| II. Tool-Only World Access | No tool, result or start view changes; architectures see T4 and W4 only through the existing tools. |
| III. Only the Graph Varies | No architecture code changes; every architecture that plays the problem plays the new level. |
| IV. Structured, Code-Scored Results | References, budgets, wasted probes and the stuck rule are computed by the existing code; T4's reference is marked as not optimal. |
| V. Honest Reporting | Same seeds (dev 1000–1009, test 2000–2019) keyed by problem and level; the new levels get their own report rows; results stay within a problem. |
| VI. No Paid Call Without `--execute` | Only planning, drawing and scripted tests; no episode is run in this feature. |
| Problem rules (signal, workshop) | The budget, reference and solvability rules apply to the new levels word for word; only the named ranges change. |
| Workflow: user writes graphs | Nothing in `src/apl/arch/` is touched. |

**Post-design re-check** (after Phase 1): passes. The one drawing change keeps T1–T3's pictures
identical (8 a row and a 64 px label column up to 64 segments).

## Project Structure

### Documentation (this feature)

```text
specs/013-harder-levels/
├── plan.md              # this file
├── research.md          # R1–R11
├── data-model.md        # the two level entries and what is derived from them
├── quickstart.md        # checks, show commands, dry runs, viewer
├── contracts/
│   └── levels.md        # where the new levels appear (CLI, viewer, report)
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
src/apl/
├── signal_trace/
│   ├── model.py         # LEVELS: + T4
│   └── render_svg.py    # pipes over 64 segments: 24 a row, label column 80 (R8)
├── workshop/
│   └── model.py         # LEVELS: + W4
└── cli.py               # signal/workshop show: choices from LEVELS (R7)

tests/
├── runner/
│   ├── fixtures/levels-pinned.json   # new: T1–T3 and W1–W3 hashes for all 30 seeds (R4)
│   ├── test_levels_pinned.py         # new: the pinned hashes; `all` includes T4 and W4
│   ├── test_signal_pinned.py         # ["all"] → ["T1", "T2", "T3"] (R5)
│   └── test_workshop_pinned.py       # ["all"] → ["W1", "W2", "W3"] (R5)
├── signal_trace/
│   ├── test_generator.py             # budget table + T4; a T4 shape test like T3's
│   ├── test_strategy.py              # new: every possible broken segment, every level (R10)
│   └── test_render.py                # T4 drawn 24 a row, labels inside the viewBox; T1–T3 unchanged
├── workshop/
│   ├── test_generator.py             # SHAPE and BOUND for W4
│   └── test_render.py                # W4 draws every item once, rows at most 7 wide
└── viewer/
    ├── test_signal.py                # level list; a T4 episode streams and replays
    └── test_workshop.py              # level list; a W4 episode streams and replays

plan.md, README.md                    # level tables, M13 row
.specify/memory/constitution.md       # T1–T4, W1–W4; v2.5.1
```

**Structure Decision**: The existing single project. Every change sits in the files that already
define, draw, list and test the levels; the per-level tests that are parametrized over `LEVELS`
(the signal generator, strategy and boundary tests; the workshop generator, agents and boundary
tests) pick up T4 and W4 without edits.

## Complexity Tracking

No violations.
