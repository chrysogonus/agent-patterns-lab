---

description: "Task list for M4: first comparison, with orchestrator architectures"
---

# Tasks: First Comparison, with Orchestrator Architectures

**Input**: Design documents from `specs/004-first-comparison/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R16), data-model.md, contracts/
(scouts.md, orchestrators.md, cli.md, results.md, viewer.md), quickstart.md

**Tests**: Requested. The spec's success criteria (SC-001 to SC-007) are test outcomes, so every
phase starts with its tests. Write them first, see them fail, then implement. The exception is T001:
it pins today's behaviour and must pass before and after. The page's JavaScript is checked by hand
(quickstart step 3) and with a headless browser.

**Organization**: Tasks are grouped by user story (US1–US5 in spec.md) so each story can be
implemented and tested on its own.

**Rules for every task**:

- **Types and data**: full type hints (mypy strict). Frozen `@dataclass(slots=True)` unless
  data-model.md says mutable (`Scout` in the environment, `SharedMap`, `ScoutState`).
- **No network in tests**: no test makes a network or model call (Constitution VI). Tests use
  `ScriptedChatModel` and `scripted_factory` from `tests/runner/scripted.py`.
- **Parallel model calls in tests**: scout strategies must decide from the messages they get, never
  from a shared queue, so parallel calls give the same answers in any order (plan Testing).
- **Who writes A7–A9**: the spec assumes the experimenter asks the agent to write
  `src/apl/arch/scouts.py`, `fanout.py`, `rounds.py` and `blackboard.py`. Confirm with the
  experimenter before T023–T026 (task T022). A1, A2, A2r and A6 (`react.py`, `mapstate.py`,
  `mapstate_routes.py`, `hybrid.py`) are not changed.
- **Shared setup**: the base prompt, the tool schemas and `prompt_fingerprint()` stay unchanged.
- **Single-agent files unchanged**: fields for several scouts are written only when they carry
  information (`scout` ≠ 0, `scouts` > 1, frames with more than one scout), research R4.
- **Untrusted text in the page**: model and tool text is inserted with `textContent` only.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: Which user story the task belongs to (US1–US5)

## Path Conventions

Single project: `src/apl/` and `tests/` at the repository root, as in plan.md.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: pin today's single-agent behaviour before anything changes, and add the scripted
strategies the later tests need.

- [X] T001 Write `tests/dungeon/test_golden.py` and its fixtures `tests/dungeon/golden/<arch>-<level>-<seed>.json`
  from the current code, before any other task: for `react`, `mapstate` and `mapstate_routes` with
  `replay_solution(dungeon)`, and `hybrid` answering `"1"`, play every dev dungeon of L1–L3 through
  `play_episode` and store `outcome.to_dict()` and `[f.to_dict() for f in build_frames(...)]`. A
  `--regen` guard (an environment variable, off by default) rewrites them; the test compares byte
  for byte. It must pass now and after every later task (SC-001).
- [X] T002 [P] Add scripted strategies to `tests/runner/scripted.py`: `by_system(mapping)` routes a
  call to a strategy by a marker string in the system message (to tell orchestrator calls from scout
  calls); `by_task(mapping)` routes scout calls by the text after `"Your task: "`; `json_answer(obj)`
  answers `json.dumps(obj)`; `walk_solution(dungeon)` reads the scout's room label and inventory
  from the latest room JSON in its messages (its start JSON or its last successful tool result) and
  answers the next action of the dungeon's solution from that state, or a text answer when the
  state is not on the solution.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: model-call roles and a thread-safe meter (research R5). US2, US3 and US5 need them.

### Tests for Phase 2 ⚠️ (write first, they must fail)

- [X] T003 [P] Extend `tests/runner/test_meter.py`: a call made with
  `config={"metadata": {"role": "orchestrator"}}` counts in `meter.orchestrator_calls` and in
  `llm_calls`; its transcript call has `"role": "orchestrator"`; a call without metadata has no
  `"role"` key (the transcript is byte for byte as before); 4 threads making 25 scripted calls each
  give `llm_calls == 100`, token totals equal to the sum, and a transcript with every distinct
  message once.

### Implementation for Phase 2

- [X] T004 In `src/apl/runner/meter.py`: add `orchestrator_calls: int = 0`; read
  `kwargs.get("metadata", {}).get("role")` in `on_chat_model_start`, keep it with the call's start
  entry, and add `"role"` to the transcript call in `on_llm_end` only when set; guard every counter,
  `_started`, the transcript and the token-cap check with one `threading.Lock`.

**Checkpoint**: T001 and T003 pass; the rest of the suite is unchanged.

---

## Phase 3: User Story 1 - Several scouts in one dungeon (Priority: P1) 🎯 MVP

**Goal**: an episode can have up to 4 scouts with their own positions and inventories, sharing
doors, items and one step budget, while one-scout episodes behave and are recorded as before.

**Independent Test**: play scripted scouts on generated dungeons, check positions, inventories,
doors, the shared step count and the end after every call, and replay the saved log (SC-002); T001
still passes (SC-001).

### Tests for User Story 1 ⚠️ (write first, they must fail)

- [X] T005 [P] [US1] Write `tests/dungeon/test_scouts.py` for contracts/scouts.md: two scouts move
  to different rooms and the episode has used 2 steps (acceptance 1.1); `use` with a key another
  scout holds fails with `not_in_inventory`, costs a step and the door stays locked (1.2); a door
  opened by scout 1 lets scout 2 through (1.3); any scout entering the exit ends the episode with
  `exit`, and `steps` counts every scout's calls (1.4); the shared budget ends the episode with
  `budget` and later calls by any scout return `episode_over` at no step (1.5); `add_scout()`
  returns 1, 2, 3, then `None` (1.6, "`None` at `MAX_SCOUTS` (4)"); a call with an unknown scout
  number raises `ValueError`; `keys_in_rooms` leaves out keys held by any scout; `describe(scout=k)`
  shows scout k's room and inventory; log entries carry `"scout"` only when not 0 and the outcome
  carries `"scouts"` only when above 1.
- [X] T006 [P] [US1] Extend `tests/dungeon/test_frames.py`: `build_frames` with a parallel list of
  scout numbers replays scripted two- and three-scout logs on at least 5 dungeons of different
  levels, with every scout's position and inventory and every opened door matching the live episode
  at every step (SC-002, acceptance 1.8); frames carry `"scouts"` only when there is more than one;
  `parse_route_file` reads `"scout"` from outcome logs and defaults to 0.
- [X] T007 [P] [US1] Extend `tests/runner/test_kit.py`: `kit.add_scout()` returns `Scout(number,
  tool_node, start)` with numbers 1–3 and `None` at the fourth; it costs no step and adds no log
  entry; `Scout.start` equals the JSON of a successful `look` by that scout; the scout's
  `tool_node` acts as that scout; two threads calling different scouts' tool nodes 50 times each
  leave 100 complete log entries and `steps == 100`.
- [X] T008 [P] [US1] Extend `tests/runner/test_results.py`: new rows have `scouts` (1 for a
  single-agent episode) and `orchestrator_calls` (0); a row written before M4 (without both fields)
  parses with both `None`; an infrastructure-error row has `scouts: null`.

### Implementation for User Story 1

- [X] T009 [US1] In `src/apl/dungeon/env.py` (research R1, data-model "Episode"): add the mutable
  `Scout(position, inventory)`, `MAX_SCOUTS = 4`, `Episode.scouts` with scout 0 created in
  `__init__`, `position` and `inventory` as read-write properties of scout 0, `add_scout() -> int |
  None`, a keyword `scout: int = 0` on `describe`, `look`, `move`, `take`, `use` and `unknown`
  (`ValueError` for an unknown number), `keys_in_rooms` over all scouts' inventories, and the exit
  check on the acting scout's position. `LogEntry` gets `scout: int = 0`, in `to_dict` only when
  not 0; `Outcome` gets `scouts: int` (distinct scouts in the log), in `to_dict` only when above 1.
- [X] T010 [US1] In `src/apl/dungeon/frames.py` (research R4): add `ScoutView(position,
  inventory)` and `Frame.scouts: tuple[ScoutView, ...]` (`to_dict` writes `"scouts"` only when
  there is more than one); `snapshot` fills it; `build_frames(..., scouts: Sequence[int] | None =
  None)` creates scouts with `add_scout()` as numbers first appear and passes `scout=` to `call`;
  `RouteFile` and `parse_route_file` carry the scout numbers.
- [X] T011 [US1] In `src/apl/kit.py` (research R2, contracts/scouts.md): add the frozen
  `Scout(number, tool_node, start)`, `Kit.add_scout`, and build every tool node (scout 0's and each
  added scout's) from one function that takes the scout number and holds one shared
  `threading.Lock` around each call. Update every place that constructs a `Kit` directly (search
  `Kit(` in `src/` and `tests/`).
- [X] T012 [US1] In `src/apl/runner/results.py` and `src/apl/runner/episode.py`: add `scouts: int |
  None` and `orchestrator_calls: int | None` to `EpisodeRow`, fill them in `completed` (from
  `outcome.scouts` and `meter.orchestrator_calls`) and `failed` (`None`, and the meter's count),
  and default both to `None` in `parse` as `output_limit_hits` is.
- [X] T013 [US1] Run the whole suite: T001's golden files must still match byte for byte, and the
  M2/M3 tests must pass unchanged.

**Checkpoint**: US1 is complete; single-agent architectures are provably unaffected.

---

## Phase 4: User Story 2 - Three orchestrator architectures (Priority: P2)

**Goal**: `fanout`, `rounds` and `blackboard` play the dungeon with several scouts, built on one
shared scout and one lockstep turn (contracts/orchestrators.md).

**Independent Test**: play each with scripted orchestrator and scout answers on dev dungeons of
every level; check scouts, model input and the merged map (SC-003).

### Tests for User Story 2 ⚠️ (write first, they must fail)

- [X] T014 [P] [US2] Extend `tests/arch/oracle.py` with `expected_shared_map(dungeon, frames,
  upto)`: the union of what all scouts saw, with every scout's room and inventory, built from the
  layout and the frames.
- [X] T015 [P] [US2] Write `tests/arch/test_scouts_shared.py`: `SharedMap.apply` after every call
  of scripted multi-scout logs equals `expected_shared_map` (acceptance 2.2); a newer observation
  replaces an older one; `DungeonMap.render` with several scouts lists each scout's room and
  inventory, and with claims a `Claims:` line; the `act` node applies replies in scout-number order
  whatever order they arrive in; a task ends when the scout answers without a tool call or its
  `steps_left` reaches 0; the orchestrator-answer reader accepts JSON inside prose, and rejects bad
  JSON, a wrong shape, a scout outside 0–3 and `steps < 1` with a reason.
- [X] T016 [P] [US2] Write `tests/arch/test_fanout.py`: with `by_system` (orchestrator answer: one
  scout following `walk_solution`, two resting) every dev dungeon of each level succeeds
  (acceptance 2.1); exactly one call has role `orchestrator` (2.3); no scout's input contains
  another scout's tool results (2.3); an invalid answer is asked again at no step and 3 in a row end
  the episode as stopped with 0 steps; asking for 5 scouts is invalid; two plays give identical
  logs.
- [X] T017 [P] [US2] Write `tests/arch/test_rounds.py`: a scripted supervisor (round 1: scout 0
  follows the solution for 3 steps; later rounds: continue) succeeds on a dev dungeon of each level
  (2.1); every orchestrator input contains the merged map and the steps used (2.4); `{"done": true}`
  ends the episode as stopped; a task for a fourth new scout when `add_scout()` returns `None` is
  dropped and the next input says so; scouts see the merged map from the start of their round.
- [X] T018 [P] [US2] Write `tests/arch/test_blackboard.py`: 4 scouts are created; with one scout
  following the solution and three answering `claim: <room> <direction>` texts, each level's dev
  dungeon succeeds (2.1); every scout input contains every scout's room and the claims line (2.5);
  no call has role `orchestrator`; two plays give identical logs.
- [X] T019 [P] [US2] Check `tests/dungeon/test_boundary.py` covers the new modules (it walks
  `src/apl/arch/`); add an assertion that `fanout`, `rounds` and `blackboard` are found and use
  `kit.model` (acceptance 2.6).
- [X] T020 [P] [US2] Update the "registered: ..." expectations in `tests/runner/test_cli_run.py`
  and `tests/runner/test_spec.py` to include `blackboard`, `fanout` and `rounds` (alphabetical).

### Implementation for User Story 2

- [X] T021 [US2] Render several scouts and claims (research R8). Done in `SharedMap.render` in
  `src/apl/arch/scouts.py` instead of `src/apl/arch/dungeon_map.py`, so A2's rendering is untouched:
  a scout sees its own "You are in" line plus "Other scouts: scout 2 is in k7 and holds nothing; …",
  the orchestrator sees "Scouts: …" instead, and claims add "Claims: scout 1 → k7 north; …".
- [X] T022 [US2] Confirm with the experimenter that the agent writes A7–A9 (Rules above); record
  the answer in `specs/004-first-comparison/spec.md` Clarifications.
- [X] T023 [US2] Write `src/apl/arch/scouts.py` (research R3, R7–R9; data-model "SharedMap",
  "ScoutState"): `SCOUT_INSTRUCTIONS` (explains the task line and other scouts, no strategy);
  `SharedMap` with `apply`; `ScoutState`; `scout_messages(kit, state, rendered_map)` building the
  model input of contracts/orchestrators.md; a `scout` node calling
  `kit.model.bind_tools(kit.tools)` with `config={"metadata": {"role": f"scout {n}"}}` and returning
  `{"replies": [(n, reply)]}`; an `act` node applying the replies in scout order through each scout's
  tool node and updating the maps, `steps_left`, `done` and `last_turn`; `read_answer(text, shape)`
  returning the parsed JSON or the reason it is invalid.
- [X] T024 [US2] Write `src/apl/arch/fanout.py` (A7): one orchestrator call (role `orchestrator`,
  `FANOUT_INSTRUCTIONS` on the base prompt) answering `{"scouts": [{"task", "steps"}]}` with 1–4
  entries, re-asked up to 3 times; scout 0 is the first entry and the others come from
  `kit.add_scout()`; lockstep turns with `Send` until every scout is done; each scout sees only its
  own map.
- [X] T025 [US2] Write `src/apl/arch/rounds.py` (A8): `plan` node (role `orchestrator`,
  `ROUNDS_INSTRUCTIONS`) with the merged map, every scout's room and inventory, the steps used and
  the last round's results; answer `{"tasks": [...]}` or `{"done": true}`, re-asked up to 3 times;
  new scout numbers created with `kit.add_scout()` (a `None` drops the task and is noted); scouts see
  the merged map from the round's start plus their own results; back to `plan` when every tasked
  scout is done.
- [X] T026 [US2] Write `src/apl/arch/blackboard.py` (A9): create scouts 1–3, give all four the fixed
  task of contracts/orchestrators.md, run lockstep turns on the live board with claims (a line
  `claim: <room> <direction>` in a reply replaces that scout's claim) until every scout is done.
- [X] T027 [US2] Register `fanout`, `rounds` and `blackboard` in `src/apl/runner/registry.py`.

**Checkpoint**: US2 complete; the three orchestrators play with scripted answers and appear in
`apl run --arch` and the viewer's list.

---

## Phase 5: User Story 3 - Watch several scouts in the viewer (Priority: P3)

**Goal**: one marker and trail per scout, turns labelled by role, replays of multi-scout episodes
(contracts/viewer.md).

**Independent Test**: a scripted two-scout episode in the viewer, live and replayed; positions,
trails and labels at several steps.

### Tests for User Story 3 ⚠️ (write first, they must fail)

- [X] T028 [P] [US3] Extend `tests/viewer/test_events.py`: with two overlapping scripted calls,
  each `turn` event has the call number of its own `thinking` event (matched by run id); events carry
  `role` (`null` for single-agent architectures); `new_input` is computed against the previous call
  of the same role; the event stream of an A2 episode is unchanged apart from `"role": null`.
- [X] T029 [P] [US3] Extend `tests/viewer/test_app.py`: a scripted `fanout` episode's `step` events
  carry `scout` and the call of that scout's latest turn, and frames carry `scouts`; the saved episode
  replays with every scout's position at every step (acceptance 3.3).

### Implementation for User Story 3

- [X] T030 [US3] In `src/apl/viewer/events.py` (research R6): `ViewerCallbacks` maps `run_id` to
  the call number, reads the role from `metadata`, keeps the previous input per role, adds `role` to
  `thinking` and `turn`, and records the latest call per role on the session.
- [X] T031 [US3] In `src/apl/viewer/app.py`: `on_step` adds `"scout": entry.scout` and uses the latest
  call of role `scout <n>` when the session has one; frames come from `snapshot`, so they carry
  `scouts`.
- [X] T032 [US3] In `src/apl/viewer/assets/index.html`: four scout colors as theme tokens (light and
  dark), one marker and one trail per scout created as scouts appear in frames, the M3 room-by-room
  walking applied per scout, turn headings `Model call N · <role>`, "Agent's view" over all scouts'
  rooms, and slider, Play and replay drawing every scout. Insert text with `textContent` only.
- [X] T033 [US3] Check the page by hand (quickstart step 3) and with the headless-browser check from
  the M3 walking fix, adapted so it samples every scout marker and plays `blackboard` with a scripted
  model; no marker leaves the grid lines.

**Checkpoint**: US3 complete; every architecture can be watched.

---

## Phase 6: User Story 4 - Run the comparison as one fair, continuable run (Priority: P4)

**Goal**: interleaved order, a code line in the dry run, `apl continue`, and the stop after 3
provider failures (contracts/cli.md).

**Independent Test**: a scripted seven-architecture run interrupted twice and continued ends with all
21 episodes exactly once, rows equal to an uninterrupted run (SC-004).

### Tests for User Story 4 ⚠️ (write first, they must fail)

- [X] T034 [P] [US4] Extend `tests/runner/test_spec.py`: `episodes()` yields level → seed → repeat →
  architecture; a one-architecture run's order is unchanged; the seven-architecture M4 spec with
  `--limit 1` has 21 episodes.
- [X] T035 [P] [US4] Write `tests/runner/test_continue.py`: a scripted run of the seven
  architectures on L1–L3, seed 1000, interrupted with `KeyboardInterrupt` after 5 and after 12
  episodes and continued each time, ends complete with 21 rows, one per key, equal to an
  uninterrupted run's rows apart from `run_id` and `latency_s` (SC-004); each refusal of
  contracts/cli.md (setting, package version, commit, dirty now, started dirty, unknown architecture)
  is reported with its message and writes nothing; several refusals are printed together; a complete
  run exits 0 with "already complete"; a cut-off last line is noted by the dry run and removed only
  by `--execute` after the checks pass; infrastructure-error rows are not played again. Use a fake
  `code_version` so the tests do not depend on the repository's git state.
- [X] T036 [P] [US4] Extend `tests/runner/test_run.py`: 3 infrastructure-error episodes in a row stop
  the run with exit code 4 and an incomplete `run.json`; 2 in a row followed by a success do not.
- [X] T037 [P] [US4] Extend `tests/runner/test_cli_run.py`: the dry run shows `code <short commit>`,
  `(uncommitted changes: this run cannot be continued)` when dirty, and `unknown` outside git; the
  calls line reads `model calls (est.)`; `apl continue` dry-run output as in contracts/cli.md; after
  exit codes 3, 4 and 130 the `continue with:` line is printed.

### Implementation for User Story 4

- [X] T038 [US4] In `src/apl/runner/spec.py`: reorder `episodes()` (research R10) and label the calls
  bound `model calls (est.)` in `format_plan`; add the `code` line.
- [X] T039 [US4] In `src/apl/runner/run.py` (research R11–R13; data-model "Continue plan"): move the
  episode loop of `execute` into a shared `_play(path, record, keys, ...)` that also stops after 3
  infrastructure errors in a row (exit code 4); add `plan_continue(run_dir, settings, known) ->
  ContinuePlan` with the refusals and `continue_run(plan, ...) -> RunOutcome`, which removes a cut-off
  last row, plays `left` into the same folder, and completes the record.
- [X] T040 [US4] In `src/apl/cli.py`: add `apl continue RUN_DIR [--execute]` (dry run, refusals with
  exit code 2 and the `apl: cannot continue <run-id>:` prefix, "already complete" with exit code 0,
  execute with progress `[i/total]` numbered within the whole run and `report.md` rewritten);
  print the `continue with:` line after exit codes 3, 4 and 130 of `apl run` and `apl continue`.
- [X] T041 [P] [US4] Add `apl continue` to the command lists in `AGENTS.md` and `README.md`.

**Checkpoint**: US4 complete; the M4 run can be planned, interrupted and continued.

---

## Phase 7: User Story 5 - Compare the architectures and write down what it shows (Priority: P5)

**Goal**: the report's "Comparison" section (contracts/results.md), the M4 run, and the conclusion.

**Independent Test**: build the report from hand-written rows and check every figure by hand
(SC-005); check every number of the conclusion against the cited report (SC-007).

### Tests for User Story 5 ⚠️ (write first, they must fail)

- [X] T042 [P] [US5] Write `tests/runner/test_compare.py`: hand-written rows of the seven
  architectures on three levels give, per level, every cell of contracts/results.md's table (success,
  efficiency, steps, tokens, calls orchestrator / scouts, latency, scouts, Δ success in pp,
  Δ efficiency, reference) as calculated by hand (SC-005); a missing reference and rows written
  before M4 show `—`; the rows in any order give the same text byte for byte; the section is absent
  for one architecture and the M2 report of `tests/runner/test_report.py` is unchanged.

### Implementation for User Story 5

- [X] T043 [US5] Write `src/apl/runner/compare.py` (research R14): `REFERENCES` as in
  contracts/results.md and `render_comparison(runs, rows) -> list[str]` producing the section,
  including the intro line with the seeds and repeats covered and the development or test notice.
- [X] T044 [US5] In `src/apl/runner/report.py`: append `render_comparison(...)` after the main table
  when the completed rows cover two or more architectures.
- [ ] T045 [US5] Plan the M4 run (quickstart step 4) on a clean committed tree with
  `APL_MODEL=openai:gpt-6-luna`: check 21 episodes, the seven architectures, seed 1000, "development
  only", a clean `code` line and the cost bound; show the bound to the experimenter before going on.
- [ ] T046 [US5] The experimenter runs the M4 run with `--execute` (quickstart step 6), continuing it
  with the printed `continue with:` line if it stops. Not an agent task: it spends money.
- [ ] T047 [US5] Draft `docs/findings/m4-first-comparison.md` from the run's `report.md` (research
  R15): the questions, the setup line, the comparison tables, what each question's rows suggest per
  level, the limitation that one episode per cell cannot separate a difference from luck, the reason
  for 21 episodes, and next steps; link it from `README.md`. The experimenter checks and edits it
  (SC-007: rerun `apl report` on the run and compare every quoted number).

**Checkpoint**: US5 complete; M4 is done when the conclusion is checked.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T048 [P] Update `plan.md`: §4 adds A7–A9 (fan-out, supervisor in rounds, blackboard) and the
  several-scout rule; §7's M4 row says seven architectures, one dev seed per level, `gpt-6-luna`, and
  M5+ lists A3–A5.
- [X] T049 [P] Update `README.md`: the architecture table gains A7–A9, the status line names M4.
- [X] T050 Run quickstart steps 1–5 and fix what they find.
- [X] T051 Run the four checks: `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .`,
  `uv run mypy`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 first of all, before any source change; T002 any time before Phase 4.
- **Foundational (Phase 2)**: after T001; blocks US1's row fields (T012), US2 and US3.
- **US1 (Phase 3)**: after Phase 2; blocks US2, US3 and US4's scripted seven-architecture run.
- **US2 (Phase 4)**: after US1; T022 (confirmation) before T023–T026.
- **US3 (Phase 5)**: after US1; its multi-scout tests need one orchestrator (T024) or scripted
  scouts through the kit.
- **US4 (Phase 6)**: T034, T036–T041 need only Phase 2; T035's seven-architecture run needs US2.
- **US5 (Phase 7)**: T042–T044 need only the row fields (T012); T045–T047 need everything before.
- **Polish (Phase 8)**: last.

### Within Each Story

- Tests first, failing; then data and environment; then architectures; then the CLI and page.
- Run the four checks at each checkpoint.

### Parallel Opportunities

- T002 beside Phase 2.
- In US1: T005–T008 together; then T009 → T010, and T011, T012 beside them.
- In US2: T014–T020 together; T024–T026 together once T023 is done.
- US3 and US4 (except T035) can proceed side by side after US1; US5's T042–T044 beside both.
- T048 and T049 together.

---

## Parallel Example: User Story 1 tests

```text
Task: "T005 Write tests/dungeon/test_scouts.py for contracts/scouts.md"
Task: "T006 Extend tests/dungeon/test_frames.py for several scouts"
Task: "T007 Extend tests/runner/test_kit.py for add_scout and the shared lock"
Task: "T008 Extend tests/runner/test_results.py for scouts and orchestrator_calls"
```

## Parallel Example: the three orchestrators

```text
Task: "T024 Write src/apl/arch/fanout.py (A7)"
Task: "T025 Write src/apl/arch/rounds.py (A8)"
Task: "T026 Write src/apl/arch/blackboard.py (A9)"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 (pin today's behaviour) and Phase 2 (roles, thread-safe meter).
2. Phase 3: several scouts in the environment and the kit.
3. Stop and validate: T001's golden files still match; scripted scouts replay exactly.

### Incremental Delivery

1. US1: the world supports scouts; nothing visible changes.
2. US2: the three orchestrators play with scripted answers → `apl run --arch fanout` works.
3. US3: they can be watched in the viewer (quickstart step 3, free on the local model).
4. US4: the run can be planned, interrupted and continued.
5. US5: the comparison section, the paid run, the conclusion → M4 done.

---

## Notes

- [P] tasks touch different files and depend on no unfinished task.
- Commit after each checkpoint; the M4 run itself needs a clean tree (research R12).
- `/speckit-converge` follows `/speckit-implement`, as for every milestone.
