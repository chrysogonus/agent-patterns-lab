---

description: "Task list for 012: the warehouse"
---

# Tasks: The Warehouse

**Input**: Design documents from `specs/012-warehouse/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R18), data-model.md, contracts/, quickstart.md

**Tests**: Yes. The spec's success criteria (SC-001–SC-007) and the plan's testing section ask for
them; each phase writes its tests first and they must fail before the implementation. Tests use
the scripted chat model (`tests/runner/scripted.py`) and never call a model.

**Organization**: by user story. US2 (the problem) comes before US1 (watching it), because the
viewer and the architectures need the problem to exist; both are P1. Constitution 2.5.0 is already
in place (done before the plan).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1–US4 from spec.md
- Paths are from the repository root

---

## Phase 1: Setup

**Purpose**: a green tree and a safety net for the workshop, as M11 had for the rune floor.

- [X] T001 Run the four checks on the tree as it is (`uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`); all must pass before T002.
- [X] T002 Pin the workshop's outputs before any code change in `tests/runner/test_workshop_pinned.py`, in the style of `tests/runner/test_rune_pinned.py`: `apl.workshop.prompt.prompt_fingerprint()` equals `d07e651ad0af`; the exact dry-run text of `apl run --problem workshop --arch react --level all --seeds dev --limit 1` stored in `tests/runner/fixtures/workshop-plan.txt` (written once with `GOLDEN_REGEN=1`). These and the earlier pins must pass now and after every later task (SC-001, FR-020).
- [X] T003 [P] Update `plan.md`: the at-a-glance line says six problems; a new §2f "Warehouse" with the world (research R2–R5), the tools table from `specs/012-warehouse/contracts/warehouse-tools.md`, the episode (ends when every package is delivered, at the budget or a stop; reference and budget of R6) and the levels table of R2 (P1 9 columns, 3 aisles, 3 packages one per aisle; P2 the same floor, a shuffle of 0, 1, 2; P3 11 columns, 5 aisles, 6 packages, a shuffle of 3,1,1,1,0 or 3,2,1,0,0); §4's "Problems" column: `react`, `mapstate`, `fanout`, `rounds`, `blackboard` gain "warehouse"; §7 gains an M12 row "The warehouse, A1, A2 and A7–A9 on it" with "Done when" from the spec and an empty status; §9 notes the warehouse as the sixth problem and that the combination vault is the one mock-up left.
- [X] T004 [P] Update `AGENTS.md`: the import rule adds `apl.warehouse.tools` and `apl.warehouse.results`; the tools sentence adds "the warehouse's `look`, `move`, `pick` and `drop`"; the command list adds `uv run apl warehouse show --level P2 --seed 1000 --route reference` and `uv run apl run --problem warehouse --arch react --level all --seeds dev --limit 1`.

**Checkpoint**: the tree is green; the five earlier problems' outputs are pinned.

---

## Phase 2: User Story 2 - The warehouse problem (Priority: P1) 🎯 MVP

**Goal**: a seed and a level always build the same warehouse; robots act only through `look`, `move`, `pick` and `drop` with the floor plan, the package count and the first view free at the start; every warehouse has a reference and a budget; A1 plays it from the runner.

**Independent Test**: generate every level and seed and check them; play the scripted agents and scripted calls against the tools; play A1 with a scripted model through `play_episode(..., problem="warehouse")`.

### Tests for User Story 2 ⚠️ (write first, they must fail)

- [X] T005 [P] [US2] Model and plans tests in `tests/warehouse/__init__.py` (empty) and `tests/warehouse/test_plans.py` on a hand-built P2-shaped floor (9 columns, 5 rows; aisles on rows 1, 3, 5 (1-based); dock A2, D I2; package 1 at B5, package 2 at E1, package 3 at G5): `corridors(cell)` names the aisle of an aisle row and the west/east corridor in column A / the last column (A1 is in "aisle 1" and "west corridor"); shelves are columns B–H on rows 2 and 4; `neighbor` refuses shelves and the edge; the shortest path from the dock to E1 is 5 moves, ties going north then east; `reference_calls` clears aisle 1 then aisle 3 (aisle 2 seen and left), ends with a drop, and its length is `reference_steps`; the blind split (one robot per aisle) and the replanning split of research R7 return per-robot call lists, and played through the episode the blind split leaves robot 1 (aisle 2, empty) idle while packages remain and the replanning split takes fewer parallel turns.
- [X] T006 [P] [US2] Generator tests in `tests/warehouse/test_generator.py`: for P1–P3 and every dev and test seed, the floor is identical across two calls; columns and rows as R2 (9×5, 9×5, 11×9); the dock and D in the west and east corridors on the shelf row north of the middle aisle; packages on distinct aisle cells in columns B to the second-last; the packages-per-aisle multiset is one of the level's spreads (P1 (1,1,1); P2 (0,1,2); P3 (3,1,1,1,0) or (3,2,1,0,0)); package names `package 1`…`package n` with the numbers not in reading order on at least one seed per level; `budget == 3 × reference_steps`; `reference_is_optimal` is false; `generate("P9", 1000)` raises `ValueError` naming P1, P2, P3 (SC-002, research R2, R5, R6).
- [X] T007 [P] [US2] Scripted-agent tests in `tests/warehouse/test_agents.py` per research R7, on every level and every dev and test seed, played through `Episode`: the reference delivers every package in exactly `reference_steps` steps (SC-003); on P2 and P3 the blind split leaves at least one robot with idle robot-turns while packages remain and the replanning split ends with every package delivered in fewer parallel turns (SC-004).
- [X] T008 [P] [US2] Episode tests in `tests/warehouse/test_env.py` on the hand-built floor of T005, per data-model.md and `specs/012-warehouse/contracts/warehouse-tools.md`: `describe(robot)` is free and equals the `look` data; the start view adds `floor` (rows of `#`, `.`, `S`, `D`, no packages) and `aisles`; `move` into a corridor cell shows `corridors` and `packages_seen` of those corridors only (north to south, then west to east); errors `invalid_direction`, `shelf`, `edge` with the contract's messages; `pick` answers `{"picked", "cell"}`, fails `no_package` and `already_carrying`; `drop` on D answers `{"delivered_package", "delivered", "packages"}`, fails `not_on_drop` and `not_carrying`; each error costs a step and adds an invalid action; the last delivery ends `delivered` with success, the budget ends `budget` (a delivery on the last step counts first); `stop()`; calls after the end answer `episode_over` with step `None`; `unknown("push")` says "The tools are look, move, pick and drop."; `add_scout()` adds robots on the dock up to 4 and records `added_turn` from `turn_source`; two robots on one cell are allowed, and when both pick in robot order the second fails `no_package`; `restart()` returns False; `outcome().to_dict()` has `delivered`, `packages`, `parallel_turns`, `idle_robot_turns`, `reference_is_optimal`, `scouts` when > 1; delivered, parallel turns and idle robot-turns are rebuilt from `outcome().to_dict()["log"]` and the floor alone (SC-006).
- [X] T009 [P] [US2] Boundary tests in `tests/warehouse/test_boundary.py`: for every level and dev seed, 300 random calls by up to 4 robots (unknown names and directions, picks and drops anywhere) give the fixed envelope and one of the contract's data shapes; errors are `{"code", "message"}`; no result lists a package on a cell outside the corridors the robot stands in; the start view is identical for two floors with the same plan and package count and different package cells; no result's JSON contains `reference` or `budget`; `AgentTools` exposes only `start`, `look`, `move`, `pick`, `drop`.
- [X] T010 [P] [US2] Kit tests in `tests/warehouse/test_kit.py`: `build_kit` gives `problem == "warehouse"`, `BASE_PROMPT` and `TOOL_SCHEMAS` per the contract (`look`, `pick`, `drop` take no parameters, `move` the direction enum), `start` the start view JSON; the tool node answers all four tools for robot 0, unknown tools with `unknown_tool` (one step) and invalid calls; `add_scout()` returns a `Scout` with its own tool node and start view until 4 robots, then None; `restart()` is False and `max_attempts` 1; the fingerprint is stable and differs from the other five problems' pinned values.
- [X] T011 [P] [US2] Render and CLI tests in `tests/warehouse/test_render.py` per `specs/012-warehouse/contracts/cli.md`: `apl warehouse show --level P2 --seed 1000` prints the header line (`Warehouse P2, seed 1000: 3 packages; reference N steps (not optimal); budget 3N`), the column letters, one line per row with `#`, `.`, `S`, `D` and package digits, and the aisles line; `--route reference` adds `reference: move …, pick, …, drop`; `--html OUT` writes a page with an SVG holding `.room` rects and `data-package` elements; an unknown level exits 2; a test seed is shown.
- [X] T012 [P] [US2] A1 tests in `tests/arch/test_react_warehouse.py`: `play_episode(key, ..., problem="warehouse")` with `react` and `play_calls` built from `reference_calls` on P2 seed 1000 gives a completed row with `success`, `steps == optimal_steps`, `delivered == packages == 3`, and the first human message is the start view JSON (FR-021).

