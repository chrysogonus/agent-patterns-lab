# Implementation Plan: Runner, Results Format, Report and A1 ReAct

**Branch**: `002-runner-react` (spec directory; work happens on `main`) | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-runner-react/spec.md`

## Summary

M2 adds everything around an architecture graph, so the experimenter's A1 ReAct can be played,
measured and reported:

- **Shared setup (`apl.kit`):** the one object an architecture receives per episode. It holds
  the run's model with a meter attached, the four tool schemas, a tool node that runs tool calls
  in order through the episode, the base prompt, the free start description and a fixed
  recursion limit (research R3–R6).
- **Runner (`apl run`):** a dry run by default that prints the matrix and real upper bounds. With
  `--execute` it plays the episodes one by one, writes a run folder (`run.json`,
  `episodes.jsonl`, per-episode outcome and conversation files), retries provider errors and
  sorts failures into scored and unscored (R7–R12).
- **Report (`apl report`):** markdown tables per architecture and level with the spread across
  repeats. It refuses to combine incompatible runs (R13).
- **A1 ReAct:** written by the experimenter in `src/apl/arch/react.py` against
  [contracts/kit.md](contracts/kit.md). Tests for it are ready and skip until it exists.

Key design choices, all confirmed by probing the pinned libraries:

- **Meter on the model object:** call and token counting, the token cap and the "no call after
  the end" guard live in one callback handler set on the model itself. Callbacks added with
  `with_config` are lost by `bind_tools`; callbacks on the model are not (R3).
- **Shared tool node instead of LangGraph's `ToolNode`:** `ToolNode` runs one turn's tool calls in
  parallel and answers invalid calls itself, which would scramble the order of moves and skip
  step counting (R4, R5).
- **Unscored errors are provider errors only:** an architecture that crashes or loops has failed;
  only provider failures after retries are excluded from scores (R7).

## Technical Context

**Language/Version**: Python 3.12 (pinned).

**Primary Dependencies**: `langgraph>=1.2.18,<1.3`, `langchain>=1.4.7,<2` (`init_chat_model`),
`langchain-openai>=1.7.3,<2`; through them `langchain-core` 1.7.x and `openai` 3.x (R1). Standard
library for settings, results and the report (`json`, `statistics`, `hashlib`, `subprocess`,
`importlib.metadata`).

**Storage**: Files under `results/` (gitignored): JSON and JSONL (R12).

**Testing**: pytest, ruff, mypy (strict). A scripted chat model stands in for the provider;
`tests/conftest.py` blocks network access for all tests (R14).

**Target Platform**: The experimenter's machine (Linux/WSL, macOS); the OpenAI API for paid runs.

**Project Type**: Python library with a CLI (`apl`).

**Performance Goals**: Less than 1 s runner overhead per episode with the scripted model
(SC-010). Model latency dominates real runs.

**Constraints**:

- No provider contact or file writes without `--execute` (Principle VI, FR-013).
- The same model and settings object for every architecture in a run (Principle I).
- `apl dungeon show` must not import LangChain (keeps it fast); `apl run` and `apl report` import
  it lazily.
- The API key is never written to a results file.

**Scale/Scope**: Runs of up to a few hundred episodes (M3: 180), sequential. About 8 new source
modules, 10 new test modules, additive changes to 4 M1 modules.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies | Status |
| --- | --- | --- |
| I. Identical Conditions | One `Settings` per run (model, temperature, reasoning effort, token cap, retries) and one base prompt and set of tool schemas, fingerprinted. Architectures get the model from the kit; the boundary test forbids creating one (R15). The report refuses to combine runs with different settings (FR-031) | PASS |
| II. Tool-Only World Access | Architectures may import only `apl.kit`, `apl.dungeon.tools` and `apl.dungeon.results`. The kit holds the episode only inside the tool node's closure. The recursion limit is a constant, not derived from the budget, which would leak the optimum (R6). The base prompt reveals neither budget nor layout (FR-004) | PASS |
| III. Only the Graph Varies | `play(kit)` leaves graph, state and node instructions to the architecture. The shared tool node counts every call, including unknown tools and malformed arguments (R4, R5). The budget, the token cap and "no call after the end" are enforced outside the graph (R3) | PASS |
| IV. Structured, Code-Scored Results | Rows with fixed fields and validation on read; outcome records in the M1 format; the report is computed from rows by code (FR-032) | PASS |
| V. Honest Reporting | Every run records its seed set; dev reports are headed "must not be reported"; runs on different seed sets cannot be combined; architecture crashes count as failures (R7, FR-030) | PASS |
| VI. No Paid Call Without `--execute` | The dry run constructs no model and opens no connection; the key check and the first model call happen only after `--execute`. Tests block the network and use a scripted model (R14) | PASS |
| Experiment Setup | Budget stays 3 × optimal from M1; the token cap from plan §8 is a shared setting (R9); stack as in the constitution (R1) | PASS |
| Development Workflow | No graph logic in `src/apl/arch/` from agents: only an empty package `__init__.py` is created there, and A1 is the experimenter's task. The runner tests use a plain-Python loop, not a `StateGraph` (R14). pytest, ruff and mypy remain the gate | PASS |

**Post-design re-check (after Phase 1)**: PASS. The data model adds one error code and one
pseudo-action to M1 (R5); both are additive, keep `AgentTools` at four tools, and keep every log
replayable. The kit contract exposes no path to the episode beyond the four tools; the `_episode`
check of the boundary test stays. Nothing goes in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/002-runner-react/
├── spec.md
├── plan.md              # this file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── kit.md           # the architecture interface (apl.kit, play, A1 behavior)
│   ├── cli.md           # apl run, apl report
│   └── results.md       # run folder, rows, conversation file, report format
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2, written by /speckit-tasks
```

