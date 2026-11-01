# Research: Several Problems, and the Survey Field

Decisions for [plan.md](plan.md). Each has the decision, the reason, and what else was
considered.

## R1. Constitution 2.0.0

**Decision**: amend with `/speckit-constitution` before any code:

- Principle I: "within a problem" — every architecture playing a problem gets that problem's base
  prompt, tool descriptions and step budget.
- Principle II: "Architectures MUST perceive and act on a problem only through that problem's
  tools (the dungeon: `look`, `move`, `take`, `use`; the survey field: `look`, `move`, `submit`).
  They MUST NOT import, call or read environment internals, generators, solvers or reference
  walks." The rest stays.
- Experiment Setup: per problem. Dungeon as now (6×, BFS solver, L1–L3). Survey field: generated
  from a seed, every cell reachable by construction, a reference walk computed by code, budget 3×
  the reference walk, levels S1–S3 in plan.md §2.
- Governance: results from different problems are never combined in one comparison.

MAJOR (2.0.0), because principle II is redefined. Also update `plan.md` §2–§4 (a "Problems"
section and the survey field) and `AGENTS.md` (the import rule names each problem's tools and
results modules).

**Rationale**: the spec requires it (FR-023), and the Constitution Check needs it to pass.

**Alternatives**: keep the four tools and model the field with them (`take` to count) — rejected:
it bends the field to fit the dungeon and the 6× budget would be far too loose.

## R2. A problem registry

**Decision**: `apl/problems.py` with a frozen `Problem` record per problem and
`PROBLEMS = {"dungeon": ..., "survey": ...}`, `DEFAULT = "dungeon"`. A problem provides: `levels`
(name → level), `dev_seeds`, `test_seeds`, `generate(level, seed)` (a world with `budget` and
`reference_steps`), `start_episode(world)`, `build_kit(episode, model)`, `prompt_fingerprint()`,
`render_text(world, route)` and, for the viewer, `board(world)` and `frame(episode, ...)`. Details
in [contracts/problems.md](contracts/problems.md).

**Rationale**: the runner and viewer each branch in one place; the dungeon modules do not change.

**Alternatives**: a `Problem` base class that `Dungeon` subclasses — rejected: it would touch the
dungeon's types. Plugins by entry point — far more than two problems need.

## R3. The kit per problem

**Decision**: `Kit` gains `problem: str`. `build_kit` keeps its signature and dungeon behavior;
`apl.survey` provides its own `build_kit` with its tool dispatch (`look`, `move`, `submit`) and the
same tool-node rules (calls run in order under one lock, `EpisodeEnded` after the episode ends,
unparsable calls answered). The shared tool-node loop moves into a private helper in `kit.py`
used by both. `prompt_fingerprint()` stays the dungeon's, unchanged (`ff9afb3b9f66`); each
problem has its own.

**Rationale**: A1 already uses only `kit.tools`, `kit.base_prompt`, `kit.start` and
`kit.tool_node`, so it plays the field with no change. Architectures that need to tell problems
apart read `kit.problem`.

**Alternatives**: one kit with all tools of all problems — breaks principle I (tool descriptions)
and confuses the model.

## R4. Field geometry and names

**Decision**: columns A, B, C… west to east, rows 1, 2, 3… north to south; a cell is named column
then row ("C4"). The start is A1, the north-west corner, for every scout. Moving north lowers the
row. Walls lie between two neighboring cells; the field's edge is a wall.

**Rationale**: coordinates are what a surveyor uses; the problem is counting, not navigation, so
names should help keep track (spec FR-010). One start corner makes the scouts' cost of reaching
their area part of what is measured.

**Alternatives**: opaque labels like the dungeon's — would turn the field back into a maze test.
Scouts starting in four corners — gives the orchestrators a split for free.

## R5. Levels

**Decision**:

| Level | Size | Walls | Deposits | Reference walk | Budget |
| --- | --- | --- | --- | --- | --- |
| S1 | 6×6 | none | 6 | 36 | 108 |
| S2 | 10×10 | none | 15 | 100 | 300 |
| S3 | 10×10 | 18 interior wall segments, at least 3 dead-end cells | 15 | computed | 3× |

**Rationale**: S1 is a baseline any architecture should solve. S2 is long enough to strain one
agent's history on a 32k-context model (about 100 steps at the very least) while four scouts each
cover 25 cells. S3 keeps the size and adds detours, so the effect of walls is isolated from size.

