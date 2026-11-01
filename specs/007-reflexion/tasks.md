---

description: "Task list for 007: A4 Reflexion"
---

# Tasks: A4 Reflexion

**Input**: Design documents from `specs/007-reflexion/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R10), data-model.md, contracts/, quickstart.md

**Tests**: Yes (SC-001–SC-008, research R10). Each phase writes its tests first; they must fail
before the implementation. Scripted model only.

**Organization**: Setup (constitution, baseline) → Foundational (attempts in the problems, kit and
runner, which every story needs) → US1 (A4 plays both problems) → US2 (viewer) → US3 (runs and
reports) → Polish.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Amend `.specify/memory/constitution.md` to 2.1.0 with `/speckit-constitution`: add the "Attempts" bullet of research R9 to "Experiment Setup", update the version line (2.1.0, last amended 2026-11-01) and the sync report. The experimenter reviews the text afterwards.
- [X] T002 Run the four checks on the tree as it is; all must pass before T003.

---

## Phase 2: Foundational (attempts below the architecture)

### Tests (write first, must fail)

- [X] T003 [P] `tests/dungeon/test_attempts.py`: with `max_attempts = 3`, after moves, a take and a use, `restart()` returns True and the episode's `describe()`, `keys_in_rooms`, `opened`, scouts equal a fresh episode's, `steps`/`invalid_actions` unchanged, `attempt == 2`, `on_restart` called; refused (False, nothing changes) at `attempt == 3`, after the end, and with the default `max_attempts = 1`; log entries after a restart have `"attempt": 2` in `to_dict`, earlier ones no `attempt` key; `outcome().to_dict()` has `"attempts": 2`, and no `attempts` key for a one-attempt episode (contracts/attempts.md, SC-002, SC-003).
- [X] T004 [P] `tests/survey/test_attempts.py`: the same for the field (`scouts`, `seen` reset, `seen_ever` kept, `cells_seen` = `len(seen_ever)`); submit table of data-model.md: with `max_attempts = 3` a wrong total gives data `{"submitted": N, "correct": false, "attempts_left": 2}`, the episode goes on, the field is restarted, `attempt == 2`, the result text contains neither the true total nor the difference (SC-004); a right total ends it; a wrong total in attempt 3 ends it with `{"submitted": N}`; with `max_attempts = 1` a wrong total ends it as before.
- [X] T005 [P] Replay test in `tests/dungeon/test_attempts.py`: play an episode with a restart in the middle and one at the very end, write `outcome().to_dict()`, and check that `parse_route_file(...).frames(dungeon)` rebuilds the same positions per step, frames after the restart carry `attempt == 2`, and the end reason matches (SC-005).
- [X] T006 [P] Kit and runner tests in `tests/runner/test_attempts_runner.py`: `kit.restart()` and `kit.max_attempts` for a retrying name (monkeypatch `registry.RETRYING` with a test double architecture that restarts once and then plays the solution) on both problems: the row's `attempts == 2`, `steps` add up; for a non-retrying name `kit.restart()` is False, `kit.max_attempts == 1`, `row.attempts is None`; `EpisodeRow.parse` of an old row (no `attempts`) gives None; the report has an `## Attempts` section only when some row has attempts > 1 (format in contracts/attempts.md); the meter counts `reflector` as a lead call.

### Implementation

- [X] T007 Dungeon attempts in `src/apl/dungeon/env.py` and `src/apl/dungeon/frames.py` per data-model.md and R1, R4: `MAX_ATTEMPTS = 3`; `Episode.attempt`, `max_attempts`, `on_restart`, `restart()`; `LogEntry.attempt` (written only when > 1); `Outcome.attempts` (written only when > 1); `Frame.attempt` (written only when > 1); `build_frames` and `RouteFile`/`parse_route_file` replay restarts (validate `attempt` as an int from 1 to `MAX_ATTEMPTS`).
- [X] T008 Survey attempts in `src/apl/survey/env.py`, `src/apl/survey/results.py` (`Submitted.correct`, `Submitted.attempts_left`, written only when set) and `src/apl/survey/frames.py` per data-model.md, R1, R3, R4.
- [X] T009 Kit and runner: `Kit.restart` (default always False) and `Kit.max_attempts` (default 1) in `src/apl/kit.py`, set in both `build_kit`s (restart under the lock); `RETRYING` in `src/apl/runner/registry.py`; `play_episode` in `src/apl/runner/episode.py` sets `max_attempts` before building the kit; `EpisodeRow.attempts` in `src/apl/runner/results.py` (nullable, parsed with default None, filled from `outcome.attempts` for retrying architectures); the `## Attempts` section in `src/apl/runner/report.py`; `"reflector"` in `LEAD_ROLES` in `src/apl/runner/meter.py`.

**Checkpoint**: T003–T006 pass; every existing test passes unchanged, including the pinned outputs.

---

## Phase 3: User Story 1 - Retries with notes on both problems (Priority: P1) 🎯 MVP

### Tests (write first, must fail)