### Implementation for User Story 2

- [X] T013 [P] [US2] Create `src/apl/warehouse/model.py` per data-model.md: `WarehouseLevel(name, columns, aisles, spreads)`, `LEVELS` for P1–P3 with the values of research R2; `Cell = tuple[int, int]`, `DIRECTIONS`, `cell_name`, `parse_cell`; the frozen `Floor(level, seed, columns, rows, dock, drop, packages, reference)` with `shelf`, `open`, `corridors(cell)`, `corridor_cells(name)`, `aisle_names`, `neighbor`, `reference_steps`, `budget = 3 × reference_steps`, `reference_is_optimal = False`; `Action(tool, args)` with `to_dict`. Also `src/apl/warehouse/seeds.py`: `DEV_SEEDS = range(1000, 1010)`, `TEST_SEEDS = range(2000, 2020)`.
- [X] T014 [US2] Create `src/apl/warehouse/plans.py`: `path(floor, start, goal)` (breadth-first search, ties north then east), `reference_calls(floor)` per research R6, and `blind_split(floor)` and `replanning_split(floor)` per R7, played against an `Episode` with a turn per round so the generator and tests can read parallel turns and idle robot-turns.
- [X] T015 [US2] Create `src/apl/warehouse/results.py`: `ErrorCode`, `EndReason` (`delivered`, `budget`, `stopped`), `RobotView`, `StartView`, `Picked`, `Dropped`, and the `ToolResult` envelope, each with `to_dict()` matching the contract's JSON.
- [X] T016 [US2] Create `src/apl/warehouse/env.py` per data-model.md: `MAX_SCOUTS = 4`, `MAX_ATTEMPTS = 1`, `LogEntry` (as the survey field's, with `scout` and `turn`), `Outcome` with `success`, `budget_hit`, `scouts`, `parallel_turns`, `idle_robot_turns` and `to_dict()`, `start_episode`, `Episode` with robots, carrying, `added_turn`, waiting and delivered packages, `seen`, `describe`, `start_view`, `look`, `move`, `pick`, `drop`, `unknown`, `stop`, `add_scout`, `restart` (False), `outcome`.
- [X] T017 [US2] Create `src/apl/warehouse/generator.py`: `generate(level, seed)` with `random.Random(f"warehouse:{level}:{seed}")`: draw a spread and shuffle it over the aisles, draw distinct package cells per aisle, shuffle the package numbers, compute the reference, and on P2 and P3 accept the draw only if `blind_split` idles a robot and `replanning_split` takes fewer parallel turns (`MAX_TRIES = 1000`); `ValueError` for an unknown level.
- [X] T018 [P] [US2] Create `src/apl/warehouse/prompt.py` (`BASE_PROMPT`, `TOOL_SCHEMAS`, `prompt_fingerprint` per the contract) and `src/apl/warehouse/tools.py` (`AgentTools` with `__slots__ = ("_episode", "start")` and `look`, `move`, `pick`, `drop` per robot).
- [X] T019 [US2] Create `src/apl/warehouse/kit.py` (`build_kit` per `specs/012-warehouse/contracts/problems.md`, modelled on `src/apl/survey/kit.py`, with a lock and `add_scout`) and `src/apl/warehouse/__init__.py` exporting `LEVELS`, `DEV_SEEDS`, `TEST_SEEDS`, `Floor`, `Episode`, `Outcome`, `generate`, `start_episode`.
- [X] T020 [US2] Register the problem: `PROBLEMS["warehouse"]` in `src/apl/problems.py` per the contract; `SUPPORTS["react"]` gains `"warehouse"` in `src/apl/runner/registry.py`; the row fields of `specs/012-warehouse/contracts/results.md` (`delivered`, `packages`, `idle_robot_turns`, end reason `delivered`) in `src/apl/runner/results.py`, so A1's row of T012 is written.
- [X] T021 [US2] Create `src/apl/warehouse/render_text.py` and add `apl warehouse show` to `src/apl/cli.py`, modelled on `apl workshop show`.

**Checkpoint**: the warehouse exists, plays scripted agents and A1, and prints from the CLI.

---

## Phase 3: User Story 1 - Watch robots clear the warehouse (Priority: P1)

**Goal**: in the viewer the experimenter opens a warehouse and watches A1, A2, A7, A8 or A9 play it, with fog by corridor, packages on cells or robots, the stats panel and the About card; episodes replay.

**Independent Test**: the viewer API for P2 seed 1000, a scripted episode's events and frames, its replay, and scripted episodes of each architecture.

### Tests for User Story 1 ⚠️ (write first, they must fail)

- [X] T022 [P] [US1] Floor map tests in `tests/arch/test_floor_map.py` per `specs/012-warehouse/contracts/architectures.md`: `from_start` keeps the plan, aisles and total; a view replaces the packages recorded on its corridors' cells with the listed ones and marks those corridors seen; `picked` and `delivered_package` update carrying and delivered; failures change nothing; `render` draws `#`, `.`, `?`, `P`, `S`, `D`, `@` and other robots' digits and lists the corridors seen and not seen and the packages seen; an oracle check plays the reference through an episode and compares the map's packages and delivered count with the episode after every step.
- [X] T023 [P] [US1] A2 tests in `tests/arch/test_mapstate_warehouse.py`: scripted `mapstate` on P2 seed 1000 with the reference calls succeeds in the reference's steps; each model call sees the base prompt with `FLOOR_MAP_INSTRUCTIONS`, its last turn and the rendered floor map (FR-022).
- [X] T024 [P] [US1] Scouts tests in `tests/arch/test_warehouse_scouts.py`: `SharedMap.from_start` builds a floor map from a warehouse start view; per-robot positions and carried packages; `scout_messages` on the warehouse uses the robot texts; A7 with a scripted orchestrator sending three robots (one per aisle) delivers on P2 with idle robot-turns > 0 and ends without a collect step; A8 with a scripted orchestrator that reassigns after round 1 delivers in fewer parallel turns than that A7 episode; A9's `claim: package 2` and `claim: aisle 3` are stored and rendered `robot n → …`, while on the dungeon `claim: package 2` is still not a claim (FR-023).
- [X] T025 [P] [US1] Viewer tests in `tests/viewer/test_warehouse.py` per `specs/012-warehouse/contracts/viewer.md`: `/api/warehouse?level=P2&seed=1000` returns the documented keys with reference frames; a test seed is refused, a bad level or seed 400; a scripted A7 episode's start event has `problem`, `packages`, `columns`, `rows`; step frames carry `seen`, `packages`, `delivered`, `parallel_turns`, `idle_robot_turns` and `scouts` with `carrying`; the end row has the warehouse fields; the replay equals the live events; the page offers the warehouse and its five architectures; the About card exists for each (the existing `tests/viewer/test_about.py` covers the new pairs through `SUPPORTS`).

### Implementation for User Story 1

- [X] T026 [US1] Create `src/apl/arch/floor_map.py` (`FloorMap` per the contract) and pick it on `warehouse` in `src/apl/arch/mapstate.py` with `FLOOR_MAP_INSTRUCTIONS`; `SUPPORTS["mapstate"]` gains `"warehouse"`.
- [X] T027 [US1] Extend `src/apl/arch/scouts.py`: `SharedMap` accepts `FloorMap` (warehouse start views recognized by their `floor` key; per-robot `positions` and `carried`), `ROBOT_INSTRUCTIONS`, warehouse branch in `scout_messages`, `_ROBOT_CLAIM` used only when the board holds a `FloorMap`; claims rendered `robot n → target`.
- [X] T028 [US1] Warehouse texts in `src/apl/arch/fanout.py` (`WAREHOUSE_FANOUT_INSTRUCTIONS`, no collect step), `src/apl/arch/rounds.py` (`WAREHOUSE_ROUNDS_INSTRUCTIONS`, `{"done": true}` stops) and `src/apl/arch/blackboard.py` (`WAREHOUSE_TASK`); `SUPPORTS` for `fanout`, `rounds`, `blackboard` gains `"warehouse"`. Their dungeon and survey texts and behaviour stay unchanged.
- [X] T029 [US1] Create `src/apl/warehouse/frames.py` (`snapshot` with the survey frame keys plus `seen`, `packages`, `delivered`, `parallel_turns`, `idle_robot_turns`, `scouts` with `carrying`; `reference_frames`) and `src/apl/warehouse/render_svg.py` (`svg`, `html`, `CELL`, `MARGIN`; shelves, `.cell` and `.room` rects with `room-x-y` ids, dock, D, `.package` elements with `data-package`).
- [X] T030 [US1] Viewer server side: `Viewer.warehouse()` and `parse_warehouse` in `src/apl/viewer/app.py` (frames for warehouse episodes, the start event's `problem`, `packages`, `columns`, `rows`, the episode-id pattern), the `/api/warehouse` route in `src/apl/viewer/server.py`.
- [X] T031 [US1] The page in `src/apl/viewer/assets/index.html`: `isWarehouse()`, the `/api/warehouse` path and reference label, fog by `frame.seen` when present, packages drawn on their cells or robots and hidden when delivered or fogged, warehouse stats rows (`Warehouse`, `Delivered n / N`, `Parallel turns`, `Idle robot-turns`), saved-episode labels.
- [X] T032 [US1] About card texts for the warehouse in `src/apl/viewer/about.py` (`TOOLS`, `MEMORY`, `ENDS`; the scouts card names who delivers instead of who submits).

**Checkpoint**: any warehouse level and seed can be shown and watched in the viewer.

---

## Phase 4: User Story 3 - Run, continue and report on the warehouse (Priority: P2)

**Goal**: warehouse runs plan, run, continue and report like the other problems.

**Independent Test**: plan, refuse, interrupt, continue and report scripted warehouse runs.

### Tests for User Story 3 ⚠️ (write first, they must fail)

- [X] T033 [P] [US3] Run tests in `tests/runner/test_warehouse_runs.py`: the dry-run plan for `--problem warehouse --arch react,mapstate,fanout,rounds,blackboard --level all --seeds dev --limit 1` lists 15 episodes and calls no model; `--arch hybrid` exits 2 with `hybrid does not play the warehouse problem (it plays: dungeon, rune, signal, workshop)`; a scripted run interrupted after two episodes continues with only the missing ones.
- [X] T034 [P] [US3] Report tests in `tests/runner/test_report.py`: hand-written warehouse rows give the table of `specs/012-warehouse/contracts/results.md` with every figure checked by hand (success share, median delivered, steps, efficiency, turns, idle, robots, budget hits, tokens, latency), the spread with repeats, no attempts section; older rows without the new fields load; the comparison section compares A7–A9 with `mapstate` and shows parallel turns.

### Implementation for User Story 3

- [X] T035 [US3] The warehouse table and spread in `src/apl/runner/report.py` and the parallel-turns comparison on the warehouse in `src/apl/runner/compare.py`.

**Checkpoint**: warehouse runs plan, continue and report.

---

## Phase 5: User Story 4 - The fairness rules hold on the warehouse (Priority: P2)

**Goal**: the import rule and the recorded fingerprints cover the warehouse.

**Independent Test**: the import test with the warehouse's modules.

### Tests for User Story 4 ⚠️ (write first, they must fail)

- [X] T036 [P] [US4] Extend `tests/dungeon/test_boundary.py`: `apl.warehouse.tools` and `apl.warehouse.results` are allowed imports; an architecture importing `apl.warehouse.generator`, `apl.warehouse.env`, `apl.warehouse.plans` or `apl.warehouse.model` fails the import test.

### Implementation for User Story 4

- [X] T037 [US4] Update the allowed-imports docstring in `src/apl/kit.py` and the boundary test's allow list; confirm two architectures on one warehouse level record the same prompt fingerprint and budget in their rows (`tests/runner/test_warehouse_runs.py`).

**Checkpoint**: the fairness rules cover the warehouse.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T038 [P] Update `README.md`: the problems list and tour gain the warehouse; the architectures table's problem columns; the commands block gains `apl warehouse show`.
- [X] T039 [P] Mark M12 done in `plan.md` §7 once the quickstart passes.
- [X] T040 Run `specs/012-warehouse/quickstart.md` steps 1–6 (the page with the headless browser for step 5–6) and the four checks; fix what they show.

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 first. Phase 2 (US2) before every other story: the problem must exist.
- Phase 3 (US1) and Phase 4 (US3) both need Phase 2; they touch different files except
  `src/apl/runner/registry.py` (T026, T028 after T020) and can otherwise run in parallel.
- Phase 5 (US4) needs Phase 2. Phase 6 last.

### Within Each Story

- Tests first, failing; then the implementation in file-dependency order (model → plans →
  results → env → generator → prompt/tools → kit → registration → CLI).
- The four checks pass at each checkpoint.

### Parallel Opportunities

- T003 and T004; the US2 tests T005–T012; T013 with T018 once results exist; the US1 tests
  T022–T025; T033 with T034; T038 with T039.

---

## Parallel Example: User Story 2 tests

```text
T005 tests/warehouse/test_plans.py
T006 tests/warehouse/test_generator.py
T007 tests/warehouse/test_agents.py
T008 tests/warehouse/test_env.py
T009 tests/warehouse/test_boundary.py
T010 tests/warehouse/test_kit.py
T011 tests/warehouse/test_render.py
T012 tests/arch/test_react_warehouse.py
```

## Implementation Strategy

### MVP first (US2)

The warehouse problem with A1 playing it from the runner and `apl warehouse show`: enough to check
the board's gap by construction (SC-002–SC-004) before any viewer work.

### Then

US1 (A2, the scouts and the viewer), US3 (reports), US4 (rules), polish. Stop at each checkpoint
and run the four checks.

### Notes

- No paid or local experiment run is started by any task.
- The other five problems' behaviour and outputs must not change (pins of T002).

## Phase 7: Convergence

- [X] T041 Rewrite the A8 test in `tests/arch/test_warehouse_scouts.py` so the scripted orchestrator gives one robot per aisle in round 1 and, from the merged map in round 2, sends the robot whose aisle was empty to a package in the crowded aisle; A8 must still take fewer parallel turns than the blind A7 episode per T024 (partial)
- [X] T042 Prefix saved warehouse episodes with their problem in the saved-episodes list of `src/apl/viewer/assets/index.html` per T031 (partial)
- [X] T043 Compare the warehouse fingerprint with the dungeon's, survey's, signal's, rune's and workshop's in `tests/warehouse/test_kit.py` per T010 (partial)
- [X] T044 Document `added_turns` (the turn each robot was added at, saved in the outcome so idle robot-turns can be rebuilt) in the Outcome section of `specs/012-warehouse/data-model.md` per data-model.md "Outcome" and T008 (unrequested)
