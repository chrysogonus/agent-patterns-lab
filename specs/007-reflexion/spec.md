# Feature Specification: A4 Reflexion

**Feature Branch**: `007-reflexion` (spec directory; no git branch is created)

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "Next milestone (M7, plan.md §4 and §7): A4 Reflexion. Does learning
from a failed attempt pay for itself? Outer retry loop, persistent notes; all attempts count
toward the budget. Done when it can be watched in the viewer and is added to the comparison on the
same seeds."

## Clarifications

### Session 2026-11-01

- Q: What does a new attempt do with the world? → A: Restart it: the same level and seed rebuilt
  from the start; the agent keeps only its written notes; steps add up across attempts.
- Q: On the survey field, does a wrong total count as a failed attempt A4 can retry? → A: Yes.
  The attempt ends with "wrong total", with no hint of the true number; A4 reflects and walks
  again; the episode is scored on the last submission.
- Q: Who writes the A4 graph in `src/apl/arch/`? → A: The agent, at the experimenter's request;
  the experimenter reviews it afterwards.
- Decided by the agent while writing the spec, open to the experimenter's override: every
  episode allows at most 3 attempts, enforced by the problem and not by A4's graph. Without a
  cap, "retry on a wrong total" lets an agent find the total by guessing 0, 1, 2, … at one step
  per guess, far within the survey budget, which would measure guessing rather than learning.

## Overview

Reflexion tries, fails, writes down what it learned, and tries again with that note. In the lab:

| Part | What it does | Tool calls |
| --- | --- | --- |
| Actor | Plays one attempt like A2: memory is the map built from this attempt's tool results, plus the notes | all of them |
| Reflector | After a failed attempt, reads how it went and writes a short note for the next attempt | none |
| Restart | Rebuilds the world for the next attempt: everything back at the start, the step count kept | none (costs no step) |

An attempt fails when the actor gives up (answers without a tool call), goes a fixed number of
turns without seeing anything new, or, on the survey field, submits a wrong total. The episode ends at once on
success, when the budget is used up, or when the last allowed attempt fails.

A4 is A2 with retries and notes, so A2 (`mapstate`) is its reference in the comparison, as for A3.
Architecture name: `reflexion`.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Retries with notes on both problems (Priority: P1)

A4 plays the dungeon and the survey field with the same model, base prompt, tool descriptions and
step budget as every other architecture. When an attempt fails, the reflector writes a note, the
world is restarted, and the actor starts again from the start with an empty map and every note
written so far. Steps of all attempts count toward the one budget.

**Why this priority**: Without it there is nothing to watch or compare.

**Independent Test**: With scripted models, play A4 episodes that fail a first attempt and succeed
on the second on dungeon L1–L3 and survey S1–S3, that use up all attempts, and that run out of
budget in the second attempt; check the outcome rows, the attempt counts, the notes the actor is
shown, and that the base prompt, tool descriptions and budget equal A2's.

**Acceptance Scenarios**:

1. **Given** a dungeon episode where the actor gives up in attempt 1, **When** the reflector has
   written its note, **Then** the world is back at the start (position, keys, doors), the actor's
   map shows only the start, its prompt shows the note, and the step count goes on from where
   attempt 1 left it.
2. **Given** a survey episode, **When** the actor submits a wrong total and attempts are left,
   **Then** the attempt ends with a result that says the total was wrong without giving the true
   number, and the next attempt starts on a restarted field.
3. **Given** a survey episode, **When** the actor submits the right total in any attempt,
   **Then** the episode ends as a success.
4. **Given** the third attempt fails, **When** it ends, **Then** the episode ends: on the survey
   field a wrong last total is scored like any wrong total, and a give-up ends it as given up.
5. **Given** the budget runs out during any attempt, **When** the last step is taken, **Then** the
   episode ends as out of budget, as for every architecture.
6. **Given** A4's module, **When** the import test runs, **Then** it passes.

---

### User Story 2 - Watch A4 try again (Priority: P1)

In the viewer the experimenter picks `reflexion`, a problem, a level and a dev seed, and presses
Run. They see the actor's turns as for A2; when an attempt fails, a reflector turn shows the note,
the board shows the restart (positions back at the start, the trail of the new attempt drawn
apart from the earlier ones), and the panel shows the attempt number. The replay shows the same.