- [X] T010 [US1] Register `reflexion` (`ARCHITECTURES`, `SUPPORTS` both problems, `RETRYING`) in `src/apl/runner/registry.py`, and update the two tests that list the registered names (`tests/runner/test_cli_run.py`, `tests/runner/test_spec.py`).
- [X] T011 [US1] `tests/arch/test_reflexion.py` (routing by system message: `REFLECTOR_INSTRUCTIONS` → reflector strategy; else actor):
  - L1 1000, L2 1001, L3 1002 and S1–S3 seed 1000: the actor gives up at once in attempt 1 (an `AIMessage` without tool call, when the human message says `Attempt 1 of 3.`), the reflector answers "Try harder.", attempt 2 plays `walk_solution` / `walk_field(..., total=true_total)`; success, `row.attempts == 2`, `row.steps` equals a scripted `mapstate` episode's, roles `actor (attempt 1)`, `reflector`, `actor (attempt 2)` … (SC-001, acceptance 1.1, 1.3);
  - attempt 2's actor input contains `Notes from earlier attempts:\n1. Try harder.` and its first map shows only the start;
  - survey S1: attempt 1 walks and submits a wrong total; the reflector input says `The attempt ended: wrong total.`; attempt 2 submits the right total; success, `attempts == 2`, `submitted_total` right (acceptance 1.2);
  - three give-ups: `end_reason == "stopped"`, `attempts == 3`, two reflector calls (acceptance 1.4, SC-003);
  - three wrong totals on S1: the episode ends `submitted` with the third total, not a success;
  - bumping a wall forever: after `MAX_STALE` (12) turns attempt 1 ends with `nothing new for 12 turns`;
  - the budget runs out in attempt 2: `budget_hit` (acceptance 1.5);
  - an empty reflector reply adds no note;
  - every system message starts with the problem's base prompt; the actor's equals base + "\n\n" + A2's map instructions + " " + `ACTOR_INSTRUCTIONS` with 3 filled in; the budget equals `mapstate`'s (SC-006).

### Implementation

- [X] T012 [US1] Write A4 in `src/apl/arch/reflexion.py` per contracts/reflexion.md, data-model.md (`ReflexionState`, transitions), research R5–R6, in the style of `src/apl/arch/plan_execute.py` (docstring naming specs/007, "Written by the agent at the experimenter's request"). T011 passes.
- [X] T013 [US1] `"reflexion": "mapstate"` in `REFERENCES` in `src/apl/runner/compare.py`.

**Checkpoint**: A4 plays both problems in scripted episodes; the four checks pass.

---

## Phase 4: User Story 2 - Watch A4 try again (Priority: P1)

- [X] T014 [US2] `tests/viewer/test_reflexion.py`: the options list `reflexion` on both problems; a scripted two-attempt episode on L1 and on S1 through the viewer emits, in order, actor turns, a `reflector` turn, a `restart` event with `attempt == 2` and a frame at the start position, then steps whose frames carry `attempt == 2`; the saved episode replays with the same events (acceptance 2.1–2.3).
- [X] T015 [US2] Emit the `restart` event from `episode.on_restart` in `src/apl/viewer/app.py` (frame via the problem's `snapshot`, step index = frames so far). T014 passes.
- [X] T016 [US2] Page in `src/apl/viewer/assets/index.html` per contracts/attempts.md "Viewer": a `restart` listener pushes the frame and adds the "Attempt n starts" card; `render` draws trail and fog from the current attempt's frames and earlier attempts as `#trail-past` (dashed, faded, CSS next to `#trail`); stats show "Attempt n / 3". Check `tests/viewer/test_page.py` still passes.

---

## Phase 5: User Story 3 - A4 in runs, reports and the comparison (Priority: P2)

- [X] T017 [US3] (passed on first run: the behavior was already built in Phase 2) `tests/runner/test_reflexion_runs.py` (as `tests/runner/test_plan_execute_runs.py`): a dry run lists `reflexion` on both problems and builds no model; an interrupted run with `mapstate` and `reflexion` continues; a scripted A4 run reported together with a scripted run of the earlier architectures shows `reflexion` with reference `mapstate`, and an `## Attempts` section; old rows and runs load as before (acceptance 3.1–3.4, SC-007).

---

## Phase 6: Polish

- [X] T018 [P] Update `plan.md` (at a glance; §4 A4 row "Problems" → "dungeon, survey"; §7 M7 ✅ for A4, A5 next) and `README.md` (architecture table, roadmap).
- [X] T019 [P] Update `AGENTS.md` only if a command changed (none expected); otherwise leave it.
- [X] T020 Run quickstart steps 1–2; re-read `src/apl/arch/reflexion.py` and the env changes against constitution I–III and 2.1.0's attempt rule; leave A4 for the experimenter's review.

---

## Dependencies & Execution Order

- T001 → T002 → T003–T006 → T007–T009 → T010–T013 → T014–T016 and T017 (either order) → T018–T020.
- T007 before T008's frames (same patterns); T009 needs T007–T008.

## Implementation Strategy

1. **MVP**: T001–T013, A4 plays both problems.
2. **Watchable**: T014–T016.
3. **Comparable**: T017.
4. **Docs and review**: T018–T020.

No task starts a paid or local experiment run.

## Phase 7: Convergence

- [X] T021 Add `"attempts": episode.max_attempts` to the viewer's `start` event when it is above 1 (`src/apl/viewer/app.py`), set `S.attempts` from it in `src/apl/viewer/assets/index.html`, and assert it in `tests/viewer/test_reflexion.py`, so the panel shows "Attempt 1 / 3" from the first frame per FR-018 (partial)
