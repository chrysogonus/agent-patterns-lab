# Tasks: Harder Top Levels for the Signal Trace and the Workshop

**Input**: Design documents from `specs/013-harder-levels/` (spec.md, plan.md, research.md,
data-model.md, contracts/levels.md, quickstart.md)

**Tests**: Requested. The constitution and `AGENTS.md` require all four checks, and the user's
standing rule is test-driven development: each story's tests are written first and must fail
before the code that makes them pass. No test makes a paid call.

**Organization**: Setup pins the existing levels; then one phase per user story. US1 (T4) and US2
(W4) are independent and both P1; US3 (runs, continue, report) builds on them.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1, US2, US3 from spec.md

---

## Phase 1: Setup

**Purpose**: a green tree and a safety net that proves T1–T3 and W1–W3 never change (FR-008,
SC-003; research R4, R5).

- [X] T001 Run the four checks on the tree as it is (`uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`); all must pass before T002.
- [X] T002 Pin the existing levels in a new `tests/runner/test_levels_pinned.py` with the fixture `tests/runner/fixtures/levels-pinned.json` (written once from the current code with `GOLDEN_REGEN=1`, in the style of `tests/runner/test_workshop_pinned.py`): for every level in T1, T2, T3 and every seed in the signal trace's `DEV_SEEDS` and `TEST_SEEDS`, a SHA-256 of the JSON of `feeder`, `runs`, `broken`, `reference_probes`, `budget` and of `apl.signal_trace.render_svg.svg(pipe)`; for every level in W1, W2, W3 and every workshop dev and test seed, a SHA-256 of the JSON of `goal`, `recipes`, `stock`, `sorted(scarce)`, `reference_choice`, `reference`, `budget` and of `apl.workshop.render_svg.svg(workshop)`. The test iterates the explicit lists `["T1", "T2", "T3"]` and `["W1", "W2", "W3"]` (never `LEVELS`), so it keeps passing after the new levels exist. It must pass now and after every later task.
- [X] T003 In `tests/runner/test_signal_pinned.py` and `tests/runner/test_workshop_pinned.py`, build the pinned dry-run plans with the explicit levels `["T1", "T2", "T3"]` and `["W1", "W2", "W3"]` instead of `["all"]` (research R5). `tests/runner/fixtures/signal-plan.txt` and `workshop-plan.txt` MUST stay byte for byte unchanged (run without `GOLDEN_REGEN`; `git diff --exit-code tests/runner/fixtures/` is clean).

**Checkpoint**: the tree is green; the old levels' pipes, workshops, drawings and plans are pinned.

---

## Phase 2: User Story 1 - Show and watch a T4 pipe (Priority: P1) 🎯 MVP

**Goal**: level T4 (256 segments, 8 pipe ends, runs ≥ 4) generates for every seed with the
existing reference and budget rules, draws readably, is offered by `apl signal show` and the
viewer, and plays and replays there.

**Independent Test**: `uv run pytest tests/signal_trace tests/viewer/test_signal.py`, then
`uv run apl signal show --level T4 --seed 1000 --route reference`.

### Tests for User Story 1 ⚠️ (write first, they must fail)

