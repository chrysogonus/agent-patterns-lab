# Implementation Plan: The Signal Trace

**Branch**: `009-signal-trace` (spec directory; work happens on the current branch) | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/009-signal-trace/spec.md`

## Summary

The lab gets a third problem, the signal trace: find the one broken segment of a pipe with
`probe(segment)` and name it with `submit(segment)`. It is built so that the choice of the next
probe is the only thing that differs: answers are always true and the layout is given at the
start. It plugs into the problem table from M5 without changing the dungeon or the survey field.

- **Constitution 2.2.0** (done before this plan): principle II names the signal trace's tools; the
  Experiment Setup describes its pipes, reference and budget; the attempt rule covers a wrong
  submission.
- **The problem**: a new package `apl.signal_trace` with the survey package's layers (R1). Pipes
  are numbered in preorder and described as runs (R3); T1 and T2 are single runs of 16 and 64, T3
  a 64-segment tree with 4 pipe ends and at most two branches per segment (R4). The layout is the
  free start view; `look` repeats it for a step (R2).
- **Reference and budget**: one greedy split strategy, bisection on a single run; the reference is
  its worst-case probes plus the submission (R5); the budget is the larger of 3× that and a full
  probe-by-probe scan: 16, 64, 64.
- **Scoring**: success is the right segment; rows add the submitted and broken segment, segments,
  probes and wasted probes (answers already implied, R7); a signal report table (R10).
- **Viewer**: `/api/signal`, a pipe board of segment boxes, and a stats panel with probes, suspects,
  wasted probes and the submission (R13). `apl signal show` prints a pipe (R12).
- **Architectures**, written by the agent (FR-025): A1 unchanged; a `ProbeLog` gives A2, A3 and A4
  their memory; A6 gets a signal branch where code lists the probes that split the suspects best
  and the model picks one (R11).

## Technical Context

**Language/Version**: Python 3.12 (pinned). The viewer page is plain HTML, CSS and JavaScript.

**Primary Dependencies**: as in M5–M8: `langgraph` 1.2.x (≥ 1.2.18), `langchain` 1.4.x,
`langchain-core`, `langchain-openai`, `langchain-ollama`. Nothing new in `pyproject.toml`.

**Storage**: run folders under `results/` and viewer episodes under `results/viewer/`
(gitignored), with the additive row fields of [contracts/results.md](contracts/results.md).

**Testing**: pytest, ruff and mypy (strict), with the scripted chat model from earlier features.
The tests:

- pin the survey field's outputs before any change, as M5 pinned the dungeon's: its prompt
  fingerprint, a dry-run plan and a report from stored rows; the dungeon's pins stay (SC-001);
- generate every signal level and every dev and test seed: determinism, segment count, one break,
  feeders below their segment, at most two per feeder, the level's pipe ends and shortest run, and
  the T3 reference bound of 8 probes (SC-002, R4);
- check the strategy: bisection's worst case is ⌈log₂ N⌉ on single runs; following the reference
  succeeds within the reference steps on every level and seed (SC-003); a probe-by-probe scan
  averages at least 3× the reference probes on T2 (SC-004);
- check the environment and tools: probe answers follow R6, errors and their step cost, attempts
  and restarts, wasted probes reproduced from saved answers (SC-006), the boundary test of R14,
  and the import rule for the new modules (FR-019);
- play scripted architectures on the signal trace: A1, A2, A3, A4 (with a wrong submission and a
  restart), A6 (options and their order), and the probe log against an oracle built from the
  episode;
- plan, refuse, interrupt, continue and report scripted signal runs (US3);
- the viewer API, a scripted episode's events and frames, and replay (US1, SC-005).

The page's JavaScript is checked by hand (quickstart step 5) and with the headless-browser check
used since M3.

**Target Platform**: the experimenter's WSL2 machine; the local vLLM server for watching
episodes. This feature makes no paid or local experiment run.

**Project Type**: Python library with a CLI (`apl`) and a local web page.

**Performance Goals**: generating a pipe and its reference (64 suspects × 64 candidates × 64
breaks for the worst case) takes well under a second, so dry runs and the viewer stay instant.

**Constraints**: no change to dungeon or survey behaviour, results or command output (FR-020). No
paid call without `--execute` (VI). Architectures import only `apl.kit`, `apl.arch` and each
problem's `tools` and `results` modules.

**Scale/Scope**: 3 problems; 3 signal levels; 10 dev and 20 test seeds; 5 architectures on the
signal trace (`react`, `mapstate`, `plan_execute`, `reflexion`, `hybrid`).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Checked against v2.2.0, amended for this feature before planning.

| Principle | How this plan complies |
| --- | --- |
| I. Identical Conditions | Every architecture on the signal trace gets its one base prompt, tool schemas and budget from `apl.problems`; the prompt fingerprint covers them. The prompt explains the pipe and the tools, never a strategy ([contracts/signal-tools.md](contracts/signal-tools.md)). |
| II. Tool-Only World Access | Architectures get `look`, `probe`, `submit` and the free layout through the kit. The probe log and A6's suspects are built from tool results only, with their own copy of the probe rule (R6, R11). The import test forbids `generator`, `env` and `strategy` (R14). |
| III. Only the Graph Varies | Every tool call costs a step, failed ones included; A6's code makes its calls through the tool node; A4's attempts share one budget. A6's option list and the probe log are graph state and node instructions. |
| IV. Structured, Code-Scored Results | Same envelope; success is `submitted_segment == broken_segment`; wasted probes and the reference are computed by code (R5, R7). |
| V. Honest Reporting | Dev 1000–1009 and test 2000–2019, keyed by the problem name; the viewer refuses test seeds (R13). |
| VI. No Paid Call Without `--execute` | `--problem signal` changes only what is planned; dry runs and tests call no model. |
| Workflow: user writes graphs | The experimenter asked the agent to write the signal versions of A1–A4 and A6 (spec Clarifications, FR-025) and reviews them. |

**Post-design re-check** (after Phase 1): passes. The contracts add no path to environment
internals, no per-architecture setting and no model call outside `--execute`. The free layout
(R2) matches how the other problems hand over their start view; the constitution text says so.

## Project Structure

### Documentation (this feature)

```text
specs/009-signal-trace/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R14
├── data-model.md        # Phase 1: entities, rules and transitions
├── quickstart.md        # Phase 1: how to check the feature end to end
├── contracts/
│   ├── problems.md      # the problem table entry and the kit
│   ├── signal-tools.md  # base prompt, tools, results, errors
│   ├── architectures.md # registry, ProbeLog, A6's signal branch, A3 and A4
│   ├── cli.md           # apl run --problem signal, apl signal show
│   ├── results.md       # row fields, report and comparison
│   └── viewer.md        # /api/signal, events, the page
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
src/apl/
├── problems.py          # PROBLEMS["signal"]
├── kit.py               # docstring: the allowed imports
├── signal_trace/        # new package (R1–R9)
│   ├── __init__.py
│   ├── model.py         # SignalLevel, LEVELS T1–T3, Run, Pipe, Action
│   ├── seeds.py         # DEV_SEEDS, TEST_SEEDS
│   ├── generator.py     # generate(level, seed): runs, tree, break, reference
│   ├── strategy.py      # suspects, informative, choose, worst_case, reference_run
│   ├── env.py           # Episode, LogEntry, Outcome, MAX_ATTEMPTS
│   ├── results.py       # agent-facing result types (architectures may import)
│   ├── tools.py         # AgentTools: start, look, probe, submit (architectures may import)
│   ├── prompt.py        # BASE_PROMPT, TOOL_SCHEMAS, prompt_fingerprint
│   ├── kit.py           # build_kit
│   ├── frames.py        # the viewer's frames and reference frames
│   ├── render_text.py   # `apl signal show`
│   └── render_svg.py    # the viewer's pipe board
├── arch/
│   ├── probe_log.py     # new: the probe log (R11)
│   ├── mapstate.py      # picks ProbeLog on signal
│   ├── plan_execute.py  # picks ProbeLog on signal
│   ├── reflexion.py     # ProbeLog on signal; "wrong segment"; staleness by `known`
│   ├── hybrid.py        # the signal branch
│   └── react.py         # unchanged
├── runner/
│   ├── registry.py      # SUPPORTS gains "signal"
│   ├── results.py       # signal row fields
│   ├── report.py        # the signal table and spread
│   └── compare.py       # REFERENCES override on signal
├── viewer/
│   ├── app.py           # /api/signal, a generic world parser, signal frames, start event
│   └── assets/index.html  # the signal board and stats
└── cli.py               # `apl signal show`; --problem choices from the table
tests/
├── signal_trace/        # new: generator, strategy, env, tools, boundary, render, kit
├── arch/                # probe_log; scripted signal episodes for A1–A4, A6
├── runner/              # signal plan/run/continue/report; survey outputs pinned
└── viewer/              # signal API, episode events, replay
AGENTS.md                # allowed imports and tools gain the signal trace's
plan.md, README.md       # §2c signal trace, §4 problems column, §7 M9
```

**Structure Decision**: the signal trace mirrors `apl.survey` module by module, so every part has
an obvious counterpart, and the runner, report and viewer gain one more branch in the places that
already branch on the problem. The test folder is `tests/signal_trace/`, not `tests/signal/`, for
the reason in R1.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| The probe rule (R6) exists twice: in `apl.signal_trace.strategy` and in `apl.arch.probe_log` | Architectures may not import runner code (Constitution II), and the environment needs the rule for wasted probes and frames | Exposing `strategy` to architectures would hand them the reference strategy; the copy is about 15 lines and a test checks both agree. |
| Signal result types repeat the survey's envelope classes | Each problem's `results` module stays self-contained, as decided in M5 | A shared base module would change both existing problems' import surface for about 30 lines. |
