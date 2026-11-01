# Implementation Plan: Several Problems, and the Survey Field

**Branch**: `005-survey-field` (spec directory; work happens on `main`) | **Date**: 2026-11-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-survey-field/spec.md`

## Summary

The lab gets a second problem, the survey field, and the code learns that there can be more than
one problem. It has six parts:

- **Constitution 2.0.0** first: principle II names each problem's own tools; the budget and level
  rules in "Experiment Setup" become per problem (research R1).
- **Problems**: a small registry, `apl.problems`, maps a problem name to its levels, seeds,
  generator, episode, kit and text renderer. `dungeon` is the default everywhere, and its code and
  outputs stay as they are (R2, R3).
- **The survey field**: a new package `apl.survey` beside `apl.dungeon`, with the same layers:
  model, generator, reference walk, episode, tools, results, text and SVG rendering. Three tools:
  `look`, `move`, `submit`. Up to 4 scouts, one shared budget of 3× the reference walk (R4–R9).
- **Runner and report**: `--problem` on `apl run`, the problem in `run.json` and every row,
  survey columns (submitted and true total, cells seen, parallel turns), and a survey report
  table. Parallel turns are counted runner-side from the model calls between tool calls, so no
  architecture can game them (R11, R12).
- **Viewer**: a problem picker, a survey board (grid, deposits, fog, scout trails) and a tally
  panel with seen, true and submitted totals (R13).
- **Architectures**, written by the agent (FR-029): A1 runs unchanged; a field map
  `apl.arch.field_map` gives A2 and the scouts their memory; A7 gains a collect step and A8 a
  `{"total": N}` answer so an orchestrator can submit; A9's scouts submit themselves (R10, R14).

## Technical Context

**Language/Version**: Python 3.12 (pinned). The viewer page uses plain HTML, CSS and JavaScript.

**Primary Dependencies**: as in M4: `langgraph` 1.2.18, `langchain` 1.4.x, `langchain-core`,
`langchain-openai`, `langchain-ollama`. Nothing new in `pyproject.toml`.

**Storage**: run folders under `results/` and viewer episodes under `results/viewer/`
(gitignored), with the additive fields of [contracts/results.md](contracts/results.md).

**Testing**: pytest, ruff and mypy (strict), with the scripted chat model from M2–M4. The tests:

- pin the dungeon's outputs before any change and compare after: the prompt fingerprint
  `ff9afb3b9f66`, a dry-run plan, a report from stored rows, and every dev dungeon's single-agent
  outcome (SC-001);
- generate every survey level and seed, check size, deposits and reachability, and check the
  reference walk is legal and, on open levels, `cells` steps long (SC-002, SC-003);
- extend the boundary test to the survey tools: results show only the current cell, the result
  shapes are fixed, and architectures import only the allowed modules (SC-005, FR-024);
- play scripted architectures on the survey field: A1, A2, A7–A9 with scripted answers, check the
  field map against an oracle built from the episode, and check parallel turns (SC-007);
- plan, interrupt, continue and report scripted survey runs, and check every refusal (FR-004,
  FR-005).

The page's JavaScript is checked by hand (quickstart step 5) and with the headless-browser check
from M3/M4, adapted to the survey board.

**Target Platform**: the experimenter's WSL2 machine; the local vLLM server on `localhost:8001`
for watching episodes. This feature makes no paid or local experiment run.

**Project Type**: Python library with a CLI (`apl`) and a local web page.

**Performance Goals**: generating a field and its reference walk takes well under a second for
every level, so the viewer and dry runs stay instant. A single-agent S2 episode on the local model
is about 100–300 model calls, a few minutes.

**Constraints**: no change to dungeon behavior, results or command output (FR-002, SC-001). No
paid call without `--execute` (VI). Architectures import only `apl.kit`, `apl.arch` and each
problem's `tools` and `results` modules (FR-024).

**Scale/Scope**: 2 problems, 3 survey levels, 10 dev and 20 test seeds per problem, 5
architectures on the survey field (`react`, `mapstate`, `fanout`, `rounds`, `blackboard`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against v1.1.0, with the amendment to 2.0.0 that this feature makes as its first task
(R1). The gate passes once that amendment is in; the code tasks depend on it.

| Principle | How this plan complies |
| --- | --- |
| I. Identical Conditions | Within a problem every architecture gets that problem's one base prompt, tool schemas and budget rule from `apl.problems`; the prompt fingerprint covers the problem's prompt and tools (R3). Runs cover one problem (FR-005), so conditions never mix. |
| II. Tool-Only World Access | Amended to "each problem's own tools". Survey architectures get `look`, `move`, `submit` through the kit; the field map is built from tool results only (R10). The boundary test covers both problems (FR-024). The field size is in the tool results, not read from the generator (R6). |
| III. Only the Graph Varies | Orchestrator submissions go through scout 0's tool node and cost one step (R14). Every survey tool call counts, failed ones included. Parallel turns are measured by the runner, not reported by the graph (R11). |
| IV. Structured, Code-Scored Results | Survey results use the same envelope; success is `submitted_total == true_total`, computed by code; no LLM judge (R7, R12). |
| V. Honest Reporting | The survey field has its own dev (1000–1009) and test (2000–2019) seeds with the dungeon's numbers; the viewer refuses test seeds for every problem (R9, R13). |
| VI. No Paid Call Without `--execute` | `--problem` changes only what is planned; dry runs and tests make no model call (R12). |
| Workflow: user writes graphs | The experimenter asked the agent to write the survey versions of A1, A2 and A7–A9 (spec Clarifications, FR-029); they review them. |

**Post-design re-check** (after Phase 1): passes. The contracts add no path to environment
internals, no per-architecture setting, and no model call outside `--execute`. The one open item
is the amendment itself, tracked below.

## Project Structure

### Documentation (this feature)

```text
specs/005-survey-field/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R16
├── data-model.md        # Phase 1: entities and their rules
├── quickstart.md        # Phase 1: how to check the feature end to end
├── contracts/
│   ├── problems.md      # the problem registry and what each problem provides
│   ├── survey-tools.md  # the survey tools, results, errors and base prompt
│   ├── architectures.md # A1, A2, A7–A9 on the survey field; the field map
│   ├── cli.md           # --problem, apl survey show, continue and report
│   ├── results.md       # new row and run.json fields
│   └── viewer.md        # viewer API and page changes
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
.specify/memory/constitution.md   # amended to 2.0.0 (R1)
src/apl/
├── problems.py          # new: problem registry, default "dungeon" (R2)
├── kit.py               # Kit gains `problem`; build_kit dispatches per problem (R3)
├── dungeon/             # unchanged behavior
├── survey/              # new package (R4–R9)
│   ├── __init__.py
│   ├── model.py         # SurveyLevel, LEVELS S1–S3, Field, cell names
│   ├── seeds.py         # DEV_SEEDS, TEST_SEEDS (same numbers as the dungeon)
│   ├── generator.py     # generate(level, seed): walls, deposits, reference walk, budget
│   ├── walk.py          # the reference walk
│   ├── env.py           # Episode: scouts, look/move/submit, budget, log, Outcome
│   ├── results.py       # agent-facing result types (architectures may import)
│   ├── tools.py         # AgentTools (architectures may import)
│   ├── prompt.py        # BASE_PROMPT, TOOL_SCHEMAS
│   ├── kit.py           # build_kit for the survey (R3)
│   ├── frames.py        # the viewer's survey snapshots (R13)
│   ├── render_text.py   # `apl survey show`
│   └── render_svg.py    # the viewer's board
├── arch/
│   ├── field_map.py     # new: memory built from survey tool results (R10)
│   ├── mapstate.py      # picks DungeonMap or FieldMap by kit.problem
│   ├── scouts.py        # SharedMap over either map; problem-specific scout text
│   ├── fanout.py        # survey: collect step and submission (R14)
│   ├── rounds.py        # survey: {"total": N} answer
│   ├── blackboard.py    # survey: task text; scouts submit
│   └── react.py         # unchanged
├── runner/
│   ├── registry.py      # SUPPORTS: which problems each architecture plays (R15)
│   ├── spec.py          # RunSpec gains problem; levels and seeds from it
│   ├── episode.py       # plays an episode of the key's problem
│   ├── meter.py         # model-call counter for parallel turns (R11)
│   ├── results.py       # problem + survey fields in rows and run.json
│   ├── run.py           # problem through execute and continue
│   ├── report.py        # survey table; refuses mixed problems
│   └── compare.py       # comparison columns per problem
├── viewer/
│   ├── app.py           # problems in /api/options, /api/survey/<level>/<seed>, problem in start
│   ├── events.py        # survey frames in step events
│   └── assets/index.html  # problem picker, survey board and tally panel
└── cli.py               # --problem; `apl survey show`
tests/
├── survey/              # new: generator, walk, env, tools, boundary, render
├── arch/                # field_map, scripted survey episodes for A1, A2, A7–A9
├── runner/              # survey plan/run/continue/report; dungeon output pinned
└── viewer/              # survey API and saved episodes
```

**Structure Decision**: the survey field mirrors `apl.dungeon` package by package, so each part
has an obvious counterpart and the dungeon stays untouched. Everything that must know which
problem it is serving goes through `apl.problems`, so the runner and viewer each have one place to
branch.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Constitution v1.1.0 names the dungeon's four tools and a fixed 6× budget | A second problem needs its own tools and budget rule | Squeezing the field into look/move/take/use would mean a fake `take` for counting and a 6× budget that lets a lost agent wander 600 steps on S2. The amendment (R1) is task 1, before any code. |
| Survey result types duplicate the dungeon's envelope classes | `apl.dungeon.results` must stay byte-for-byte compatible for the dungeon (FR-002) | A shared base module would change the dungeon's import surface and the boundary test's allowed list for no gain; the duplication is about 30 lines. |