- [X] T004 [P] [US1] Generator tests in `tests/signal_trace/test_generator.py`: the budget table gains `("T4", 256)`; a new `test_t4_is_a_bounded_tree_marked_as_a_reference` in the style of the T3 test: for every dev and test seed, `pipe.segments == 256`, 15 runs (`len(pipe.runs) == 15`: 8 pipe ends give 2 × 8 − 1 runs), `not pipe.reference_is_optimal` and `pipe.reference_probes <= 12`; `test_an_unknown_level_is_refused` matches `"T1, T2, T3, T4"`. The parametrized shape, determinism and run tests pick up T4 from `LEVELS` (FR-001–FR-003, FR-007, SC-001).
- [X] T005 [P] [US1] A new `test_the_reference_finds_every_possible_break` in `tests/signal_trace/test_strategy.py`, parametrized over `sorted(LEVELS)`: for every dev and test seed and every segment `k` in `1..pipe.segments`, `dataclasses.replace(pipe, broken=k)` played with `reference_run` submits `k`, uses at most `pipe.reference_probes` probes, and every answer equals `wet` of the replaced pipe (SC-002; research R10). Keep the existing seeded-break test.
- [X] T006 [P] [US1] Render and CLI tests in `tests/signal_trace/test_render.py` (research R8): for T4 seed 1000, `svg(pipe)` has 256 `data-seg` boxes and a viewBox width of `2 × MARGIN + 80 + 24 × CELL` (= 732); for every T4 dev and test seed, every `<text class="label" …>from N</text>` has `x − len(text) × 7.2 ≥ MARGIN / 2` (the 12 px monospace estimate), and the source label likewise; a T3 pipe still has viewBox width `2 × MARGIN + 64 + 8 × CELL` (= 300); `apl signal show --level T4 --seed 1000 --route reference` exits 0 and prints 15 run lines and a `reference:` line; `apl signal show --level T9 --seed 1000` exits 2 (FR-011, FR-012).
- [X] T007 [P] [US1] Viewer tests in `tests/viewer/test_signal.py`: `test_options_and_the_pipe` expects `levels == ["T1", "T2", "T3", "T4"]`; `viewer.signal("T4", "1000")` answers `segments == 256`, `budget == 256`, `reference_is_optimal` false and an SVG with 256 `data-seg` boxes; a new `test_a_hybrid_episode_on_t4_streams_and_replays`, built like `test_a_hybrid_episode_streams_signal_frames_and_replays` with `scripted_factory(lambda messages: AIMessage("1"))`, plays hybrid on T4 seed 1000: the last frame has `submitted == pipe.broken`, the row is a success, and the saved episode replays with the same events (FR-012, SC-005).

### Implementation for User Story 1

- [X] T008 [US1] Add `"T4": SignalLevel("T4", segments=256, ends=8, min_run=4)` to `LEVELS` in `src/apl/signal_trace/model.py` (data-model.md). No other signal rule changes.
- [X] T009 [US1] In `src/apl/signal_trace/render_svg.py`, derive the row width and the label column from the pipe: `PER_ROW` 8 and `LABEL` 64 for pipes of up to 64 segments, 24 and 80 above (research R8); `layout`, `inlet` and `svg` use the pipe's values; update the module docstring. T002's pinned T1–T3 SVG hashes must still pass.
- [X] T010 [US1] In `src/apl/cli.py`, build `apl signal show`'s `--level` choices from `sorted(apl.signal_trace.LEVELS)` instead of `["T1", "T2", "T3"]`, as `apl dungeon show` does (research R7). Read through `PROBLEMS["signal"].levels`, since `cli.py` imports the problem packages lazily. Found while implementing: the viewer's `EPISODE_ID` pattern in `src/apl/viewer/app.py` allowed only level digits 1–3, so a T4 or W4 episode could not be looked up; it now allows `[LSTWP][1-4]`, and T007's T4 test asserts the id matches.

**Checkpoint**: T004–T007 pass; T4 can be shown, drawn, played and replayed; T002 and T003 pass.

---

## Phase 3: User Story 2 - Show and watch a W4 workshop (Priority: P1)

**Goal**: level W4 (12 craftables, depth 5, 3 conflicts) generates for every seed with the
existing rules, draws, is offered by `apl workshop show` and the viewer, and plays and replays
there.

**Independent Test**: `uv run pytest tests/workshop tests/viewer/test_workshop.py`, then
`uv run apl workshop show --level W4 --seed 1000 --route reference`.

### Tests for User Story 2 ⚠️ (write first, they must fail)

