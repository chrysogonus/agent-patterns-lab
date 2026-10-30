---

description: "Task list for M1: dungeon generator, environment, tools and solver"
---

# Tasks: Dungeon Generator, Environment, Tools and Solver

**Input**: Design documents from `specs/001-dungeon-environment/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (tools.md,
outcome.md, cli.md), quickstart.md

**Tests**: Requested. The spec's success criteria (SC-001 to SC-012) and plan.md's M1 done
criterion are defined as test outcomes, so every story phase starts with its tests. Write them
first, see them fail, then implement.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested on
its own.

**Rules for every task**:
- Standard library only.
- Frozen `@dataclass(slots=True)` types unless data-model.md says mutable.
- Full type hints (mypy strict).
- Nothing goes in `src/apl/arch/` (Constitution, Development Workflow).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story the task belongs to (US1–US5)

## Path Conventions

Single project: `src/apl/` and `tests/` at the repository root, as in plan.md.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Package skeleton and tooling for the new modules

- [X] T001 Create the empty package `src/apl/dungeon/__init__.py` (module docstring only) and the directory `src/apl/dungeon/assets/`
- [X] T002 [P] Create `tests/__init__.py` and `tests/dungeon/__init__.py` (both empty), so tests can import `tests.dungeon.reference`
- [X] T003 Add `[project.scripts] apl = "apl.cli:main"` to `pyproject.toml`, and create `src/apl/cli.py` with a `main(argv: list[str] | None = None) -> int` that builds an `argparse` parser with a `dungeon` subcommand group and returns 2 when no subcommand is given; run `uv sync` and confirm `uv run apl --help` works

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Types and the solver that every story builds on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T004 Implement `src/apl/dungeon/model.py` per data-model.md "Internal types":
  - `Direction` (StrEnum `north, east, south, west` in that order, with `delta` and `opposite`).
  - `Pos = tuple[int, int]` (x = column, y = row, `(0, 0)` north-west).
  - `Level`, and `LEVELS` with exactly the FR-010 table (L1: 3, 0, 1, 0; L2: 4, 1, 2, 0; L3: 5, 2, 3, 2).
  - `Edge`: unordered, smaller position first; the rule is "the two positions differ by exactly 1 in x or in y".
  - `Layout` with `validate()` enforcing:
    - "`size` ≥ 2"
    - "Every edge lies inside the grid"
    - "`locks` keys are a subset of `doors`; the values are distinct colors"
    - "One key per lock color; each key lies in a room"
    - "`start`, `exit` inside the grid; different"
    - "`labels`: exactly one per room; unique"
  - `Action(tool, args)` with the argument counts from data-model.md.
  - `Solution(actions, length)` with `length == len(actions)`.
  - `Dungeon(level, seed, layout, solution)` with `budget = 3 * solution.length`.
  - A canonical `to_dict()` on `Layout`, `Dungeon`, `Action` and `Solution`: sorted keys, positions as `[x, y]`, edges as sorted pairs.
- [X] T005 [P] Implement `src/apl/dungeon/results.py` per contracts/tools.md:
  - `ErrorCode` (StrEnum: `invalid_direction`, `no_door`, `locked`, `no_such_item`, `not_in_inventory`, `wrong_key`, `not_locked`, `episode_over`).
  - `EndReason` (StrEnum: `exit`, `budget`, `stopped`).
  - `ExitView`, `RoomView`, `InventoryView`, `DoorOpened`, `ToolError` and `ToolResult`.
  - Each `to_dict()` gives exactly the JSON shapes and key order in contracts/tools.md.
  - Item names are `"<color> key"`.
  - This module MUST NOT import `model.py` internals except `Direction`.
- [X] T006 Implement `solve(layout: Layout) -> Solution | None` in `src/apl/dungeon/solver.py` (research R4):
  - BFS over `(room, keys_taken_mask, doors_opened_mask)`.
  - Successor order: `take`, then `use` in direction order, then `move` in direction order.
  - Keys are taken as `take("<color> key")`; a door is opened with `use("<color> key", direction)` and is passable afterwards from both sides.
  - Return `None` when the exit is unreachable.
  - Also add `Dungeon.from_layout(layout)` in `src/apl/dungeon/model.py`: level and seed `None`; solves the layout; raises `ValueError("unsolvable layout")` if `solve` returns `None` (data-model.md "Dungeon").
- [X] T007 [P] Create `tests/dungeon/reference.py` with five hand-built 3×3 `Layout` builders. They do not need to meet level rules; they only need `Layout.validate()`.
  - **Coordinates:** `(x, y)`, with `(0, 0)` north-west and south = `y + 1`. Give each builder an ASCII sketch docstring. `grid_labels(size)` assigns labels `a2, a3, …` in grid order (fine for tests; hand-built dungeons don't need random labels).
  - **Shared ring:** the open doors `(0,0)-(0,1)`, `(0,1)-(0,2)`, `(0,2)-(1,2)`, `(1,2)-(2,2)`, `(2,2)-(2,1)`, `(2,1)-(2,0)` and `(0,0)-(1,0)`, with start `(0,0)` and exit `(2,0)`. The long way round, west then south then east then north, is 6 moves.
  - `two_open_routes()`: the ring plus an open door `(1,0)-(2,0)`. Optimal **2** (east, east).
  - `locked_shortcut_wins()`: the ring plus `(1,0)-(2,0)` locked `red`, with the red key at `(1,0)`. Optimal **4** (move east, take, use east, move east), shorter than the 6-move ring.
  - `open_route_wins()`: as above, but the red key is at `(0,2)`. The locked route costs 2 moves + take + 3 moves + use + move = **8**, so the optimum is the open ring at **6**, with no `use`.
  - `chained_keys()`: open doors `(0,0)-(1,0)`, `(0,0)-(0,1)` and `(2,0)-(2,1)`; `(1,0)-(2,0)` locked `red` with the red key at `(0,1)`; `(2,1)-(2,2)` locked `blue` with the blue key at `(2,1)`. Start `(0,0)`, exit `(2,2)`. Optimal **10**: south, take red, north, east, use red east, east, south, take blue, use blue south, south.
  - `key_behind_own_door()`: `(0,0)-(1,0)` locked `red` with the red key at `(1,0)`, and `(1,0)-(2,0)` open. Start `(0,0)`, exit `(2,0)`. **Unsolvable**.
  - Expose `REFERENCE: list[tuple[str, Layout, int | None]]` with these five entries: the name, the layout, and the known optimal length, or `None` when unsolvable (SC-008).
- [X] T008 Write `tests/dungeon/test_model.py`:
  - `Layout.validate()` rejects each listed rule violation.
  - `Edge(a, b) == Edge(b, a)`; non-neighbor edges are rejected.
  - `LEVELS` matches FR-010.
  - `Dungeon.budget == 3 * solution.length`.
  - `Dungeon.from_layout` raises on `key_behind_own_door()`.
  - `solve(two_open_routes())` returns a solution of length 2.

**Checkpoint**: Types, result shapes and the solver exist. Stories can start.

---

## Phase 3: User Story 1 - Generate a solvable dungeon from a seed (Priority: P1) 🎯 MVP

**Goal**: `generate(level, seed)` returns a reproducible dungeon that meets every level rule
and comes with its shortest solution.

**Independent Test**: Generate many seeds per level, check each against the level rules and the
solver, and confirm that the same seed reproduces the same dungeon.

### Tests for User Story 1 ⚠️ (write first, they must fail)

- [X] T009 [P] [US1] Write `tests/dungeon/test_generator.py`:
  - For every level and every seed in `DEV_SEEDS`, `TEST_SEEDS` and `range(10_000, 11_000)`: `check_level_rules(d.layout, d.level)` returns no violations and `solve(d.layout)` equals `d.solution` (SC-001, FR-013).
  - Generating twice gives equal `to_dict()` (SC-003).
  - Golden SHA-256 fingerprints of `json.dumps(d.to_dict(), sort_keys=True)` for seeds 1000 and 2000 on each level, filled in after the first green run (FR-009).
  - At least 95 distinct fingerprints across 100 seeds per level (SC-004).
  - `ValueError` for level `"L9"`, seed `-1` and seed `1.5` (edge cases).
  - Generating and solving all dev and test seeds for all levels takes < 10 s (SC-006).
- [X] T010 [P] [US1] Write `tests/dungeon/test_labels.py` (SC-009):
  - Labels are unique per dungeon and identical across regeneration.
  - Across 100 seeds per level, every position receives at least 10 different labels.
  - Every label is in `LABEL_POOL`, and `len(LABEL_POOL) >= 100`.
- [X] T011 [P] [US1] Write `tests/dungeon/test_seeds.py`: `DEV_SEEDS` has 10 seeds, `TEST_SEEDS` has 20, and the two are disjoint (FR-023).
- [X] T012 [P] [US1] Write `tests/dungeon/test_rules.py`: hand-made layouts that break each rule make `check_level_rules` report that exact rule. Cover FR-001 to FR-008: a non-neighbor door, a disconnected room, start/exit too close, duplicate lock colors, a bypassable lock, a key in the start room, a key on the shortest route to its door, an L3 second key in front of the first door, and fewer than 2 empty dead ends on L3.

### Implementation for User Story 1

- [X] T013 [P] [US1] Implement `src/apl/dungeon/seeds.py`: `DEV_SEEDS = range(1000, 1010)` and `TEST_SEEDS = range(2000, 2020)` (research R11).
- [X] T014 [P] [US1] Implement `check_level_rules(layout: Layout, level: Level) -> list[str]` in `src/apl/dungeon/rules.py`. It returns one message per violated rule from FR-001 to FR-008:
  - grid size;
  - connected when locks are ignored;
  - start/exit distance ≥ 2·(N−1) with locks ignored;
  - lock count and distinct colors;
  - every lock necessary (exit unreachable with that door as a wall);
  - each key reachable before its door, not in the start room, and not on the shortest lock-ignoring route from the start to its door;
  - on L3, the second key behind the first door;
  - on L3, ≥ 2 dead ends that are not start/exit and hold no key;
  - extra-door count = `len(doors) - (N*N - 1)`.
- [X] T015 [US1] Implement `generate(level_name: str, seed: int) -> Dungeon` and `LABEL_POOL` in `src/apl/dungeon/generator.py`, following research R1–R3 step by step:
  - RNG `random.Random(f"apl:{level}:{seed}")`.
  - Randomized Kruskal spanning tree.
  - Start/exit chosen among pairs with tree distance ≥ 2·(N−1).
  - Lock doors on the tree path, in order.
  - Extra doors only within a region.
  - Keys per R2 step 5.
  - Recheck with `check_level_rules` and `solve`, and retry on failure (max 1,000 attempts, then `RuntimeError`).
  - Labels via `rng.sample(LABEL_POOL, N*N)` in grid order.
  - `LABEL_POOL` = 23 letters `abcdefghjkmnpqrstuvwxyz` × digits `2–9` (184 labels).
  - Colors drawn from `("red", "blue", "green", "yellow")`.
  - Validate inputs first (edge cases). Depends on T013 and T014.
- [X] T016 [US1] Export `generate`, `solve`, `check_level_rules`, `LEVELS`, `DEV_SEEDS` and `TEST_SEEDS` from `src/apl/dungeon/__init__.py`, then run T009–T012 to green and fill in the golden fingerprints in `tests/dungeon/test_generator.py`.

**Checkpoint**: Dungeons can be generated, checked and reproduced (MVP).

---

## Phase 4: User Story 2 - Play an episode through the four tools (Priority: P2)

**Goal**: An episode an architecture can play only through `look`, `move`, `take` and `use`, with
structured results, step counting, a budget, end reasons and an outcome record with the log.

**Independent Test**: Scripted call sequences on hand-built dungeons, including every error
code, checking results, step counts and the outcome.

### Tests for User Story 2 ⚠️ (write first, they must fail)

- [X] T017 [P] [US2] Write `tests/dungeon/test_env.py` against contracts/tools.md and contracts/outcome.md, using `Dungeon.from_layout` on `tests/dungeon/reference.py` layouts:
  - The free start description equals `look()`'s data, and `steps == 0` (FR-014).
  - One test per error code: `invalid_direction`, `no_door`, `locked` (the message names the color), `no_such_item`, `not_in_inventory`, `wrong_key`, `not_locked` and `episode_over`. Each asserts the step count afterwards: +1, or +0 for `episode_over` (SC-005).
  - Error precedence: `use("red key", "up")` without the key gives `invalid_direction`.
  - A successful `take` and `use`; afterwards the door is passable from both sides and the key is still in the inventory (FR-019).
  - Exit on the last budget step gives success, not `budget_hit`.
  - Running out of budget gives `budget`.
  - `stop()` gives `stopped`, costs no step and is idempotent.
  - `outcome()` before the end raises `RuntimeError`.
  - The outcome `to_dict()` keys and values match contracts/outcome.md, including `level`/`seed` `null` for hand-built dungeons.
  - The log records every call, with `step: null` for `episode_over`.
  - Revisiting a room shows the same label (Story 2, scenario 6).
- [X] T018 [P] [US2] Write `tests/dungeon/test_boundary.py`:
  - **SC-007:** walk every dev dungeon on each level with a scripted random walk of 200 calls (fixed RNG), mixing valid and invalid calls. For every result, assert that the JSON has only the keys in contracts/tools.md, that the only label it contains is the current room's, and that it holds no coordinates, budget or optimal length.
  - **Constitution II:** if `src/apl/arch/` exists, parse every `.py` file under it with `ast`, and fail on any import of `apl.dungeon` other than `apl.dungeon.tools` and `apl.dungeon.results`. The test passes while the directory is absent.
  - `AgentTools` has no public attributes besides `start`, `look`, `move`, `take` and `use`.

### Implementation for User Story 2

- [X] T019 [US2] Implement `src/apl/dungeon/env.py` per data-model.md "Episode", "LogEntry" and "Outcome":
  - `start_episode(dungeon) -> Episode`.
  - The mutable `Episode` with `position`, `inventory`, `opened`, `steps`, `invalid_actions`, `end_reason` and `log`.
  - Methods `look()`, `move(d)`, `take(item)`, `use(item, d)`, `stop()` and `outcome()`.
  - Error checks in the contracts/tools.md table order.
  - Exit check before the budget check.
  - `episode_over` is not counted and does not change state.
  - `LogEntry(index, step, action, result)`.
  - `Outcome` with `to_dict()` exactly as contracts/outcome.md.
  - Results are built only from `results.py` types and only from the current room.
- [X] T020 [US2] Implement `AgentTools` in `src/apl/dungeon/tools.py`:
  - Wraps an `Episode` in a private attribute.
  - Exposes `start` (the free start description) and `look`, `move`, `take` and `use`, delegating to the episode; no other public attributes.
  - Re-export `AgentTools`, `start_episode`, `Episode` and `Outcome` from `src/apl/dungeon/__init__.py`.
  - Run T017–T018 to green.

**Checkpoint**: Architectures have a complete, scored world to play in.

---

## Phase 5: User Story 3 - Trust the shortest solution (Priority: P3)

**Goal**: Show that the solver's length is truly the shortest and matches what the tools allow.

**Independent Test**: Reference dungeons with hand-worked answers, plus replaying the solution for
every dev and test dungeon. Depends on US1 (generation) and US2 (environment).

### Tests for User Story 3 ⚠️

- [X] T021 [P] [US3] Write `tests/dungeon/test_solver.py`:
  - For every entry in `REFERENCE`, `solve(layout)` returns `None` exactly when the known answer is `None`, and otherwise a solution whose `length` equals the known optimum (SC-008).
  - For `locked_shortcut_wins`, the solution contains a `use`; for `open_route_wins`, it contains none (Story 3, scenarios 1–2).
  - Solving the same layout twice gives identical actions.
- [X] T022 [P] [US3] Write `tests/dungeon/test_replay.py`: for every level and every seed in `DEV_SEEDS` and `TEST_SEEDS`, replaying `d.solution.actions` through `start_episode(d)` gives `ok: true` on every call and ends with `end_reason == "exit"` and `steps == d.solution.length` (SC-002).

### Implementation for User Story 3

- [X] T023 [US3] Re-derive each reference optimum from T007 by hand and write the step-by-step reasoning into the builder docstrings in `tests/dungeon/reference.py`. Make T021 and T022 green. Where they fail, fix `src/apl/dungeon/solver.py` or `src/apl/dungeon/env.py`, never the known answers, unless the hand derivation itself was wrong. In that case, correct both T007's numbers and the docstring.

**Checkpoint**: Efficiency scores and budgets rest on a verified number.

---

## Phase 6: User Story 4 - Inspect a dungeon and a route as a text map (Priority: P4)

**Goal**: `apl dungeon show` prints a text map, optionally with a route overlay and a step table.

**Independent Test**: Render a few seeds with and without the solver's route and check content
and visit order. Depends on US1 and US2.

### Tests for User Story 4 ⚠️

- [X] T024 [P] [US4] Write `tests/dungeon/test_frames.py`:
  - `build_frames(d, d.solution.actions)` has `len(actions) + 1` frames.
  - Frame 0 is the start state.
  - After each step, the frame's `position`, `inventory`, `keys_in_rooms` and `opened` equal a parallel `Episode`'s state (SC-012, for every dev dungeon).
  - Failed actions leave `position` unchanged.
  - Passing a log with a tampered result raises `ValueError` (research R7).
- [X] T025 [P] [US4] Write the text-map tests in `tests/dungeon/test_render.py`:
  - For every dev dungeon, the map contains every label, `S`, `E`, every locked door's uppercase color letter and every key's lowercase letter (SC-010).
  - With the solution overlay, every route room has `*`, and the step table lists rooms in visit order, all visit numbers for revisited rooms, the `took`/`opened` events, error codes for failed actions and an `end:` line (FR-025).
  - Rendering twice gives identical text (SC-011).
- [X] T026 [P] [US4] Write `tests/dungeon/test_cli.py` (for the contracts/cli.md command), calling `apl.cli.main([...])` with `capsys`:
  - `dungeon show --level L3 --seed 1000` exits 0 and prints the map.
  - `--route solution` prints the step table ending in `(exit)`.
  - `--route FILE` accepts both route-file formats.
  - An unknown level, a negative seed, or a malformed route file exits 2.

### Implementation for User Story 4

- [X] T027 [US4] Implement `Frame` and `build_frames(dungeon, actions, expected_results=None) -> list[Frame]` in `src/apl/dungeon/frames.py`, per data-model.md "Frame" and research R7:
  - Replays through `start_episode`.
  - Snapshots the state after each step.
  - Compares against `expected_results` when they are given.
  - Also add `parse_route_file(data: object) -> RouteFile` (actions, logged results and logged `end_reason`), which accepts both formats from contracts/cli.md and raises `ValueError` on anything else. `build_frames` takes the logged `end_reason` too: a `stopped` end is applied after the replay (stopping is not a tool call), and any other mismatch is an error.
- [X] T028 [US4] Implement `render_text(dungeon, frames: list[Frame] | None = None) -> str` in `src/apl/dungeon/render_text.py`, using the cell, wall, door and marker format and the step table from contracts/cli.md (research R8).
- [X] T029 [US4] Implement `apl dungeon show --level --seed [--route solution|PATH]` in `src/apl/cli.py`: generate, optionally build frames, print `render_text`, and map `ValueError` and JSON errors to exit code 2 with a message on stderr. Then run T024–T026 to green.

**Checkpoint**: Routes are visible in the terminal.

---

## Phase 7: User Story 5 - Watch a route play back as an animation (Priority: P5)

**Goal**: One self-contained HTML file: a still SVG without a route, and an animated player with
controls when there is one.

**Independent Test**: Produce files for a few dungeons and routes, check their content and
determinism in tests, and play them in a browser offline. Depends on US4 (frames).

### Tests for User Story 5 ⚠️

- [X] T030 [P] [US5] Add the HTML tests to `tests/dungeon/test_render.py`:
  - For every dev dungeon, the SVG contains every label, the start and exit markers, each lock color and each key (SC-010).
  - With a route, `<script type="application/json" id="apl-frames">` parses to the `to_dict()` of `build_frames(...)` (SC-012 data side).
  - Without a route, the file has no `<script>` and no controls (Story 5, scenario 6).
  - The output contains no `http:`, `https:`, `//` URL, external `src=` or external `href=` (FR-026).
  - Rendering twice gives identical bytes (SC-011).
  - Any `</` inside the embedded JSON is escaped.
  - The template loads via `importlib.resources.files("apl.dungeon") / "assets" / "player.html"`.

