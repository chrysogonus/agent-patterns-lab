# Plan

> **At a glance.** Six small simulated problems (a dungeon, a survey field, a signal trace, a rune
> floor, a workshop and a warehouse), one model, and several hand-built LangGraph architectures,
> scored by code. M0–M13 are built: every architecture in §4 is in, M12 added the warehouse and M13
> a harder top level on the signal trace and the workshop.
> The [README](README.md) is the short tour. This file holds the design: the worlds (§2–§2f),
> the fairness rules (§3), the architectures (§4), the metrics (§5) and the milestones (§7).

## 1. Goal

Learn how agent architectures behave by building several of them for one task and measuring
them under identical conditions.

**Question:** with the model and tools fixed, how do architectures differ in success,
efficiency and cost on exploration tasks that get harder step by step?

The task is deliberately small and fully simulated, so every result can be scored by code and
every run is cheap to repeat.

The lab has six problems: the dungeon (§2), the survey field (§2b), the signal trace (§2c), the
rune floor (§2d), the workshop (§2e) and the warehouse (§2f). Each problem has its own tools,
levels, seeds and budget rule, and architectures are compared only within a problem. Each problem
after the dungeon is built so that one property shows: splitting the work (survey field), choosing
what to look at next (signal trace), learning from failure (rune floor), planning ahead (workshop)
and adapting a split of the work (warehouse).

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

## 2c. Signal trace

Built so that the choice of what to look at next is the only thing that differs (specs/009): every
answer is true and the whole layout is known, so a model can only waste probes, never be misled.

### World

- Water flows from a source S through segments numbered 1..N. Each segment is fed from S or from
  one other segment with a lower number; a segment feeds at most two others, so the pipe can
  branch. Exactly one segment is broken: it and every segment downstream of it are dry, every
  other segment is wet.
- The layout is given free at the start, as runs: `{"from": F, "first": a, "last": b}` means F
  feeds a, a feeds a+1, and so on up to b.

### Tools

| Tool | Returns |
| --- | --- |
| `look()` | The layout again: the number of segments and the runs |
| `probe(segment)` | Whether water reaches that segment, or an error (no such segment) |
| `submit(segment)` | Ends the episode naming that segment as broken, or an error (no such segment) |

### Episode

The episode ends at the first submission, when the step budget is used up, or when the
architecture stops. It is a success when the submitted segment is the broken one. Code computes a
reference: the worst case of a greedy split strategy (bisection on a single run, the optimum
there) plus the submission. The step budget is the larger of 3× the reference and a full
probe-by-probe scan (N−1 probes and the submission). A probe whose answer earlier answers already
implied counts as wasted.

### Levels

| Level | Segments | Layout | Reference | Budget | Purpose |
| --- | --- | --- | --- | --- | --- |
| T1 | 16 | one run | 5 (optimal) | 16 | Baseline; every architecture should find it |
| T2 | 64 | one run | 7 (optimal) | 64 | About 6 probes for bisection, about 32 for a scan |
| T3 | 64 | a tree with 4 pipe ends, every run ≥ 4 | about 8 | 64 | Halfway along the numbers is no longer the best probe |
| T4 | 256 | a tree with 8 pipe ends, every run ≥ 4 | about 12 | 256 | Fifteen runs to weigh: the best split is harder to find |

Seeds: the same numbers as the other problems, keyed by the problem name.

## 2d. Rune floor

Built so that learning a rule from failures is what differs (specs/010): the whole floor is
visible, only the rule deciding which steps are safe is hidden, and the only way to learn it is to
be trapped by it.

### World

- A rectangle of cells named as on the survey field (`A1` is the north-west corner). The start S
  is the west edge's middle cell, the goal G the east edge's middle cell; every other cell is red,
  blue, green or yellow. The floor is given free at the start.
- A *walk* is the cells stepped on since the agent last stood on S. A hidden rule judges each step
  with the walk so far. A forbidden step is a trap: the agent is back on S and a new walk starts.
  Stepping onto S starts a new walk without a trap; stepping onto G always ends the episode.
- Every floor has a safe path, and the straight row from S to G is never safe.

### Tools

