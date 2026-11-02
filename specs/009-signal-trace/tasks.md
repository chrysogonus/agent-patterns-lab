---

description: "Task list for 009: the signal trace"
---

# Tasks: The Signal Trace

**Input**: Design documents from `specs/009-signal-trace/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R14), data-model.md, contracts/, quickstart.md

**Tests**: Yes. The spec's success criteria (SC-001–SC-007) and the plan's testing section ask for
them; each phase writes its tests first and they must fail before the implementation. Tests use
the scripted chat model (`tests/runner/scripted.py`) and never call a model.

**Organization**: by user story. US2 (the problem) comes before US1 (watching it), because the
viewer and the architectures need the problem to exist; both are P1. Constitution 2.2.0 is already
in place (done before the plan).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1–US4 from spec.md
- Paths are from the repository root

---

## Phase 1: Setup

**Purpose**: a green tree and a safety net for the survey field, as M5 had for the dungeon.

- [X] T001 Run the four checks on the tree as it is (`uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`); all must pass before T002.
- [X] T002 Pin the survey field's outputs before any code change in `tests/runner/test_survey_pinned.py`, in the style of `tests/runner/test_dungeon_pinned.py`: `apl.survey.prompt.prompt_fingerprint()` equals its current value (read it now and write it into the test); the exact dry-run text of `apl run --problem survey --arch react --level all --seeds dev --limit 1` (fixed settings record and code dict, as the dungeon pin builds it) stored in `tests/runner/fixtures/survey-plan.txt`. These tests and `tests/runner/test_dungeon_pinned.py` must pass now and after every later task (SC-001, FR-020).
- [X] T003 [P] Update `plan.md`: the at-a-glance line says three problems; a new §2c "Signal trace" with the world (segments, runs, source S, one broken segment, probe answers always true, the free layout), the tools table from `specs/009-signal-trace/contracts/signal-tools.md`, the episode (ends at a submission, the budget or a stop; success when the submitted segment is the broken one; reference and budget rule of research R4/R5) and the levels table of research R4 (T1 16 one run budget 16; T2 64 one run budget 64; T3 64, a tree with 4 pipe ends, each segment feeds at most two, every run ≥ 4, budget 64); §4's "Problems" column: `react`, `mapstate`, `plan_execute`, `reflexion` gain "signal", `hybrid` becomes "dungeon, signal"; §7 gains an M9 row "The signal trace, A1–A4 and A6 on it" with "Done when" from the spec and an empty status; §9 notes the signal trace as the third problem.
- [X] T004 [P] Update `AGENTS.md`: the import rule adds `apl.signal_trace.tools` and `apl.signal_trace.results`; the tools sentence adds "the signal trace's `look`, `probe` and `submit`"; the command list adds `uv run apl signal show --level T2 --seed 1000 --route reference` and `uv run apl run --problem signal --arch react --level all --seeds dev --limit 1`.

**Checkpoint**: the tree is green; dungeon and survey outputs are pinned.

---

## Phase 2: User Story 2 - The signal-trace problem (Priority: P1) 🎯 MVP

**Goal**: a seed and a level always build the same pipe; agents act only through `look`, `probe`, `submit` with the layout free at the start; every pipe has a reference and a budget; A1 plays it from the runner.

**Independent Test**: generate every level and seed and check them; play scripted probe sequences against the tools; play A1 with a scripted model through `play_episode(..., problem="signal")`.

### Tests for User Story 2 ⚠️ (write first, they must fail)

- [X] T005 [P] [US2] Generator tests in `tests/signal_trace/__init__.py` (empty) and `tests/signal_trace/test_generator.py`: for T1–T3 and every dev and test seed, the pipe is identical across two calls; `segments` 16/64/64; every `feeder[k − 1] < k` ("always `< k`"); at most two segments per feeder; the number of pipe ends equals `ends` 1/1/4; `runs` are ordered by `first`, cover 1..N exactly once as contiguous ranges, each run's `feeder` feeds its `first`, and every run is at least `min_run` long ("every run at least 4 segments" on T3); T1 and T2 are the single run `Run(0, 1, N)`; `1 ≤ broken ≤ N`; `reference_is_optimal` true on T1 and T2, false on T3; `budget == max(3 × reference_steps, segments)`, i.e. 16, 64, 64; on T3 `reference_probes ≤ 8`; `generate("T9", 1000)` raises `ValueError` naming T1, T2, T3 (SC-002, research R4).
- [X] T006 [P] [US2] Strategy tests in `tests/signal_trace/test_strategy.py`: `suspects` on a hand-built line of 8 and a hand-built tree of 10 (one junction) for wet and dry answers per research R6 (a wet answer at k removes k's path from S; a dry answer keeps only suspects on it); `informative`; `choose` minimises the larger part and takes the lowest segment on a tie; `worst_case` of a single run of N equals ⌈log₂ N⌉ for N in 1, 2, 3, 5, 8, 16, 17, 64; for every level and every dev and test seed, `reference_run(pipe)` probes at most `reference_probes` times, every answer equals `pipe.wet(k)`, and it ends with a submission of `pipe.broken` (SC-003); a probe-by-probe scan (probe the lowest informative suspect until one suspect is left) averages at least 3 × `reference_probes` probes over every T2 dev and test seed (SC-004).
- [X] T007 [P] [US2] Episode tests in `tests/signal_trace/test_env.py` per data-model.md "LogEntry and Episode" and its transitions: `describe()` is free and equals the `look` data; `look` costs a step; `probe(32)` and `probe("32")` answer `{"segment": 32, "water": pipe.wet(32)}`; `0`, `N + 1`, `"S"`, `1.5`, `True`, `"about 3"` fail with `no_such_segment` and the contract message, cost a step, add an invalid action and are not probes; `submit` of the broken segment ends `submitted` with success, a wrong one ends `submitted` without success; with `max_attempts = 3` a wrong submission returns `{"submitted": k, "correct": false, "attempts_left": 2}`, calls `on_restart` once, clears the answers, sets `attempt` 2 and keeps `steps`; a wrong submission on the last attempt ends the episode; the budget ends it `budget`, and a submission on the last step counts first; `stop()`; any call after the end returns `episode_over` with step `None`; `wasted_probes` counts a repeat, a probe downstream of a known dry segment and one upstream of a known wet segment, and starts again each attempt; `unknown("scan")` says "The tools are look, probe and submit." and costs a step; `outcome().to_dict()` has the data-model fields (`submitted_segment`, `broken_segment`, `segments`, `probes`, `wasted_probes`, `reference_is_optimal`, `attempts` when > 1).
- [X] T008 [P] [US2] Boundary tests in `tests/signal_trace/test_boundary.py` per research R14: for every level and dev seed, 300 random calls (including bad segments) give the fixed envelope and one of the data shapes `{"segments", "runs"}`, `{"segment", "water"}`, `{"submitted"}`; errors are `{"code", "message"}`; the start and `look` results are identical for the same layout with every broken segment (`dataclasses.replace(pipe, broken=k)`); every probe answer equals `pipe.wet(k)`; `AgentTools` exposes only `start`, `look`, `probe`, `submit`.
- [X] T009 [P] [US2] Kit tests in `tests/signal_trace/test_kit.py`: `build_kit` gives `problem == "signal"`, `BASE_PROMPT` and `TOOL_SCHEMAS` verbatim from `specs/009-signal-trace/contracts/signal-tools.md` (`probe` and `submit` take `{"segment": {"type": "integer", ...}}`), `start` the layout result JSON; the tool node answers `look`, `probe`, `submit` (argument `segment`, passed raw), unknown tools with `unknown_tool` (one step) and invalid calls; `add_scout()` returns None; `restart` and `max_attempts` reach the episode; the fingerprint is stable and differs from the dungeon's `ff9afb3b9f66` and the survey's pinned value.
- [X] T010 [P] [US2] Render and CLI tests in `tests/signal_trace/test_render.py` and `tests/signal_trace/test_cli.py` per `specs/009-signal-trace/contracts/cli.md`: `apl signal show --level T1 --seed 1000` prints the header line (segments, runs, broken segment, reference steps with "optimal" or "a reference", budget) and `  S → 1–16`; T3 prints one line per run (`  18 → 19–30`); `--route reference` adds `reference: <k> wet|dry, ... → submit <broken>`; `--html OUT` writes a page containing the SVG with `data-seg` boxes; an unknown level exits 2; a test seed is shown.
- [X] T011 [P] [US2] Add a strategy `play_calls(calls: Sequence[tuple[str, Mapping[str, object]]]) -> Strategy` to `tests/runner/scripted.py` (one tool call per turn, in order, then a text answer), and A1 tests in `tests/arch/test_react_signal.py`: `play_episode(key, ..., problem="signal")` with `react` and `play_calls` built from `reference_run` on T2 seed 1000 gives a completed row with `success`, `steps ≤ optimal_steps`, and the first human message is the start layout JSON; a wrong submission gives `success == False` (FR-021).

### Implementation for User Story 2

- [X] T012 [P] [US2] Create `src/apl/signal_trace/model.py` per data-model.md: `SignalLevel(name, segments, ends, min_run)`, `LEVELS = {"T1": SignalLevel("T1", 16, 1, 16), "T2": SignalLevel("T2", 64, 1, 64), "T3": SignalLevel("T3", 64, 4, 4)}`; `Run(feeder, first, last)` (feeder 0 is S); the frozen `Pipe(level, seed, feeder, runs, broken, reference_probes, reference_is_optimal)` with `segments`, `reference_steps = reference_probes + 1`, `budget = max(3 × reference_steps, segments)`, `upstream(k)` (k and its feeders up to S) and `wet(k) = broken not in upstream(k)`; `Action(tool, args)` as the survey's.
- [X] T013 [P] [US2] Create `src/apl/signal_trace/seeds.py`: `DEV_SEEDS = range(1000, 1010)`, `TEST_SEEDS = range(2000, 2020)`.
- [X] T014 [US2] Create `src/apl/signal_trace/strategy.py` per research R5/R6 and data-model.md "Suspects": `runs_of(feeder)`, `suspects(feeder, answers)`, `informative(feeder, suspects, k)`, `choose(feeder, suspects)`, `worst_case(feeder)`, `reference_run(pipe)` returning the probes with their answers and the submitted segment. Plain functions over the feeder tuple, so the generator can call them before a `Pipe` exists.
- [X] T015 [US2] Create `src/apl/signal_trace/generator.py` per research R3/R4: `generate(level, seed) -> Pipe` with `random.Random(f"signal:{level}:{seed}")`; one run when `ends == 1`; for T3, grow a tree segment by segment (extend a pipe end, or at three seeded moments start a branch from a segment that feeds only one, so each segment feeds at most two and there are exactly 4 pipe ends), renumber it in preorder, and draw again up to `MAX_TRIES = 1000` when a run is shorter than `min_run`; `broken = rng.randint(1, N)`; `reference_probes = worst_case(feeder)`; `reference_is_optimal = len(runs) == 1`; `ValueError` for an unknown level naming T1, T2, T3.
- [X] T016 [P] [US2] Create `src/apl/signal_trace/results.py` per data-model.md "Results": `ErrorCode` (`no_such_segment`, `unknown_tool`, `episode_over`), `EndReason` (`submitted`, `budget`, `stopped`), `LayoutView` (`{"segments": N, "runs": [{"from": "S" | k, "first": a, "last": b}, ...]}`), `ProbeView` (`{"segment": k, "water": bool}`), `Submitted` (with optional `correct`, `attempts_left`, as the survey's), `ToolError`, `ToolResult` with the shared envelope.
- [X] T017 [US2] Create `src/apl/signal_trace/env.py` per data-model.md: `MAX_ATTEMPTS = 3`; `LogEntry` (with `attempt`, and `wasted` shown only when true); `Outcome`; `Episode` with `describe`, `look`, `probe`, `submit`, `unknown`, `restart`, `stop`, `outcome`, `suspects`, `on_step`, `on_restart`, `max_attempts = 1` by default, the segment parsing of research R8 (a JSON integer or a string of digits, 1..N), the contract's error messages, wasted probes per research R7 using `strategy.informative`, and the retry rule of the survey's `_call` (a wrong submission with attempts left returns the retry `Submitted` and restarts); `start_episode(pipe)`.
- [X] T018 [P] [US2] Create `src/apl/signal_trace/tools.py`: `AgentTools` with the free `start` (the layout result) and `look`, `probe`, `submit`, nothing else public; docstring names the allowed imports.
- [X] T019 [P] [US2] Create `src/apl/signal_trace/prompt.py`: `BASE_PROMPT` and `TOOL_SCHEMAS` verbatim from `specs/009-signal-trace/contracts/signal-tools.md` (each description ending " Every call costs one step, including failed calls."; `segment` described as "The number of a segment."); `prompt_fingerprint()` as the survey's.
- [X] T020 [US2] Create `src/apl/signal_trace/kit.py`: `build_kit(episode, model)` on `apl.kit._tool_node`, dispatching `look`, `probe` and `submit` (argument `segment`, passed raw), else `episode.unknown`; `Kit(problem="signal", start=<layout JSON>, add_scout=lambda: None, restart=..., max_attempts=episode.max_attempts, ...)`.
- [X] T021 [US2] Create `src/apl/signal_trace/__init__.py` (exports as `apl/survey/__init__.py` does) and register `"signal"` in `PROBLEMS` in `src/apl/problems.py` per `specs/009-signal-trace/contracts/problems.md`, with lazily imported kit and fingerprint wrappers named as the survey's. Update the one test that lists the problems exactly, `tests/viewer/test_survey.py` (`{"dungeon", "survey"}` → with `"signal"`).
- [X] T022 [P] [US2] Create `src/apl/signal_trace/render_text.py` (the contracts/cli.md text, with `route` adding the reference line) and `src/apl/signal_trace/render_svg.py` (`CELL`, `MARGIN`; S, then each run as a row of boxes `<rect class="seg" data-seg="k">` with their numbers, wrapped at 16 a row, an arrow from the feeder; the broken box gets `class="seg broken"`; `animated` adds the elements the page marks, per contracts/viewer.md).
- [X] T023 [US2] In `src/apl/cli.py`: `apl signal show --level --seed [--route reference] [--html OUT]` beside `apl survey show`; `--problem` choices on `apl run` come from `problems.PROBLEMS`; the help line for the `signal` command group.
- [X] T024 [US2] In `src/apl/runner/registry.py`: `SUPPORTS["react"]` gains `"signal"` (the others join in US1 as each is written).

**Checkpoint**: T005–T011 pass; A1 plays the signal trace from the runner; `apl signal show` works (quickstart step 3); both pins pass.

---

## Phase 3: User Story 1 - Watch an architecture trace a pipe (Priority: P1)

**Goal**: A2, A3, A4 and A6 play the signal trace; in the viewer, pick the signal trace, a level and a dev seed, run an architecture and watch the probes, the water and the suspect band; replay saved episodes.

**Independent Test**: scripted A2, A3, A4 and A6 signal episodes with a checked probe log and option list; the viewer API, events and replay for a scripted signal episode.

### Tests for User Story 1 ⚠️ (write first, they must fail)

- [X] T025 [P] [US1] Probe log tests in `tests/arch/test_probe_log.py` per `specs/009-signal-trace/contracts/architectures.md`: built from a start layout; a successful `probe` adds `(segment, water)`, a failed call changes nothing, a `look` replaces the runs; `render()` prints exactly the contract example for that layout and answers; `known` counts distinct segments probed; `suspects()` equals `apl.signal_trace.strategy.suspects` for random answers on every T3 dev seed (the copy agrees, plan Complexity Tracking).
- [X] T026 [P] [US1] A2 and A3 on the signal trace in `tests/arch/test_signal_archs.py`: `mapstate` with a scripted model on T2: the system message is the signal base prompt plus `PROBE_LOG_INSTRUCTIONS`, and every turn's last message is the probe log's render, matching a log built from the episode after every call; `plan_execute` with a scripted planner (`{"plan": ["find the broken segment"]}`), an executor that plays `reference_run` and a replanner `{"done": true}` succeeds on T1, with the probe log in the executor's prompt; the dungeon and survey tests of both stay as they are.
- [X] T027 [P] [US1] A4 on the signal trace in `tests/arch/test_reflexion_signal.py` per the contract's A4 test: a scripted A4 on T1 submits a wrong segment once, then (after the reflector's note) the right one: the graph's and the episode's attempt both go from 1 to 2, `on_restart` is called exactly once, the steps of both attempts add up in one budget, the reflector's prompt says "The attempt ended: wrong segment."; an actor that only repeats probes it already made fails the attempt after `MAX_STALE` turns, because `known` does not grow.
- [X] T028 [P] [US1] A6 on the signal trace in `tests/arch/test_hybrid_signal.py` per the contract: the first T2 option list is exactly the 8 probes `32, 31, 33, 30, 34, 29, 35, 28` written as `probe 32: leaves 32 if wet, 32 if dry`, ...; once at most 4 suspects remain, `submit k` for each suspect follows the probes; with one suspect the only option is `submit k`; a scripted model answering `1` every turn finds the broken segment on every T2 dev seed within `reference_probes` probes and no wasted probe; answers that name no option are re-asked without a step and end the episode after `MAX_MISSES`; the dungeon A6 tests stay as they are.
- [X] T029 [P] [US1] Viewer tests in `tests/viewer/test_signal.py` per `specs/009-signal-trace/contracts/viewer.md`: `/api/options` has `problems.signal` with levels T1–T3, the dev seeds and the architectures that play it; `/api/signal?level=T2&seed=1000` returns the contract fields; seed 2000 is 403; level `T9` is 400; `POST /api/episodes` with `"problem": "signal"` and `fanout` is 400 with the support message; a scripted `hybrid` episode's `start` event has `problem`, `segments` and `broken`, each `step` frame has `answers`, `suspects`, `probes`, `wasted`, `submitted`, the `end` event a row with `problem == "signal"`; the saved episode replays with the same events and `episode.json` records the problem (US1 1–5, SC-005); the dungeon and survey responses stay as they are.

### Implementation for User Story 1

- [X] T030 [US1] Create `src/apl/arch/probe_log.py` per the contract: `ProbeLog.from_start`, `apply`, `render`, `known`, `suspects` (its own copy of research R6, from the runs and answers only); docstring: built from tool results only, written by the agent at the experimenter's request.
- [X] T031 [US1] In `src/apl/arch/mapstate.py`: `PROBE_LOG_INSTRUCTIONS` verbatim from the contract, and `ProbeLog` with these instructions when `kit.problem == "signal"`, beside the survey branch; `SUPPORTS["mapstate"]` gains `"signal"` in `src/apl/runner/registry.py`.
- [X] T032 [US1] In `src/apl/arch/plan_execute.py`: the probe log and its instructions on `signal`; `SUPPORTS["plan_execute"]` gains `"signal"`.
- [X] T033 [US1] In `src/apl/arch/reflexion.py`: the probe log and its instructions on `signal`; `WRONG_SEGMENT = "wrong segment"` as the failure after a wrong submission on `signal`; the `restart` node skips `kit.restart()` for both `WRONG_TOTAL` and `WRONG_SEGMENT`, since the environment has already restarted; `_size` uses `known` for a `ProbeLog`; `SUPPORTS["reflexion"]` gains `"signal"`.
- [X] T034 [US1] In `src/apl/arch/hybrid.py`: a `kit.problem == "signal"` branch with `SIGNAL_HYBRID_INSTRUCTIONS` verbatim from the contract, a probe log in state, options built from `ProbeLog.suspects()` (the 8 best informative probes by `max(left if wet, left if dry)`, lowest first on a tie, then `submit k` for each suspect at ≤ 4, only `submit k` at 1), the dungeon's answer parsing, re-ask and `MAX_MISSES`, and each option carried out with one tool call through `kit.tool_node`; `SUPPORTS["hybrid"]` becomes `{"dungeon", "signal"}`.
- [X] T035 [US1] Create `src/apl/signal_trace/frames.py`: `snapshot(episode, step, action, result)` with the data-model.md "Frame" keys (`attempt` only when > 1) and `reference_frames(pipe)` from `reference_run`.
- [X] T036 [US1] In `src/apl/viewer/app.py`: `GET /api/signal` with the contract fields; one world parser for every problem (level, seed, test-seed refusal through `problems.get(problem)`) used by `/api/signal`, `/api/survey` and `POST /api/episodes`, with the dungeon and survey responses unchanged; `frame_of` and the episode's world chosen by problem (`episode.pipe` for the signal trace); the `start` event adds `problem`, `segments` and `broken` on `signal`; `episode.json` records the problem for every problem but the dungeon, as today for the survey.
- [X] T037 [US1] In `src/apl/viewer/assets/index.html`: an `isSignal()` branch: load `/api/signal`; draw the SVG; per frame mark boxes wet, dry, suspect or cleared from `answers` and `suspects`, draw the water up to the wet segments, ring the broken box unless "Agent's view" is on; the reference toggle labelled "Reference probes" numbers the reference's probes; the stats panel shows `Pipe <level> seed <seed>`, steps against budget and reference, probes, suspects left, wasted, broken (unless "Agent's view") and `Submitted <k> — right|wrong`; the dungeon and survey views unchanged.
- [X] T038 [US1] Check `src/apl/viewer/assets/index.html` with the headless-browser check used since M3, on a scripted `hybrid` T2 episode: boxes change per step, the shaded band shrinks, the stats end with "Submitted <broken> — right"; then quickstart step 5 by hand with the local model (the experimenter).

**Checkpoint**: T025–T029 pass; the experimenter can watch and replay signal episodes (SC-005).

---

## Phase 4: User Story 3 - Run, continue and report on the signal trace (Priority: P2)

**Goal**: plan, run, continue and report signal runs with `--problem signal`; the report has its own table.

**Independent Test**: plan without `--execute`; play a scripted signal run, interrupt and continue it; check the report against the rows.

### Tests for User Story 3 ⚠️ (write first, they must fail)

- [X] T039 [P] [US3] CLI tests in `tests/runner/test_cli_run.py`: `apl run --problem signal --arch react,mapstate,plan_execute,reflexion,hybrid --level all --seeds dev --limit 1` prints a plan with `problem  signal`, levels T1, T2, T3, 15 episodes, writes nothing and builds no model; `--arch fanout` exits 2 with `fanout does not play the signal problem (it plays: dungeon, survey)` (US3 1–2).
- [X] T040 [P] [US3] Run tests in `tests/runner/test_signal_runs.py` (as `tests/runner/test_plan_execute_runs.py`): a scripted signal run stopped after 2 of 4 episodes continues from `run.json`'s problem and plays only the missing episodes; its rows have `problem == "signal"` and `submitted_segment`, `broken_segment`, `segments`, `probes`, `wasted_probes`, `reference_is_optimal`; an infrastructure-error row still records `broken_segment` and `segments` (US3 3, contracts/results.md).
- [X] T041 [P] [US3] Report tests in `tests/runner/test_report.py` and `tests/runner/test_compare.py`: from hand-written signal rows, the title ends "on the signal trace", the table has the contract header (Right, Probes, Wasted, Efficiency, Budget hit, Tokens, Latency); the spread table has Right and Probes (min–max) with repeats; the comparison uses the dungeon's columns and gives `hybrid` the reference `mapstate` on signal, while on the dungeon it stays `mapstate_routes`; a dungeon and a signal run together are refused (US3 4).

### Implementation for User Story 3

- [X] T042 [US3] In `src/apl/runner/results.py`: `EpisodeRow` gains `submitted_segment`, `broken_segment`, `segments`, `probes`, `wasted_probes` (nullable, None on dungeon and survey rows, accepted as int or null on parse); `completed` fills them from a signal outcome by an attribute check, as `_survey` does; `failed` records `broken_segment` and `segments` from `episode.pipe`.
- [X] T043 [US3] In `src/apl/runner/report.py`: the signal table and spread table per `specs/009-signal-trace/contracts/results.md`, chosen by `first.problem == "signal"`; the dungeon and survey tables unchanged (both pins pass).
- [X] T044 [US3] In `src/apl/runner/compare.py`: a per-problem override of `REFERENCES` (`{"signal": {"hybrid": "mapstate"}}`) used by the comparison; the signal comparison uses the dungeon's header.

**Checkpoint**: T039–T041 pass; quickstart steps 4 and 6 work.

---

## Phase 5: User Story 4 - The fairness rules hold on the signal trace (Priority: P2)

**Goal**: the rule tests cover the third problem.

**Independent Test**: the import test passes with the signal modules allowed and fails for an architecture importing signal internals; two architectures on one signal level record the same prompt, tools and budget.

### Tests for User Story 4 ⚠️ (write first, they must fail)

- [X] T045 [P] [US4] In `tests/dungeon/test_boundary.py`: `ALLOWED` gains `apl.signal_trace.tools` and `apl.signal_trace.results`; a test like `test_the_survey_field_internals_are_forbidden_too` shows that a source importing `apl.signal_trace.generator`, `apl.signal_trace.env`, `apl.signal_trace.strategy` or `apl.signal_trace.model` is rejected (FR-019, US4 2).
- [X] T046 [P] [US4] In `tests/runner/test_run.py`: a scripted signal run with `react` and `mapstate` on T1 records one `prompt_fingerprint` (the signal trace's) in `run.json`, and both rows have the same `budget` and `optimal_steps` (US4 3).

### Implementation for User Story 4

- [X] T047 [US4] In `src/apl/kit.py`: the module docstring names the signal trace's `tools` and `results` among the allowed imports. Fix anything T045–T046 find.

**Checkpoint**: T045–T046 pass.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T048 [P] Update `README.md`: the problems section gains the signal trace (with `apl signal show` and `apl run --problem signal`), the architecture table says which problems each plays, the roadmap gains M9.
- [X] T049 [P] Docstrings of the touched architecture modules (`mapstate.py`, `plan_execute.py`, `reflexion.py`, `hybrid.py`) say the signal version was written by the agent at the experimenter's request (specs/009).
- [X] T050 Mark M9 ✅ in `plan.md` §7 and the at-a-glance line.
- [X] T051 Run steps 1–4 of `specs/009-signal-trace/quickstart.md` and fix what they find.
- [X] T052 Run the four checks: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`.
- [X] T053 `/speckit-converge` for this feature, appending any remaining work to `specs/009-signal-trace/tasks.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 first; T002–T004 after it, in parallel.
- **US2 (Phase 2)**: after Phase 1; blocks every other story.
- **US1 (Phase 3)**: after US2 (it needs the signal episode, kit and strategy).
- **US3 (Phase 4)**: after US2; can run alongside US1 (T040 and T041 use scripted or hand-written rows; T039 needs every name in `SUPPORTS`, so it passes once T031–T034 are done).
- **US4 (Phase 5)**: after US2.
- **Polish (Phase 6)**: after all stories.

### Within Each Story

- Tests first, failing; then model → strategy → generator → results → environment → tools, prompt → kit → registry → CLI.
- US2: T012, T013, T016 → T014 → T015 → T017 → T018, T019 → T020 → T021 → T022 → T023 → T024.
- US1: T030 → T031, T032, T033, T034; T035 → T036 → T037 → T038.
- `tests/runner/test_dungeon_pinned.py` and `tests/runner/test_survey_pinned.py` pass after every task.

### Parallel Opportunities

- T003, T004 (docs).
- T005–T011 (US2 tests); T012, T013, T016, T018, T019, T022 (separate new files).
- T025–T029 (US1 tests); T031–T034 after T030 (separate architecture files, each with its own `SUPPORTS` line: do the `registry.py` edits one after another).
- T039–T041 (US3 tests); T045, T046 (US4 tests).

---

## Parallel Example: User Story 2 tests

```bash
Task: "T005 Generator tests in tests/signal_trace/test_generator.py"
Task: "T006 Strategy tests in tests/signal_trace/test_strategy.py"
Task: "T007 Episode tests in tests/signal_trace/test_env.py"
Task: "T008 Boundary tests in tests/signal_trace/test_boundary.py"
Task: "T009 Kit tests in tests/signal_trace/test_kit.py"
```

## Parallel Example: the architectures on the signal trace

```bash
Task: "T031 ProbeLog on signal in src/apl/arch/mapstate.py"
Task: "T032 ProbeLog on signal in src/apl/arch/plan_execute.py"
Task: "T033 ProbeLog, wrong segment and the restart guard in src/apl/arch/reflexion.py"
Task: "T034 The signal branch in src/apl/arch/hybrid.py"
```

---

## Implementation Strategy

### MVP first (US2)

1. Phase 1: a green tree, the survey pins, the docs.
2. Phase 2: the signal trace, playable by A1 from the runner and printable with `apl signal show`.
3. Stop and check: every pipe is valid, the reference is bisection on single runs and bounded on
   T3, A1 scores right and wrong submissions, both pins pass.

### Then

4. US1: the probe log, A2, A3, A4 and A6, then the viewer. This is where the experimenter starts
   watching.
5. US3: signal runs and reports, for checking what the viewer showed across seeds.
6. US4: the rule tests for the third problem.
7. Polish, the four checks, `/speckit-converge`.

### Notes

- No task starts a paid or local experiment run; quickstart step 5 is the experimenter's, by hand.
- Commits only when the experimenter asks.

---

## Phase 7: Convergence

- [X] T054 In `src/apl/viewer/assets/index.html` `renderSignal`, draw every segment upstream of a wet answer as water (the path from S to each wet probe, read from the SVG's run rows or from a feeder map sent with `/api/signal`), so the water visibly reaches the furthest known wet segments; keep probed boxes marked, per FR-016 (partial)
- [X] T055 Add a test in `tests/signal_trace/test_env.py` that rebuilds `wasted_probes` from a finished episode's `outcome().to_dict()["log"]` alone (probe answers and attempts, with `apl.signal_trace.strategy`), for a scripted run with repeats, implied probes and a restart, and checks it equals the outcome's count, per SC-006 (partial)
- [X] T056 Remove the unused `scout` parameters from `look`, `probe`, `submit` and `unknown` in `src/apl/signal_trace/env.py` (the signal trace has one agent, research R9), per data-model.md "LogEntry and Episode" (unrequested)
