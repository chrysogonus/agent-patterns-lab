# Implementation Plan: A2 Map State and the First Comparison

**Branch**: `003-map-state-comparison` (spec directory; work happens on `main`) | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-map-state-comparison/spec.md`

## Summary

M3 answers plan.md's first question, "does explicit memory beat history?", with A2, a paired
180-episode run, and a written conclusion. It has four parts:

- **A2 (`mapstate`)**: an explicit map is kept in the graph state and updated from every tool
  result. It is rendered as text and replaces the message history. The model sees the base
  prompt with A2's map instructions, its previous turn, and the map (research R1–R6). The agent
  writes A2, as the experimenter asked.
- **One fair, continuable run**: the episodes are interleaved by architecture (R8). A new
  `apl continue RUN_DIR` plays only the missing episodes, after checking that the settings, the
  versions and the committed code are identical (R9, R10). The run stops after 3 infrastructure
  errors in a row, so an outage cannot fill the run with error rows (R11).
- **Comparison report**: for exactly two architectures, `report.md` gains a per-level comparison
  with spreads and differences. It also gets a per-dungeon count of higher, same and lower over
  paired repeats, with a sign-test p-value (R12, R13).
- **Conclusion**: `docs/findings/m3-map-state.md` is written from the run's report (R14).

## Technical Context

**Language/Version**: Python 3.12 (pinned).

**Primary Dependencies**: as in M2: `langgraph` 1.2.x, `langchain` 1.4.x, `langchain-core`,
`langchain-ollama`, `langchain-openai`. Nothing new; the sign test uses `math.comb`.

**Storage**: run folders under `results/` (gitignored), in the M2 format. There are no new
fields. The conclusion is a markdown file in `docs/findings/`.

**Testing**: pytest, ruff and mypy (strict). The scripted chat model from M2 is used, with
`replay_solution` changed to count its own calls (R7). An oracle derived from the layout and the
frames checks the map (R7). The network stays blocked.

**Target Platform**: the experimenter's machine (WSL2 Linux) with local Ollama `qwen3:8b` on an
RTX 5070 Ti.

**Project Type**: Python library with a CLI (`apl`).

**Performance Goals**: updating and rendering the map adds less than 10 ms per turn. A2's prompt
stays near 2,000 tokens, while A1's grows up to the 16,384-token context. The 180-episode run
takes about 8–9 h (R15).

**Constraints**:

- The base prompt, the tool schemas and the prompt fingerprint are unchanged from M2.
- A1 (`react.py`) is unchanged.
- No paid call without `--execute`, for `apl continue` too.
- Continuing requires the same settings, versions and commit, and a clean tree.

**Scale/Scope**:

- 2 new architecture modules;
- 1 new runner module (`compare.py`);
- changes to `spec.py`, `run.py`, `registry.py`, `report.py` and `cli.py`;
- 4 new test modules, and changes to `scripted.py`, `test_spec.py` and the boundary test if
  needed;
- 1 findings document, and updates to README and AGENTS.md.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies | Status |
| --- | --- | --- |
| I. Identical Conditions | Both architectures play in one run, with one `Settings` object, model, base prompt and fingerprint. A2 uses `kit.model`. Continuing refuses any difference in settings, versions or code (R9, R10). The interleaved order also spreads drift over time evenly (R8) | PASS |
| II. Tool-Only World Access | The map is built only from the call and result JSON that A2 received (R3). The one inference, that a door works both ways, follows from the base prompt's rules. The imports stay inside the boundary (`apl.kit`, `apl.dungeon.results`, `apl.arch`), and the existing boundary test covers the new files. The map holds no positions, steps or budget | PASS |
| III. Only the Graph Varies | A2 changes the graph, the state schema and its node instructions (`MAP_INSTRUCTIONS`) on top of the unchanged base prompt. Every call goes through `kit.tool_node`, so every step counts. The instructions contain no strategy advice, so the comparison is about memory (R5) | PASS |
| IV. Structured, Code-Scored Results | Rows are unchanged. The comparison, the per-dungeon counts and the p-values are computed by code from rows (R12, R13). The conclusion quotes them | PASS |
| V. Honest Reporting | Dev seeds only, and the test seeds stay unused (FR-008). Each comparison section repeats the "must not be reported" notice. Spreads across the 3 repeats are shown. The p-value footnote says it describes these dev seeds only | PASS |
| VI. No Paid Call Without `--execute` | `apl continue` is a dry run without `--execute` and constructs no model. The tests use the scripted model with the network blocked | PASS |
| Experiment Setup | The levels, the budget (3 × optimal), the token cap and the seed split are unchanged | PASS |
| Development Workflow | The experimenter asked the agent to write A2 (spec Assumptions, clarification Q3). This is recorded in the spec. pytest, ruff and mypy remain the gate | PASS |

**Post-design re-check (after Phase 1)**: PASS. The data model adds no row or run fields and
keeps M2 runs readable. The episode order changes only for runs with several architectures; the
order within one architecture is as before. The `apl continue` contract cannot play anything
without `--execute`. The A2 contract sends no history, which is enforced by the state having no
reducer and checked by recorded inputs (US1/AC5, AC6). Nothing goes in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/003-map-state-comparison/
├── spec.md
├── plan.md              # this file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── mapstate.md      # A2: graph, model input, map text
│   ├── cli.md           # apl run changes, apl continue, exit codes
│   └── report.md        # comparison and per-dungeon sections
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2, written by /speckit-tasks
```

### Source Code (repository root)

```text
src/apl/
├── cli.py                    # + `apl continue`; code line; exit 4; "continue with" hint
├── arch/
│   ├── dungeon_map.py        # new: DungeonMap (from_start, apply, render) (R3, R4)
│   └── mapstate.py           # new: A2 graph, MAP_INSTRUCTIONS (R1, R2, R5)
└── runner/
    ├── registry.py           # + "mapstate"
    ├── spec.py               # episode order level→seed→repeat→arch (R8); code line in plan (R10)
    ├── run.py                # shared play loop; plan_continuation / continue_run (R9); streak stop (R11)
    ├── compare.py            # new: level comparison, per-dungeon counts, sign test (R12, R13)
    └── report.py             # calls compare for two architectures

tests/
├── arch/
│   ├── oracle.py             # new: expected map from layout + frames (R7)
│   ├── test_dungeon_map.py   # new: apply/render rules, invariants, SC-002, SC-003
│   └── test_mapstate.py      # new: SC-001, model input layout (AC5, AC6), stop/budget
├── runner/
│   ├── scripted.py           # replay_solution counts its own calls (R7)
│   ├── test_spec.py          # new order
│   ├── test_continue.py      # new: interrupt twice and continue, refusals, cut-off row, complete run (SC-004)
│   ├── test_compare.py       # new: hand-computed comparison, left-out pairs, p-values (SC-005)
│   ├── test_run.py           # + streak stop (exit 4)
│   └── test_cli_run.py       # + apl continue dry run/refusals, code line
└── dungeon/
    └── test_boundary.py      # unchanged rules; covers the new arch files

docs/findings/m3-map-state.md # new, after the run (R14)
README.md, AGENTS.md          # M3 status, apl continue command
```

**Structure Decision**: the existing single-package layout is kept. The map gets its own module
in `apl/arch/`, so later architectures (A3, A6) can reuse it under the same import boundary.
The comparison logic gets its own runner module, so `report.py` stays the M2 tables plus one
call.

## Complexity Tracking

No constitution violations to justify.