**Alternatives**: 12×12 for S2 — the reference walk alone (144 steps) would make single-agent
episodes slow on the local model.

## R6. What a cell result says

**Decision**: every `look` and successful `move` returns the cell view:

```json
{"cell": "C4", "deposit": true, "exits": ["north", "east", "west"], "columns": 10, "rows": 10}
```

The start view (free, as on the dungeon) is the same for A1. `submit` returns
`{"submitted": 12}`. The field size is in every view so no architecture needs it from elsewhere
and the base prompt stays the same for all levels.

**Rationale**: everything an agent needs to know when it has seen everything comes from tool
results (principle II). The true total is never shown.

**Alternatives**: the size in the base prompt — the prompt would differ per level and so would
the fingerprint within one run.

## R7. Episode rules and end reasons

**Decision**: `apl.survey.env.Episode` mirrors the dungeon's: scouts (max 4, added at A1 for no
step), a step counter, invalid-call counter, log with `LogEntry`, `on_step` observer, `stop()`.
End reasons: `submitted`, `budget`, `stopped`. A successful `submit` ends the episode; the budget
ends it when used up; `stop()` when the architecture returns. Success = `submitted` and the total
equals the deposit count. Re-entering a cell gives the same view. `submit` accepts a JSON integer
≥ 0, or a string of digits (models sometimes quote numbers); anything else is `invalid_total`,
costs a step and the episode goes on.

**Rationale**: the same shape lets the runner, meter and viewer treat both problems alike.

**Alternatives**: allow several submissions and score the last — makes "submit early, fix later"
a strategy the budget pays for, and complicates scoring.

## R8. The reference walk

**Decision**: open levels: the snake walk (row 1 east, row 2 west, …), which enters every cell
with `cells − 1` moves; plus 1 for `submit`, so `reference_steps = cells`. Walled levels: a greedy
walk that always goes to the nearest unseen cell by breadth-first search, ties broken north, east,
south, west; `reference_is_optimal = false` in the field and the rows. Both are computed at
generation time and tested for legality against the episode.

**Rationale**: the shortest walk covering every cell of a walled grid is a hard search problem; a
fixed, legal, near-short walk is enough for a budget and an efficiency ratio, as long as the
results say it is a reference (FR-013).

**Alternatives**: an exact search — exponential; a depth-first walk — much longer than needed on
open stretches.

## R9. Generation

**Decision**: `random.Random(f"survey:{level}:{seed}")`. Deposits: `deposits` distinct cells,
never A1, chosen uniformly. S3 walls: add random interior wall segments one at a time, keeping one
only if every cell stays reachable, until the level's count is reached and at least 3 cells have
exactly one exit; retry with the next draw if 1,000 tries fail. Seeds: `range(1000, 1010)` dev,
`range(2000, 2020)` test.

**Rationale**: reachable by construction, deterministic, cheap. The same seed numbers keep the CLI
and viewer simple; the problem name in the RNG key makes the worlds unrelated.

**Alternatives**: a maze carver — builds a maze, which is what S3 must not become.

## R10. The field map and A2 on the field

**Decision**: `apl/arch/field_map.py` with `FieldMap`, built from the start view and `apply(name,
args, result)` like `DungeonMap`. It holds the cells seen (deposit, exits), the current cell and
the field size. `render()` shows a picture of the field (`@` here, `o` deposit, `.` seen, `?`
unseen), the counts "cells seen k of n" and "deposits seen d", and the unseen cells next to seen
ones. `SharedMap` in `scouts.py` becomes generic over the map type (both maps have `current`,
`apply`, `render`), and scout and orchestrator texts get a survey variant. A2 (`mapstate`) picks
`FieldMap` when `kit.problem == "survey"`, with field map instructions of the same kind as
`MAP_INSTRUCTIONS` (they explain the map, not a strategy). A2 joins the survey field (spec FR-028).

**Rationale**: the scouts are A2's agent with a task; without A2 on the field, comparing scouts
with A1 would mix two effects (memory and splitting). Building the field map is needed for the
scouts anyway, so A2 costs little. Showing "deposits seen" is the field's counterpart of the
dungeon map listing items: a fact from tool results, not advice.

