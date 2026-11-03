---

description: "Task list for 006: A3 plan-and-execute"
---

# Tasks: A3 Plan-and-Execute

**Input**: Design documents from `specs/006-plan-and-execute/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R10), data-model.md, contracts/, quickstart.md

**Tests**: Yes. The success criteria (SC-001–SC-008) and research R10 ask for them; as in M2–M5,
each phase writes its tests first and they must fail before the implementation. Tests use the
scripted chat model (`tests/runner/scripted.py`) and never call a model.

**Organization**: by user story. US2 (A3 playing both problems fairly) comes before US1 (watching
it), because the viewer needs the architecture to exist; both are P1.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1–US3 from spec.md
- Paths are from the repository root

---

## Phase 1: Setup

**Purpose**: a green baseline before any change.

- [X] T001 Run `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` and `uv run mypy` on the unchanged tree and note the results; all four must pass before T002 (if one fails, stop and report it instead of fixing unrelated code).

---

## Phase 2: Foundational (blocking prerequisites)

**Purpose**: the name exists, so tests can load A3 through the registry.

- [X] T002 Register A3 in `src/apl/runner/registry.py` per contracts/runner-viewer.md: `ARCHITECTURES["plan_execute"] = "apl.arch.plan_execute"` (after `"blackboard"`) and `SUPPORTS["plan_execute"] = _BOTH`. Until T008, `is_written("plan_execute")` is false, so the viewer does not list it and `apl run` marks it "not written yet".

**Checkpoint**: `uv run apl run --arch plan_execute --level L1 --seeds dev --limit 1` prints a plan with `plan_execute (not written yet)`.

---

## Phase 3: User Story 2 - A3 plays both problems under the fairness rules (Priority: P1) 🎯 MVP

**Goal**: `plan_execute` plays the dungeon and the survey field with a planner, an A2-style executor and a replanner, bounded by constants, with planning calls counted apart.

**Independent Test**: `uv run pytest tests/arch/test_plan_execute.py tests/runner/test_meter.py` passes: scripted A3 escapes L1–L3, gets S1–S3 right, stops on each limit, and its prompt, tools and budget equal A2's.

### Tests for User Story 2 (write first, must fail)

- [X] T003 [P] [US2] Meter test in `tests/runner/test_meter.py`, next to `test_counts_orchestrator_calls_and_records_roles`: calls with metadata role `planner` and `replanner` count into `orchestrator_calls`; `executor (subgoal 1)` and `scout 0` do not; each role is recorded in the transcript (contracts/runner-viewer.md, research R7).
- [X] T004 [P] [US2] Create `tests/arch/test_plan_execute.py` with helpers: `_play(problem, level, seed, strategy)` (as `tests/arch/orchestrated.py` `play` and `tests/arch/test_survey_archs.py` `_play`), and a strategy that routes by system message (`by_system`) to the planner (marker `PLANNER_INSTRUCTIONS[:60]`), replanner (`REPLANNER_INSTRUCTIONS[:60]`) and executor (default). Tests for the happy path:
  - dungeon L1 1000, L2 1001, L3 1002: planner answers `{"plan": ["reach the exit"]}`, executor uses `walk_solution(generate(level, seed))`; the row is a success with `efficiency == 1.0` and `steps` equal to a scripted `mapstate` episode with the same strategy (SC-002, acceptance 2.1);
  - survey S1–S3 seed 1000: planner `{"plan": ["walk every cell and submit the total"]}`, executor `walk_field(generate(level, 1000).walk, total=<true count>)`; success, `steps` equal to scripted `mapstate` (SC-002, acceptance 2.2);
  - `row.orchestrator_calls` equals the number of planner + replanner calls and `roles(result)` starts with `"planner"` followed by `"executor (subgoal 1)"`; `row.steps` equals the executor's applied tool calls (SC-004, acceptance 2.3).
- [X] T005 [P] [US2] Fairness tests in `tests/arch/test_plan_execute.py`: on L3 1002 and S2 1000, the executor's system message equals `kit.base_prompt + "\n\n" + MAP_INSTRUCTIONS + " " + EXECUTOR_INSTRUCTIONS` (field: `FIELD_MAP_INSTRUCTIONS`); every system message A3 sends starts with the problem's base prompt; the run row's prompt fingerprint and budget equal a scripted `mapstate` episode's on the same level and seed (SC-003, acceptance 2.5 is covered by the existing boundary test's glob over `src/apl/arch/`).
- [X] T006 [P] [US2] Limit and edge-case tests in `tests/arch/test_plan_execute.py` (data-model.md transitions; SC-005):
  - planner answers `"?"` three times → `end_reason == "stopped"`, `orchestrator_calls == 3`, `steps == 0`; the second planner input starts with `Your answer was not used:`;
  - planner answers a plan with 9 subgoals, then `{"plan": []}`, then an entry `""` → each is unusable ("A plan is a list of 1 to `MAX_SUBGOALS` (8) strings, each non-empty after stripping");
  - executor answers without a tool call on every subgoal and the replanner keeps answering a plan → A3 stops after `MAX_IDLE` (3) idle subgoals, with no replanner call after the third;
  - executor bumps a wall forever (`bump_wall`) → after `MAX_TURNS` (20) executor turns the replanner is called and its input contains `unfinished after 20 turns`;
  - replanner answers `{"done": true}` after the first subgoal → `end_reason == "stopped"`;
  - `{"done": true}` from the planner is unusable (valid only for the replanner);
  - the replanner's input lists each finished subgoal with `done: <report>`, the subgoals still planned, and `Steps used so far: N` matching the steps applied;
  - when the executor enters the exit mid-subgoal, the transcript's last call is an executor call (no planning call after the end);
  - two subgoals in a row: the second subgoal's first executor input has no previous turn (only system, subgoal line, map) and the role is `executor (subgoal 2)`.

### Implementation for User Story 2

- [X] T007 [US2] Count planning roles in `src/apl/runner/meter.py`: add `LEAD_ROLES = frozenset({"orchestrator", "planner", "replanner"})` and count `role in LEAD_ROLES` into `orchestrator_calls`; update the attribute's comment (specs/006 R7). T003 passes; existing meter tests unchanged.
- [X] T008 [US2] Write A3 in `src/apl/arch/plan_execute.py` per contracts/plan-execute.md, data-model.md and research R1–R6, in the style of `src/apl/arch/mapstate.py` and `rounds.py` (module docstring naming specs/006 and "Written by the agent at the experimenter's request"):
  - constants `MAX_SUBGOALS = 8`, `MAX_TURNS = 20`, `MAX_IDLE = 3`; `MAX_MISSES` imported from `apl.arch.hybrid`;
  - texts `PLANNER_INSTRUCTIONS`, `REPLANNER_INSTRUCTIONS`, `EXECUTOR_INSTRUCTIONS` with the wording of research R2 and R4 (setup and answer format only, no strategy advice);
  - `PlanState` (TypedDict, no reducers) with the fields of data-model.md, and an `Outcome` record;
  - nodes `planner`, `executor`, `act`, `replanner`; `act` applies tool calls exactly as A2's `act` (`kit.tool_node`, then `map.apply` per result); roles `planner`, `replanner`, `executor (subgoal N)` via `config={"metadata": {"role": ...}}`;
  - plans read with `apl.arch.scouts.read_answer` and a local `read_plan` that returns the list or the reason it is unusable;
  - conditional edges per the transitions table; invoke with `recursion_limit=kit.recursion_limit`; the map is `FieldMap.from_start` on the survey field, else `DungeonMap.from_start`.
  T004–T006 pass.

**Checkpoint**: A3 plays both problems in scripted episodes; the four checks pass.

---

## Phase 4: User Story 1 - Watch A3 plan and execute (Priority: P1)

**Goal**: `plan_execute` is offered in the viewer for both problems; its turns appear with their roles and replay the same.

**Independent Test**: `uv run pytest tests/viewer` passes with the new tests.

### Tests for User Story 1 (write first)

- [X] T009 [P] [US1] In `tests/viewer/test_plan_execute.py`, test that the options list `plan_execute` for both `dungeon` and `survey` (acceptance 1.1), building the app with the real registry as `test_options_list_the_problems_and_who_plays_them` does.
- [X] T010 [P] [US1] Viewer episode test: play a scripted A3 episode on L1 1000 and on S1 1000 through the app as the existing viewer episode tests do; the streamed `thinking`/`turn` events carry the roles `planner`, then `executor (subgoal 1)` …, then `replanner` in call order (acceptance 1.2, 1.3); the planner's turn text is the scripted plan JSON; the saved episode replays with the same events (acceptance 1.4).

### Implementation for User Story 1

- [X] T011 [US1] Make T009–T010 pass. Expected: no change in `src/apl/viewer/` (contracts/runner-viewer.md). If a change is needed, keep it to the viewer and note it in research.md as R11.

**Checkpoint**: A3 can be chosen and watched in the viewer on any level and dev seed of both problems.

---

## Phase 5: User Story 3 - A3 in runs, reports and the comparison (Priority: P2)

**Goal**: A3 plans, continues and reports like the others, and joins a comparison next to `mapstate`.

**Independent Test**: `uv run pytest tests/runner` passes with the new tests.

### Tests for User Story 3 (write first, must fail)

As built, T012–T015 live together in `tests/runner/test_plan_execute_runs.py`, reusing the helpers of the files named below, so the existing tests stay as they were.


- [X] T012 [P] [US3] In `tests/runner/test_compare.py`: a comparison built from rows that include `plan_execute` lists it with reference `mapstate` and fills its Δ columns against `mapstate`'s rows (acceptance 3.3, FR-014); on the survey header too.
- [X] T013 [P] [US3] Report-together test (SC-007), in `tests/runner/test_compare.py` or `tests/runner/test_report.py`: play a scripted run of the seven dungeon architectures and a separate scripted run of `plan_execute` on L1 1000 with the same settings, report both run folders together; the comparison shows eight architectures for L1. The same on the survey field with `react`, `mapstate`, `fanout`, `rounds`, `blackboard` and `plan_execute` (six). Reporting together with a run of different settings is refused (acceptance 3.4).
- [X] T014 [P] [US3] In `tests/runner/test_continue.py`: an interrupted scripted run with `plan_execute` among its architectures continues with only the missing episodes (acceptance 3.2), on both problems (extend `ARCHS` / `SURVEY_ARCHS` only in the new test, so the existing tests keep checking what they checked).
- [X] T015 [P] [US3] In `tests/runner/test_cli_run.py` or `tests/runner/test_spec.py`: a dry run with `--arch plan_execute` on each problem lists it without "not written yet", prints the estimate and limits, and calls no model (acceptance 3.1, SC-006).

### Implementation for User Story 3

- [X] T016 [US3] Add `"plan_execute": "mapstate"` to `REFERENCES` in `src/apl/runner/compare.py`. T012–T015 pass.

**Checkpoint**: A3 can join the M4 comparison and any survey comparison under the same conditions.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T017 [P] Update `plan.md`: the "At a glance" line (M0–M5 built, A3 built in M6, A4–A5 next); §4 A3 row "Problems" → "dungeon, survey"; §7 M6+ row notes A3 done (A4, A5 still ⏳).
- [X] T018 [P] Update `README.md`: the architecture table row for A3 (built, both problems, `plan_execute`) and the milestone line for M6+.
- [X] T019 Run quickstart.md steps 1–3 (the four checks and the free dry runs) and record the outcome; steps 4–5 are the experimenter's choice and not run.
- [X] T020 Read `src/apl/arch/plan_execute.py` against constitution I–III once more (imports, constants not derived from the budget, only `act` calls `kit.tool_node`, nothing shown that tool results did not reveal) and leave the module for the experimenter's review.

---

## Dependencies & Execution Order

- **Setup (T001)** → **Foundational (T002)** → **US2 (T003–T008)** → **US1 (T009–T011)** and **US3 (T012–T016)** in either order → **Polish (T017–T020)**.
- Within US2: T003–T006 before T007–T008; T007 before T008's role-count assertions pass.
- US1 and US3 need A3 written (T008); they do not depend on each other.

## Parallel Opportunities

- T003, T004, T005, T006: different test concerns (T004–T006 share one new file, so write them in one pass if working alone).
- T009 and T010; T012–T015: different files.
- T017 and T018.

```text
# US3 tests together:
T012 tests/runner/test_compare.py   T014 tests/runner/test_continue.py   T015 tests/runner/test_cli_run.py
```

## Implementation Strategy

1. **MVP**: T001–T008. A3 plays both problems in scripted episodes; the four checks pass.
2. **Watchable**: T009–T011. The experimenter can watch A3 in the viewer.
3. **Comparable**: T012–T016. A3 joins the M4 comparison and survey comparisons.
4. **Docs and review**: T017–T020.

No task starts a paid or local experiment run.

## Phase 7: Convergence

- [X] T021 Give the replanner the start result as well, in `src/apl/arch/plan_execute.py` (`replanner` parts, after the note), and assert it in `tests/arch/test_plan_execute.py` (`test_the_replanner_sees_reports_and_the_plan_still_to_do`) per FR-004 (partial)
- [X] T022 Parametrize `test_the_side_panel_shows_each_job_and_replays_it` in `tests/viewer/test_plan_execute.py` over L1–L3 and S1–S3 per SC-001 (partial)
