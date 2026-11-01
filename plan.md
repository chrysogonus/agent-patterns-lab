# Plan

## 1. Goal

Learn how agent architectures behave by building several of them for one task and measuring
them under identical conditions.

**Question:** with the model and tools fixed, how do architectures differ in success,
efficiency and cost on exploration tasks that get harder step by step?

The task is deliberately small and fully simulated, so every result can be scored by code and
every run is cheap to repeat.

Since M5 the lab has two problems: the dungeon (§2) and the survey field (§2b). Each problem has
its own tools, levels, seeds and budget rule, and architectures are compared only within a
problem. The survey field is built so that one property shows: on an open field with no dead
ends, splitting the work between scouts should pay off, unlike in the M4 dungeons.

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
budget is 6× the shortest solution.

### Levels

| Level | Grid | Locks | Purpose |
| --- | --- | --- | --- |
| L1 | 3×3 | none | Baseline; every architecture should pass |
| L2 | 4×4 | one key, one door | Detours and remembering where things are |
| L3 | 5×5 | two chained keys, dead ends | Planning and backtracking |

### Seeds

Fixed **dev** seeds are used while building and tuning. Separate **test** seeds are used only
for reported results, so tuning does not leak into them.

## 2b. Survey field

### World

- An N×N grid of cells under fog. Some cells hold an ore deposit (at most one each). Cells are
  named column letter then row number: A1 is the north-west corner, columns go east, rows go
  south.
- Every agent starts in A1. Walls may separate neighboring cells; every cell is reachable.

### Tools

| Tool | Returns |
| --- | --- |
| `look()` | The current cell's name, whether it holds a deposit, the directions one can move, and the field's size |
| `move(direction)` | The same for the new cell, or an error (wall or field edge) |
| `submit(total)` | Ends the episode with this number of deposits, or an error (not a whole number) |

### Episode

The episode ends at the first successful submission, when the step budget is used up, or when the
architecture stops. It is a success when the submitted total is the true number of deposits.
Code computes a reference walk that enters every cell (the snake walk on open levels, the
shortest there; a greedy nearest-unseen-cell walk on walled ones). The step budget is 3× the
reference steps (the walk plus the submission).

### Levels

| Level | Grid | Walls | Deposits | Purpose |
| --- | --- | --- | --- | --- |
| S1 | 6×6 | none | 6 | Baseline; every architecture should get it right |
| S2 | 10×10 | none | 15 | A long history for one agent; open regions for scouts |
| S3 | 10×10 | 18 interior segments, at least 3 dead ends | 15 | Walls bring back detours, where scouts may lose their lead |

Seeds: the dungeon's numbers (dev 1000–1009, test 2000–2019); the problem name keys the generator,
so the worlds are unrelated.

## 3. Fairness rules

These become the Spec Kit constitution.

1. Within a problem, every architecture uses the same model, temperature, base prompt, tool
   descriptions and step budget.
2. Architectures see the world only through the problem's tools. They never read environment
   internals, the generator, the solver or the reference walk.
3. Only the graph may differ: nodes, edges, state and what each node is told.
4. Tool results and final outcomes are structured data, not free text, so scoring is exact.
5. Results are reported on test seeds only, with repeats and their spread.
6. No paid call happens without an explicit `--execute`.

## 4. Architectures

Each architecture is built by hand with `StateGraph`. The user writes the graphs; the point of
the repository is to learn LangGraph.

| ID | Architecture | What it tests | LangGraph features | Problems |
| --- | --- | --- | --- | --- |
| A1 | ReAct | The baseline: memory is the message history only | Tool node, conditional edge, loop limit | dungeon, survey |
| A2 | Map state | Does explicit memory beat history? The explored map lives in graph state and is rendered each turn | State schema, reducers | dungeon, survey |
| A2r | Map state with routes (`mapstate_routes`) | Does a planning aid help a small model? A2's map plus the shortest known route to each unexplored exit | Same graph as A2 | dungeon |
| A3 | Plan-and-execute | Does planning help on L3? Planner sets subgoals, executor runs them, replanner reacts | Multiple nodes, cycles | — |
| A4 | Reflexion | Does learning from a failed attempt pay for itself? All attempts count toward the budget | Outer retry loop, persistent notes | — |
| A5 | Supervisor | Do subagents help or only add cost? Navigator and inventory subagents | Subgraphs, handoffs | — |
| A6 | Hybrid | How much of the work needs a model at all? Code searches the known map, the model picks targets | Plain Python nodes mixed with model nodes | dungeon |
| A7 | Fan-out once (`fanout`) | Does splitting the exploration help? An orchestrator splits the dungeon once; up to 4 scouts explore on their own maps | `Send`, parallel branches, reducers | dungeon, survey |
| A8 | Supervisor in rounds (`rounds`) | Does replanning on the merged map help the scouts? Short tasks per round, replanned on what all scouts saw | `Send` in a cycle, shared state | dungeon, survey |
| A9 | Shared blackboard (`blackboard`) | Can scouts coordinate without a planner? They take turns on one live map and claim frontiers | Round-robin routing over shared state | dungeon, survey |

A7–A9 put up to 4 scouts in one episode. Each scout has its own position and inventory; doors,
items left in rooms and the step budget are shared, and every scout's tool calls count toward the
one budget. The scout is A2's map-state agent with a task, so A2 is their single-agent reference.

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
| M4 | First comparison of seven architectures (A1, A2, A2r, A6, and the orchestrators A7–A9 with several scouts) | Continuable runs, a comparison report and a written conclusion, from one dev seed per level on `openai:gpt-6-luna` (21 episodes, a first look) |
| M5 | Several problems and the survey field (A1, A2, A7–A9 on it) | Any survey level and seed can be shown and watched in the viewer; survey runs plan, continue and report like dungeon runs; the dungeon is unchanged |
| M6+ | One architecture per feature: A3, A4, A5 | Each one can be watched in the viewer and is added to the comparison on the same seeds |

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

- A second problem (since M5): the survey field, where splitting the work should pay off
  (specs/005). Further boards are sketched in the problem mock-ups (signal trace, combination
  vault, workshop, warehouse robots, rune floor), one per later feature.
