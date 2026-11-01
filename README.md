# agent-patterns-lab

A playground for comparing LangGraph agent architectures on the same generated problems,
scored by code.

> **Status: M5 in progress.** M4 is done: three orchestrator architectures with several scouts,
> continuable runs, and a first comparison of seven architectures. M5 adds a second problem, the
> survey field, where splitting the work between scouts should pay off. The design and milestones
> are in [`plan.md`](plan.md).
>
> First results (one episode per architecture and level, not reportable):
> [`docs/findings/m4-first-comparison.md`](docs/findings/m4-first-comparison.md).

## What this is

Every architecture gets the same dungeon, the same tools, the same model and the same step
budget. Only the graph changes, so differences in the results come from the architecture.
Scoring is exact: the environment knows whether the agent reached the exit and how many steps
the shortest solution takes. There is no LLM judge.

## The dungeon

A grid of rooms joined by doors. Some doors are locked and open only with a key of the same
color, which lies somewhere else in the dungeon. The agent starts in one room and has to find
the exit. It sees only the room it is in.

| Tool | What it does |
| --- | --- |
| `look()` | Describe the current room: exits (and their lock color), items, inventory, whether this is the exit |
| `move(direction)` | Go through an open door |
| `take(item)` | Pick up an item in the room |
| `use(item, direction)` | Unlock a door with a key |

Dungeons are generated from a seed and are solvable by construction. A solver checks each one
and records the shortest solution. There are three levels:

| Level | Grid | Locks |
| --- | --- | --- |
| L1 | 3×3 | none |
| L2 | 4×4 | one key, one door |
| L3 | 5×5 | two chained keys, dead ends |

## The survey field

A square grid of cells under fog; some cells hold an ore deposit. Every agent starts in A1, the
north-west corner, and has to find out how many deposits the field holds. There are no dead ends
on the open levels, so several scouts can each take a part of the field.

| Tool | What it does |
| --- | --- |
| `look()` | Describe the current cell: its name, whether it holds a deposit, the open directions, the field's size |
| `move(direction)` | Go to the neighboring cell |
| `submit(total)` | Submit the number of deposits; this ends the episode |

An episode succeeds when the total is right. Code computes a reference walk that enters every
cell, and the budget is 3× its steps.

| Level | Grid | Walls | Deposits |
| --- | --- | --- | --- |
| S1 | 6×6 | none | 6 |
| S2 | 10×10 | none | 15 |
| S3 | 10×10 | interior walls, dead ends | 15 |

Each problem has its own tools, prompt and budget; architectures are compared only within a
problem.

## Architectures

Each one is built by hand with LangGraph's `StateGraph`.

| ID | Architecture | Idea | Problems |
| --- | --- | --- | --- |
| A1 | ReAct | The model calls tools in a loop and remembers only through its message history | dungeon, survey |
| A2 | Map state | The explored map is kept in graph state and shown to the model every turn | dungeon, survey |
| A2r | Map state with routes | A2's map plus the shortest known route to each unexplored exit | dungeon |
| A3 | Plan-and-execute | A planner sets subgoals, an executor carries them out, the plan is revised on surprises | — |
| A4 | Reflexion | After a failed attempt the agent writes down what went wrong and tries again | — |
| A5 | Supervisor | A supervisor delegates to a navigator and an inventory subagent | — |
| A6 | Hybrid | Code searches the known map; the model only chooses where to go next | dungeon |
| A7 | Fan-out once | An orchestrator sends up to 4 scouts out once; each explores on its own map | dungeon, survey |
| A8 | Supervisor in rounds | An orchestrator gives scouts short tasks and replans on the map they all saw | dungeon, survey |
| A9 | Shared blackboard | No planner: scouts take turns on one shared map and claim unexplored exits | dungeon, survey |

## How a comparison works

A run is a matrix of architectures × levels × seeds × repeats. Each episode records whether
the agent escaped, its steps against the shortest solution, invalid actions, LLM calls, tool
calls, tokens, latency and whether it ran out of steps. The report shows each architecture and
level with the spread across repeats.

Runs call a paid API. The runner only prints the planned matrix and an estimate of calls unless
it gets `--execute`.

## Model

One setting chooses the model for every architecture, in LangChain's `provider:model` form:

```bash
# .env (never committed; see .env.example for every setting)
APL_MODEL=vllm:qwen3.5-9b          # local vLLM, free; also ollama:qwen3:8b or openai:gpt-6-luna
```

The default is Qwen3.5 9B served by a local [vLLM](https://docs.vllm.ai) server at
`http://localhost:8001/v1` (`APL_BASE_URL`), started with `--reasoning-parser qwen3`,
`--enable-auto-tool-choice --tool-call-parser qwen3_coder`, `--max-model-len 32768` and
Qwen's recommended thinking-mode sampling (`--override-generation-config '{"temperature": 1.0,
"top_p": 0.95, "top_k": 20, "min_p": 0.0, "presence_penalty": 1.5, "repetition_penalty": 1.0}'`;
the quantized checkpoint ships none, so vLLM would otherwise sample unfiltered). A model call
takes about 2 seconds.
The model's reasoning is shown in the viewer and kept in the transcripts, but never sent back to
it. The context window is the server's (`--max-model-len`, 32,768 here), and the runner records
it. A prompt that outgrows it ends the episode as the architecture's failure.