- [X] T011 [P] [US2] Generator tests in `tests/workshop/test_generator.py`: `SHAPE["W4"] = (12, 5, 3, 3)` (craftables, depth, alternatives, scarce) and `BOUND["W4"] = 48`; the unknown-level test, if it names the levels, includes W4. The parametrized agent tests in `tests/workshop/test_agents.py` (reference crafts the goal in its steps, greedy gets stuck, the planner fits the budget) and the boundary tests pick up W4 from `LEVELS` (FR-004–FR-007, SC-001, SC-002).
- [X] T012 [P] [US2] Render and CLI tests in `tests/workshop/test_render.py` (research R9): for every W4 dev and test seed, `svg(w)` has one `data-item` box per craftable and raw material, no two boxes overlap (from `places(w)`: boxes in one row are at least `BOX_W + GAP_X` apart), and no row of `layers(w)` holds more than 7 items; `apl workshop show --level W4 --seed 1000 --route reference` exits 0 and prints the goal, the stock with 3 scarce materials and a `reference:` line; `apl workshop show --level W9 --seed 1000` exits 2 (FR-011, FR-012).
- [X] T013 [P] [US2] Viewer tests in `tests/viewer/test_workshop.py`: `test_options_and_the_workshop` expects `levels == ["W1", "W2", "W3", "W4"]`; a new `test_a_react_episode_on_w4_streams_and_replays`, built like `test_a_react_episode_streams_workshop_frames_and_replays` with `scripted_factory(play_calls(reference_calls(w)))` for W4 seed 1000: the last frame ends `goal`, the row is a success with `wasted == 0`, and the saved episode replays with the same events (FR-012, SC-005).

### Implementation for User Story 2

- [X] T014 [US2] Add `"W4": WorkshopLevel("W4", 12, 5, 3)` to `LEVELS` in `src/apl/workshop/model.py` (data-model.md). No other workshop rule changes.
- [X] T015 [US2] In `src/apl/cli.py`, build `apl workshop show`'s `--level` choices from `list(apl.workshop.LEVELS)` (the workshop's level order) instead of `["W1", "W2", "W3"]` (research R7).

**Checkpoint**: T011–T013 pass; W4 can be shown, drawn, played and replayed; T002 and T003 pass.

---

## Phase 4: User Story 3 - Run, continue and report the new levels (Priority: P2)

**Goal**: `--level all` includes the new level last, the new level can be chosen alone, saved
three-level runs continue and report unchanged, and reports show the new level.

**Independent Test**: `uv run pytest tests/runner/test_levels_pinned.py`, then the dry runs in
quickstart.md §3.

### Tests for User Story 3 ⚠️ (write first, they must fail before US1/US2 land)

- [X] T016 [US3] In `tests/runner/test_levels_pinned.py`: `RunSpec.build(["react"], ["all"], "dev", limit=1, problem="signal").levels == ("T1", "T2", "T3", "T4")` and the workshop equivalent is `("W1", "W2", "W3", "W4")`; `--level T4` and `--level W4` alone plan one level each; the dry-run upper bounds of the `all` plans include the new level's budget (signal 256; workshop 3 × the seed-1000 W4 reference) (FR-009, SC-004).
- [X] T017 [US3] A continue-and-report test in `tests/runner/test_levels_pinned.py`, using the helpers of `tests/runner/test_continue.py`: start a signal run with `react` on `["T1", "T2", "T3"]`, dev seed 1000, a scripted model, interrupted after one episode; after this feature, `apl continue`'s plan for that directory holds exactly the remaining T1–T3 episodes (no T4); a completed run that includes T4 seed 1000 reports a T4 row and a `### T4` comparison section (FR-010, FR-013, SC-004).

### Implementation for User Story 3

- [X] T018 [US3] No production change is expected (research R6, R7): `RunSpec` resolves `all` from `PROBLEMS[problem].levels`, `run.json` stores resolved levels, and the report groups by level. If T016 or T017 fails after US1 and US2, fix the cause in `src/apl/runner/` and record it here. Result: none needed; with T4 and W4 removed, T016 and T017's report test fail, and the continue test passes either way (it guards saved runs).

**Checkpoint**: T016 and T017 pass; quickstart.md §3 and §4 behave as written.

