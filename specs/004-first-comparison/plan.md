# Implementation Plan: First Comparison, with Orchestrator Architectures

**Branch**: `004-first-comparison` (spec directory; work happens on `main`) | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-first-comparison/spec.md`

## Summary

M4 runs the lab's first comparison and adds three orchestrator architectures. It has five parts:

- **Several scouts**: an episode can have up to 4 scouts, each with its own position and inventory,
  sharing doors, items and one step budget. Architectures get more scouts through
  `kit.add_scout()`. Scout 0 is the existing agent, so the single-agent architectures run the same
  code on the same state (research R1–R5).
- **A7–A9**: `fanout`, `rounds` and `blackboard`, built on one shared scout (A2's map-state agent
  with a task) and one lockstep turn: the scouts' model calls run in parallel, then their tool calls
  are applied in scout order (R3, R7–R9).
- **Viewer**: one marker and trail per scout, turns labelled by role (R6).
- **The run**: the parked design's interleaved order, `apl continue`, code identity and the stop
  after 3 provider failures (R10–R13). The run is 7 architectures × L1–L3 × dev seed 1000 × 1
  repeat = 21 episodes on `openai:gpt-6-luna` (R16).
- **The report and conclusion**: a "Comparison" section with all architectures side by side per
  level and their differences to a reference architecture (R14), and a written conclusion (R15).

## Technical Context

**Language/Version**: Python 3.12 (pinned). The viewer page uses plain HTML, CSS and JavaScript.

**Primary Dependencies**: as in M3: `langgraph` 1.2.18 (`Send` for the parallel scout calls),
`langchain` 1.4.x, `langchain-core`, `langchain-openai`, `langchain-ollama`. Nothing new in
`pyproject.toml`.

**Storage**: run folders under `results/` and viewer episodes under `results/viewer/` (gitignored),
with the additive fields of [contracts/results.md](contracts/results.md). The conclusion goes to
`docs/findings/`.

**Testing**: pytest, ruff and mypy (strict). The scripted chat model from M2/M3, with strategies
that read the messages (not a shared queue) so that parallel scout calls give the same answers in
any order. The tests:

- pin the single-agent outcomes of every dev dungeon before the environment changes, and compare
  after (SC-001);
- play scripted scouts and replay their logs (SC-002);
- play each orchestrator with scripted answers and check the merged map against an oracle built from
  the frames (SC-003, extending M3's `tests/arch/oracle.py`);
- interrupt and continue scripted runs (SC-004), and check every refusal (FR-015);
- build the comparison from hand-written rows (SC-005).

The page's JavaScript is checked by hand (quickstart step 3) and with the headless-browser check
used for the M3 walking fix, adapted to several scouts.

**Target Platform**: the experimenter's WSL2 machine. The M4 run calls OpenAI's API; development
and the viewer use the local vLLM server on `localhost:8001`.

**Project Type**: Python library with a CLI (`apl`) and a local web page.

**Performance Goals**: the 21-episode run completes in well under two hours (R16). The parallel
scout calls make a lockstep turn about as long as its slowest model call.

**Constraints**:

- No paid call without `--execute`; tests make none.
- The base prompt, the tool schemas and the prompt fingerprint are unchanged.
- A1, A2, A2r and A6 are unchanged, and their outcomes stay byte for byte the same (FR-005).
- The architecture import boundary is unchanged.
- One episode at a time (FR-012); parallelism exists only inside an orchestrator episode.

**Scale/Scope**:

- 4 new architecture modules (`scouts.py`, `fanout.py`, `rounds.py`, `blackboard.py`) and small
  additions to `dungeon_map.py`;
- 1 new runner module (`compare.py`);
- changes to `env.py`, `frames.py`, `kit.py`, `meter.py`, `results.py`, `run.py`, `spec.py`,
  `report.py`, `registry.py`, `cli.py`, `viewer/events.py`, `viewer/app.py`, `viewer/assets/index.html`;
- about 8 new or extended test modules.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies | Status |
| --- | --- | --- |
| I. Identical Conditions | All seven architectures run in one run with one settings record and `kit.model`. Scouts and orchestrators use the same model object; the role is metadata only and changes nothing sent. The scout limit (4) is set by the shared setup, not per architecture | PASS |
| II. Tool-Only World Access | Every scout acts only through the four tools of its own tool node. `add_scout` reveals only the start room, as a `look` would (R2). Merged maps come only from tool results (R8). The import boundary covers the new modules | PASS |
| III. Only the Graph Varies | The orchestrators differ only in graph, state and node instructions. Every tool call of every scout counts toward the episode's single step budget (contracts/scouts.md). Orchestrator re-asks cost no step, like A6's | PASS |
| IV. Structured, Code-Scored Results | New fields (`scout`, `scouts`, `orchestrator_calls`, `role`) are structured. The comparison is computed by code from rows (R14). No LLM judges | PASS |
| V. Honest Reporting | The run uses dev seed 1000 only; the report and conclusion carry the development notice. Test seeds stay unused | PASS |
| VI. No Paid Call Without `--execute` | `apl run` and `apl continue` are dry runs without `--execute`; the dry run shows a hard cost bound from the token cap. Tests use the scripted model with the network blocked | PASS |
| Experiment Setup | Levels, budget (6×), solver and seed split are unchanged. Efficiency stays measured against the single-agent shortest solution, for every architecture | PASS |
| Development Workflow | The spec assumes the experimenter asks the agent to write A7–A9, as with A2r and A6; this must be confirmed before `/speckit-implement` writes them (Constitution: "unless the user asks") | PASS, pending confirmation |

**Post-design re-check (after Phase 1)**: PASS.

- No amendment is needed: Principle III's "single step budget" holds with several scouts, and
  Principle II applies to each scout. The Experiment Setup does not assume one agent beyond the
  solver, which stays the reference.
- A PATCH clarification of Principle III ("every scout's calls") would make the rule explicit; it
  can be made with `/speckit-constitution` but is not required.
- The model-calls bound in the dry run becomes an estimate (contracts/cli.md); the token and cost
  bounds, which Constitution VI relies on, stay hard.

Nothing goes in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/004-first-comparison/
├── spec.md
├── plan.md              # this file
├── research.md          # Phase 0: R1–R6 scouts, R7–R9 orchestrators, R10–R13 run, R14–R16 report and run
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── scouts.md        # environment and kit with several scouts
│   ├── orchestrators.md # A7–A9: graphs, model input, answers
│   ├── cli.md           # apl run order, code line, apl continue, exit codes
│   ├── results.md       # log, outcome, row, transcript, report comparison
│   └── viewer.md        # events, frames, page
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2, written by /speckit-tasks
```

