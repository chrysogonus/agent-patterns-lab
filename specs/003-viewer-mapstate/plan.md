# Implementation Plan: Browser Viewer and A2 Map State

**Branch**: `003-viewer-mapstate` (spec directory; work happens on `main`) | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-viewer-mapstate/spec.md`

## Summary

M3 makes the agents watchable. It has four parts:

- **`apl serve`**: a local web page. The experimenter picks a level and a seed (the dungeon is
  regenerated identically every time), picks an architecture, and watches it play live:
  - moves on the map, with an "agent's view" fog and a shortest-solution overlay;
  - every model turn with its reasoning, tool calls and results;
  - running statistics.

  Episodes are saved and replay from the same event log.

  It is built from the standard library's HTTP server and Server-Sent Events, with no new
  dependency (research R1–R8).
- **Hooks**: an `on_step` hook on `Episode`, and two optional arguments to `play_episode` (R3).
  The viewer observes the same model and episode as `apl run`, and the architectures do not
  change.
- **vLLM**: the experimenter now serves Qwen3.5-9B with vLLM. It takes about 2 s per call
  instead of 9 s, returns the reasoning separately, and has an 8,192-token context. The new
  default model is `vllm:qwen3.5-9b`:
  - a small `ChatOpenAI` subclass captures the reasoning for display without sending it back
    (R9);
  - a prompt that outgrows the context becomes the architecture's failure instead of stopping
    the run (R10).
- **A2 (`mapstate`)**: the design reviewed earlier, carried over from
  `docs/parked/m4-comparison/` (R11–R17). An explicit map in the graph state replaces the
  message history. The agent writes it, as the experimenter asked.

The 180-episode comparison is parked for M4.

## Technical Context

**Language/Version**: Python 3.12 (pinned). The page uses plain HTML, CSS and JavaScript (ES2020)
for a current desktop browser.

**Primary Dependencies**: as in M2: `langgraph` 1.2.x, `langchain` 1.4.x, `langchain-core`,
`langchain-openai` (also used for vLLM), and `langchain-ollama`. The viewer uses only the
standard library (`http.server`, `threading`, `json`). Nothing new in `pyproject.toml`.

**Storage**: files under `results/viewer/<id>/` (gitignored): `events.jsonl`, plus the M2
`outcome.json` and `conversation.json`, plus `episode.json`.

**Testing**: pytest, ruff and mypy (strict). The scripted chat model from M2 is used, with
`replay_solution` counting its own calls. The tests:

- call the viewer's app functions directly, without sockets;
- run one HTTP/SSE smoke test through a fixture that allows loopback only;
- check the A2 map against an oracle built from the layout and frames.

The page's JavaScript is checked by hand (quickstart), plus a test that the elements it needs
exist.

**Target Platform**: the experimenter's WSL2 machine with an RTX 5070 Ti. The vLLM server runs in
Docker on `localhost:8001`, and the browser runs on Windows or WSL.

**Project Type**: Python library with a CLI (`apl`) and a local web page.

**Performance Goals**:

- a dungeon is shown within 2 s (SC-001), and a step appears within 1 s of the tool call
  (SC-002);
- a reload catches up within 2 s (SC-003);
- a model call takes about 2 s on vLLM, so an L1 episode takes about 20 s.

**Constraints**:

- The viewer binds to `127.0.0.1` only.
- Test seeds are refused.
- No paid call without `--execute`.
- The base prompt, the tool schemas and the fingerprint are unchanged.
- A1 is unchanged.
- `apl run` and `apl report` are unchanged, apart from `mapstate`, the vLLM provider and the
  context-overflow classification.

**Scale/Scope**:

- one viewer package with 4 modules and 1 HTML asset;
- 2 architecture modules and 1 runner module (`vllm.py`);
- small changes to 7 existing modules;
- about 6 new test modules.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | How this plan complies | Status |
| --- | --- | --- |
| I. Identical Conditions | The viewer plays through the runner's `play_episode` with the one `Settings` object and the default model factory (R3). The model can be changed only through settings. Reasoning capture on vLLM is display-only and does not change what is sent (R9). Each saved episode records its settings | PASS |
| II. Tool-Only World Access | The viewer only observes: its hooks read the episode and the model after the fact and give the agent nothing (FR-007). A2's map comes only from the call and result JSON (R13). The import boundary is unchanged and covers the new arch files | PASS |
| III. Only the Graph Varies | A2 changes its graph, state and node instructions only. Every tool call goes through `kit.tool_node`. The context-overflow rule applies to all architectures alike (R10) | PASS |
| IV. Structured, Code-Scored Results | Viewer episodes produce the same `EpisodeRow`, outcome and transcript as runs, plus a structured event log. The page shows numbers computed by code and judges nothing | PASS |
| V. Honest Reporting | Test seeds are refused in the viewer, for both dungeons and episodes (R6). Watching is development use. No comparison is reported in M3 | PASS |
| VI. No Paid Call Without `--execute` | Only local providers (`ollama:`, `vllm:`) run from the page without a flag. Any other needs `apl serve --execute` (R8, SC-005). `apl run` keeps its dry-run default. vLLM's `/models` metadata request is not a model call and happens only in `apl serve` or with `--execute`. Tests use the scripted model with the network blocked | PASS |
| Experiment Setup | The levels, budget, token cap and seed split are unchanged. The model change is a settings change, recorded per run and episode | PASS |
| Development Workflow | The experimenter asked the agent to write A2 (spec Assumptions). pytest, ruff and mypy remain the gate | PASS |

**Post-design re-check (after Phase 1)**: PASS.

- The hooks are additive and default to off, so `apl run` behaves as before.
- The API contract exposes nothing to an architecture.
- Ids are matched against a strict pattern before any file access.
- The context-overflow reclassification changes a run outcome from "run stops" to "episode
  scored as failed". That is consistent with Constitution III, since the prompt is the
  architecture's.

Nothing goes in Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/003-viewer-mapstate/
├── spec.md
├── plan.md              # this file
├── research.md          # Phase 0: R1–R10 viewer and vLLM, R11–R17 A2
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── viewer-api.md    # HTTP endpoints and SSE events
│   ├── mapstate.md      # A2: graph, model input, map text
│   └── cli.md           # apl serve, settings, error classification
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2, written by /speckit-tasks
```