**Alternatives**: keep A2 off the field (the spec's first draft) — leaves the scouts without their
reference. Hide the count — would test arithmetic on a list, not memory.

## R11. Parallel turns

**Decision**: the survey `Episode` takes an optional `turn_source: Callable[[], int]`; the runner
sets it to the meter's model-call counter. Each log entry stores the counter at the time of the
call. `parallel_turns` = the number of distinct counter values among counted calls.

- A1, A2: one value per reply with tool calls.
- A7, A8: the scouts' model calls run in parallel before `act` applies all their calls, so a
  lockstep turn has one value; an orchestrator's submission after its own call is a turn of its
  own.
- A9: one scout per turn, so one value per scout turn — as slow as it really is.

**Rationale**: measured outside the graph, so no architecture can claim parallelism it does not
have (principle III); it needs no change to the architectures.

**Alternatives**: the longest single scout's step count — would make A9 look parallel. Wall time
only — noisy across providers.

## R12. Rows, run record, report

**Decision**: `EpisodeRow` gains `problem` (older rows: `"dungeon"`), and for the survey
`submitted_total`, `true_total`, `cells_seen`, `cells`, `parallel_turns`, `reference_is_optimal`
(all `None` on dungeon rows). `optimal_steps` holds the reference steps on survey rows, so the
existing efficiency column keeps its meaning (reference ÷ steps on success). `run.json` gains
`problem`. `apl report` refuses runs of different problems; the survey report has its own table
(right totals, median absolute error of wrong totals, median share of cells seen, steps, parallel
turns, tokens, latency, spread), and the comparison section adds Δ parallel turns. Dungeon plans
and reports print exactly what they print now: the `problem` line appears only for other problems.

**Rationale**: additive fields keep old runs readable; one problem per run keeps comparisons
fair (FR-005).

**Alternatives**: a separate row class per problem — two parsers and two row files for the same
runner.

## R13. Viewer

**Decision**: `/api/options` gains `problems` (name → levels, dev and test seeds, architectures
that support it) while keeping its dungeon fields. A new `/api/survey/<level>/<seed>` returns the
board (SVG, size, deposits, reference walk frames). `POST /api/episodes` takes `problem`
(default `dungeon`). The `start` event and saved episodes carry the problem. Survey step frames
carry each scout's cell, the set of seen cells, deposits seen and, at the end, the submitted
total. The page adds a problem picker and a survey renderer: grid, deposits, fog over unseen cells
when "Agent's view" is on, scout markers and trails in the existing colors, and a tally panel
(true, seen so far, submitted with right or wrong).

**Rationale**: the experimenter's first use (US1); the step slider, side panel and replay work on
frames, which both problems produce.

**Alternatives**: a separate page for the survey — duplicates the side panel and replay.

## R14. Who submits in the scout architectures

**Decision**:

- A7: after all scouts finish, a new `collect` node calls the orchestrator once more with each
  scout's final report; it answers `{"total": N}`, and the graph submits it through scout 0's
  tool node as a `submit` call (one step, logged as scout 0). Up to `MAX_MISSES` re-asks, as for
  the plan. Dungeon: unchanged, no collect node.
- A8: on the survey the stop answer is `{"total": N}` instead of `{"done": true}`, submitted the
  same way. Dungeon: unchanged.
- A9: scouts have the `submit` tool; the task text asks them to count all deposits, and the first
  successful submission ends the episode.
- Scouts in A7 and A8 also have `submit` in their tool list (principle I: same tools), but their
  task text says the orchestrator submits.

**Rationale**: an orchestrator does not call tools in M4's design; routing its answer through a
tool call keeps the step accounting and the log uniform (spec FR-015).

**Alternatives**: the environment sums scouts' reports — would remove the aggregation that the
field is meant to test.

## R15. Which architecture plays which problem

**Decision**: `registry.SUPPORTS: dict[str, frozenset[str]]`: `react`, `mapstate`, `fanout`,
`rounds`, `blackboard` → dungeon and survey; `mapstate_routes`, `hybrid` → dungeon. `RunSpec.build`
and the viewer refuse other pairs with "<arch> does not play the <problem> problem".

**Rationale**: one table, next to the names, checked before any episode.

**Alternatives**: a `PROBLEMS` constant in each architecture module — the registry would have to
import the modules to plan a run.

## R16. Keeping the dungeon unchanged

**Decision**: before the first code change, add tests that pin: the dungeon prompt fingerprint;
the dry-run plan text for `apl run --arch react --level all --seeds dev --limit 2`; a report
rendered from a stored M4 `episodes.jsonl` fixture; and the single-agent outcomes of every dev
dungeon (`tests/dungeon/test_golden.py` already does this). They must pass unchanged after every task.

**Rationale**: SC-001 is easiest to keep when it is checked from the first commit.
