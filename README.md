# agent-patterns-lab

A playground for comparing LangGraph agent architectures on the same generated dungeon,
scored by code.

> **Status: M0 done.** The repository, toolchain and Spec Kit are set up. Nothing is runnable
> yet beyond the test suite. The design and milestones are in [`plan.md`](plan.md).

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

## Architectures

Each one is built by hand with LangGraph's `StateGraph`.

| ID | Architecture | Idea |
| --- | --- | --- |
| A1 | ReAct | The model calls tools in a loop and remembers only through its message history |
| A2 | Map state | The explored map is kept in graph state and shown to the model every turn |
| A3 | Plan-and-execute | A planner sets subgoals, an executor carries them out, the plan is revised on surprises |
| A4 | Reflexion | After a failed attempt the agent writes down what went wrong and tries again |
| A5 | Supervisor | A supervisor delegates to a navigator and an inventory subagent |
| A6 | Hybrid | Code searches the known map; the model only chooses where to go next |

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
# .env (never committed)
APL_MODEL=anthropic:claude-haiku-5-5
ANTHROPIC_API_KEY=...
```

The default is Claude Haiku 5.5. It is cheap, and a weaker model leaves room for architectures
to differ.

## Development

Requires [uv](https://docs.astral.sh/uv/). Python 3.12 is pinned in `.python-version`.

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

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

Planned:

```text
src/apl/dungeon/   generator, environment, tools, solver
src/apl/arch/      one module per architecture
src/apl/runner/    run matrix, results, report
tests/
specs/             Spec Kit feature specs
.specify/          Spec Kit configuration and templates
results/           experiment output (not committed)
```

## License

MIT, see [`LICENSE`](LICENSE).
