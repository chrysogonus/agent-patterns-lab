# Plan

## 1. Goal

Learn how agent architectures behave by building several of them for one task and measuring
them under identical conditions.

**Question:** with the model and tools fixed, how do architectures differ in success,
efficiency and cost on exploration tasks that get harder step by step?

The task is deliberately small and fully simulated, so every result can be scored by code and
every run is cheap to repeat.

## 2. Environment

### World

- An N×N grid of rooms. Doors join neighboring rooms. The generator builds a random spanning
  tree, so every room is reachable, then adds a few extra doors for loops. Dead ends come from
  the tree's leaves.
- One room is the start and one is the exit, placed far apart.
- Locked doors have a color and open only with a key of that color. Each key is placed in the
  part of the dungeon that can be reached before its door, so every dungeon is solvable by
  construction.
- A breadth-first solver over (room, keys held, doors opened) confirms that the dungeon is
  solvable and records the shortest solution in steps.

### Tools

The agent sees only the room it is in.

| Tool | Returns |
| --- | --- |
| `look()` | Exits with direction and lock color, items in the room, inventory, whether this is the exit |
| `move(direction)` | The new room's description, or an error (no door, locked) |
| `take(item)` | Updated inventory, or an error |
| `use(item, direction)` | Whether the door opened, or an error (wrong key, no door) |

Every tool call counts as one step, including invalid ones. Errors are clear and structured so
that architectures can recover from them.

### Episode

An episode ends when the agent reaches the exit, runs out of steps, or gives up. The step
budget is about 3× the shortest solution.

### Levels

| Level | Grid | Locks | Purpose |
| --- | --- | --- | --- |
| L1 | 3×3 | none | Baseline; every architecture should pass |
| L2 | 4×4 | one key, one door | Detours and remembering where things are |
| L3 | 5×5 | two chained keys, dead ends | Planning and backtracking |

### Seeds

Fixed **dev** seeds are used while building and tuning. Separate **test** seeds are used only
for reported results, so tuning does not leak into them.

## 3. Fairness rules

These become the Spec Kit constitution.

1. Every architecture uses the same model, temperature, base prompt, tool descriptions and
   step budget.
2. Architectures see the world only through the four tools. They never read environment
   internals, the generator or the solver.
3. Only the graph may differ: nodes, edges, state and what each node is told.
4. Tool results and final outcomes are structured data, not free text, so scoring is exact.
5. Results are reported on test seeds only, with repeats and their spread.
6. No paid call happens without an explicit `--execute`.

## 4. Architectures

Each architecture is built by hand with `StateGraph`. The user writes the graphs; the point of
the repository is to learn LangGraph.

| ID | Architecture | What it tests | LangGraph features |
| --- | --- | --- | --- |
| A1 | ReAct | The baseline: memory is the message history only | Tool node, conditional edge, loop limit |
| A2 | Map state | Does explicit memory beat history? The explored map lives in graph state and is rendered each turn | State schema, reducers |
| A3 | Plan-and-execute | Does planning help on L3? Planner sets subgoals, executor runs them, replanner reacts | Multiple nodes, cycles |
| A4 | Reflexion | Does learning from a failed attempt pay for itself? All attempts count toward the budget | Outer retry loop, persistent notes |
| A5 | Supervisor | Do subagents help or only add cost? Navigator and inventory subagents | Subgraphs, handoffs |
| A6 | Hybrid | How much of the work needs a model at all? Code searches the known map, the model picks targets | Plain Python nodes mixed with model nodes |

## 5. Runner and metrics

```bash
apl run --arch react --level L2 --seeds dev --repeats 3            # prints the plan only
apl run --arch react --level L2 --seeds dev --repeats 3 --execute  # spends money
apl report results/<run-id>
```

Without `--execute`, the runner prints the matrix and an estimate of model calls.

One JSONL row per episode:

| Field | Meaning |
| --- | --- |
| `success` | Reached the exit |
| `steps`, `optimal_steps`, `efficiency` | Steps taken, shortest solution, their ratio |
| `invalid_actions` | Tool calls that returned an error |
| `budget_hit` | Ran out of steps |
| `llm_calls`, `tool_calls` | Model and tool calls |
| `input_tokens`, `output_tokens` | Token use |
| `latency_s` | Wall time |

`apl report` writes a markdown table for each architecture and level: success rate, median
efficiency, tokens and the spread across repeats.

## 6. Stack

- Python 3.12, uv
- LangGraph 1.2.x
- LangChain `init_chat_model`, so `APL_MODEL` can name any provider in `provider:model` form
- pytest, ruff, mypy
- Optional later: tracing with Langfuse

## 7. Milestones

Each milestone after M0 is one Spec Kit feature (`/speckit-specify` through
`/speckit-implement`).

| Milestone | Scope | Done when |
| --- | --- | --- |
| M0 | Repository, README, this plan, Spec Kit for Claude Code and Codex | `specify` is set up for both agents |
| M1 | Generator, environment, tools, solver. No model | Tests show every generated dungeon is solvable and the solver finds the shortest solution |
| M2 | Runner, results format, report, A1 ReAct | One dry run and one small paid run produce a report |
| M3 | Browser viewer and A2 map state | In the browser, any level and seed can be shown and regenerated, and A1 or A2 can be watched playing it live; episodes are saved and replayable |
| M4 | First comparison, A1 vs A2 | Continuable runs, a comparison report and a written conclusion; the episode count is decided then (the parked design in `docs/parked/m4-comparison/` assumed 180) |
| M5+ | One architecture per feature: A3, A4, A5, A6 | Each one can be watched in the viewer and is added to the comparison on the same seeds |

Paperclip comes in from M5, when several architectures can be built as parallel tickets.

## 8. Cost control

- Dry run by default; `--execute` to spend money.
- Start with small matrices and grow them only once results look stable.
- A per-run token cap stops an episode that loops.

## 9. Decisions and open questions

Decided:

- Default model (since M3): `vllm:qwen3.5-9b`, Qwen3.5 9B on a local vLLM server (free, about
  2 s per call, 8,192-token context set on the server), through `APL_MODEL` and `APL_BASE_URL`.
  `ollama:qwen3:8b` (the M2 default, 16,384-token `APL_NUM_CTX`) and `openai:gpt-6-luna` remain
  options. Runs with different models are never combined.
- The subscription gateway (`~/workspace/subscription-gateway`) is used wherever a step needs no
  tool calls. It rejects `tools` and runs the request through an agent CLI, so it never runs
  experiment episodes: every architecture must call the same raw model (constitution I).
- License: MIT.

Open:

- Add a second environment later (for example a meeting scheduler for multi-agent patterns)?