| Tool | Returns |
| --- | --- |
| `look()` | The floor again: its size, every tile's color, the start, the goal and the agent's cell |
| `move(direction)` | The tile moved onto and its color, a trap (where, and that the agent is back on S), the goal reached, or an error (off the floor, unknown direction) |

### Episode

The episode ends at the goal, when the step budget is used up, or when the architecture stops. It
is a success when the goal is reached. Code computes a reference: the moves on the shortest safe
path, found by a search over (cell, rule state), so it is the optimum. The step budget is 4× the
reference. A trap is repeated when an earlier trap sprang on the same cell in the same rule state.

### Levels

| Level | Floor | Rule | Purpose |
| --- | --- | --- | --- |
| R0 | 7×5 | none: a fixed set of trap cells | Control: nothing to learn beyond "not that cell" |
| R1 | 7×5 | a cycle of 3 colors over the walk (e.g. red, blue, green) | Baseline rule; one walk of three safe steps shows it |
| R2 | 9×7 | a cycle of 4 that doubles a color (e.g. red, red, blue, green) | Takes more than one trap to pin down |
| R3 | 9×7 | one color allowed on odd rows, another on even rows | The obvious guess, a color order, is wrong |

Seeds: the same numbers as the other problems, keyed by the problem name.

## 2e. Workshop

Built so that planning ahead is what differs (specs/011): steps depend on each other, a scarce raw
material is needed in two places, and the obvious recipe for one part uses it up.

### World

- A goal item, craftable items made from recipes, and raw materials with a stock count each, some
  scarce (stock 1). A recipe is a list of inputs, one unit each. Most items have one recipe; a
  *tempting* item has two, and its first uses the scarce material one level down (frame ← iron bar
  ← coal), while another branch needs that material too.
- The goal and the stock are given free at the start; a recipe is seen only by inspecting the
  item. The episode ends as stuck once the goal can no longer be made from the inventory and the
  stock.

### Tools

| Tool | Returns |
| --- | --- |
| `look()` | The goal, the stock with counts, and the inventory |
| `inspect(item)` | The item's recipes, or that it is a raw material |
| `gather(item)` | One unit of a raw material from the stock into the inventory |
| `craft(item, recipe)` | The item made with recipe 1 or 2 from the inventory |

### Episode

The episode ends when the goal is crafted, stuck, at the budget, or when the architecture stops. It
is a success when the goal is crafted. Code computes a reference: one inspect of every craftable
item the shortest plan crafts, plus its gathers and crafts. The step budget is 3× the reference. A
scarce unit used beyond the reference plan's use counts as wasted.

### Levels

| Level | Craftables | Depth | Conflicts | Purpose |
| --- | --- | --- | --- | --- |
| W1 | 3 | 2 | none (one harmless second recipe) | Baseline; every architecture should finish |
| W2 | 5 | 3 | 1 | The mock-up's lantern: planning saves the coal |
| W3 | 8 | 4 | 2 | Two conflicts a plan must hold at once |
| W4 | 12 | 5 | 3 | Three scarce materials a plan must protect at once |

Seeds: the same numbers as the other problems, keyed by the problem name.

## 2f. Warehouse

Built so that adapting a split of the work is what differs (specs/012): the packages are spread
unevenly and found only by looking, so a split decided before anyone has looked leaves a robot
idle.

### World

- Rows of shelves with aisles between them, a cross corridor at each end, a dock S in the west
  corridor where robots start and a drop zone D in the east corridor, both off the aisles. Cells are
  named as on the survey field.
- Packages stand on aisle cells. The floor plan and the number of packages are given free at the
  start; a robot sees the packages of the corridors it stands in.
- A robot carries one package at a time and delivers it by dropping it on D. Up to 4 robots (for
  the orchestrators); they share cells and never block each other.

### Tools

| Tool | Returns |
| --- | --- |
| `look()` | The robot's cell, the corridors it stands in and the packages it sees there, what it carries, whether it is on D, and the packages delivered |
| `move(direction)` | The same view after one step, or an error (shelf, edge of the floor, unknown direction) |
| `pick()` | That the robot now carries the package on its cell, or an error (no package, already carrying) |
| `drop()` | That the carried package is delivered, or an error (not on D, carrying nothing) |