### Implementation for User Story 5

- [X] T031 [P] [US5] Create `src/apl/dungeon/assets/player.html`, the player template with inline CSS and JS and no external references:
  - Placeholders for the SVG and the frames JSON.
  - Controls per contracts/cli.md: play/pause (Space), step back (←), step forward (→), a slider to jump, and a speed select of 0.5×, 1×, 2× and 4× (1× = 2 steps/s).
  - An info panel with the step number, action, result and inventory.
  - `render(i)` draws only from `frames[i]`: agent position, the trail of steps `0..i`, keys in rooms, open doors, and the highlighted failed action (FR-028).
  - Transitions turned off under `prefers-reduced-motion`.
- [X] T032 [US5] Implement `render_html(dungeon, frames: list[Frame] | None = None) -> str` in `src/apl/dungeon/render_html.py` (research R9):
  - Builds the SVG with integer coordinates.
  - Escapes text with `html.escape`.
  - Embeds the frames via `json.dumps(..., sort_keys=True)` with `</` → `<\/`.
  - Fills `player.html` when there are frames; otherwise outputs a minimal HTML page with the SVG only.
  - The output is byte-deterministic.
- [X] T033 [US5] Add `--html OUT.html` to `apl dungeon show` in `src/apl/cli.py` to write `render_html`, extend `tests/dungeon/test_cli.py` to check that the file is written, and run T030 to green.
- [X] T034 [US5] Run `uv build --wheel --out-dir <scratch dir>` and confirm the wheel contains `apl/dungeon/assets/player.html` (plan.md, Structure Decision). If it doesn't, add the file to the build configuration in `pyproject.toml`.