---

## Phase 5: Polish & Cross-Cutting Concerns

- [X] T019 [P] Amend `.specify/memory/constitution.md` (research R11): "Levels T1–T3 are defined in plan.md" → "Levels T1–T4 …", "Levels W1–W3 …" → "Levels W1–W4 …"; version 2.5.0 → 2.5.1, Last Amended 2026-11-03; a Sync Impact Report entry naming specs/013 and the two changed lines (FR-016). Done without the report entry: the constitution keeps no Sync Impact Report (earlier amendments changed only the version line), so none was invented.
- [X] T020 [P] Update `plan.md`: §2c levels table gains `| T4 | 256 | a tree with 8 pipe ends, every run ≥ 4 | about 12 | 256 | More runs to weigh: the best split is harder to find |`; §2e levels table gains `| W4 | 12 | 5 | 3 | Three scarce materials a plan must protect at once |`; §7 gains an M13 row "Harder top levels: T4 on the signal trace, W4 on the workshop" with the spec's "Done when" and status ✅ once T022 passes; §9 notes that M13 added T4 and W4 after the first `gpt-6-luna` run showed the signal trace and the workshop saturate, and that noisy probes stay deferred (FR-017).
- [X] T021 [P] Update `README.md`: the signal levels table gains `| T4 | 256 | a tree with 8 pipe ends | about 11–12 probes + submit | 256 |`; the workshop levels table gains `| W4 | 12 | three | 3× the reference plan |`; any sentence that counts the levels (three) says four (FR-017).
- [X] T022 Run the four checks; all pass with no paid call (SC-006). Then run quickstart.md §2–§4 (show commands, dry runs, continue of a saved signal run) and record the outputs' key numbers (T4: 15 runs, reference, budget 256; W4: 3 scarce, reference 36–41) in this task's line when checked. The browser check of quickstart.md §5 needs the experimenter's viewer restarted; ask before restarting it. Checked 2026-11-03: four checks pass (1509 tests); T4 seed 1000: 256 segments, 15 runs, reference 13 steps (9 probes + submit on its seeded break), budget 256, picture 732 × 666; W4 seed 1000: 3 scarce, reference 39 steps, budget 117; `--level all` dry runs list T1–T4 and W1–W4; `apl continue` on the saved signal run refuses because the tree has uncommitted changes (the rule for continuing), and T017 covers continue with a clean tree. Browser check (§5) not done: waits for a viewer restart.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001–T003)**: first; T002 and T003 must pass before any production change.
- **US1 (T004–T010)** and **US2 (T011–T015)**: independent of each other after Setup; T010 and
  T015 both edit `src/apl/cli.py`, so run them one after the other.
- **US3 (T016–T018)**: its tests are written first; they pass once US1 and US2 are in.
- **Polish (T019–T022)**: after the stories; T022 last.

### Within Each Story

- Tests first, failing for the expected reason (the level is unknown, the drawing is narrow, the
  list has three entries); then the level entry, then the drawing or CLI change.

### Parallel Opportunities

- T004, T005, T006, T007 (four different test files); T011, T012, T013; T019, T020, T021.
- US1 and US2 as wholes, apart from the shared `src/apl/cli.py` edit.

---

## Parallel Example: User Story 1 tests

```text
T004 tests/signal_trace/test_generator.py
T005 tests/signal_trace/test_strategy.py
T006 tests/signal_trace/test_render.py
T007 tests/viewer/test_signal.py
```

---

## Implementation Strategy

### MVP first (US1)

Setup, then US1: T4 alone gives the signal trace a level that is not saturated, and proves the
pinning, drawing and CLI pattern that US2 repeats.

### Then

US2 (W4), US3 (runs, continue, report), Polish. Each checkpoint leaves the tree green.

### Notes

- No episode is run against a model in this feature; the comparison on T4 and W4 is M14.
- Nothing in `src/apl/arch/` changes.
- Commit only when the experimenter asks.