### Episode

The episode ends when every package is delivered, when the step budget is used up, or when the
architecture stops. It is a success when every package is delivered. Code computes a reference: the
steps of a single robot that clears the aisles north to south, carrying each package to D as soon
as it sees it (a reference, not an optimum). The step budget is 3× the reference, shared by all
robots, so more robots buy no steps; their gain shows in parallel turns.

### Levels

| Level | Floor | Packages | Spread | Purpose |
| --- | --- | --- | --- | --- |
| P1 | 9 columns, 3 aisles | 3 | one per aisle | Baseline; every architecture should finish |
| P2 | 9 columns, 3 aisles | 3 | a shuffle of 0, 1, 2 | The mock-up: a blind split leaves a robot idle |
| P3 | 11 columns, 5 aisles | 6 | a shuffle of 3, 1, 1, 1, 0 or 3, 2, 1, 0, 0 | More to reassign |

Seeds: the same numbers as the other problems, keyed by the problem name.

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
| A1 | ReAct | The baseline: memory is the message history only | Tool node, conditional edge, loop limit | dungeon, survey, signal, rune, workshop, warehouse |
| A2 | Map state | Does explicit memory beat history? The explored map lives in graph state and is rendered each turn | State schema, reducers | dungeon, survey, signal, rune, workshop, warehouse |
| A2r | Map state with routes (`mapstate_routes`) | Does a planning aid help a small model? A2's map plus the shortest known route to each unexplored exit | Same graph as A2 | dungeon |
| A3 | Plan-and-execute | Does committing to a plan help? Planner sets subgoals, executor runs them in order, replanner is asked only when a subgoal cannot be done or finished, or the plan is used up | Multiple nodes, cycles | dungeon, survey, signal, rune, workshop |
| A4 | Reflexion | Does learning from a failed attempt pay for itself? All attempts count toward the budget. On the rune floor the walk log is kept across attempts, so A4 has A2's full walk history and differs in the notes and its retry controls. On the dungeon an attempt fails only by giving up or going stale, and the report notes that those results measure reflection together with these stall restarts | Outer retry loop, persistent notes | dungeon, survey, signal, rune, workshop |
| A4r | Retry (`retry`) | What do A4's notes add? A4's attempts, restarts and stall rule with no reflector and no notes; A4 against it isolates the notes | Same graph as A4 without the reflector node | dungeon, survey, signal, rune, workshop |
| A5 | Supervisor (`supervisor`) | Do subagents help or only add cost? A supervisor hands tasks to a navigator (look, move) and an inventory subagent (take, use) | Subgraphs, handoffs (`Command`); on the workshop a researcher (look, inspect) and a crafter (gather, craft) | dungeon, workshop |
| A6 | Hybrid | How much of the work needs a model at all? Code searches the known map, the model picks targets | Plain Python nodes mixed with model nodes | dungeon, signal, rune, workshop |
| A7 | Fan-out once (`fanout`) | Does splitting the exploration help? An orchestrator splits the dungeon once; up to 4 scouts explore on their own maps | `Send`, parallel branches, reducers | dungeon, survey, warehouse |
| A8 | Supervisor in rounds (`rounds`) | Does replanning on the merged map help the scouts? Short tasks per round, replanned on what all scouts saw | `Send` in a cycle, shared state | dungeon, survey, warehouse |
| A9 | Shared blackboard (`blackboard`) | Can scouts coordinate without a planner? They take turns on one live map and claim frontiers | Round-robin routing over shared state | dungeon, survey, warehouse |

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

