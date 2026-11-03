# Implementation Plan: The Rune Floor

**Branch**: `010-rune-floor` (spec directory; work happens on git branch `m10-rune-floor`) | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/010-rune-floor/spec.md`

## Summary

The lab gets a fourth problem, the rune floor: cross a floor of colored tiles from S to G while a
hidden rule decides which steps are safe, and a trap sends the agent back to S. It is built so that
learning the rule from failures is what differs: the colors are given at the start, and only the
rule is hidden. It plugs into the problem table from M5 without changing the other three problems.

- **Constitution 2.3.0** (done before this plan): principle II names the rune floor's tools and
  forbids reading the rule, the trap cells and the reference path; the Experiment Setup describes
  the floors, the reference and the 4× budget; the attempt rule covers a trap.
- **The problem**: a new package `apl.rune` with the signal trace's layers (R1). Cells are named
  as on the survey field, S and G sit on the middle row's ends, four colors (R2). A walk is the
  cells stepped on since S; the rule judges each step with the walk so far (R3).
- **Levels** (R4): R0 7×5 with fixed trap cells (the control), R1 7×5 with a 3-color cycle, R2 9×7
  with a 4-cycle that doubles a color, R3 9×7 with one allowed color per row parity.
- **Generation** (R5): a planted path colored to fit the rule, random colors elsewhere; accepted
  when a safe path exists, the straight row traps, and (R0) a memory-only agent finishes.
- **Reference and budget** (R6): breadth-first search over (cell, rule state), exact; the budget is
  4× it.
- **Scoring**: success is reaching G; rows add traps, repeated traps (same cell, same rule state,
  R8) and walks; a rune report table (R11).
- **Viewer**: `/api/rune`, a floor board with trails, trap crosses and the agent, the rule and the
  reference path under the truth view (R14). `apl rune show` prints a floor (R13).
- **Architectures**, written by the agent (FR-025): A1 unchanged; a `WalkLog` gives A2, A3 and A4
  their memory; A4 treats a trap as a failed attempt; A6 gets a rune branch where code offers the
  moves with what happened on each tile before (R12).

## Technical Context

**Language/Version**: Python 3.12 (pinned). The viewer page is plain HTML, CSS and JavaScript.

**Primary Dependencies**: as in M9: `langgraph` 1.2.x, `langchain` 1.4.x, `langchain-core`,
`langchain-openai`, `langchain-ollama`. Nothing new in `pyproject.toml`.

**Storage**: run folders under `results/` and viewer episodes under `results/viewer/`
(gitignored), with the additive row fields of [contracts/results.md](contracts/results.md).

**Testing**: pytest, ruff and mypy (strict), with the scripted chat model from earlier features.
The tests:

- pin the signal trace's outputs before any change, as M9 pinned the survey's: its prompt
  fingerprint, a dry-run plan and a report from stored rows; the dungeon's and survey's pins stay
  (SC-001);
- generate every rune level and every dev and test seed: determinism, size, colors, S and G, a
  finite reference within the pinned bounds, the straight row not safe (SC-002, R5);
- check the rule families and the search on hand-built floors: each rule's `allows`, the state
  after S and after a trap, the reference against a brute-force count;
- play the scripted agents of R7: the reference path reaches G in exactly the reference (SC-003);
  the learner fits the budget and the repeater runs out on every floor (SC-004); the memory-only
  agent finishes every R0 floor;
- check the environment and tools: steps, S and G, edges, traps and repeats, attempts and
  restarts, counts reproduced from saved steps (SC-006), the boundary test of R15, and the import
  rule for the new modules (FR-019);
- play scripted architectures on the rune floor: A1, A2, A3, A4 (with a trap and a restart, and a
  batch of moves whose first traps: the rest do not run), A6
  (options and their records), and the walk log against an oracle built from the episode;
- plan, refuse, interrupt, continue and report scripted rune runs (US3);
- the viewer API, a scripted episode's events and frames, and replay (US1, SC-005).

The page's JavaScript is checked by hand (quickstart step 5) and with the headless-browser check
used since M3.

**Target Platform**: the experimenter's WSL2 machine; the local vLLM server for watching
episodes. This feature makes no paid or local experiment run.

**Project Type**: Python library with a CLI (`apl`) and a local web page.

**Performance Goals**: generating a floor (a few draws, each a search over at most 63 × 4 states)
takes well under a second, so dry runs and the viewer stay instant.

**Constraints**: no change to dungeon, survey or signal behaviour, results or command output
(FR-020). No paid call without `--execute` (VI). Architectures import only `apl.kit`, `apl.arch`
and each problem's `tools` and `results` modules.

**Scale/Scope**: 4 problems; 4 rune levels; 10 dev and 20 test seeds; 5 architectures on the rune
floor (`react`, `mapstate`, `plan_execute`, `reflexion`, `hybrid`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against v2.3.0, amended for this feature before planning.

| Principle | How this plan complies |
| --- | --- |
| I. Identical Conditions | Every architecture on the rune floor gets its one base prompt, tool schemas and budget from `apl.problems`; the prompt fingerprint covers them. The prompt says a hidden rule exists and what a trap does, never what the rule is about ([contracts/rune-tools.md](contracts/rune-tools.md)). |
| II. Tool-Only World Access | Architectures get `look`, `move` and the free floor through the kit. The walk log and A6's records are built from tool results only, with no copy of any rule (R12). The import test forbids `generator`, `env` and `rules` (R15). |
| III. Only the Graph Varies | Every tool call costs a step, failed ones included; A6's code makes its calls through the tool node; A4's attempts share one budget. The walk log and A6's options are graph state and node instructions. |
| IV. Structured, Code-Scored Results | Same envelope; a trap is a structured result; success, traps, repeated traps and the reference are computed by code (R6, R8). |
| V. Honest Reporting | Dev 1000–1009 and test 2000–2019, keyed by the problem name; the viewer refuses test seeds (R14). |
| VI. No Paid Call Without `--execute` | `--problem rune` changes only what is planned; dry runs and tests call no model. |
| Workflow: user writes graphs | The experimenter asked the agent to write the rune versions of A1–A4 and A6 (spec Clarifications, FR-025) and reviews them. |

**Post-design re-check** (after Phase 1): passes. The contracts add no path to environment
internals, no per-architecture setting and no model call outside `--execute`. The free floor (R2)
matches how the other problems hand over their start view, and the constitution text says the
colors are given at the start.

## Project Structure

### Documentation (this feature)

```text
specs/010-rune-floor/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R15
├── data-model.md        # Phase 1: entities, rules and transitions
├── quickstart.md        # Phase 1: how to check the feature end to end
├── contracts/
│   ├── problems.md      # the problem table entry and the kit
│   ├── rune-tools.md    # base prompt, tools, results, errors
│   ├── architectures.md # registry, WalkLog, A6's rune branch, A3 and A4
│   ├── cli.md           # apl run --problem rune, apl rune show
│   ├── results.md       # row fields, report and comparison
│   └── viewer.md        # /api/rune, events, the page
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
src/apl/
├── problems.py          # PROBLEMS["rune"]
├── kit.py               # docstring: the allowed imports
├── rune/                # new package (R1–R10)
│   ├── __init__.py
│   ├── model.py         # RuneLevel, LEVELS R0–R3, COLORS, cell names, Floor, Action
│   ├── seeds.py         # DEV_SEEDS, TEST_SEEDS
│   ├── rules.py         # Rule, allows, next_state, describe, outcome_of, reference, reference_path
│   ├── generator.py     # generate(level, seed): planted path, colors, acceptance (R5, R7)
│   ├── env.py           # Episode, LogEntry, Outcome, MAX_ATTEMPTS
│   ├── results.py       # agent-facing result types (architectures may import)
│   ├── tools.py         # AgentTools: start, look, move (architectures may import)
│   ├── prompt.py        # BASE_PROMPT, TOOL_SCHEMAS, prompt_fingerprint
│   ├── kit.py           # build_kit
│   ├── frames.py        # the viewer's frames and reference frames
│   ├── render_text.py   # `apl rune show`
│   └── render_svg.py    # the viewer's floor board
├── arch/
│   ├── walk_log.py      # new: the walk log (R12)
│   ├── mapstate.py      # picks WalkLog on rune
│   ├── plan_execute.py  # picks WalkLog on rune
│   ├── reflexion.py     # WalkLog on rune; "trap" joins RESTARTED; calls one at a time, stop at a trap; staleness by `known`
│   ├── hybrid.py        # the rune branch
│   └── react.py         # unchanged
├── runner/
│   ├── registry.py      # SUPPORTS gains "rune"
│   ├── results.py       # rune row fields
│   ├── report.py        # the rune table and spread
│   └── compare.py       # the A6 reference override on rune
├── viewer/
│   ├── app.py           # /api/rune, rune frames, start event, episode-id pattern
│   ├── server.py        # the /api/rune route
│   └── assets/index.html  # the rune board and stats
└── cli.py               # `apl rune show`
tests/
├── rune/                # new: rules, generator, scripted agents, env, tools, boundary, render, kit
├── arch/                # walk_log; scripted rune episodes for A1–A4, A6
├── runner/              # rune plan/run/continue/report; signal outputs pinned
└── viewer/              # rune API, episode events, replay
AGENTS.md                # allowed imports, tools and commands gain the rune floor's
plan.md, README.md       # §2d rune floor, §4 problems column, §7 M10
```

**Structure Decision**: the rune floor mirrors `apl.signal_trace` module by module, with `rules`
in place of `strategy`, and the runner, report and viewer gain one more branch in the places that
already branch on the problem.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Rune result types repeat the other problems' envelope classes | Each problem's `results` module stays self-contained, as decided in M5 | A shared base module would change three problems' import surface for about 30 lines. |