**Checkpoint**: Every story works on its own and together.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T035 [P] Update `README.md`: the status line (M1 done), a short "Try it" block with the `apl dungeon show` commands from quickstart.md, and change "Layout: Planned" so it marks `src/apl/dungeon/` as existing.
- [X] T036 [P] Add `uv run apl dungeon show --level L3 --seed 1000 --route solution` to the Commands block in `AGENTS.md`.
- [X] T037 Run all of `specs/001-dungeon-environment/quickstart.md`, steps 1–6. Open `/tmp/l3-1000.html` and `/tmp/l2-errors.html` in a browser with the network turned off, and check play, pause, step, jump, speed, failed-action highlighting, and that jumping to the end equals playing to the end.
- [X] T038 Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy`, and fix everything until all four pass.
- [X] T039 Re-check the plan.md Constitution Check against the finished code. In particular, confirm that nothing under `src/apl/` outside `apl.dungeon` imports the solver into agent-facing code, and that `results.py` exposes no positions.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: none.
- **Foundational (Phase 2)**: depends on Setup and blocks every story.
- **US1 (P1)**: after Foundational.
- **US2 (P2)**: after Foundational. It uses hand-built dungeons, so it doesn't need US1.
- **US3 (P3)**: needs US1 and US2.
- **US4 (P4)**: needs US1 and US2.
- **US5 (P5)**: needs US4, for frames and the CLI.
- **Polish**: after all stories.

```text
Setup → Foundational ─┬─ US1 ─┬─ US3
                      └─ US2 ─┴─ US4 ── US5 ── Polish