### Source Code (repository root)

```text
src/apl/
├── cli.py                    # + `apl run`, `apl report` (lazy imports)
├── kit.py                    # Kit, EpisodeEnded, base prompt, tool schemas, tool node (contracts/kit.md)
├── arch/
│   ├── __init__.py           # package marker only (docstring)
│   └── react.py              # A1 ReAct: written by the experimenter
├── runner/
│   ├── __init__.py
│   ├── settings.py           # Settings, .env loading, fingerprint, key check (R2, R11)
│   ├── spec.py               # RunSpec, EpisodeKey, upper bounds (R10)
│   ├── registry.py           # architecture names → modules (R6)
│   ├── meter.py              # Meter callback, Transcript (R3, R12)
│   ├── episode.py            # play one episode → row and files (R7)
│   ├── run.py                # run loop, run folder, run.json, retries/classification (R8, R12)
│   ├── results.py            # EpisodeRow, RunRecord: build, write, parse
│   └── report.py             # compatibility, stats, markdown (R13)
└── dungeon/
    ├── model.py              # + pseudo-tool `unknown` (R5)
    ├── results.py            # + ErrorCode.UNKNOWN_TOOL
    ├── env.py                # + Episode.unknown
    └── frames.py             # + dispatch of `unknown`

tests/
├── conftest.py               # blocks network, sets dummy API keys (R14)
├── runner/
│   ├── __init__.py
│   ├── scripted.py           # scripted chat model and strategies
│   ├── loop_arch.py          # test-only architecture: a plain Python loop, no StateGraph
│   ├── test_settings.py      # env/.env parsing, defaults, invalid values, fingerprint
│   ├── test_spec.py          # matrix, seed selection, upper bounds
│   ├── test_kit.py           # tool node: order, malformed args, unknown tool, end of episode
│   ├── test_meter.py         # counting, missing usage, token cap, guard after the end
│   ├── test_run.py           # episodes end to end with the scripted model, files, errors, interrupt
│   ├── test_results.py       # row derivations, parse/validate, conversation dedup
│   ├── test_report.py        # hand-computed figures, spread, errors, compatibility
│   └── test_cli_run.py       # dry run output, no network, no files, exit codes
├── arch/
│   ├── __init__.py
│   └── test_react.py         # A1 with the scripted model; skips until react.py exists
└── dungeon/
    ├── test_env.py           # + unknown tool
    ├── test_frames.py        # + log with an unknown tool replays
    └── test_boundary.py      # + apl.kit allowed, model creation forbidden (R15)
```

Also updated: `pyproject.toml` (dependencies), `uv.lock`, `AGENTS.md` (import rule),
`README.md` (status, Try it), `specs/001-dungeon-environment/contracts/tools.md` gets a one-line
note pointing to the new error code in this feature's kit contract.

**Structure Decision**: The runner is a new package `src/apl/runner/` next to `src/apl/dungeon/`,
as the README layout planned. The kit is a single top-level module `src/apl/kit.py`, so that
architectures import one small, stable surface and nothing from the runner. `src/apl/arch/`
holds only the experimenter's files plus an empty package marker; the registry that names them
lives in the runner. Tests mirror the source layout.

## Complexity Tracking

No constitution violations, so nothing to justify.