**Why this priority**: The plan's done-when names the viewer first.

**Independent Test**: Play a scripted two-attempt A4 episode on L1 and on S1 through the viewer;
check that the events carry the attempt numbers and the reflector's role, that the frames show the
restart, and that the saved episode replays with the same events.

**Acceptance Scenarios**:

1. **Given** the viewer on any dungeon or survey level and dev seed, **When** the experimenter
   opens the architecture list, **Then** `reflexion` can be chosen.
2. **Given** an A4 episode, **When** an attempt fails, **Then** the side panel shows a reflector
   turn with its note, and the board and panel show attempt 2 starting from the start.
3. **Given** a saved A4 episode, **When** it is replayed or checked with the command-line tools,
   **Then** the frames, including the restarts, match the live ones.

---

### User Story 3 - A4 in runs, reports and the comparison (Priority: P2)

The experimenter plans, runs, continues and reports A4 like every other architecture, on either
problem. Rows record how many attempts each episode used; the report shows it; the comparison
places A4 next to `mapstate`. An A4 run under the M4 conditions can be reported together with the
M4 run.

**Why this priority**: This is how the experimenter checks whether retrying pays for itself.

**Independent Test**: Dry-run A4 on both problems; play a scripted A4 run, interrupt and continue
it; report it together with a scripted run of the other architectures; check the attempts and the
reference.

**Acceptance Scenarios**:

1. **Given** `reflexion` is named, **When** a run is planned without `--execute`, **Then** the
   plan lists it and no model is called.
2. **Given** an A4 run and an earlier run under the same conditions, **When** they are reported
   together, **Then** the comparison shows A4 per level with reference `mapstate`.
3. **Given** a completed A4 run, **When** the report is read, **Then** it shows the median number
   of attempts per level, and the reflector's calls apart from the actor's.
4. **Given** rows and saved episodes from before this feature, **When** they are loaded, reported,
   continued or replayed, **Then** they work as before, read as one attempt.

---

### Edge Cases

- The actor gives up at its very first turn: the attempt fails without a step; the reflector is
  called; a fixed number of attempts in a row without a tool call is still bounded by the cap of 3.
- The reflector's reply is empty: the next attempt starts with the notes written so far; an empty
  note is not added.
- The budget runs out in the middle of an attempt, or exactly on a wrong submission: the episode
  ends as out of budget; a wrong submission on the last step is scored as that submission.
- A restart is asked for when no attempts are left or the episode is over: it is refused and the
  architecture stops.
- Any other architecture: never restarts; a wrong total still ends its episode at once, exactly as
  before this feature.
- Notes grow: they are kept as written; with at most 3 attempts there are at most 2 notes.

## Requirements *(mandatory)*

### Functional Requirements

**Attempts in the problems**

- **FR-001**: Both problems MUST support restarting an episode's world: everything goes back to
  its start state (dungeon: scouts at the start with empty inventories, keys in their rooms, doors
  locked; survey field: scouts at the start, cells seen reset), while steps, invalid actions and
  the log go on.
- **FR-002**: An episode MUST allow at most 3 attempts (a constant of the problem rules, not
  derived from the budget). A restart MUST cost no step and MUST be refused when no attempt is
  left or the episode is over.
- **FR-003**: Only an architecture registered as retrying MUST be able to restart. For every other
  architecture, episodes MUST behave exactly as before this feature.
- **FR-004**: On the survey field, in an episode of a retrying architecture, a wrong total MUST
  end the attempt instead of the episode while attempts are left. Its result MUST say the total was
  wrong and how many attempts are left, and MUST NOT reveal the true total or how far off it was.
  The world MUST then be restarted for the next attempt. A right total, or a wrong total in the
  last attempt, MUST end the episode as a submission does today.
- **FR-005**: Every tool call of every attempt MUST count toward the one step budget
  (constitution III). The episode MUST be scored on how it ended: the dungeon on reaching the
  exit, the survey field on the last submitted total.
- **FR-006**: Each log entry MUST record its attempt, so that replaying a log rebuilds every
  restart exactly; logs without attempts MUST read as attempt 1.

**The architecture**

- **FR-007**: The lab MUST have an architecture A4 named `reflexion`, registered for both problems
  and as retrying.
