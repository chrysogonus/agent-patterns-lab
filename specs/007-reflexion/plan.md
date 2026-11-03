# Implementation Plan: A4 Reflexion

**Branch**: `007-reflexion` (spec directory; work happens on `main`) | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-reflexion/spec.md`

## Summary

A4 retries with notes. Unlike A3, it needs support below the architecture:

- **Constitution 2.1.0** first: "Experiment Setup" states the attempt rule (research R9).
- **Problems**: both `Episode` classes learn `restart()`, an attempt counter and a cap of 3
  (`MAX_ATTEMPTS`); a restart resets the world and costs no step. On the survey field, a wrong
  total by a retrying architecture ends the attempt and restarts the field (R1, R3). Logs,
  outcomes and frames carry the attempt only when it is above 1, so nothing else changes (R4).
- **Kit and runner**: `kit.restart` and `kit.max_attempts`; `registry.RETRYING`; `play_episode`
  raises the cap only for retrying architectures; rows record attempts; the report adds an
  "Attempts" section when there is something to show; the reflector counts as a lead call; A4's
  reference is `mapstate` (R2, R7).
- **Viewer**: a `restart` event, attempt numbers in frames and stats, the current attempt's trail
  and fog, earlier trails dashed (R8).
- **A4** (`src/apl/arch/reflexion.py`), written by the agent: an A2 actor per attempt, a
  reflector after each failed attempt, a restart node; an attempt fails on a give-up, a wrong
  total, or 12 turns in a row that revealed nothing new (R5, R6).

## Technical Context

**Language/Version**: Python 3.12; the viewer page in plain HTML, CSS and JavaScript.

**Primary Dependencies**: unchanged (`langgraph` 1.2.x, `langchain` 1.4.x).

**Storage**: run folders and viewer episodes as before; additive optional fields only
([data-model.md](data-model.md)).

**Testing**: pytest, ruff, mypy (strict), the scripted model; research R10 lists the tests. The
page is checked by hand (quickstart step 4).

**Target Platform**: the experimenter's WSL2 machine. No experiment run in this feature.

**Project Type**: Python library with a CLI and a local web page.

**Performance Goals**: none new.

**Constraints**: constitution I–VI; byte-identical outputs for every non-retrying architecture
(pinned tests from specs/005); every A4 loop bounded by constants, the cap or the budget.

**Scale/Scope**: two env modules, two frame modules, kit, runner (episode, results, report, meter,
registry, compare), viewer (app, page), one architecture, tests, docs.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Status |
| --- | --- | --- |
| I. Identical Conditions | Same model, base prompt, tool schemas and budget for A4; the restart is a kit capability, not a tool, so the fingerprint is unchanged. A4 adds node instructions after the base prompt only. | ✅ |
| II. Tool-Only World Access | A4 sees tool results, its notes and its own counters. A restart reveals nothing: the restarted world looks exactly like `kit.start`. The wrong-total result says only right or wrong and the attempts left. | ✅ |
| III. Only the Graph Varies | Every tool call of every attempt counts toward the one budget, as the principle requires for A4. | ✅ |
| IV. Structured, Code-Scored Results | Attempts are structured fields; scoring by code (the last submission, the exit). | ✅ |
| V. Honest Reporting | No run; `MAX_STALE` may be tuned on dev seeds only. | ✅ |
| VI. No Paid Call Without `--execute` | No new model path outside episodes; scripted tests. | ✅ |
| Experiment Setup | The attempt rule is new; T001 amends the constitution (2.1.0) before code. | ✅ after T001 |
| Workflow: graphs by the user | The experimenter asked the agent to write A4. | ✅ |

**Post-design re-check**: unchanged. The one asymmetry, that a retrying architecture learns
whether its total was wrong, is the rule the amendment states and the attempt cap bounds.

## Project Structure

### Documentation (this feature)

```text
specs/007-reflexion/
├── plan.md, research.md (R1–R10), data-model.md, quickstart.md
├── contracts/attempts.md, contracts/reflexion.md
├── checklists/requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
.specify/memory/constitution.md   # 2.1.0: attempts
src/apl/
├── kit.py                        # Kit.restart, Kit.max_attempts; dungeon build_kit
├── dungeon/env.py, frames.py     # restart, attempts in log/outcome/frames, replay
├── survey/env.py, frames.py, results.py, kit.py   # restart, wrong-total attempt, attempts
├── arch/reflexion.py             # new: A4
├── runner/registry.py, episode.py, results.py, report.py, meter.py, compare.py
└── viewer/app.py, assets/index.html
tests/
├── dungeon/test_attempts.py, survey/test_attempts.py      # new
├── arch/test_reflexion.py, runner/test_reflexion_runs.py, viewer/test_reflexion.py  # new
plan.md, README.md
```

**Structure Decision**: the existing layout; A4 reuses `apl.arch.dungeon_map`,
`apl.arch.field_map` and A2's instruction texts.

## Complexity Tracking

No constitution violations.
