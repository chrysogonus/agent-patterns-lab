---

description: "Task list for 010: the rune floor"
---

# Tasks: The Rune Floor

**Input**: Design documents from `specs/010-rune-floor/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R15), data-model.md, contracts/, quickstart.md

**Tests**: Yes. The spec's success criteria (SC-001–SC-007) and the plan's testing section ask for
them; each phase writes its tests first and they must fail before the implementation. Tests use
the scripted chat model (`tests/runner/scripted.py`) and never call a model.

**Organization**: by user story. US2 (the problem) comes before US1 (watching it), because the
viewer and the architectures need the problem to exist; both are P1. Constitution 2.3.0 is already
in place (done before the plan).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1–US4 from spec.md
- Paths are from the repository root

---

## Phase 1: Setup

**Purpose**: a green tree and a safety net for the signal trace, as M9 had for the survey field.

- [X] T001 Run the four checks on the tree as it is (`uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`); all must pass before T002.
- [X] T002 Pin the signal trace's outputs before any code change in `tests/runner/test_signal_pinned.py`, in the style of `tests/runner/test_survey_pinned.py`: `apl.signal_trace.prompt.prompt_fingerprint()` equals its current value (`4393e09f0471`; read it now to confirm); the exact dry-run text of `apl run --problem signal --arch react --level all --seeds dev --limit 1` (fixed settings record and code dict, as the survey pin builds it) stored in `tests/runner/fixtures/signal-plan.txt`. These tests, `tests/runner/test_dungeon_pinned.py` and `tests/runner/test_survey_pinned.py` must pass now and after every later task (SC-001, FR-020).
- [X] T003 [P] Update `plan.md`: the at-a-glance line says four problems; a new §2d "Rune floor" with the world (cells named as on the survey field, S and G on the middle row's ends, four colors, a hidden rule, walks, traps back to S, the free floor), the tools table from `specs/010-rune-floor/contracts/rune-tools.md`, the episode (ends at G, the budget or a stop; success when G is reached; reference by search over cell and rule state, budget 4× the reference, research R6) and the levels table of research R4 (R0 7×5 fixed trap cells; R1 7×5 a 3-color cycle; R2 9×7 a 4-cycle that doubles a color; R3 9×7 one color for odd rows and one for even rows); §4's "Problems" column: `react`, `mapstate`, `plan_execute`, `reflexion` gain "rune", `hybrid` becomes "dungeon, signal, rune"; §7 gains an M10 row "The rune floor, A1–A4 and A6 on it" with "Done when" from the spec and an empty status; §9 notes the rune floor as the fourth problem.
- [X] T004 [P] Update `AGENTS.md`: the import rule adds `apl.rune.tools` and `apl.rune.results`; the tools sentence adds "the rune floor's `look` and `move`"; the command list adds `uv run apl rune show --level R1 --seed 1000 --route reference` and `uv run apl run --problem rune --arch react --level all --seeds dev --limit 1`.

**Checkpoint**: the tree is green; dungeon, survey and signal outputs are pinned.

---

## Phase 2: User Story 2 - The rune-floor problem (Priority: P1) 🎯 MVP

**Goal**: a seed and a level always build the same floor and rule; agents act only through `look` and `move` with the floor free at the start; every floor has a reference and a budget; A1 plays it from the runner.

**Independent Test**: generate every level and seed and check them; play the scripted agents and scripted walks against the tools; play A1 with a scripted model through `play_episode(..., problem="rune")`.

### Tests for User Story 2 ⚠️ (write first, they must fail)

- [X] T005 [P] [US2] Rule and search tests in `tests/rune/__init__.py` (empty) and `tests/rune/test_rules.py` on hand-built floors: `allows` for each kind (`none` forbids exactly the trap cells; `cycle` allows the cell whose color is `colors[state]`; `rows` allows color `a` on odd rows (1, 3, …) and `b` on even rows); `next_state` (+1 modulo the cycle length on `cycle`, always 0 otherwise); `outcome_of` gives `start` onto S (state back to 0), `goal` onto G whatever the rule, `trap` onto a forbidden cell, `safe` otherwise; stepping back onto a cell of the same walk counts toward the state (research R3); `reference` equals a brute-force count of the shortest safe walk on a 4×3 floor for each rule kind; `reference_path` starts at S, ends at G, has `reference` moves, every step allowed in its state, ties broken north, east, south, west; `describe` gives `colors cycle: red, blue, green`, `odd rows blue, even rows yellow`, `fixed trap cells`.
- [X] T006 [P] [US2] Generator tests in `tests/rune/test_generator.py`: for R0–R3 and every dev and test seed, the floor is identical across two calls; size 7×5, 7×5, 9×7, 9×7; `start == (0, rows // 2)`, `goal == (columns − 1, rows // 2)`; every other cell has one of `COLORS`; the rule kind is `none`, `cycle` (3 distinct colors), `cycle` (`a, a, b, c` with a, b, c distinct), `rows` (two distinct colors); `reference` is finite and `> columns − 1` (the straight row is not safe, SC-002); `reference ≤ 12` on R0–R1 and `≤ 16` on R2–R3; `budget == 4 × reference`; `reference_is_optimal` is true; `generate("R9", 1000)` raises `ValueError` naming R0, R1, R2, R3 (research R4, R5).
- [X] T007 [P] [US2] Scripted-agent tests in `tests/rune/test_agents.py` per research R7, on every level and every dev and test seed, played through `Episode`: walking `reference_path` reaches G in exactly `reference` steps with no trap (SC-003); the *learner* (the straight row east until the first trap, then `reference_path`) reaches G within the budget; the *repeater* (the straight row east again and again) ends `budget` without reaching G (SC-004); the *memory-only* agent reaches G within the budget on every R0 floor. Put the three agents in `tests/rune/agents.py` so the generator test and the viewer tests can reuse them; the generator's own copy of the memory-only agent (T014) must agree with this one on every R0 seed.
- [X] T008 [P] [US2] Episode tests in `tests/rune/test_env.py` per data-model.md "Episode" and its transitions: `describe()` is free and equals the `look` data (`{"columns", "rows", "start", "goal", "position", "floor"}`, rows from row 1, `start` and `goal` words in place of colors); `look` costs a step; `move("east")` onto an allowed cell answers `{"position", "color"}` and extends the walk; `"up"` and `"East"` fail `invalid_direction`, off the floor fails `edge` with the contract messages, each costs a step, adds an invalid action and leaves the position; onto S answers `{"position": <S>, "color": "start"}`, starts a new walk (`walks` + 1) and is no trap; onto a forbidden cell answers `{"trap", "color", "position": <S>}` (`ok` true, not an invalid action), starts a new walk and counts a trap; a second trap on the same cell in the same rule state counts as repeated, the same cell in another state does not (R1), the same cell always does on R0 and R3 (research R8); onto G ends `goal` with success; with `max_attempts = 3` a trap adds `"attempts_left": 2`, calls `on_restart` once, sets `attempt` 2 and keeps `steps` and the trap counts; with no attempt left a trap has no `attempts_left` and the episode goes on; the budget ends it `budget`, and reaching G on the last step counts first; `stop()`; any call after the end returns `episode_over` with step `None`; `unknown("jump")` says "The tools are look and move." and costs a step; `outcome().to_dict()` has `traps`, `repeated_traps`, `walks`, `reference_is_optimal`, and `attempts` when > 1; the trap and repeated-trap counts are rebuilt from `outcome().to_dict()["log"]` alone with `apl.rune.rules` and equal the outcome's (SC-006).
- [X] T009 [P] [US2] Boundary tests in `tests/rune/test_boundary.py` per research R15: for every level and dev seed, 300 random calls (including bad directions and edges) give the fixed envelope and one of the data shapes of the contract (floor view, step, trap, goal); errors are `{"code", "message"}`; the start and `look` results are identical for one floor's colors under every rule kind (`dataclasses.replace(floor, rule=...)`); no result's JSON contains `cycle`, `rule`, `odd`, `even` or `reference`; `AgentTools` exposes only `start`, `look`, `move`.
- [X] T010 [P] [US2] Kit tests in `tests/rune/test_kit.py`: `build_kit` gives `problem == "rune"`, `BASE_PROMPT` and `TOOL_SCHEMAS` verbatim from `specs/010-rune-floor/contracts/rune-tools.md` (`move` takes `{"direction": {"type": "string", "enum": ["north", "east", "south", "west"], ...}}`), `start` the floor result JSON; the tool node answers `look`, `move` (argument `direction`, passed raw), unknown tools with `unknown_tool` (one step) and invalid calls; `add_scout()` returns None; `restart` and `max_attempts` reach the episode; the fingerprint is stable and differs from the dungeon's `ff9afb3b9f66`, the survey's and the signal trace's pinned values.
- [X] T011 [P] [US2] Render and CLI tests in `tests/rune/test_render.py` and `tests/rune/test_cli.py` per `specs/010-rune-floor/contracts/cli.md`: `apl rune show --level R1 --seed 1000` prints the header line (size, rule in words, reference steps with "optimal", budget), the column letters, one line per row with `r b g y`, `S` and `*`, and the legend; `--route reference` adds `reference: A3 → … → <goal> (<n> moves)`; `--html OUT` writes a page containing the SVG with `data-cell` tiles; an unknown level exits 2; a test seed is shown.
- [X] T012 [P] [US2] A1 tests in `tests/arch/test_react_rune.py`: `play_episode(key, ..., problem="rune")` with `react` and `play_calls` (from `tests/runner/scripted.py`) built from `reference_path` on R1 seed 1000 gives a completed row with `success`, `steps == optimal_steps`, `traps == 0`, and the first human message is the start floor JSON; a scripted walk along the straight row gives `traps ≥ 1` and, played to the budget, `success == False` with `budget_hit` (FR-021).

### Implementation for User Story 2

- [X] T013 [P] [US2] Create `src/apl/rune/model.py` per data-model.md: `RuneLevel(name, columns, rows, rule)`, `LEVELS = {"R0": RuneLevel("R0", 7, 5, "none"), "R1": RuneLevel("R1", 7, 5, "cycle3"), "R2": RuneLevel("R2", 9, 7, "cycle4"), "R3": RuneLevel("R3", 9, 7, "rows")}`; `COLORS = ("red", "blue", "green", "yellow")`; `Cell = tuple[int, int]`, `name(cell)` (`A1`-style) and `parse(name)`; the frozen `Floor(level, seed, columns, rows, colors, start, goal, rule, reference)` with `reference_steps`, `budget = 4 × reference` and `reference_is_optimal = True`; `Action(tool, args)` as the signal trace's. Also `src/apl/rune/seeds.py`: `DEV_SEEDS = range(1000, 1010)`, `TEST_SEEDS = range(2000, 2020)`.
- [X] T014 [US2] Create `src/apl/rune/rules.py` per data-model.md "Rule" and "Search" and research R3, R6: the frozen `Rule(kind, colors, traps)`; `allows`, `next_state`, `describe`, `outcome_of(floor, state, cell) -> "safe" | "trap" | "start" | "goal"` (the one place the move physics live), `reference(floor)` and `reference_path(floor)` (breadth-first over `(cell, state)` from `(start, 0)`, ties north, east, south, west). Plain functions over the colors, size and rule, so the generator can call them before a `Floor` exists.
- [X] T015 [US2] Create `src/apl/rune/generator.py` per research R5: `generate(level, seed) -> Floor` with `random.Random(f"rune:{level}:{seed}")`; per draw pick the rule (R1: 3 distinct colors; R2: `a, a, b, c`; R3: two distinct colors; R0: none), walk a self-avoiding path from S to G biased east (east weighted 3, north and south 1) of at most `columns − 1 + 6` moves, color its cells so the rule allows them in order, color every other cell at random, on R0 make each cell off the path a trap with probability 0.35; accept when the reference is finite and `> columns − 1`, and on R0 when the memory-only agent (research R7, its own copy here) reaches G within `4 × reference`; draw again up to `MAX_TRIES = 1000`; `ValueError` for an unknown level naming R0, R1, R2, R3.
- [X] T016 [P] [US2] Create `src/apl/rune/results.py` per data-model.md "Results": `ErrorCode` (`invalid_direction`, `edge`, `unknown_tool`, `episode_over`), `EndReason` (`goal`, `budget`, `stopped`), `FloorView`, `StepView`, `TrapView` (optional `attempts_left`), `GoalView`, `ToolError`, `ToolResult` with the shared envelope.
- [X] T017 [US2] Create `src/apl/rune/env.py` per data-model.md "Episode" and "Outcome": `MAX_ATTEMPTS = 3`; `LogEntry(index, step, action, result, attempt, scout=0)`; `Outcome`; `Episode` with `describe`, `look`, `move`, `unknown`, `restart`, `stop`, `outcome`, `on_step`, `on_restart`, `max_attempts = 1` by default; the direction parsing of research R9 (exactly one of the four words, as the survey's); the contract's error messages; moves through `rules.outcome_of`; traps and repeated traps per research R8 (`(cell, state)` seen before in the episode, every attempt); `walks`; the retry rule (a trap with attempts left adds `attempts_left` and restarts: `attempt` + 1, `on_restart`); `restart()` puts the agent on S and starts a new walk; `start_episode(floor)`.
- [X] T018 [P] [US2] Create `src/apl/rune/tools.py`: `AgentTools` with the free `start` (the floor result) and `look`, `move`, nothing else public; docstring names the allowed imports.
- [X] T019 [P] [US2] Create `src/apl/rune/prompt.py`: `BASE_PROMPT` and `TOOL_SCHEMAS` verbatim from `specs/010-rune-floor/contracts/rune-tools.md` (each description ending " Every call costs one step, including failed calls."; `direction` as the survey's `_DIRECTION`); `prompt_fingerprint()` as the others'.
- [X] T020 [US2] Create `src/apl/rune/kit.py`: `build_kit(episode, model)` on `apl.kit._tool_node`, dispatching `look` and `move` (argument `direction`, passed raw), else `episode.unknown`; `Kit(problem="rune", start=<floor JSON>, add_scout=lambda: None, restart=..., max_attempts=episode.max_attempts, ...)`.
- [X] T021 [US2] Create `src/apl/rune/__init__.py` (exports as `apl/signal_trace/__init__.py` does) and register `"rune"` in `PROBLEMS` in `src/apl/problems.py` per `specs/010-rune-floor/contracts/problems.md`, with lazily imported kit and fingerprint wrappers named as the others'. Update the test that lists the problems exactly, `tests/viewer/test_survey.py` (`{"dungeon", "survey", "signal"}` → with `"rune"`).
- [X] T022 [P] [US2] Create `src/apl/rune/render_text.py` (the contracts/cli.md text, with `route` adding the reference line) and `src/apl/rune/render_svg.py` (a tile `<rect class="tile" data-cell="C3">` per cell in a soft fill of its color, `S` and `G` labelled, the reference path as a polyline `class="reference"`, the rule as `<text class="rule">`; `animated` adds ids to the reference and the rule (hidden under "Agent's view") and the empty groups `#trails`, `#traps`, `#agent`, per contracts/viewer.md).
- [X] T023 [US2] In `src/apl/cli.py`: `apl rune show --level --seed [--route reference] [--html OUT]` beside `apl signal show`; the help line for the `rune` command group. (`--problem` already takes its choices from `PROBLEMS`.)
- [X] T024 [US2] In `src/apl/runner/registry.py`: `SUPPORTS["react"]` gains `"rune"` (the others join in US1 as each is written).

**Checkpoint**: T005–T012 pass; A1 plays the rune floor from the runner; `apl rune show` works (quickstart step 3); all three pins pass.

---

## Phase 3: User Story 1 - Watch an architecture cross a rune floor (Priority: P1)

**Goal**: A2, A3, A4 and A6 play the rune floor; in the viewer, pick the rune floor, a level and a dev seed, run an architecture and watch the trails, traps and reflections; replay saved episodes.

**Independent Test**: scripted A2, A3, A4 and A6 rune episodes with a checked walk log and option list; the viewer API, events and replay for a scripted rune episode.

### Tests for User Story 1 ⚠️ (write first, they must fail)

- [X] T025 [P] [US1] Walk log tests in `tests/arch/test_walk_log.py` per `specs/010-rune-floor/contracts/architectures.md`: built from a start floor; a safe `move` extends the current walk; a trap closes it as `trap at D3` and opens a new one; a move onto S closes it as `back on start`; a goal result ends it; a failed call changes nothing; `look` refreshes floor and position; `render()` prints exactly the contract example for that floor and walks; `known` counts distinct cells stepped on, traps included; `record(cell)` lists `(walk step, "safe" | "trap")` with walk step 1 for the first cell after S; on every R1 dev seed, a log built from a scripted episode's results agrees with the episode's walks and traps.
- [X] T026 [P] [US1] A2 and A3 on the rune floor in `tests/arch/test_rune_archs.py`: `mapstate` with a scripted model on R1: the system message is the rune base prompt plus `WALK_LOG_INSTRUCTIONS`, and every turn's last message is the walk log's render, matching a log built from the episode after every call; `plan_execute` with a scripted planner (`{"plan": ["reach the goal"]}`), an executor that walks `reference_path` and a replanner `{"done": true}` succeeds on R1, with the walk log in the executor's prompt; the other problems' tests of both stay as they are.
- [X] T027 [P] [US1] A4 on the rune floor in `tests/arch/test_reflexion_rune.py` per the contract's two A4 tests: (1) a scripted A4 on R1 walks the straight row into a trap, then (after the reflector's note) follows `reference_path`: the graph's and the episode's attempt both go from 1 to 2, `on_restart` is called exactly once, the reflector is called once and its prompt says "The attempt ended: trap.", the steps of both attempts add up in one budget; (2) an A4 reply with three moves whose first traps: only the first move runs (one step), the episode's position is S, the graph's and the episode's attempt are both 2, the kept reply has one call and one tool message, and the next model call is the reflector's; also, with no attempt left, a trap does not end the attempt and the rest of a batch runs; an actor that only re-walks known cells fails the attempt after `MAX_STALE` turns, because `known` does not grow.
- [X] T028 [P] [US1] A6 on the rune floor in `tests/arch/test_hybrid_rune.py` per the contract: on R1 seed 1000 the first option list is the moves from S that stay on the floor (north, east, south order; no west), each `never stepped on` with its cell and color; after a safe step and a trap the options carry `safe at walk step 1 (once)` and `trap at walk step 2 (once)`; a move onto the start or the goal reads `move west to the start` / `move east to the goal`; a scripted model whose answers walk `reference_path` reaches G in `reference` steps; answers that name no option are re-asked without a step and end the episode after `MAX_MISSES`; the dungeon and signal A6 tests stay as they are.
- [X] T029 [P] [US1] Viewer tests in `tests/viewer/test_rune.py` per `specs/010-rune-floor/contracts/viewer.md`: `/api/options` has `problems.rune` with levels R0–R3, the dev seeds and the architectures that play it; `/api/rune?level=R1&seed=1000` returns the contract fields; seed 2000 is 403; level `R9` is 400; `POST /api/episodes` with `"problem": "rune"` and `fanout` is 400 with the support message; a scripted `react` episode's `start` event has `problem`, `columns`, `rows`, `start` and `goal`, each `step` frame has the data-model.md "Frames" keys, the `end` event a row with `problem == "rune"`; a scripted `reflexion` episode with a trap emits one `restart` event; the saved episode replays with the same events, its id (level `R1`) matches the episode-id pattern, and `episode.json` records the problem (US1 1–6, SC-005); the other problems' responses stay as they are.

### Implementation for User Story 1

- [X] T030 [US1] Create `src/apl/arch/walk_log.py` per the contract: `WalkLog.from_start`, `apply`, `render`, `known`, `record`; docstring: built from tool results only, no rule, written by the agent at the experimenter's request.
- [X] T031 [US1] In `src/apl/arch/mapstate.py`: `WALK_LOG_INSTRUCTIONS` verbatim from the contract, and `WalkLog` with these instructions when `kit.problem == "rune"`, beside the signal branch; `SUPPORTS["mapstate"]` gains `"rune"` in `src/apl/runner/registry.py`.
- [X] T032 [US1] In `src/apl/arch/plan_execute.py`: the walk log and its instructions on `rune`; `SUPPORTS["plan_execute"]` gains `"rune"`.
- [X] T033 [US1] In `src/apl/arch/reflexion.py`: the walk log and its instructions on `rune`; `TRAP = "trap"` as the failure after a trap result with `attempts_left`; `RESTARTED` gains it; on `rune` the `act` node runs the reply's calls one at a time (each as a one-call message through `kit.tool_node`, as `hybrid.py` does), stops after the first result with `attempts_left`, and keeps the reply with only the calls that ran (as `_until_submit` does); `_size` uses `known` for a `WalkLog`; `SUPPORTS["reflexion"]` gains `"rune"`.
- [X] T034 [US1] In `src/apl/arch/hybrid.py`: a `kit.problem == "rune"` branch with `RUNE_HYBRID_INSTRUCTIONS` verbatim from the contract, a walk log in state, options built from `WalkLog.record` (the moves that stay on the floor, north, east, south, west, each with its record or `never stepped on`, and the start and goal wordings), the dungeon's answer parsing, re-ask and `MAX_MISSES`, and each option carried out with one tool call through `kit.tool_node`; `SUPPORTS["hybrid"]` becomes `{"dungeon", "signal", "rune"}`. Update the tests that quote hybrid's support list: `tests/runner/test_cli_run.py` and `tests/viewer/test_survey.py` (`(it plays: dungeon, signal)` → `(it plays: dungeon, rune, signal)`).
- [X] T035 [US1] Create `src/apl/rune/frames.py`: `snapshot(episode, step, action, result)` with the data-model.md "Frames" keys (`attempt` only when > 1) and `reference_frames(floor)` from `reference_path`.
- [X] T036 [US1] In `src/apl/viewer/app.py` and `src/apl/viewer/server.py`: `GET /api/rune` with the contract fields through the generic world parser; `frame_of` and the episode's world chosen by problem (`episode.floor` for the rune floor); the `start` event adds `problem`, `columns`, `rows`, `start` and `goal` on `rune`; `episode.json` records the problem; `EPISODE_ID` accepts `[LSTR][0-3]`.
- [X] T037 [US1] In `src/apl/viewer/assets/index.html`: an `isRune()` branch: load `/api/rune`; draw the SVG; per frame draw the current walk as a bold line from S, earlier walks as faded lines, a cross on every trap (the latest larger) and the agent's marker; the rule and the reference path hidden under "Agent's view"; the reference toggle labelled "Reference path" outlines the reference path; the stats panel shows `Floor <level> seed <seed>`, steps against budget and reference, walk and attempt, traps and repeated traps, the rule (unless "Agent's view") and `Reached G` or `Out of budget`; the other problems' views unchanged.
- [X] T038 [US1] Check `src/apl/viewer/assets/index.html` with the headless-browser check used since M3, on a scripted `reflexion` R1 episode with one trap: the trail grows per step, the trap draws a cross and fades the walk, the stats count one trap and end with "Reached G", and switching problem to and from `rune` raises no page error; then quickstart step 5 by hand with the local model (the experimenter).

**Checkpoint**: T025–T029 pass; the experimenter can watch and replay rune episodes (SC-005).

---

## Phase 4: User Story 3 - Run, continue and report on the rune floor (Priority: P2)

**Goal**: plan, run, continue and report rune runs with `--problem rune`; the report has its own table.

**Independent Test**: plan without `--execute`; play a scripted rune run, interrupt and continue it; check the report against the rows.

### Tests for User Story 3 ⚠️ (write first, they must fail)

- [X] T039 [P] [US3] CLI tests in `tests/runner/test_cli_run.py`: `apl run --problem rune --arch react,mapstate,plan_execute,reflexion,hybrid --level all --seeds dev --limit 1` prints a plan with `problem  rune`, levels R0, R1, R2, R3, 20 episodes, writes nothing and builds no model; `--arch fanout` exits 2 with `fanout does not play the rune problem (it plays: dungeon, survey)` (US3 1–2).
- [X] T040 [P] [US3] Run tests in `tests/runner/test_rune_runs.py` (as `tests/runner/test_signal_runs.py`): a scripted rune run stopped after 2 of 4 episodes continues from `run.json`'s problem and plays only the missing episodes; its rows have `problem == "rune"` and `traps`, `repeated_traps`, `walks`, `reference_is_optimal`; an infrastructure-error row still records `optimal_steps`, with null counts (US3 3, contracts/results.md).
- [X] T041 [P] [US3] Report tests in `tests/runner/test_report.py` and `tests/runner/test_compare.py`: from hand-written rune rows, the title ends "on the rune floor", the table has the contract header (Success, Steps, Traps, Repeated, Efficiency, Budget hit, Tokens, Latency); the spread table has Success and Traps (min–max) with repeats; the comparison uses the dungeon's columns and gives `hybrid` the reference `mapstate` on rune, while on the dungeon it stays `mapstate_routes`; a rune and a signal run together are refused; the row-key-order test gains the three fields after the signal trace's (US3 4).

### Implementation for User Story 3

- [X] T042 [US3] In `src/apl/runner/results.py`: `EpisodeRow` gains `traps`, `repeated_traps`, `walks` (nullable, None on other problems' rows, accepted as int or null on parse), appended after the signal trace's fields; `completed` fills them from a rune outcome by an attribute check, as `_signal` does; `failed` records `optimal_steps` from `episode.floor`.
- [X] T043 [US3] In `src/apl/runner/report.py`: the rune table and spread table per `specs/010-rune-floor/contracts/results.md`, chosen by `first.problem == "rune"`; the other tables unchanged (all three pins pass).
- [X] T044 [US3] In `src/apl/runner/compare.py`: `PROBLEM_REFERENCES` gains `"rune": {"hybrid": "mapstate"}`.

**Checkpoint**: T039–T041 pass; quickstart steps 4 and 6 work.

---

## Phase 5: User Story 4 - The fairness rules hold on the rune floor (Priority: P2)

**Goal**: the rule tests cover the fourth problem.

**Independent Test**: the import test passes with the rune modules allowed and fails for an architecture importing rune internals; two architectures on one rune level record the same prompt, tools and budget.

### Tests for User Story 4 ⚠️ (write first, they must fail)

- [X] T045 [P] [US4] In `tests/dungeon/test_boundary.py`: `ALLOWED` gains `apl.rune.tools` and `apl.rune.results`; a test like the signal trace's shows that a source importing `apl.rune.generator`, `apl.rune.env`, `apl.rune.rules` or `apl.rune.model` is rejected (FR-019, US4 2).
- [X] T046 [P] [US4] In `tests/runner/test_run.py`: a scripted rune run with `react` and `mapstate` on R1 records one `prompt_fingerprint` (the rune floor's) in `run.json`, and both rows have the same `budget` and `optimal_steps` (US4 3).

### Implementation for User Story 4

- [X] T047 [US4] In `src/apl/kit.py`: the module docstring names the rune floor's `tools` and `results` among the allowed imports. Fix anything T045–T046 find.

**Checkpoint**: T045–T046 pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T048 [P] Update `README.md`: the problems section gains the rune floor (with `apl rune show` and `apl run --problem rune`), the architecture table says which problems each plays, the roadmap gains M10.
- [X] T049 [P] Docstrings of the touched architecture modules (`mapstate.py`, `plan_execute.py`, `reflexion.py`, `hybrid.py`) say the rune version was written by the agent at the experimenter's request (specs/010).
- [X] T050 Mark M10 ✅ in `plan.md` §7 and the at-a-glance line.
- [X] T051 Remove the Sync Impact Report comment from `.specify/memory/constitution.md` (it is review scratch, not governance text).
- [X] T052 Run steps 1–4 of `specs/010-rune-floor/quickstart.md` and fix what they find.
- [X] T053 Run the four checks: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`.
- [X] T054 `/speckit-converge` for this feature, appending any remaining work to `specs/010-rune-floor/tasks.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 first; T002–T004 after it, in parallel.
- **US2 (Phase 2)**: after Phase 1; blocks every other story.
- **US1 (Phase 3)**: after US2 (it needs the rune episode, kit and rules).
- **US3 (Phase 4)**: after US2; can run alongside US1 (T040 and T041 use scripted or hand-written rows; T039 needs every name in `SUPPORTS`, so it passes once T031–T034 are done).
- **US4 (Phase 5)**: after US2.
- **Polish (Phase 6)**: after all stories.

### Within Each Story

- Tests first, failing; then model → rules → generator → results → environment → tools, prompt → kit → registry → CLI.
- US2: T013, T016 → T014 → T015 → T017 → T018, T019 → T020 → T021 → T022 → T023 → T024.
- US1: T030 → T031, T032, T033, T034; T035 → T036 → T037 → T038.
- The dungeon, survey and signal pins pass after every task.

### Parallel Opportunities

- T003, T004 (docs).
- T005–T012 (US2 tests); T013, T016, T018, T019, T022 (separate new files).
- T025–T029 (US1 tests); T031–T034 after T030 (separate architecture files, each with its own `SUPPORTS` line: do the `registry.py` edits one after another).
- T039–T041 (US3 tests); T045, T046 (US4 tests).

---

## Parallel Example: User Story 2 tests

```bash
Task: "T005 Rule and search tests in tests/rune/test_rules.py"
Task: "T006 Generator tests in tests/rune/test_generator.py"
Task: "T007 Scripted-agent tests in tests/rune/test_agents.py"
Task: "T008 Episode tests in tests/rune/test_env.py"
Task: "T009 Boundary tests in tests/rune/test_boundary.py"
```

## Parallel Example: the architectures on the rune floor

```bash
Task: "T031 WalkLog on rune in src/apl/arch/mapstate.py"
Task: "T032 WalkLog on rune in src/apl/arch/plan_execute.py"
Task: "T033 WalkLog, trap and the one-at-a-time act in src/apl/arch/reflexion.py"
Task: "T034 The rune branch in src/apl/arch/hybrid.py"
```

---

## Implementation Strategy

### MVP first (US2)

1. Phase 1: a green tree, the signal pins, the docs.
2. Phase 2: the rune floor, playable by A1 from the runner and printable with `apl rune show`.
3. Stop and check: every floor is valid, the reference is exact, the learner fits and the repeater
   does not, A1 scores successes and budget hits, all three pins pass.

### Then

4. US1: the walk log, A2, A3, A4 and A6, then the viewer. This is where the experimenter starts
   watching.
5. US3: rune runs and reports, for checking what the viewer showed across seeds.
6. US4: the rule tests for the fourth problem.
7. Polish, the four checks, `/speckit-converge`.

### Notes

- No task starts a paid or local experiment run; quickstart step 5 is the experimenter's, by hand.
- Commits only when the experimenter asks.

---

## Phase 7: Convergence

- [X] T055 In `src/apl/viewer/assets/index.html`, tick the "Reference path" toggle when a rune floor is loaded (the experimenter can still untick it), so the reference path is outlined as soon as the floor is picked, per US1/AC1 (partial)
- [X] T056 Record A4's rune-only actor sentence `RUNE_ATTEMPT` ("On this floor an attempt also fails when a step springs a trap.") under "A3 and A4" in `specs/010-rune-floor/contracts/architectures.md`, per contracts/architectures.md (unrequested)
