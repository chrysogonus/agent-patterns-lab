---

description: "Task list for 008: A5 Supervisor"
---

# Tasks: A5 Supervisor

**Input**: Design documents from `specs/008-supervisor/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R9), data-model.md, contracts/, quickstart.md

**Tests**: Yes (SC-001–SC-008, research R9). Each phase writes its tests first; they must fail
before the implementation. Scripted model only.

**Organization**: Setup → US1 (A5 plays the dungeon) → US2 (viewer) → US3 (runs and reports) →
Polish. No foundational phase: nothing below the architecture changes.

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Run the four checks on the tree as it is; all must pass before T002.

---

## Phase 2: User Story 1 - A5 plays the dungeon under the fairness rules (Priority: P1) 🎯 MVP

### Tests (write first, must fail)

- [X] T002 [US1] Register `supervisor` (`ARCHITECTURES`, `SUPPORTS` = dungeon only) in `src/apl/runner/registry.py`, and update the two tests that list the registered names (`tests/runner/test_cli_run.py`, `tests/runner/test_spec.py`).
- [X] T003 [US1] `tests/arch/test_supervisor.py` (routing by system message: `SUPERVISOR_INSTRUCTIONS`, `NAVIGATOR_INSTRUCTIONS`, `INVENTORY_INSTRUCTIONS`), with a scripted split walk built on `walk_solution` (supervisor hands to the helper owning the next solution action; each helper answers with text where the next action is not its own):
  - L1 1000, L2 1001, L3 1002: success, `steps` and `budget` equal a scripted `mapstate` episode's; roles start `supervisor`, `navigator (task 1)`; on L3 an `inventory (task n)` role appears; `orchestrator_calls` equals the number of `supervisor` roles (SC-001, SC-003, US1 1–2);
  - a navigator reply with `take` and `move` runs only the move: one step, the take answered `Not made: take is the inventory helper's tool. It cost no step.`; a navigator that only calls `take` ends within the limits with `end_reason == "stopped"` (US1 3, SC-004);
  - `{"done": true}` first → `stopped`, no step; `MAX_MISSES` unusable answers (no JSON, `"to": "cook"`, empty task) → `stopped` after exactly that many supervisor calls, the second call's input contains the note; `MAX_IDLE` handoffs whose helper answers at once → `stopped`; a navigator bumping a wall forever → after `MAX_TURNS` turns the supervisor input contains `unfinished after 20 turns`; the budget running out in a task → `budget_hit` with no supervisor call after it (US1 4, edge cases);
  - every system message starts with `BASE_PROMPT`; the navigator's equals base + "\n\n" + `MAP_INSTRUCTIONS` + " " + `NAVIGATOR_INSTRUCTIONS`, the inventory's likewise; the supervisor's last human message ends with the map; the helper's first head message contains the start result and `Your task:`; the tools offered to each helper are exactly its two schemas, equal to the kit's (SC-002);
  - `registry.plays("supervisor", "survey")` is False (US3 2).

### Implementation

- [X] T004 [US1] Write A5 in `src/apl/arch/supervisor.py` per contracts/supervisor.md, data-model.md (`SupervisorState`, `Report`, transitions) and research R1–R6, in the style of `src/apl/arch/plan_execute.py` (docstring naming specs/008, "Written by the agent at the experimenter's request"). T003 passes.
- [X] T005 [US1] `"supervisor"` in `LEAD_ROLES` in `src/apl/runner/meter.py` (with its comment) and `"supervisor": "mapstate"` in `REFERENCES` in `src/apl/runner/compare.py`.

**Checkpoint**: A5 plays the dungeon in scripted episodes; the four checks pass.

---

## Phase 3: User Story 2 - Watch A5 hand off (Priority: P1)

- [X] T006 [US2] `tests/viewer/test_supervisor.py` (as `tests/viewer/test_plan_execute.py`): the options list `supervisor` for the dungeon and not for the survey field; a scripted L3 1002 episode through the viewer emits turns whose roles are, in order, `supervisor`, `navigator (task 1)` … with an `inventory (task n)`, steps whose frames end at the exit, and a successful row; the saved episode replays with the same events (US2 1–4, SC-005). No viewer code change expected (research R8).

---

## Phase 4: User Story 3 - A5 in runs, reports and the comparison (Priority: P2)

- [X] T007 [US3] `tests/runner/test_supervisor_runs.py` (as `tests/runner/test_plan_execute_runs.py`, dungeon only): a dry run lists `supervisor` and builds no model; a survey dry run is refused; an interrupted run with `mapstate` and `supervisor` continues; a scripted A5 run reported together with a scripted run of the other dungeon architectures shows `supervisor` with reference `mapstate` (US3 1–4, SC-006, SC-007).

---

## Phase 5: Polish

- [X] T008 [P] Update `plan.md` (at a glance; §4 A5 row "Problems" → "dungeon", LangGraph features; §7 M8 ✅) and `README.md` (architecture table, roadmap).
- [X] T009 [P] Update `AGENTS.md` only if a command changed (none expected); otherwise leave it. (No command changed; left as is.)
- [X] T010 Run quickstart steps 1–2; re-read `src/apl/arch/supervisor.py` against constitution I–III; leave A5 for the experimenter's review.

---

## Dependencies & Execution Order

- T001 → T002–T003 → T004–T005 → T006 and T007 (either order) → T008–T010.

## Implementation Strategy

1. **MVP**: T001–T005, A5 plays the dungeon.
2. **Watchable**: T006.
3. **Comparable**: T007.
4. **Docs and review**: T008–T010.

No task starts a paid or local experiment run.

## Phase 6: Convergence

- [X] T011 Add a test to `tests/arch/test_supervisor.py` in which the navigator calls a tool that does not exist (`unknown_tool()`): the call reaches the dungeon, costs one step and an invalid action, and the navigator's next input holds the dungeon's error, per spec Edge Cases (partial)
