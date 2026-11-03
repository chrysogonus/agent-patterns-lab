---

description: "Task list for 011: the workshop"
---

# Tasks: The Workshop

**Input**: Design documents from `specs/011-workshop/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R15), data-model.md, contracts/, quickstart.md

**Tests**: Yes. The spec's success criteria (SC-001–SC-007) and the plan's testing section ask for
them; each phase writes its tests first and they must fail before the implementation. Tests use
the scripted chat model (`tests/runner/scripted.py`) and never call a model.

**Organization**: by user story. US2 (the problem) comes before US1 (watching it), because the
viewer and the architectures need the problem to exist; both are P1. Constitution 2.4.0 is already
in place (done before the plan).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1–US4 from spec.md
- Paths are from the repository root

---

## Phase 1: Setup

**Purpose**: a green tree and a safety net for the rune floor, as M10 had for the signal trace.

- [X] T001 Run the four checks on the tree as it is (`uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`); all must pass before T002.
- [X] T002 Pin the rune floor's outputs before any code change in `tests/runner/test_rune_pinned.py`, in the style of `tests/runner/test_signal_pinned.py`: `apl.rune.prompt.prompt_fingerprint()` equals `7c213929b31a`; the exact dry-run text of `apl run --problem rune --arch react --level all --seeds dev --limit 1` stored in `tests/runner/fixtures/rune-plan.txt`. These tests and the dungeon, survey and signal pins must pass now and after every later task (SC-001, FR-020).
- [X] T003 [P] Update `plan.md`: the at-a-glance line says five problems; a new §2e "Workshop" with the world (goal, recipes hidden until inspected, items with one or two recipes, raw materials with a stock, scarce ones, stuck), the tools table from `specs/011-workshop/contracts/workshop-tools.md`, the episode (ends at the goal, stuck, the budget or a stop; reference and budget of research R6) and the levels table of research R3 (W1 3 craftables, depth 2, no conflict; W2 5, depth 3, 1 conflict; W3 8, depth 4, 2 conflicts); §4's "Problems" column: `react`, `mapstate`, `plan_execute`, `reflexion`, `hybrid` gain "workshop", `supervisor` becomes "dungeon, workshop"; §7 gains an M11 row "The workshop, A1–A6 on it" with "Done when" from the spec and an empty status; §9 notes the workshop as the fifth problem; also fix §1's stale "Since M5 the lab has two problems" sentence to name every problem.
- [X] T004 [P] Update `AGENTS.md`: the import rule adds `apl.workshop.tools` and `apl.workshop.results`; the tools sentence adds "the workshop's `look`, `inspect`, `gather` and `craft`"; the command list adds `uv run apl workshop show --level W2 --seed 1000 --route reference` and `uv run apl run --problem workshop --arch react --level all --seeds dev --limit 1`.

**Checkpoint**: the tree is green; the four earlier problems' outputs are pinned.

---

## Phase 2: User Story 2 - The workshop problem (Priority: P1) 🎯 MVP

**Goal**: a seed and a level always build the same workshop; agents act only through `look`, `inspect`, `gather` and `craft` with the goal and stock free at the start; every workshop has a reference and a budget; A1 plays it from the runner.

**Independent Test**: generate every level and seed and check them; play the scripted agents and scripted calls against the tools; play A1 with a scripted model through `play_episode(..., problem="workshop")`.

### Tests for User Story 2 ⚠️ (write first, they must fail)

- [X] T005 [P] [US2] Plans tests in `tests/workshop/__init__.py` (empty) and `tests/workshop/test_plans.py` on hand-built workshops, the mock-up's lantern among them (lantern ← frame, lens, oil; frame: recipe 1 iron bar, recipe 2 wood + resin; iron bar ← coal + iron ore; lens ← glass; glass ← sand + coal; oil ← seeds; coal stock 1): `feasible` is true at the start, false once the iron bar is crafted (the coal is inside it), true with a held glass; `reference_calls` inspects each craftable when first reached, gathers what is missing, crafts depth first, uses recipe 2 for the frame and has exactly `reference` calls; `greedy_calls` crafts the iron bar with recipe 1 of the frame; `reference_use` gives `{("glass", "coal"): 1}`; `planner_calls` inspects every craftable reachable through any recipe before its first gather.
- [X] T006 [P] [US2] Generator tests in `tests/workshop/test_generator.py`: for W1–W3 and every dev and test seed, the workshop is identical across two calls; every input is a craftable or a raw material of the workshop; the craftables reachable through reference recipes form a tree under the goal (each used once, no cycle) with the level's craftables 3/5/8 and depth 2/3/4; the number of items with two recipes is 1/1/2 and of scarce materials 0/1/2, each scarce with stock 1; W1's second recipe uses plentiful raw materials only; every name is from `CRAFTABLE_NAMES` or `RAW_NAMES`; `budget == 3 × reference`; `reference_is_optimal` is true; references within W1 ≤ 12, W2 ≤ 20, W3 ≤ 32; `generate("W9", 1000)` raises `ValueError` naming W1, W2, W3 (SC-002, research R3, R4, R6).
- [X] T007 [P] [US2] Scripted-agent tests in `tests/workshop/test_agents.py` per research R7, on every level and every dev and test seed, played through `Episode`: the reference plan crafts the goal in exactly `reference` steps with `wasted == 0` (SC-003); the greedy plan ends `stuck` on W2 and W3 with `wasted ≥ 1` and crafts the goal on W1; the planner crafts the goal within the budget on every level (SC-004).
- [X] T008 [P] [US2] Episode tests in `tests/workshop/test_env.py` on the hand-built lantern of T005, per data-model.md "Episode" and the contract: `describe()` is free and equals the `look` data `{"goal", "stock", "inventory"}`; `inspect` of a craftable answers `{"item", "recipes"}`, of a raw material `{"item", "raw": true}`, an unknown name fails `unknown_item`; `gather` moves one unit and answers `{"gathered", "stock", "inventory"}`, a craftable fails `not_raw`, an empty stock `out_of_stock`; `craft` answers `{"crafted", "recipe", "inventory"}`, `recipe` as `2` or `"2"`, a raw material or a missing recipe number fails `no_such_recipe`, missing inputs fail `missing_inputs` naming them; every error message as in the contract, each costs a step and adds an invalid action; crafting the goal ends `goal` with success and `"goal": true`; crafting the iron bar ends `stuck` with `"stuck": true`, wasted 1; with `max_attempts = 3` the same craft answers `"stuck": true, "attempts_left": 2`, calls `on_restart` once, refills the stock, empties the inventory, sets `attempt` 2 and keeps `steps`, `wasted`, `inspected`; on the last attempt it ends `stuck`; the budget ends it `budget` and the goal on the last step counts first; `stop()`; calls after the end answer `episode_over` with step `None`; `unknown("build")` says "The tools are look, inspect, gather and craft."; `outcome().to_dict()` has `stuck`, `wasted`, `inspected`, `crafted`, `reference_is_optimal` and `attempts` when > 1; `wasted` and the stuck moment are rebuilt from `outcome().to_dict()["log"]` alone with `apl.workshop.plans` (SC-006).
- [X] T009 [P] [US2] Boundary tests in `tests/workshop/test_boundary.py` per research R15: for every level and dev seed, 300 random calls (unknown names, raw and craftable names, recipe 0–3) give the fixed envelope and one of the contract's data shapes; errors are `{"code", "message"}`; no result shows a recipe of an item before it was inspected in that episode; the start and `look` results are identical for two workshops with the same goal and stock and different recipes; no result's JSON contains `scarce`, `reference` or `budget`; `AgentTools` exposes only `start`, `look`, `inspect`, `gather`, `craft`.
- [X] T010 [P] [US2] Kit tests in `tests/workshop/test_kit.py`: `build_kit` gives `problem == "workshop"`, `BASE_PROMPT` and `TOOL_SCHEMAS` verbatim from the contract (`inspect` and `gather` take `{"item": {"type": "string"}}`, `craft` `{"item": string, "recipe": integer}`), `start` the start view JSON; the tool node answers all four tools (arguments passed raw), unknown tools with `unknown_tool` (one step) and invalid calls; `add_scout()` returns None; `restart` and `max_attempts` reach the episode; the fingerprint is stable and differs from the dungeon's, survey's, signal's and rune's pinned values.
- [X] T011 [P] [US2] Render and CLI tests in `tests/workshop/test_render.py` per `specs/011-workshop/contracts/cli.md`: `apl workshop show --level W2 --seed 1000` prints the header line, the stock line with `(scarce)` marks, one line per craftable depth first with `|` between recipes, `*` on the reference's choice and `!` on a tempting first recipe; `--route reference` adds `reference: inspect …, craft <goal> 1`; `--html OUT` writes a page with an SVG with `data-item` boxes; an unknown level exits 2; a test seed is shown.
- [X] T012 [P] [US2] A1 tests in `tests/arch/test_react_workshop.py`: `play_episode(key, ..., problem="workshop")` with `react` and `play_calls` built from `reference_calls` on W2 seed 1000 gives a completed row with `success`, `steps == optimal_steps`, `wasted == 0`, and the first human message is the start view JSON; `play_calls` from `greedy_calls` gives `success == False`, `end_reason == "stuck"`, `stuck` true (FR-021).

### Implementation for User Story 2

- [X] T013 [P] [US2] Create `src/apl/workshop/model.py` per data-model.md: `WorkshopLevel(name, craftables, depth, conflicts)`, `LEVELS = {"W1": (3, 2, 0), "W2": (5, 3, 1), "W3": (8, 4, 2)}` as `WorkshopLevel`s; `CRAFTABLE_NAMES` (20 words) and `RAW_NAMES` (14 words); the frozen `Workshop(level, seed, goal, recipes, stock, scarce, reference_choice, reference)` with `reference_steps`, `budget = 3 × reference`, `reference_is_optimal = True`, `raw(name)`, `craftable(name)`; `Action(tool, args)`. Also `src/apl/workshop/seeds.py`: `DEV_SEEDS = range(1000, 1010)`, `TEST_SEEDS = range(2000, 2020)`.
- [X] T014 [US2] Create `src/apl/workshop/plans.py` per data-model.md "Plans" and research R5–R8: `feasible(workshop, stock, inventory)` (every combination of open recipe choices; held items used first), `reference_calls`, `greedy_calls`, `planner_calls`, `reference_use`, and a `choices(workshop)` helper for the planner's search. Plain functions over a `Workshop`.
- [X] T015 [US2] Create `src/apl/workshop/generator.py` per research R3, R4: `generate(level, seed) -> Workshop` with `random.Random(f"workshop:{level}:{seed}")`; draw names, grow the tree, give raw inputs, add the conflicts (scarce material, `X` and `T` in depth-first order, no ancestor relations, `M` behind `T`'s new first recipe), W1's harmless second recipe; stock = the reference plan's use plus 1–2 for plentiful materials, exactly 1 for scarce ones; accept when the reference is feasible and, on W2–W3, the greedy plan gets stuck (on W1 it does not); draw again up to `MAX_TRIES = 1000`; `ValueError` for an unknown level naming W1, W2, W3.
- [X] T016 [P] [US2] Create `src/apl/workshop/results.py` per data-model.md "Results": `ErrorCode` (`unknown_item`, `not_raw`, `out_of_stock`, `no_such_recipe`, `missing_inputs`, `unknown_tool`, `episode_over`), `EndReason` (`goal`, `stuck`, `budget`, `stopped`), `StoreView`, `RecipesView`, `RawView`, `GatheredView`, `CraftedView` (optional `goal`, `stuck`, `attempts_left`), `ToolError`, `ToolResult` with the shared envelope.
- [X] T017 [US2] Create `src/apl/workshop/env.py` per data-model.md "Episode", "Outcome" and its transitions: `MAX_ATTEMPTS = 3`; `LogEntry`; `Outcome`; `Episode` with `describe`, `look`, `inspect`, `gather`, `craft`, `unknown`, `restart`, `stop`, `outcome`, `on_step`, `on_restart`, `max_attempts = 1`; the recipe-number parsing of research R9 (an integer or a string of at most 1 digit); the contract's messages; waste per research R8; the stuck check after every successful craft; the retry rule (stuck with attempts left adds `attempts_left`, resets stock and inventory, `attempt` + 1, `on_restart` after the step is logged); `start_episode(workshop)`.
- [X] T018 [P] [US2] Create `src/apl/workshop/tools.py`: `AgentTools` with the free `start` and `look`, `inspect`, `gather`, `craft`, nothing else public.
- [X] T019 [P] [US2] Create `src/apl/workshop/prompt.py`: `BASE_PROMPT` and `TOOL_SCHEMAS` verbatim from the contract (`item` described as "The item's name, as the results write it."; `recipe` as "The recipe's number: 1 or 2."); `prompt_fingerprint()` as the others'.
- [X] T020 [US2] Create `src/apl/workshop/kit.py`: `build_kit(episode, model)` on `apl.kit._tool_node`, dispatching the four tools (arguments `item` and `recipe` passed raw), else `episode.unknown`; `Kit(problem="workshop", start=<start JSON>, add_scout=lambda: None, restart=..., max_attempts=episode.max_attempts, ...)`.
- [X] T021 [US2] Create `src/apl/workshop/__init__.py` and register `"workshop"` in `PROBLEMS` in `src/apl/problems.py` per `specs/011-workshop/contracts/problems.md`. Update `tests/viewer/test_survey.py`'s exact list of problems (with `"workshop"`).
- [X] T022 [P] [US2] Create `src/apl/workshop/render_text.py` (the contracts/cli.md text, with `route` adding the reference line) and `src/apl/workshop/render_svg.py` (one box `<rect class="item ..." data-item="frame">` per item in layers by depth under the goal, edges from item to inputs with `data-recipe` and second recipes dashed, raw materials as leaves with their stock, the reference choices' edges marked `class="reference"`; `animated` adds ids and the groups the page fills, per contracts/viewer.md).
- [X] T023 [US2] In `src/apl/cli.py`: `apl workshop show --level --seed [--route reference] [--html OUT]` beside `apl rune show`; the help line for the `workshop` command group.
- [X] T024 [US2] In `src/apl/runner/registry.py`: `SUPPORTS["react"]` gains `"workshop"`; in `src/apl/runner/results.py`: `EpisodeRow` gains `stuck` (bool), `wasted`, `inspected`, `crafted` (nullable, after the rune floor's fields, accepted as int/bool or null on parse, `None` on other problems' rows), filled from a workshop outcome by an attribute check; `end_reason` accepts `stuck`. Extend the row-key-order test in `tests/runner/test_results.py`.

**Checkpoint**: T005–T012 pass; A1 plays the workshop from the runner; `apl workshop show` works (quickstart step 3); all pins pass.

---

## Phase 3: User Story 1 - Watch an architecture build the goal item (Priority: P1)

**Goal**: A2–A6 play the workshop; in the viewer, pick the workshop, a level and a dev seed, run an architecture and watch the tree open, the stock and inventory change and the scarce material run out; replay saved episodes.

**Independent Test**: scripted A2–A6 workshop episodes with a checked workshop log, helper split and option list; the viewer API, events and replay for a scripted workshop episode.

### Tests for User Story 1 ⚠️ (write first, they must fail)

- [X] T025 [P] [US1] Workshop log tests in `tests/arch/test_workshop_log.py` per `specs/011-workshop/contracts/architectures.md`: built from a start view; `inspect` records recipes or raw; `gather` and `craft` take the stock and inventory from the result; failed calls change nothing; `render()` prints exactly the data-model.md example for the lantern after inspecting the lantern and the frame and gathering sand; `known` counts items inspected; `options()` lists inspections (first seen order), gathers with `(n left)` (stock order), and crafts with `(uses a, b)` only when the inputs are held; on every W2 dev seed a log built from a scripted episode agrees with the episode's stock and inventory.
- [X] T026 [P] [US1] A2 and A3 in `tests/arch/test_workshop_archs.py`: `mapstate` with a scripted model on W2: the system message is the workshop base prompt plus `WORKSHOP_LOG_INSTRUCTIONS`, and every turn's last message is the log's render built from the episode so far; `plan_execute` with a scripted planner, an executor that plays `reference_calls` and a replanner `{"done": true}` crafts the goal on W2, with the log in the executor's prompt; the other problems' tests of both stay as they are.
- [X] T027 [P] [US1] A4 in `tests/arch/test_reflexion_workshop.py` per the contract's A4 tests: a scripted A4 on W2 plays `greedy_calls` one call per turn and gets stuck, then (after the reflector's note) plays `reference_calls` in one reply: the graph's and the episode's attempt both go from 1 to 2, `on_restart` once, the reflector once with "The attempt ended: stuck.", the steps of both attempts in one budget, and the actor's system text ends with `WORKSHOP_ATTEMPT`; a reply whose first call leaves the goal impossible runs only that call.
- [X] T028 [P] [US1] A5 in `tests/arch/test_supervisor_workshop.py`: on W2 a scripted supervisor hands `{"to": "researcher", ...}` then `{"to": "crafter", ...}` then `{"done": true}`; the researcher (system text with its own instructions) plays the reference's inspections, the crafter its gathers and crafts; the goal is crafted; the researcher's `gather` and the crafter's `inspect` are refused without reaching the workshop (no step); the supervisor's system text is the workshop one from the contract; the dungeon supervisor tests stay as they are.
- [X] T029 [P] [US1] A6 in `tests/arch/test_hybrid_workshop.py`: on W2 seed 1000 the first options are `inspect <goal>` then `gather R (n left)` for each raw material; after inspecting the goal, its craftable inputs are offered for inspection; a craft is offered only when its inputs are held, as `craft X with recipe k (uses a, b)`; a scripted model whose answers follow `reference_calls` crafts the goal in `reference` steps; answers that name no option are re-asked without a step and end after `MAX_MISSES`; the other problems' A6 tests stay as they are.
- [X] T030 [P] [US1] Viewer tests in `tests/viewer/test_workshop.py` per `specs/011-workshop/contracts/viewer.md`: `/api/options` has `problems.workshop` with levels W1–W3, the dev seeds and the six architectures; `/api/workshop?level=W2&seed=1000` returns the contract fields; seed 2000 is 403; level `W9` is 400; `POST /api/episodes` with `fanout` is 400 with the support message; a scripted `react` episode's `start` event has `problem`, `goal`, `stock` and `scarce`, each `step` frame has the data-model.md "Frames" keys, the `end` event a row with `problem == "workshop"`; a scripted `reflexion` episode that gets stuck emits one `restart` event; the saved episode replays with the same events, its id (level `W2`) matches the episode-id pattern, and `episode.json` records the problem.

### Implementation for User Story 1

- [X] T031 [US1] Create `src/apl/arch/workshop_log.py` per the contract: `WorkshopLog.from_start`, `apply`, `render`, `known`, `options`; docstring: built from tool results only, no plan, written by the agent at the experimenter's request.
- [X] T032 [US1] In `src/apl/arch/mapstate.py`: `WORKSHOP_LOG_INSTRUCTIONS` verbatim from the contract and `WorkshopLog` when `kit.problem == "workshop"`; `SUPPORTS["mapstate"]` gains `"workshop"`.
- [X] T033 [US1] In `src/apl/arch/plan_execute.py`: the workshop log and its instructions on `workshop`; `SUPPORTS["plan_execute"]` gains `"workshop"`.
- [X] T034 [US1] In `src/apl/arch/reflexion.py`: the workshop log and its instructions on `workshop`; `STUCK = "stuck"` joins `RESTARTED`; the one-call-at-a-time `act` on `rune` and `workshop`, stopping after a result with `attempts_left`, failure `stuck` on the workshop; `WORKSHOP_ATTEMPT` on the workshop only; `_size` uses `known` for a `WorkshopLog`; `SUPPORTS["reflexion"]` gains `"workshop"`.
- [X] T035 [US1] In `src/apl/arch/supervisor.py`: helpers per problem (`dungeon`: navigator and inventory on the dungeon map, `workshop`: researcher and crafter on the workshop log), with the supervisor and helper texts of the contract for the workshop and the dungeon's unchanged; `SUPPORTS["supervisor"]` becomes `{"dungeon", "workshop"}`. Update `tests/runner/test_supervisor_runs.py` (`(it plays: dungeon)` → `(it plays: dungeon, workshop)`).
- [X] T036 [US1] In `src/apl/arch/hybrid.py`: a `kit.problem == "workshop"` branch with `WORKSHOP_HYBRID_INSTRUCTIONS` verbatim from the contract, the workshop log in state, options from `WorkshopLog.options()`, the dungeon's answer parsing, re-ask and `MAX_MISSES`, one tool call per option; `SUPPORTS["hybrid"]` becomes `{"dungeon", "signal", "rune", "workshop"}`. Update the tests that quote hybrid's support list: `tests/runner/test_cli_run.py` and `tests/viewer/test_survey.py` (`(it plays: dungeon, rune, signal)` → `(it plays: dungeon, rune, signal, workshop)`).
- [X] T037 [US1] Create `src/apl/workshop/frames.py`: `snapshot(episode, step, action, result)` with the data-model.md "Frames" keys (`attempt` only when > 1) and `reference_frames(workshop)` from `reference_calls`.
- [X] T038 [US1] In `src/apl/viewer/app.py` and `src/apl/viewer/server.py`: `GET /api/workshop` with the contract fields through the generic world parser; frames and the episode's world by problem (`episode.workshop`); the `start` event adds `problem`, `goal`, `stock` and `scarce` on `workshop`; `episode.json` records the problem; the episode-id pattern accepts `W[1-3]`.
- [X] T039 [US1] In `src/apl/viewer/assets/index.html`: an `isWorkshop()` branch: load `/api/workshop`; draw the SVG; per frame show `?` on uninspected craftables and hide their edges under "Agent's view", update stock labels (a scarce one red at 0) and held-count badges, fill the goal when crafted; the reference toggle ("Reference plan") outlines the reference edges under the truth view, restoring the shared toggle when another problem is shown (as for the rune floor); the stats panel shows `Workshop <level> seed <seed>`, steps against budget and reference, inspected, wasted, attempt, and `Crafted <goal>`, `Stuck` or `Out of budget`; the other problems' views unchanged.
- [X] T040 [US1] Check `src/apl/viewer/assets/index.html` with the headless-browser check used since M3, on a scripted `reflexion` W2 episode that gets stuck once and then succeeds: the tree opens per inspection, the scarce material turns red, the stats end with "Crafted <goal>", and switching problem to and from `workshop` raises no page error; then quickstart step 5 by hand with the local model (the experimenter).

**Checkpoint**: T025–T030 pass; the experimenter can watch and replay workshop episodes (SC-005).

---

## Phase 4: User Story 3 - Run, continue and report on the workshop (Priority: P2)

**Goal**: plan, run, continue and report workshop runs with `--problem workshop`; the report has its own table.

**Independent Test**: plan without `--execute`; play a scripted workshop run, interrupt and continue it; check the report against the rows.

### Tests for User Story 3 ⚠️ (write first, they must fail)

- [X] T041 [P] [US3] CLI tests in `tests/runner/test_cli_run.py`: `apl run --problem workshop --arch react,mapstate,plan_execute,reflexion,supervisor,hybrid --level all --seeds dev --limit 1` prints a plan with `problem  workshop`, levels W1, W2, W3, 18 episodes, writes nothing and builds no model; `--arch fanout` exits 2 with `fanout does not play the workshop problem (it plays: dungeon, survey)` (US3 1–2).
- [X] T042 [P] [US3] Run tests in `tests/runner/test_workshop_runs.py` (as `tests/runner/test_rune_runs.py`): a scripted workshop run stopped after 2 of 4 episodes continues and plays only the missing episodes; its rows have `problem == "workshop"` and `stuck`, `wasted`, `inspected`, `crafted`, `reference_is_optimal`; an infrastructure-error row still records `optimal_steps` and `budget`, with null counts (US3 3).
- [X] T043 [P] [US3] Report tests in `tests/runner/test_report.py`: from hand-written workshop rows, the title ends "on the workshop", the table has the contract header (Success, Stuck, Steps, Wasted, Efficiency, Budget hit, Tokens, Latency); the spread table has Success and Steps (min–max) with repeats; the comparison gives `hybrid` the reference `mapstate` on the workshop; a workshop and a rune run together are refused (US3 4).

### Implementation for User Story 3

- [X] T044 [US3] In `src/apl/runner/report.py`: the workshop table and spread table per `specs/011-workshop/contracts/results.md`, chosen by `first.problem == "workshop"`; the title "on the workshop"; the other tables unchanged (all pins pass).
- [X] T045 [US3] In `src/apl/runner/compare.py`: `PROBLEM_REFERENCES` gains `"workshop": {"hybrid": "mapstate"}`.

**Checkpoint**: T041–T043 pass; quickstart steps 4 and 6 work.

---

## Phase 5: User Story 4 - The fairness rules hold on the workshop (Priority: P2)

**Goal**: the rule tests cover the fifth problem.

**Independent Test**: the import test passes with the workshop modules allowed and fails for an architecture importing workshop internals; two architectures on one workshop level record the same prompt, tools and budget.

### Tests for User Story 4 ⚠️ (write first, they must fail)

- [X] T046 [P] [US4] In `tests/dungeon/test_boundary.py`: `ALLOWED` gains `apl.workshop.tools` and `apl.workshop.results`; a test like the rune floor's shows that a source importing `apl.workshop.generator`, `apl.workshop.env`, `apl.workshop.plans` or `apl.workshop.model` is rejected (FR-019, US4 2).
- [X] T047 [P] [US4] In `tests/runner/test_run.py`: a scripted workshop run with `react` and `mapstate` on W1 records the workshop's `prompt_fingerprint` in `run.json`, and both rows have the same `budget` and `optimal_steps` (US4 3).

### Implementation for User Story 4

- [X] T048 [US4] In `src/apl/kit.py`: the module docstring names the workshop's `tools` and `results` among the allowed imports. Fix anything T046–T047 find.

**Checkpoint**: T046–T047 pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T049 [P] Update `README.md`: "The five problems", a section "5. The workshop: plan before you craft" (tools and levels tables), the architecture table's Workshop column, the `apl workshop show` and `apl run --problem workshop` commands, the roadmap's M11, the repository layout and the contract links.
- [X] T050 [P] Docstrings of the touched architecture modules (`mapstate.py`, `plan_execute.py`, `reflexion.py`, `supervisor.py`, `hybrid.py`) say the workshop version was written by the agent at the experimenter's request (specs/011).
- [X] T051 Mark M11 ✅ in `plan.md` §7 and the at-a-glance line.
- [X] T052 Remove the Sync Impact Report comment from `.specify/memory/constitution.md`.
- [X] T053 Run steps 1–4 of `specs/011-workshop/quickstart.md` and fix what they find.
- [X] T054 Run the four checks: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`.
- [X] T055 `/speckit-converge` for this feature, appending any remaining work to `specs/011-workshop/tasks.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 first; T002–T004 after it, in parallel.
- **US2 (Phase 2)**: after Phase 1; blocks every other story.
- **US1 (Phase 3)**: after US2 (it needs the workshop episode, kit and plans).
- **US3 (Phase 4)**: after US2; can run alongside US1 (T041 needs every name in `SUPPORTS`, so it passes once T032–T036 are done).
- **US4 (Phase 5)**: after US2.
- **Polish (Phase 6)**: after all stories.

### Within Each Story

- Tests first, failing; then model → plans → generator → results → environment → tools, prompt → kit → registry and rows → CLI.
- US2: T013, T016 → T014 → T015 → T017 → T018, T019 → T020 → T021 → T022 → T023 → T024.
- US1: T031 → T032, T033, T034, T035, T036; T037 → T038 → T039 → T040.
- The dungeon, survey, signal and rune pins pass after every task.

### Parallel Opportunities

- T003, T004 (docs).
- T005–T012 (US2 tests); T013, T016, T018, T019, T022 (separate new files).
- T025–T030 (US1 tests); T032–T036 after T031 (separate architecture files; do the `registry.py` edits one after another).
- T041–T043 (US3 tests); T046, T047 (US4 tests).

---

## Parallel Example: User Story 2 tests

```bash
Task: "T005 Plans tests in tests/workshop/test_plans.py"
Task: "T006 Generator tests in tests/workshop/test_generator.py"
Task: "T007 Scripted-agent tests in tests/workshop/test_agents.py"
Task: "T008 Episode tests in tests/workshop/test_env.py"
Task: "T009 Boundary tests in tests/workshop/test_boundary.py"
```

## Parallel Example: the architectures on the workshop

```bash
Task: "T032 WorkshopLog on workshop in src/apl/arch/mapstate.py"
Task: "T033 WorkshopLog on workshop in src/apl/arch/plan_execute.py"
Task: "T034 WorkshopLog, stuck and the one-at-a-time act in src/apl/arch/reflexion.py"
Task: "T035 Per-problem helpers in src/apl/arch/supervisor.py"
Task: "T036 The workshop branch in src/apl/arch/hybrid.py"
```

---

## Implementation Strategy

### MVP first (US2)

1. Phase 1: a green tree, the rune pins, the docs.
2. Phase 2: the workshop, playable by A1 from the runner and printable with `apl workshop show`.
3. Stop and check: every workshop is valid, the reference is exact, the greedy plan gets stuck on
   W2–W3 and the planner fits the budget, A1 scores successes and stuck episodes, all pins pass.

### Then

4. US1: the workshop log, A2–A6, then the viewer. This is where the experimenter starts watching.
5. US3: workshop runs and reports.
6. US4: the rule tests for the fifth problem.
7. Polish, the four checks, `/speckit-converge`.

### Notes

- No task starts a paid or local experiment run; quickstart step 5 is the experimenter's, by hand.
- Commits only when the experimenter asks.