### Source Code (repository root)

```text
src/apl/
├── cli.py                    # + `apl serve`
├── viewer/                   # new
│   ├── __init__.py
│   ├── app.py                # options, dungeon, start/stop/list episodes (R4–R8)
│   ├── events.py             # EpisodeSession, ViewerCallbacks (R2, R3, R5)
│   ├── server.py             # ThreadingHTTPServer on 127.0.0.1, routing, SSE (R1, R2)
│   └── assets/index.html     # the page (R7)
├── arch/
│   ├── dungeon_map.py        # new: DungeonMap (R13, R14)
│   └── mapstate.py           # new: A2 graph, MAP_INSTRUCTIONS (R11, R12, R15)
├── dungeon/
│   ├── env.py                # + Episode.on_step
│   ├── frames.py             # _snapshot → snapshot
│   └── render_html.py        # + room rects
└── runner/
    ├── episode.py            # + callbacks, on_episode; context overflow → arch_error (R10)
    ├── registry.py           # + "mapstate"
    ├── run.py                # factory: vllm provider; record server context
    ├── settings.py           # vllm default, APL_BASE_URL, per-provider output default
    └── vllm.py               # new: VLLMChat, server context lookup (R9)

tests/
├── viewer/                   # new
│   ├── test_app.py           # options, dungeon, seeds, 409, stop, guard (SC-001, SC-005)
│   ├── test_events.py        # event order for scripted A1/A2, catch-up, save + replay (SC-003, SC-004)
│   ├── test_server.py        # one loopback HTTP + SSE smoke test
│   └── test_page.py          # index.html has the elements the script uses
├── arch/
│   ├── oracle.py             # new: expected map from layout + frames (R17)
│   ├── test_dungeon_map.py   # new
│   └── test_mapstate.py      # new
├── runner/
│   ├── scripted.py           # replay_solution counts its own calls
│   ├── test_vllm.py          # new: reasoning capture, not resent, context lookup
│   ├── test_episode_hooks.py # new: on_step, callbacks, context overflow
│   ├── test_settings.py      # + vllm defaults, APL_BASE_URL
│   └── test_cli_run.py       # default model name in the dry run; vllm context line
└── dungeon/
    └── test_render.py        # + room rects
```

Other files that change:

- `README.md`: the status line (already updated), a "Watch an agent" section, and the Model
  section for vLLM;
- `AGENTS.md`: the `apl serve` command;
- `plan.md` §7 (already updated) and §9: the vLLM default;
- `.env.example`.

**Structure Decision**: the viewer is its own subpackage, because it is a separate entry point
with its own asset. It depends on the runner (to play episodes) and the dungeon (to draw), and
nothing depends on it. The map gets its own module in `apl/arch/`, so later architectures can
reuse it under the same import boundary.

## Complexity Tracking

No constitution violations to justify.