| Milestone | Scope | Done when | Status |
| --- | --- | --- | :---: |
| M0 | Repository, README, this plan, Spec Kit for Claude Code and Codex | `specify` is set up for both agents | ✅ |
| M1 | Generator, environment, tools, solver. No model | Tests show every generated dungeon is solvable and the solver finds the shortest solution | ✅ |
| M2 | Runner, results format, report, A1 ReAct | One dry run and one small paid run produce a report | ✅ |
| M3 | Browser viewer and A2 map state | In the browser, any level and seed can be shown and regenerated, and A1 or A2 can be watched playing it live; episodes are saved and replayable | ✅ |
| M4 | First comparison of seven architectures (A1, A2, A2r, A6, and the orchestrators A7–A9 with several scouts) | Continuable runs, a comparison report and a written conclusion, from one dev seed per level on `openai:gpt-6-luna` (21 episodes, a first look) | ✅ |
| M5 | Several problems and the survey field (A1, A2, A7–A9 on it) | Any survey level and seed can be shown and watched in the viewer; survey runs plan, continue and report like dungeon runs; the dungeon is unchanged | ✅ |
| M6 | A3 plan-and-execute (`plan_execute`) on both problems | It can be watched in the viewer and is added to the comparison on the same seeds | ✅ |
| M7 | A4 Reflexion (`reflexion`) on both problems, with up to 3 attempts per episode (constitution 2.1.0) | It can be watched in the viewer and is added to the comparison on the same seeds | ✅ |
| M8 | A5 supervisor (`supervisor`) on the dungeon | It can be watched in the viewer and is added to the comparison on the same seeds | ✅ |
| M9 | The signal trace (§2c), with A1–A4 and A6 on it | Any signal level and seed can be shown and watched in the viewer; signal runs plan, continue and report like the other problems; the dungeon and the survey field are unchanged | ✅ |
| M10 | The rune floor (§2d), with A1–A4 and A6 on it | Any rune level and seed can be shown and watched in the viewer; rune runs plan, continue and report like the other problems; the other problems are unchanged | ✅ |
| M11 | The workshop (§2e), with A1–A6 on it | Any workshop level and seed can be shown and watched in the viewer; workshop runs plan, continue and report like the other problems; the other problems are unchanged | ✅ |
| M12 | The warehouse (§2f), with A1, A2 and A7–A9 on it | Any warehouse level and seed can be shown and watched in the viewer; warehouse runs plan, continue and report like the other problems; the other problems are unchanged | ✅ |
| M13 | Harder top levels: T4 on the signal trace (§2c), W4 on the workshop (§2e) | Any T4 and W4 seed can be shown and watched in the viewer; runs with `--level all` include them; T1–T3, W1–W3 and saved runs are unchanged | ✅ |

Paperclip comes in from M5, when several architectures can be built as parallel tickets.

## 8. Cost control

- Dry run by default; `--execute` to spend money.
- Start with small matrices and grow them only once results look stable.
- A per-episode token cap (`APL_TOKEN_CAP`) stops an episode that loops.

## 9. Decisions and open questions

Decided:

- Default model (since M3): `vllm:qwen3.5-9b`, Qwen3.5 9B on a local vLLM server (free, about
  2 s per call, 32,768-token context set on the server), through `APL_MODEL` and `APL_BASE_URL`.
  `ollama:qwen3:8b` (the M2 default, 16,384-token `APL_NUM_CTX`) and `openai:gpt-6-luna` remain
  options. Runs with different models are never combined.
- The subscription gateway (`~/workspace/subscription-gateway`) is used wherever a step needs no
  tool calls. It rejects `tools` and runs the request through an agent CLI, so it never runs
  experiment episodes: every architecture must call the same raw model (constitution I).
- License: MIT.
- A second problem (since M5): the survey field, where splitting the work should pay off
  (specs/005). Further boards are sketched in the problem mock-ups (signal trace, combination
  vault, workshop, warehouse robots, rune floor), one per later feature.
- A third problem (since M9): the signal trace, where the choice of the next probe is all that
  differs (specs/009). Noisy probes are left for a later level or feature.
- A fourth problem (since M10): the rune floor, where learning a hidden rule from traps is what
  differs (specs/010); R0, a floor with no rule, is the control where reflecting can only cost.
- A fifth problem (since M11): the workshop, where planning ahead under a scarce material is what
  differs (specs/011).
- A sixth problem (since M12): the warehouse, where adapting a split of the work to packages found
  along the way is what differs (specs/012). The combination vault is the one mock-up board left.
- Harder top levels (since M13): T4 and W4 (specs/013), after the first `gpt-6-luna` run on the
  four new problems showed every architecture solving the signal trace and the workshop. T4 keeps
  the signal budget rule (a full scan, 256 steps), so it separates architectures by wasted probes
  and tokens; noisy probes stay deferred.