### Source Code (repository root)

```text
src/apl/
├── kit.py                    # + Scout, Kit.add_scout, shared tool-node lock (R2, R3)
├── cli.py                    # + `apl continue`; code line; exit code 4; continue hint
├── dungeon/
│   ├── env.py                # + Scout, add_scout, scout= on tools, per-scout exit check (R1)
│   └── frames.py             # + scouts in replay and frames (R4)
├── arch/
│   ├── dungeon_map.py        # + render of several scouts and claims (R8)
│   ├── scouts.py             # new: ScoutState, SharedMap, scout turn, act node (R3, R7, R8)
│   ├── fanout.py             # new: A7 (R9)
│   ├── rounds.py             # new: A8 (R9)
│   └── blackboard.py         # new: A9
├── runner/
│   ├── compare.py            # new: comparison section (R14)
│   ├── meter.py              # + lock, roles, orchestrator calls (R5)
│   ├── registry.py           # + fanout, rounds, blackboard
│   ├── report.py             # + calls compare.render when ≥ 2 architectures
│   ├── results.py            # + scouts, orchestrator_calls in rows
│   ├── run.py                # + continue plan and execution, stop after 3 errors (R11–R13)
│   └── spec.py               # episode order; calls bound labelled as an estimate (R10)
└── viewer/
    ├── events.py             # + run-id call numbers, roles, scout on steps (R6)
    ├── app.py                # + scout on step events, scouts in frames
    └── assets/index.html     # + markers and trails per scout, role labels

tests/
├── dungeon/
│   ├── test_scouts.py        # new: rules of contracts/scouts.md, replay (SC-002)
│   ├── test_golden.py        # new: single-agent outcomes pinned before the change (SC-001)
│   └── test_boundary.py      # covers the new arch modules
├── arch/
│   ├── test_scouts_shared.py # new: SharedMap vs oracle, lockstep order
│   ├── test_fanout.py        # new
│   ├── test_rounds.py        # new
│   └── test_blackboard.py    # new (SC-003)
├── runner/
│   ├── test_continue.py      # new: interrupt, continue, refusals (SC-004, FR-015)
│   ├── test_compare.py       # new: hand-written rows (SC-005)
│   ├── test_meter.py         # + roles, parallel calls
│   ├── test_spec.py          # + order
│   └── test_cli_run.py       # + code line, apl continue, exit codes
└── viewer/
    └── test_app.py           # + roles, scout on steps, scouts in frames
```

Other files that change:

- `plan.md`: §4 adds A7–A9 and the several-scout idea; §7 M4 row (seven architectures, one seed,
  `gpt-6-luna`) and M5+ (A3–A5 left);
- `README.md`: the architecture table, the `apl continue` command, a link to the conclusion;
- `AGENTS.md`: the `apl continue` command;
- `docs/findings/m4-first-comparison.md`: the conclusion, after the run.

**Structure Decision**: the scout machinery shared by A7–A9 gets its own module in `apl/arch/`,
next to `dungeon_map.py`, so the three orchestrator modules hold only what differs between them. The
comparison section gets its own runner module, so `report.py`'s M2 tables stay untouched.

## Complexity Tracking

No constitution violations to justify.
