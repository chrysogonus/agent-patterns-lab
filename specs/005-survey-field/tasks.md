---

description: "Task list for 005: several problems, and the survey field"
---

# Tasks: Several Problems, and the Survey Field

**Input**: Design documents from `specs/005-survey-field/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R16), data-model.md, contracts/, quickstart.md

**Tests**: Yes. The spec's success criteria (SC-001–SC-007) and the plan's testing section ask for
them; as in M2–M4, each phase writes its tests first and they must fail before the implementation.
Tests use the scripted chat model (`tests/runner/scripted.py`) and never call a model.

**Organization**: by user story. US2 (the survey field) comes before US1 (watching it), because
the viewer needs the problem to exist; both are P1.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1–US4 from spec.md
- Paths are from the repository root

---

## Phase 1: Setup

**Purpose**: the rules and the safety net come first.

- [X] T001 Amend the constitution to 2.0.0 with `/speckit-constitution`, per research R1: principle I "within a problem"; principle II "Architectures MUST perceive and act on a problem only through that problem's tools (the dungeon: `look`, `move`, `take`, `use`; the survey field: `look`, `move`, `submit`)", generators, solvers and reference walks included in what they must not read; "Experiment Setup" per problem (dungeon unchanged; survey field: reachable by construction, reference walk computed by code, budget 3× the reference walk, levels S1–S3); Governance: results of different problems are never combined in one comparison. Update the version line in `.specify/memory/constitution.md`. Not an implementation task: the experimenter confirms the amendment text.
- [X] T002 [P] Update `plan.md`: §1 says the lab has several problems; a new §2b "Survey field" with the grid, the three tools, levels S1–S3 (research R5 table), the reference walk and 3× budget; §4's table gains a "Problems" column (`react`, `mapstate`, `fanout`, `rounds`, `blackboard`: dungeon and survey; `mapstate_routes`, `hybrid`: dungeon); §7 gains this feature as M5 and moves A3–A5 to M6+.
- [X] T003 [P] Update `AGENTS.md`: the import rule allows `apl.kit`, `apl.dungeon.tools`, `apl.dungeon.results`, `apl.survey.tools` and `apl.survey.results`; the command list gains `uv run apl survey show --level S2 --seed 1000` and `uv run apl run --problem survey --arch react --level all --seeds dev --limit 1`.
- [X] T004 Pin the dungeon's outputs before any code change, per research R16, in `tests/runner/test_dungeon_pinned.py`: `prompt_fingerprint() == "ff9afb3b9f66"`; the exact dry-run text of `apl run --arch react --level all --seeds dev --limit 2` (with a fixed settings record and code dict); `render(...)` of a report from a small stored `episodes.jsonl` + `run.json` fixture under `tests/runner/fixtures/dungeon-run/` (copy two rows of the M4 run's shape, no secrets). These tests must pass now and after every later task (SC-001).

**Checkpoint**: constitution 2.0.0 is in; the dungeon is pinned.

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: the runner learns that there is more than one problem, with only the dungeon registered.

### Tests for Phase 2 ⚠️ (write first, they must fail)

- [X] T005 [P] Tests for the registry in `tests/test_problems.py`: `get(None)` and `get("dungeon")` return the dungeon with levels L1–L3, dev seeds 1000–1009, test seeds 2000–2019; `get("chess")` raises `ValueError` naming the known problems; the dungeon entry's `generate`, `start_episode`, `build_kit` and `prompt_fingerprint` are the existing functions (contracts/problems.md).
- [X] T006 [P] Tests for support refusals in `tests/runner/test_spec.py`: `RunSpec.build(..., problem="dungeon")` behaves as today; with a problem an architecture does not play (using a test-only `supports` mapping), it raises `ValueError("hybrid does not play the survey problem (it plays: dungeon)")`; `--level all` expands to the problem's levels; `RunSpec.problem` defaults to `"dungeon"`.
- [X] T007 [P] Tests in `tests/runner/test_results.py`: rows and `run.json` without `problem` parse as `"dungeon"`; a row's `problem` survives a write/read round trip; the survey-only fields (`submitted_total`, `true_total`, `cells_seen`, `cells`, `parallel_turns`, `reference_is_optimal`) default to `None` and are accepted as int/bool or `None` (contracts/results.md).
- [X] T008 [P] Tests in `tests/runner/test_settings.py`: `Settings.record()` is unchanged; `Settings.record(problem="dungeon")` equals it; the fingerprint comes from the named problem.

### Implementation for Phase 2

- [X] T009 Create `src/apl/problems.py` per contracts/problems.md: the frozen `Problem` dataclass, an `EpisodeLike` protocol (`steps`, `log`, `end_reason`, `on_step`, `stop()`, `outcome()`, `add_scout()`), `PROBLEMS` with only `"dungeon"` for now (its `reference_steps` read from `solution.length` inside the entry, dungeon modules unchanged), `DEFAULT = "dungeon"` and `get(name)`.
- [X] T010 In `src/apl/kit.py`: add `problem: str` to `Kit` (set to `"dungeon"` by `build_kit`); move the tool-node loop (ordered calls under one lock, `EpisodeEnded` once ended, invalid calls answered) into a private helper `_tool_node(episode, lock, call)` that `build_kit` uses, so a survey kit can reuse it; `BASE_PROMPT`, `TOOL_SCHEMAS` and `prompt_fingerprint()` unchanged (T004 must still pass).
- [X] T011 In `src/apl/runner/registry.py`: add `SUPPORTS` (contracts/problems.md table, with `"survey"` entries present from the start) and `plays(arch, problem) -> bool`.
- [X] T012 In `src/apl/runner/spec.py`: `RunSpec` gains `problem: str = "dungeon"`; `build(..., problem=None, supports=SUPPORTS)` takes levels and seed sets from `problems.get(problem)`, refuses unsupported pairs with the T006 message, and keeps the dungeon's error texts; `upper_bounds` generates worlds through the problem; `format_plan` prints a `problem` line after `architectures` only when the problem is not the dungeon (contracts/cli.md).
- [X] T013 In `src/apl/runner/settings.py`: `record(problem: str = "dungeon")` takes `prompt_fingerprint` from `problems.get(problem)`.
- [X] T014 In `src/apl/runner/results.py`: `EpisodeRow` gains `problem: str = "dungeon"` and the six survey fields, all optional on parse; `RunRecord` gains `problem: str = "dungeon"`; `completed(...)` and `failed(...)` take the problem; survey fields stay `None` for the dungeon.
- [X] T015 In `src/apl/runner/episode.py`: `play_episode(..., problem: str = "dungeon")` builds the world, episode and kit through `problems.get(problem)` and passes the problem to the row; the dungeon path is unchanged (golden test `tests/dungeon/test_golden.py` and T004 pass).
- [X] T016 In `src/apl/runner/run.py`: `execute` and `continue_run` pass `spec.problem` / `record.problem` through to `play_episode` and into `run.json`; `plan_continue` rebuilds the `RunSpec` with the record's problem.

**Checkpoint**: all existing tests and T004–T008 pass; the dungeon behaves and prints as before.

---

## Phase 3: User Story 2 - The survey field problem (Priority: P1) 🎯 MVP

**Goal**: a seed and a level always build the same field; agents act only through `look`, `move`, `submit`; every field has a reference walk and a 3× budget; A1 plays it unchanged.

**Independent Test**: generate every level and seed and check them; play scripted walks against the tools; play A1 with a scripted model through `play_episode(..., problem="survey")`.

### Tests for User Story 2 ⚠️ (write first, they must fail)

- [X] T017 [P] [US2] Generator tests in `tests/survey/test_generator.py`: for S1–S3 and every dev and test seed, the field is identical across two calls; `size` 6/10/10; exactly `deposits` 6/15/15 deposit cells, never `A1`; every cell reachable from `A1`; S3 has 18 interior wall segments and at least 3 cells with exactly one exit; S1 and S2 have no walls (SC-002).
- [X] T018 [P] [US2] Reference walk tests in `tests/survey/test_walk.py`: the walk is legal from `A1` (no move into a wall or off the field), enters every cell; on S1 and S2 `reference_steps == size²` and `reference_is_optimal` is true; on S3 it is false; `budget == 3 * reference_steps`; following the walk and submitting the true total succeeds within `reference_steps` steps (SC-003).
- [X] T019 [P] [US2] Episode tests in `tests/survey/test_env.py`: cell views have exactly `{"cell", "deposit", "exits", "columns", "rows"}` and exits ordered north, east, south, west; `move` into a wall or edge fails with `wall` and costs a step; `invalid_direction`; `submit` accepts `12` and `"12"`, refuses `-1`, `"about 12"`, `1.5`, `true` with `invalid_total` (costs a step, episode goes on); a successful submit ends with `submitted` and `success` iff the total is right; budget end; `stop()`; calls after the end return `episode_over` with step `None`; re-entering a cell gives the same view; up to 4 scouts at `A1`, `add_scout()` costs no step and returns `None` at 4; `seen` and `cells_seen` cover all scouts; `parallel_turns` is the number of distinct `turn` values from `turn_source`, and equals `steps` without one (data-model "Survey Episode", R7, R11).
- [X] T020 [P] [US2] Boundary tests in `tests/survey/test_boundary.py`: for every level and dev seed, 300 random calls (including bad directions and totals) never show another cell's name or deposit, the true total, the budget or the reference steps; every result has the fixed envelope and one of the two data shapes; `AgentTools` exposes only `start`, `look`, `move`, `submit` (contracts/survey-tools.md "What a result never shows").
- [X] T021 [P] [US2] Kit tests in `tests/survey/test_kit.py`: `build_kit` for a survey episode has `problem == "survey"`, the survey `TOOL_SCHEMAS` and `BASE_PROMPT` from contracts/survey-tools.md verbatim, `start` as the start-cell result JSON; the tool node answers `look`/`move`/`submit`, unknown tools with `unknown_tool` (costs a step), and invalid calls; the survey fingerprint differs from `ff9afb3b9f66` and is stable.
- [X] T022 [P] [US2] A1 on the field in `tests/arch/test_react_survey.py`: `play_episode(key, ..., problem="survey")` with `react` and a scripted model that walks the S1 snake and submits the right total gives a completed row with `success`, `steps == 36`, `parallel_turns == 36`, `cells_seen == 36`, `submitted_total == true_total == 6`; a scripted wrong total gives `success == False` (FR-026).
- [X] T023 [P] [US2] Text render tests in `tests/survey/test_render.py` and CLI tests in `tests/survey/test_cli.py`: `apl survey show --level S1 --seed 1000` prints a 6×6 grid with column letters A–F, row numbers 1–6, deposits, the start and the true total; `--route reference` adds the walk; `--html OUT` writes an SVG page; an unknown level exits 2 (contracts/cli.md).

### Implementation for User Story 2

- [X] T024 [P] [US2] Create `src/apl/survey/model.py`: `Cell = tuple[int, int]` (column, row); `cell_name((col, row)) = "ABCDEFGHIJ"[col] + str(row + 1)`; `SurveyLevel(name, size, deposits, walls, min_dead_ends)` and `LEVELS = {"S1": (6, 6, 0, 0), "S2": (10, 15, 0, 0), "S3": (10, 15, 18, 3)}` (size, deposits, walls, min_dead_ends); the frozen `Field` dataclass with the data-model fields (`level`, `seed`, `size`, `walls`, `deposits`, `start=(0, 0)`, `walk`, `reference_steps = len(walk) + 1`, `reference_is_optimal`, `budget = 3 × reference_steps`) and `exits(cell)` in the order north, east, south, west.
- [X] T025 [P] [US2] Create `src/apl/survey/seeds.py`: `DEV_SEEDS = range(1000, 1010)`, `TEST_SEEDS = range(2000, 2020)`.
- [X] T026 [US2] Create `src/apl/survey/walk.py` per research R8: `snake(size)` for open fields; `greedy(field_without_walk)` that always walks to the nearest unseen cell by breadth-first search, ties broken north, east, south, west.
- [X] T027 [US2] Create `src/apl/survey/generator.py` per research R9: `generate(level, seed) -> Field` with `random.Random(f"survey:{level}:{seed}")`; deposits are `deposits` distinct cells, "never the start"; S3 walls added one at a time, kept only if every cell stays reachable, until the count is reached and at least 3 cells have one exit, retrying with the next draw after 1,000 failed tries; the walk from T026 (`snake` without walls, `greedy` otherwise); `ValueError` for an unknown level naming S1, S2, S3.
- [X] T028 [P] [US2] Create `src/apl/survey/results.py`: `ErrorCode` (`invalid_direction`, `wall`, `invalid_total`, `unknown_tool`, `episode_over`), `EndReason` (`submitted`, `budget`, `stopped`), `CellView`, `Submitted`, `ToolError`, `ToolResult` with the same `to_dict` envelope as the dungeon's (contracts/survey-tools.md).
- [X] T029 [US2] Create `src/apl/survey/env.py`: `LogEntry` (with `turn`), `Outcome` (data-model "Survey Outcome"), `Episode` with scouts (max 4), `seen`, `look`/`move`/`submit`/`unknown`/`stop`/`outcome`/`describe`/`add_scout`, `on_step`, `turn_source`; the error messages of contracts/survey-tools.md; a submission on the last step counts before the budget; `start_episode(field)`.
- [X] T030 [P] [US2] Create `src/apl/survey/tools.py`: `AgentTools` with the free `start` view and `look`, `move`, `submit` per scout, nothing else public.
- [X] T031 [P] [US2] Create `src/apl/survey/prompt.py`: `BASE_PROMPT` and `TOOL_SCHEMAS` verbatim from contracts/survey-tools.md (each description ending " Every call costs one step, including failed calls."), `submit`'s parameter `{"total": {"type": "integer", "description": "The number of deposits in the whole field."}}`; `prompt_fingerprint()` over both, as the dungeon's.
- [X] T032 [US2] Add `build_kit(episode, model)` for the survey in `src/apl/survey/kit.py`, using `apl.kit`'s `_tool_node` helper: dispatch `look`, `move` (argument `direction`), `submit` (argument `total`, passed raw so the episode validates it), else `episode.unknown`; `Kit(problem="survey", ...)`; `add_scout` as on the dungeon.
- [X] T033 [US2] Create `src/apl/survey/__init__.py` (exports as `apl/dungeon/__init__.py` does) and register `"survey"` in `PROBLEMS` in `src/apl/problems.py`.
- [X] T034 [US2] Wire `turn_source` in `src/apl/runner/meter.py` and `src/apl/runner/episode.py`: the meter exposes `model_calls_started` (incremented in `on_chat_model_start`, thread-safe); `play_episode` sets `episode.turn_source` when the episode has that attribute (survey only; the dungeon `Episode` is not changed).
- [X] T035 [P] [US2] Create `src/apl/survey/render_text.py` (grid with column letters and row numbers, `o` deposits, `S` start, walls as `|` and `—` between cells, the true total and reference steps; with a route, the cells it enters numbered by first visit) and `src/apl/survey/render_svg.py` (the board as SVG: cells, deposits, walls, start, using the viewer's `CELL` and `MARGIN`, with CSS classes the page styles).
- [X] T036 [US2] Add `apl survey show --level --seed [--route reference] [--html OUT]` in `src/apl/cli.py`, the counterpart of `_show` for the dungeon.

**Checkpoint**: T017–T023 pass; A1 plays the field from the runner; `apl survey show` works (quickstart step 3).

---

## Phase 4: User Story 1 - Watch an architecture survey a field (Priority: P1)

**Goal**: in the viewer, pick the survey field, a level and a dev seed, run A1, A2 or a scout architecture, and watch fog lift, scout trails and the tally; replay saved episodes.

**Independent Test**: scripted A1, A2, A7–A9 survey episodes with checked field maps and submissions; the viewer API and saved episodes for a scripted survey episode.

### Tests for User Story 1 ⚠️ (write first, they must fail)

- [X] T037 [P] [US1] Field map tests in `tests/arch/test_field_map.py`: built from a start view and applied results only; failed calls change nothing; `render()` for the contracts/architectures.md example prints exactly that text (picture with `@`, `o`, `.`, `?`, the field line, "Cells seen: 6 of 36. Deposits seen: 1.", walls, unseen neighbors); `@` on a deposit still counts it.
- [X] T038 [P] [US1] Oracle in `tests/arch/oracle.py`: add `field_oracle(episode, viewer)` that builds the expected `FieldMap` content (cells seen with deposits and exits, positions) from a survey episode's log, as `oracle.py` does for the dungeon.
- [X] T039 [P] [US1] A2 on the field in `tests/arch/test_mapstate_survey.py`: with a scripted model on S1, every turn's last message equals the `FieldMap` render, which matches the oracle after every call; the system message is the survey base prompt plus `FIELD_MAP_INSTRUCTIONS`; dungeon A2 tests unchanged.
- [X] T040 [P] [US1] Scout tests in `tests/arch/test_scouts_survey.py`: `SharedMap` over a `FieldMap` merges four scouts' results, shows other scouts by number in the picture, and matches the oracle after every applied call of scripted `rounds` and `blackboard` episodes on S2.
- [X] T041 [P] [US1] A7 on the field in `tests/arch/test_fanout_survey.py`: a scripted plan of 4 scouts with quadrant tasks, scouts that answer without a tool call with a count, and a collect answer `{"total": 15}` end with one `submit` call logged as scout 0, `submitted_total == 15`, and `parallel_turns` smaller than `steps`; a bad collect answer is re-asked up to `MAX_MISSES` times, then the episode ends `stopped` without a submission; the dungeon A7 tests are unchanged.
- [X] T042 [P] [US1] A8 on the field in `tests/arch/test_rounds_survey.py`: `{"total": N}` ends the episode through a submission; `{"done": true}` on the survey is refused as a bad answer and re-asked; dungeon A8 tests unchanged.
- [X] T043 [P] [US1] A9 on the field in `tests/arch/test_blackboard_survey.py`: scouts share one board, claims `claim: C4 east` are shown, and the first successful `submit` by any scout ends the episode; `parallel_turns == steps` for one call per turn (R11).
- [X] T044 [P] [US1] Viewer API tests in `tests/viewer/test_app.py`: `/api/options` keeps its dungeon fields and adds `problems` (contracts/viewer.md); `/api/survey/S1/1000` returns the board with `true_total`, `deposits`, `walls`, `svg` and reference frames; `/api/survey/S1/2000` is 403; `POST /api/episodes` with `"problem": "survey"` and `hybrid` is 400 with the support message; the dungeon responses are byte-for-byte unchanged.
- [X] T045 [P] [US1] Viewer event tests in `tests/viewer/test_events.py`: a scripted survey episode's `start` event has `problem` and `true_total`; each `step` frame has `scouts`, `seen`, `deposits_seen`, `submitted`, `steps`; the `end` event has `submitted_total` and `success`; the saved episode reopens with its problem.

### Implementation for User Story 1

- [X] T046 [US1] Create `src/apl/arch/field_map.py` per contracts/architectures.md and research R10: `FieldMap.from_start(start_json)`, `apply(name, args, result)`, `render()`; the same `current` attribute `SharedMap` uses.
- [X] T047 [US1] In `src/apl/arch/mapstate.py`: add `FIELD_MAP_INSTRUCTIONS` (explains the picture's symbols and the lines below it, no strategy) and pick `FieldMap` and these instructions when `kit.problem == "survey"`; the dungeon path unchanged.
- [X] T048 [US1] In `src/apl/arch/scouts.py`: make `SharedMap` work with `DungeonMap` or `FieldMap` (construct from `kit.problem`; the map's own `render` with other scouts shown, inventories only for the dungeon); survey variants of `SCOUT_INSTRUCTIONS` and `MAP_INSTRUCTIONS` use (field, no keys); a helper `submit(kit, total) -> None` that calls scout 0's tool node with one `submit` tool call (research R14); the dungeon texts unchanged.
- [X] T049 [US1] In `src/apl/arch/fanout.py`: survey instructions (the field, scouts report a count by answering without a tool call) and the `collect` node: after the scouts, ask the orchestrator with each scout's report for `{"total": <whole number>}`, re-ask up to `MAX_MISSES`, then `submit`; the dungeon graph unchanged.
- [X] T050 [US1] In `src/apl/arch/rounds.py`: survey instructions with the stop answer `{"total": <whole number>}`, submitted through the T048 helper; `{"done": true}` refused on the survey; the dungeon graph unchanged.
- [X] T051 [US1] In `src/apl/arch/blackboard.py`: the survey `TASK` per contracts/architectures.md; scouts end the episode by submitting; the dungeon task unchanged.
- [X] T052 [US1] In `src/apl/viewer/app.py`: `problems` in `/api/options` (levels, dev seeds, test-seed range, architectures from `SUPPORTS` that are written); `GET /api/survey/<level>/<seed>` (403 for test seeds, as `parse_dungeon`); `POST /api/episodes` takes `problem` (default `"dungeon"`), refuses unsupported architectures with 400, and plays through `play_episode(..., problem=...)`; the `start` event carries `problem` and, for the survey, `true_total`.
- [X] T053 [US1] In `src/apl/viewer/events.py` and a new `src/apl/survey/frames.py`: survey snapshots (`scouts` cells, `seen`, `deposits_seen`, `submitted`, `steps`) emitted with each step; the `end` event adds `submitted_total` and `success`; saved `events.jsonl` keeps the problem so "Saved episodes" can reopen it.
- [X] T054 [US1] In `src/apl/viewer/assets/index.html`: a problem picker before the level picker (levels, seeds and architectures follow it); a survey renderer that draws the board SVG, fog on cells not in `seen` when "Agent's view" is on, scout markers and trails in the existing `--agent`/`--scout1..3` colors; a tally panel "True total", "Seen so far", "Submitted" with right or wrong; the step slider, side panel, Stop and replay working for both problems; the dungeon view unchanged.
- [X] T055 [US1] Check `src/apl/viewer/assets/index.html` with the M3/M4 headless-browser check, adapted to a scripted four-scout S2 episode: fog lifts per step, trails per scout, the tally ends with "Submitted 15 — right"; then quickstart step 5 by hand with the local model (the experimenter).

**Checkpoint**: T037–T045 pass; the experimenter can watch and replay survey episodes (SC-004).

---

## Phase 5: User Story 3 - Run, continue and report on a chosen problem (Priority: P2)

**Goal**: plan, run, continue and report survey runs with the dungeon's commands plus `--problem`; the survey report has its own columns.

**Independent Test**: plan without `--execute`; play a scripted survey run, interrupt and continue it; check the report against the rows.

### Tests for User Story 3 ⚠️ (write first, they must fail)

- [X] T056 [P] [US3] CLI tests in `tests/runner/test_cli_run.py`: `apl run --problem survey --arch react,mapstate,fanout,rounds,blackboard --level all --seeds dev --limit 1` prints a plan with `problem  survey`, levels S1, S2, S3, 15 episodes, and writes nothing and calls no model; `--arch hybrid` exits 2 with `apl: hybrid does not play the survey problem (it plays: dungeon)`; without `--problem` the output equals the T004 pin.
- [X] T057 [P] [US3] Run and continue tests in `tests/runner/test_continue.py`: a scripted survey run stopped after 2 of 5 episodes continues from `run.json`'s problem, plays the rest on the survey field, and writes rows with `problem == "survey"` and the survey fields; an older `run.json` without `problem` continues as a dungeon run.
- [X] T058 [P] [US3] Report tests in `tests/runner/test_report.py` and `tests/runner/test_compare.py`: from hand-written survey rows, the main table shows Right, Off by (median absolute error of wrong totals, `—` if none), Seen, Steps, Turns, Tokens, Latency per architecture and level; the spread table min–max of Right, Steps, Turns; the comparison adds Δ right and Δ turns with references `mapstate → react` and scouts → `mapstate`; mixing a dungeon and a survey run is refused with the contracts/cli.md message; dungeon reports equal the T004 pin.

### Implementation for User Story 3

- [X] T059 [US3] In `src/apl/cli.py`: `--problem` on `apl run` (choices from `PROBLEMS`, default `dungeon`), passed to `RunSpec.build`; `apl continue` and `apl report` take the problem from the run.
- [X] T060 [US3] In `src/apl/runner/results.py`: `EpisodeRow.completed` fills the survey fields from the survey `Outcome` (`submitted_total`, `true_total`, `cells_seen`, `cells`, `parallel_turns`, `reference_is_optimal`); `failed` fills `true_total` and `cells` from the field.
- [X] T061 [US3] In `src/apl/runner/report.py`: `check_compatible` refuses different problems; a survey main table and spread table per contracts/results.md; the dungeon tables unchanged.
- [X] T062 [US3] In `src/apl/runner/compare.py`: the survey comparison columns (Δ right, Δ turns) and reference pairs; the dungeon comparison unchanged.

**Checkpoint**: T056–T058 pass; quickstart steps 4 and 6 work.

---

## Phase 6: User Story 4 - The fairness rules hold within each problem (Priority: P2)

**Goal**: the tests that enforce the rules cover both problems.

**Independent Test**: the import test passes with the survey modules allowed and fails for an architecture importing field internals; two architectures on one survey level record the same prompt, tools and budget.

### Tests for User Story 4 ⚠️ (write first, they must fail)

- [X] T063 [P] [US4] In `tests/dungeon/test_boundary.py`: `ALLOWED` gains `apl.survey.tools` and `apl.survey.results`; add a check that an architecture source importing `apl.survey.generator` or `apl.survey.env` (written to a temporary file and parsed the same way) is rejected.
- [X] T064 [P] [US4] In `tests/runner/test_run.py`: a scripted survey run with `react` and `mapstate` on S1 records one `prompt_fingerprint` (the survey's) in `run.json`, and both rows have the same `budget` and `optimal_steps`; the kit each got has the same `tools` and `base_prompt`.

### Implementation for User Story 4

- [X] T065 [US4] In `src/apl/runner/run.py`: `run.json`'s settings record uses `settings.record(problem=spec.problem)`; `src/apl/viewer/app.py` records the episode's problem the same way.

**Checkpoint**: T063–T064 pass.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T066 [P] Update `README.md`: the status line names M5; a short "Problems" section (dungeon, survey field) with `apl survey show` and `apl run --problem survey`; the architecture table gains which problems each plays; the viewer section mentions the problem picker.
- [X] T067 [P] Docstrings: `src/apl/kit.py` and `src/apl/survey/tools.py`, `results.py` name the allowed imports for both problems; `src/apl/arch/*.py` headers that are touched say the survey version was written by the agent at the experimenter's request.
- [X] T068 Run steps 1–4 of `specs/005-survey-field/quickstart.md` and fix what they find.
- [X] T069 Run the four checks configured in `pyproject.toml`: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`.
- [X] T070 `/speckit-converge` for this feature, appending any remaining work to `specs/005-survey-field/tasks.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 first (the experimenter confirms it); T002–T004 after it, in parallel.
- **Foundational (Phase 2)**: after Phase 1; blocks every story.
- **US2 (Phase 3)**: after Phase 2.
- **US1 (Phase 4)**: after US2 (it needs the survey episode and kit).
- **US3 (Phase 5)**: after US2; can run alongside US1 (different files except `results.py`, which T060 touches after T014).
- **US4 (Phase 6)**: after US2; T065 after T016.
- **Polish (Phase 7)**: after all stories.

### Within Each Story

- Tests first, failing; then models → environment → kit → runner wiring → architectures → viewer.
- US2: T024, T025, T028 → T026 → T027 → T029 → T030, T031 → T032 → T033 → T034; T035 → T036.
- US1: T046 → T047, T048 → T049, T050, T051; T052 → T053 → T054 → T055.
- T004 and `tests/dungeon/test_golden.py` must pass after every task.

### Parallel Opportunities

- T002, T003 (docs).
- T005–T008 (Phase 2 tests).
- T017–T023 (US2 tests), and T024, T025, T028, T030, T031, T035 (separate new files).
- T037–T045 (US1 tests); T049–T051 after T048 (separate architecture files).
- T056–T058 (US3 tests); US3 and US1 implementation after US2.

---

## Parallel Example: User Story 2 tests

```bash
Task: "T017 Generator tests in tests/survey/test_generator.py"
Task: "T018 Reference walk tests in tests/survey/test_walk.py"
Task: "T019 Episode tests in tests/survey/test_env.py"
Task: "T020 Boundary tests in tests/survey/test_boundary.py"
Task: "T021 Kit tests in tests/survey/test_kit.py"
```

## Parallel Example: the scout architectures on the field

```bash
Task: "T049 fanout collect node in src/apl/arch/fanout.py"
Task: "T050 rounds total answer in src/apl/arch/rounds.py"
Task: "T051 blackboard survey task in src/apl/arch/blackboard.py"
```

---

## Implementation Strategy

### MVP first (US2)

1. Phase 1 (constitution, pins) and Phase 2 (registry).
2. Phase 3: the survey field, playable by A1 from the runner and printable with `apl survey show`.
3. Stop and check: every field is valid, the dungeon is pinned, A1 scores right and wrong totals.

### Then

4. US1: field map, A2 and the scouts, then the viewer. This is where the experimenter starts
   watching (the point of the feature).
5. US3: survey runs and reports, for checking what the viewer showed across seeds.
6. US4: the rule tests for both problems.
7. Polish, the four checks, `/speckit-converge`.

### Notes

- Commit after each checkpoint; the dungeon pins make regressions visible at once.
- No task runs an experiment; a survey comparison run is the experimenter's choice afterwards.

---

## Phase 8: Convergence

- [X] T071 Add a scripted S2 episode in `tests/arch/test_survey_archs.py` where A8 gives four scouts one quarter of the open field each (rows 1–3, 4–5, 6–8, 9–10 or similar) and they walk it in parallel; check the total is right and `parallel_turns` is at most about a third of the reference walk's 100 steps, per SC-007 (partial)
- [X] T072 Add a viewer test in `tests/viewer/test_survey.py` with four scouts on S2 where scout 3 moves onto a deposit: its step event has `scout == 3`, the frame's `scouts[3].position` is the new cell and `deposits_seen` goes up by one, per US1/AC2 (partial)
- [X] T073 Make `src/apl/runner/spec.py` (`RunSpec.build`) and `src/apl/viewer/app.py` (`Viewer.plays`) use `registry.plays` for the support check, with names outside the table playing only the dungeon, per plan: R15 (partial)