```

### Within Each Story

Tests first, and they must fail. Then implementation in task order. The story is done when its
tests pass.

### Parallel Opportunities

- **Setup:** T002 can run beside T001.
- **Foundational:** T005 and T007 can run beside T004. T006 needs T004.
- **US1 and US2:** can run in parallel once Foundational is done.
- **US1:** tests T009–T012 together; then T013 and T014 in parallel, then T015.
- **US2:** tests T017 and T018 together.
- **US3:** T021 and T022 together.
- **US4:** T024–T026 together.
- **US5:** T031 can run beside T030.
- **Polish:** T035 and T036 together.

---

## Parallel Example: User Story 1

```bash
# Tests first, together:
Task: "Write tests/dungeon/test_generator.py (T009)"
Task: "Write tests/dungeon/test_labels.py (T010)"
Task: "Write tests/dungeon/test_seeds.py (T011)"
Task: "Write tests/dungeon/test_rules.py (T012)"

# Then the two independent modules:
Task: "Implement src/apl/dungeon/seeds.py (T013)"
Task: "Implement src/apl/dungeon/rules.py (T014)"
```

## Parallel Example: User Stories 1 and 2

```bash
# After Phase 2, the two stories don't touch each other's files:
Task: "US1: T009–T016 (generator, rules, seeds, labels)"
Task: "US2: T017–T020 (env, tools, boundary tests)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 Setup, then Phase 2 Foundational.
2. Phase 3 (US1): generate, check and reproduce dungeons.
3. **Stop and validate**: `uv run pytest tests/dungeon/test_generator.py tests/dungeon/test_rules.py`.

