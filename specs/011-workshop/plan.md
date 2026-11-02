# Implementation Plan: The Workshop

**Branch**: `011-workshop` (spec directory; work happens on git branch `m11-workshop`) | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/011-workshop/spec.md`

## Summary

The lab gets a fifth problem, the workshop: craft a goal item from hidden recipes and a limited
stock, where the obvious recipe for one part uses up a scarce material another part needs. It is
built so that planning ahead is what differs. It plugs into the problem table without changing the
other four problems.

- **Constitution 2.4.0** (done before this plan): principle II names `look`, `inspect`, `gather`,
  `craft` and forbids reading recipes except through `inspect`, the reference plan and the stuck
  check; the Experiment Setup describes the workshop; the attempt rule covers getting stuck.
- **The problem**: a new package `apl.workshop` (R1). Items are words from fixed lists (R2). Trees
  of 3, 5 and 8 craftables (W1–W3) with 0, 1 and 2 conflicts; a conflict hides a scarce material
  one level down behind a tempting first recipe (R3, R4). Code ends an episode as stuck once the
  goal cannot be made (R5).
- **Reference and budget** (R6): the reference plan's inspections, gathers and crafts; budget 3×.
- **Scoring**: success is crafting the goal; rows add stuck, wasted scarce units, inspected and
  crafted (R8, R11).
- **Viewer**: `/api/workshop`, the tree drawn as in the mock-up with `?` for uninspected items, the
  stock turning red, held-item badges (R14). `apl workshop show` prints a workshop (R13).
- **Architectures**, written by the agent (FR-026): A1 unchanged; a `WorkshopLog` for A2, A3, A4
  and A5's helpers; A4 treats getting stuck as a failed attempt and runs calls one at a time; A5's
  helpers become per-problem, a researcher and a crafter on the workshop; A6 offers the actions it
  can take now (R12).

## Technical Context

**Language/Version**: Python 3.12 (pinned). The viewer page is plain HTML, CSS and JavaScript.

**Primary Dependencies**: as in M10. Nothing new in `pyproject.toml`.

**Storage**: run folders under `results/` and viewer episodes under `results/viewer/`
(gitignored), with the additive row fields of [contracts/results.md](contracts/results.md).

**Testing**: pytest, ruff and mypy (strict), with the scripted chat model. The tests:

- pin the rune floor's outputs before any change (fingerprint and dry-run plan); the other pins
  stay (SC-001);
- generate every workshop level and every dev and test seed: determinism, the level's craftables,
  depth and conflicts, the tree with no cycle, scarce stock 1, the reference feasible, the greedy
  plan stuck on W2–W3 and not on W1, budget 3× (SC-002);
- check the stuck check and the plans on hand-built workshops (the mock-up's lantern among them);
- play the scripted agents of R7 through the environment: reference (exactly the reference, no
  waste, SC-003), greedy (stuck on W2–W3), planner (within budget, SC-004);
- check the environment and tools: every result shape and error of the contract, waste, stuck,
  attempts and restarts, counts rebuilt from saved steps (SC-006), the boundary test of R15, the
  import rule (FR-019);
- play scripted architectures on the workshop: A1, A2, A3, A4 (stuck, restart, one call at a time),
  A5 (researcher and crafter, refused cross-calls), A6 (options and their order), and the workshop
  log against an oracle built from the episode;
- plan, refuse, interrupt, continue and report scripted workshop runs (US3);
- the viewer API, a scripted episode's events and frames, and replay (US1, SC-005).

The page is checked with the headless-browser script used since M3, and by hand (quickstart 5).

**Target Platform**: the experimenter's WSL2 machine. This feature makes no paid or local
experiment run.

**Project Type**: Python library with a CLI (`apl`) and a local web page.

**Performance Goals**: generating a workshop (a few draws, each a check over at most 2³ recipe
choices) takes well under a second.

**Constraints**: no change to the other four problems' behaviour, results or command output
(FR-020). No paid call without `--execute` (VI). Architectures import only `apl.kit`, `apl.arch`
and each problem's `tools` and `results`.

**Scale/Scope**: 5 problems; 3 workshop levels; 10 dev and 20 test seeds; 6 architectures on the
workshop.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against v2.4.0, amended for this feature before planning.

| Principle | How this plan complies |
| --- | --- |
| I. Identical Conditions | Every architecture on the workshop gets its one base prompt, tool schemas and budget from `apl.problems`; the prompt explains the workshop and the tools, never planning advice ([contracts/workshop-tools.md](contracts/workshop-tools.md)). |
| II. Tool-Only World Access | Architectures get the four tools and the free start view. The workshop log and A6's options come from tool results only; neither plans nor knows which materials are scarce. The import test forbids `generator`, `env`, `plans` and `model` (R15). |
| III. Only the Graph Varies | Every tool call costs a step; A5's helpers and A6's code call through the tool node; A4's attempts share one budget. A5's per-problem helpers and texts are graph and node instructions. |
| IV. Structured, Code-Scored Results | Same envelope; success, stuck, waste and the reference are computed by code (R5, R6, R8). |
| V. Honest Reporting | Dev 1000–1009 and test 2000–2019, keyed by the problem name; the viewer refuses test seeds. |
| VI. No Paid Call Without `--execute` | `--problem workshop` changes only what is planned; dry runs and tests call no model. |
| Workflow: user writes graphs | The experimenter asked the agent to write the workshop versions of A1–A6 (spec Clarifications, FR-026) and reviews them. |

**Post-design re-check** (after Phase 1): passes. The stuck result tells an agent only that the goal
can no longer be made, which it could work out from what it saw; it never says why.

## Project Structure

### Documentation (this feature)

```text
specs/011-workshop/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R15
├── data-model.md        # Phase 1: entities, plans and transitions
├── quickstart.md        # Phase 1: how to check the feature end to end
├── contracts/
│   ├── problems.md      # the problem table entry and the kit
│   ├── workshop-tools.md  # base prompt, tools, results, errors
│   ├── architectures.md # registry, WorkshopLog, A4, A5's helpers, A6's options
│   ├── cli.md           # apl run --problem workshop, apl workshop show
│   ├── results.md       # row fields, report and comparison
│   └── viewer.md        # /api/workshop, events, the page
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
src/apl/
├── problems.py          # PROBLEMS["workshop"]
├── kit.py               # docstring: the allowed imports
├── workshop/            # new package (R1–R10)
│   ├── __init__.py
│   ├── model.py         # WorkshopLevel, LEVELS W1–W3, names, Workshop, Action
│   ├── seeds.py         # DEV_SEEDS, TEST_SEEDS
│   ├── plans.py         # feasible, reference_calls, greedy_calls, planner_calls, reference_use
│   ├── generator.py     # generate(level, seed): tree, conflicts, stock, acceptance (R3–R6)
│   ├── env.py           # Episode, LogEntry, Outcome, MAX_ATTEMPTS
│   ├── results.py       # agent-facing result types (architectures may import)
│   ├── tools.py         # AgentTools: start, look, inspect, gather, craft (architectures may import)
│   ├── prompt.py        # BASE_PROMPT, TOOL_SCHEMAS, prompt_fingerprint
│   ├── kit.py           # build_kit
│   ├── frames.py        # the viewer's frames and reference frames
│   ├── render_text.py   # `apl workshop show`
│   └── render_svg.py    # the viewer's tree
├── arch/
│   ├── workshop_log.py  # new: the workshop log (R12)
│   ├── mapstate.py      # picks WorkshopLog on workshop
│   ├── plan_execute.py  # picks WorkshopLog on workshop
│   ├── reflexion.py     # WorkshopLog; "stuck" joins RESTARTED; one call at a time on workshop
│   ├── supervisor.py    # per-problem helpers: researcher and crafter on the workshop
│   ├── hybrid.py        # the workshop branch
│   └── react.py         # unchanged
├── runner/
│   ├── registry.py      # SUPPORTS gains "workshop" (supervisor too)
│   ├── results.py       # workshop row fields, end reason "stuck"
│   ├── report.py        # the workshop table and spread
│   └── compare.py       # the A6 reference override on workshop
├── viewer/
│   ├── app.py           # /api/workshop, frames, start event, episode-id pattern
│   ├── server.py        # the /api/workshop route
│   └── assets/index.html  # the tree, stock, inventory and stats
└── cli.py               # `apl workshop show`
tests/
├── workshop/            # new: model, plans, generator, agents, env, boundary, render, kit
├── arch/                # workshop_log; scripted workshop episodes for A1–A6
├── runner/              # workshop plan/run/continue/report; rune outputs pinned
└── viewer/              # workshop API, episode events, replay
AGENTS.md                # allowed imports, tools and commands gain the workshop's
plan.md, README.md       # §2e workshop, §4 problems column, §7 M11
```

**Structure Decision**: the workshop mirrors `apl.rune` module by module, with `plans` in place of
`rules`. A5 is the only architecture whose structure changes: its two helpers are looked up by
problem instead of being fixed to the dungeon's.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Workshop result types repeat the other problems' envelope classes | Each problem's `results` module stays self-contained, as decided in M5 | A shared base module would change four problems' import surface. |