`ollama:` models still work (`APL_NUM_CTX` sets their context, default 16,384, because Ollama's
own 4,096 would silently cut off long episodes). Optional settings, the same for every
architecture in a run: `APL_TEMPERATURE`, `APL_REASONING_EFFORT` (both default to the provider's
default), `APL_MAX_OUTPUT_TOKENS` (per model call; 8,192 for vLLM, otherwise 4,096),
`APL_TOKEN_CAP` (tokens per episode, default 2,000,000), and `APL_PRICE_INPUT` /
`APL_PRICE_OUTPUT` (USD per 1M tokens, for the dry run's worst-case cost).

## Development

Requires [uv](https://docs.astral.sh/uv/). Python 3.12 is pinned in `.python-version`.

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

### Try it

```bash
uv run apl dungeon show --level L3 --seed 1000                       # text map
uv run apl dungeon show --level L3 --seed 1000 --route solution      # with the shortest route
uv run apl dungeon show --level L3 --seed 1000 --route solution --html l3.html  # animation
```

```bash
uv run apl survey show --level S2 --seed 1000                        # a survey field
uv run apl survey show --level S3 --seed 1000 --route reference      # with the reference walk
```

Open `l3.html` in a browser to play the route back step by step. `--route` also accepts a JSON
file with an action list or a recorded outcome; see
[`contracts/cli.md`](specs/001-dungeon-environment/contracts/cli.md).

### Run an experiment

```bash
uv run apl run --arch react --level all --seeds dev --limit 2            # plan only, free
uv run apl run --arch react --level all --seeds dev --limit 2 --execute  # plays it
uv run apl report results/<run-id>                                       # report again
uv run apl continue results/<run-id> [--execute]                         # rest of a cut-off run
uv run apl run --problem survey --arch react,fanout --level all --seeds dev --limit 1  # survey
uv run apl dungeon show --level L2 --seed 1001 \
  --route results/<run-id>/episodes/react-L2-1001-r1.outcome.json --html episode.html
```

Each run gets a folder under `results/` with `run.json` (settings), `episodes.jsonl` (one row
per episode), the tool log and model conversation of every episode, and `report.md`. See
[`contracts/results.md`](specs/002-runner-react/contracts/results.md). An architecture is a module
`src/apl/arch/<name>.py` with `play(kit)`; see
[`contracts/kit.md`](specs/002-runner-react/contracts/kit.md).

### Watch an agent

```bash
uv run apl serve        # then open http://127.0.0.1:8765/
```

The viewer is a local page (reachable only from this machine):

- Pick a problem (dungeon or survey field), a level and any seed: the same seed always builds the
  same world. Test seeds (2000–2019) are refused, so they stay unseen for reported results.
- On the survey field, the panel shows the true total, the deposits seen so far and, at the end,
  the submitted total with right or wrong.
- Pick an architecture (`react`, `mapstate`, `mapstate_routes`, `hybrid`, `fanout`, `rounds`,
  `blackboard`) and a model (`APL_MODEL`, `vllm:qwen3.5-9b` or `openai:gpt-6-luna`), and press
  Run. Every step appears on the map as it happens, and every model turn in the side panel: its
  new input (for A2, A6 and the scouts, its map), reasoning, tool calls and their results. Stats
  count up as it goes.
- With several scouts (A7–A9), each has its own marker and trail color, and each model turn says
  whether it was the orchestrator or which scout.
- "Agent's view" dims the rooms no scout has been in yet. "Shortest solution" draws the
  solver's route. The slider goes back to any step; Stop ends the episode after the current
  model turn.
- Every episode is saved under `results/viewer/<id>/` (events, outcome, conversation, settings)
  and can be replayed from "Saved episodes".

Local models (`vllm:`, `ollama:`) run without a flag; a paid provider needs
`apl serve --execute`. See [`contracts/viewer-api.md`](specs/003-viewer-mapstate/contracts/viewer-api.md).

## Working with Spec Kit

The repository uses [Spec Kit](https://github.com/github/spec-kit) for Claude Code and Codex.
Each milestone in `plan.md` becomes one feature spec.

| Step | Claude Code | Codex |
| --- | --- | --- |
| Project rules, once | `/speckit-constitution` | `$speckit-constitution` |
| Describe a feature | `/speckit-specify` | `$speckit-specify` |
| Technical plan | `/speckit-plan` | `$speckit-plan` |
| Task list | `/speckit-tasks` | `$speckit-tasks` |
| Build it | `/speckit-implement` | `$speckit-implement` |
| Check what is left | `/speckit-converge` | `$speckit-converge` |

Repeat implement and converge until converge reports `Converged`.

## Layout

```text
src/apl/problems.py  the problems by name: dungeon, survey
src/apl/dungeon/   generator, environment, tools, solver, text map, HTML view
src/apl/survey/    the survey field: generator, reference walk, environment, tools, pictures
src/apl/cli.py     the `apl` command
src/apl/kit.py     what an architecture gets per episode (model, tools, prompt)
src/apl/arch/      one module per architecture, written by hand
src/apl/runner/    run matrix, results, report, model providers
src/apl/viewer/    `apl serve`: the browser viewer
docs/parked/       designs set aside for a later milestone
tests/
specs/             Spec Kit feature specs
.specify/          Spec Kit configuration and templates
results/           experiment output (not committed)
```

## License

MIT, see [`LICENSE`](LICENSE).