### Incremental Delivery

1. US1: dungeons exist.
2. US2: the dungeons are playable through the four tools (the interface M2 needs).
3. US3: the solver is verified, completing plan.md's M1 done criterion.
4. US4: the text map and route overlay.
5. US5: the animation.

Commit after each checkpoint.

---

## Notes

- [P] tasks use different files and have no dependency on incomplete tasks.
- Quote data-model.md rules exactly when implementing; don't loosen them.
- The golden fingerprints in T009 are filled in only once, after the first green run. Changing
  them later means the dungeons changed, and any results based on them are invalidated
  (Constitution, Experiment Setup).

---

## Phase 9: Convergence

- [X] T040 Extend the boundary scan in `tests/dungeon/test_boundary.py` so that it also fails on any access to the private `_episode` attribute of `AgentTools` in `src/apl/arch/`, both as an attribute (`tools._episode`) and as a string in `getattr(..., "_episode")`; add cases to `test_boundary_scan_catches_forbidden_imports` showing both forms are caught, per Constitution II and FR-022 (partial)
- [X] T041 Add round-trip tests in `tests/dungeon/test_render.py` for every level and every dev seed. From the text map, rebuild the set of open doors (gaps), locked doors (color letters) and walls, and assert it equals the layout's `doors` and `locks`, with every label present. From the SVG, rebuild the full-length wall segments and lock segments, and assert they match the layout's walls and `locks`. Per SC-010, FR-024 and FR-026 (partial)
- [X] T042 Parametrize `test_overlay_marks_the_route_and_lists_steps` in `tests/dungeon/test_render.py` over all levels instead of L3 only. For levels without locks, the `took`/`opened` assertions apply only to keys that exist. Per SC-010 and US4/AC2 (partial)

---

## Phase 10: Convergence

- [X] T043 Extend `_forbidden` in `tests/dungeon/test_boundary.py` to also flag string constants in `src/apl/arch/` that name an `apl.dungeon` module other than `apl.dungeon.tools` or `apl.dungeon.results`, such as `importlib.import_module("apl.dungeon.solver")` or `__import__("apl.dungeon.env")`; add both forms, plus an allowed `"apl.dungeon.tools"` string, to `test_boundary_scan_catches_forbidden_imports`, per Constitution II and plan R5 (partial)