- **FR-008**: A4's actor MUST play each attempt the way A2 plays an episode: memory is the map
  built from this attempt's tool results, plus its latest turn; at a restart the map MUST start
  again from the new start result.
- **FR-009**: The actor MUST be shown every note written so far, on every turn of later attempts.
- **FR-010**: An attempt MUST end when the actor answers without a tool call, when a fixed number
  of its turns in a row revealed no room or cell new to this attempt (a constant, not derived from
  the budget), or when a survey submission is answered as wrong. A plain turn limit would either
  never matter on the dungeon or make S2's 100-cell walk impossible in one attempt.
- **FR-011**: After a failed attempt with attempts left, the reflector MUST be called once with
  what that attempt revealed (its map at the end, its last reply, and why the attempt ended) and
  the notes so far, and MUST answer with a short note. It makes no tool call.
- **FR-012**: A4's instructions on top of the base prompt MUST explain attempts, notes and the
  reflector's job only, with no strategy advice for the problem.
- **FR-013**: A4's model calls MUST be marked by job (actor, reflector), with the attempt number
  on the actor's calls.
- **FR-014**: The agent writes A4 in `src/apl/arch/`, at the experimenter's request; the
  experimenter reviews it afterwards. Other architectures' behavior MUST NOT change.

**Runner, report and viewer**

- **FR-015**: `apl run`, `apl continue` and `apl report` MUST accept `reflexion` on both problems;
  without `--execute`, no model is called (constitution VI).
- **FR-016**: Each result row MUST record the attempts the episode used; rows from before this
  feature read as 1.
- **FR-017**: The report MUST show the median attempts per architecture and level, and the
  comparison MUST list A4 with reference `mapstate`. Reflector calls MUST be counted apart from
  actor calls, as orchestrator calls are.
- **FR-018**: The viewer MUST offer `reflexion` on both problems, show each attempt's number,
  show a restart on the board (positions back at the start, earlier attempts' trails set apart),
  show the reflector's turns with their notes, and replay saved A4 episodes exactly.
- **FR-019**: The constitution's "Experiment Setup" MUST state the attempt rule: up to 3 attempts
  per episode for a retrying architecture, the world restarted between them, every step counted,
  and on the survey field a wrong total ending an attempt.
- **FR-020**: plan.md and the README MUST list A4 as built, on both problems.

### Key Entities

- **Attempt**: one try at the episode's task from the start state; numbered from 1; ends on
  success, on a failure (give-up, nothing new for too long, wrong total) or with the episode.
- **Note**: the reflector's short text after a failed attempt; carried into every later attempt.
- **Restart**: the world rebuilt for the next attempt; costs no step; at most 2 per episode.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every dungeon and survey level, a scripted A4 episode that gives up in attempt 1
  and follows the shortest solution (or the reference walk and the right total) in attempt 2
  succeeds, with steps equal to attempt 1's steps plus a scripted A2's steps.
- **SC-002**: After every restart, the world equals a freshly started episode on the same level and
  seed in every checked state (positions, keys, doors, cells seen), and the step count is
  unchanged.
- **SC-003**: No scripted A4 episode uses more than 3 attempts, and no episode of any other
  architecture ever restarts or changes outcome compared with before this feature.
- **SC-004**: A wrong-total result never contains the true total or the error's size.
- **SC-005**: Every saved A4 episode replays from its log to the same frames and outcome.
- **SC-006**: A4's base prompt fingerprint, tool descriptions and budget equal A2's on the same
  level and seed.
- **SC-007**: A report of a scripted A4 run together with a scripted run of the earlier
  architectures shows A4 per level with reference `mapstate` and its median attempts.
- **SC-008**: Every test, lint, format and type check passes; dry runs and tests make no paid call.

## Assumptions

- A4 builds on A2 like A3 does, so A2 is the reference and the difference is retries with notes.
- The map does not carry over between attempts: the experimenter chose "keeps only its written
  notes". The notes may say anything the reflector writes, including what the map showed.
- The attempt cap of 3 is the same on both problems and for any later retrying architecture.
- The wrong-total signal is information other architectures never get; that is what Reflexion
  learns from, and the attempt cap bounds it. The constitution amendment (FR-019) records it.
- The constitution amendment adds rules to a section without redefining a principle: a MINOR
  version (2.1.0), made with `/speckit-constitution`; the experimenter reviews its text.
- No local or paid experiment run is part of this feature.
