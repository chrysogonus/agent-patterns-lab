# Feature Specification: Several Problems, and the Survey Field

**Feature Branch**: `005-survey-field` (spec directory; no git branch is created)

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "Multi-problem support plus the first new problem, the survey field.
The lab gains a second problem next to the dungeon so architectures can be compared on problems
with different properties. (1) Problems: each problem declares its own tools, level ladder, seeds,
solver/scoring and step budget; the fairness rules (same model, prompt, tool descriptions, budget;
world access only through the problem's tools; structured results; dev vs test seeds; no paid call
without --execute) apply within a problem. The dungeon stays as the first problem and keeps working
unchanged. The constitution's four-tool rule is amended accordingly. (2) Survey field: an open N×N
field (no walls at the first level) with ore hidden under fog; the agent moves, scans the room it is
in, and finally submits a total; scored by whether the total is correct, steps, and tokens. Levels
grow the field size and later add walls, so the scouts' advantage can be watched appearing and
disappearing. Tools are structured like the dungeon's (move, look/scan, submit). (3) Runner, report
and viewer: `apl run`, `apl continue`, `apl report` and `apl serve` take a problem; the viewer shows
the survey field with fog, scout colors, and the agent's counted total next to the true total. (4)
Architectures: generic ones (A1 ReAct, the scout orchestrators A7–A9) run on the survey field;
map-specific ones (A2, A2r, A6) need a problem-specific state view and may be out of scope for this
feature. Goal: reproduce the expected reversal of M4, where four scouts beat one agent on an open
field. Visual mock-up of the intended boards: https://claude.ai/artifact/VEDrZX6TuFapmV4rHkTCqB"

## Clarifications

### Session 2026-11-01

- Q: Who writes the field versions of A1 and A7–A9 in `src/apl/arch/`? → A: The agent, at the
  experimenter's request, as with A7–A9 in M4; the experimenter reviews them afterwards.

## User Scenarios & Testing *(mandatory)*

The user of this feature is the experimenter. They want to try architectures on more than one
kind of problem, watch them in the viewer, and see each architecture's strengths and weaknesses
for themselves. The dungeon showed little difference between most architectures (M4 findings).
The survey field is built to show one: on an open field with no dead ends, splitting the work
between scouts should pay off, while one agent's growing history should make it lose count.

The survey field in one paragraph: a square field of cells, covered in fog. Some cells hold an ore
deposit. The agent walks from cell to cell; entering a cell shows what is in it. When it thinks it
has seen everything, it submits the number of deposits. The episode is a success when the number
is right.

Architectures in this feature:

| Name | Architecture | On the dungeon | On the survey field |
| --- | --- | --- | --- |
| `react` | A1 ReAct | as before | yes |
| `mapstate` | A2 map state | as before | yes, with a field map (the scouts' single-agent reference) |
| `fanout` | A7 fan-out once | as before | yes, with a field scout |
| `rounds` | A8 supervisor in rounds | as before | yes, with a field scout |
| `blackboard` | A9 shared blackboard | as before | yes, with a field scout |
| `mapstate_routes`, `hybrid` | A2r, A6 | as before | no (later feature) |

### User Story 1 - Watch an architecture survey a field (Priority: P1)

In the viewer, the experimenter picks the survey field, a level and a dev seed, and sees the field.
They pick an architecture and press Run. Every step appears on the field as it happens: fog lifts
from each cell an agent enters, each scout has its own color, and a panel shows the true total, the
deposits seen so far by all agents together, and, at the end, the submitted total, marked right or
wrong. The side panel shows each model turn as it does for the dungeon. Episodes are saved and can
be replayed.

**Why this priority**: This is what the experimenter asked for: trying architectures on a new
problem by hand and seeing the difference. It needs the problem itself (US2) and is the first thing
they will use.

**Independent Test**: Start the viewer, open survey field S1 seed 1000, play a scripted agent that
walks every cell and submits the right total, and check that the fog, the seen count, the submitted
total and the replay all match the saved events.

**Acceptance Scenarios**:

1. **Given** the viewer is open, **When** the experimenter picks the survey field, level S1 and seed
   1000, **Then** the field is shown with its deposits, and with "Agent's view" on, every cell is
   under fog.
2. **Given** an episode with four scouts is running, **When** scout 3 enters a cell, **Then** that
   cell's fog lifts, the step shows in scout 3's color, and the seen count goes up if the cell holds
   a deposit not seen before.
3. **Given** an episode ends with a submitted total, **When** the experimenter looks at the panel,
   **Then** it shows the submitted total next to the true total, marked right or wrong.
4. **Given** the experimenter picks an architecture that does not support the survey field, **When**
   they look at the architecture list, **Then** that architecture cannot be chosen for this problem.
5. **Given** a test seed, **When** the experimenter enters it for any problem, **Then** the viewer
   refuses it, as it does for the dungeon.

---

### User Story 2 - The survey field problem (Priority: P1)

A seed and a level always build the same field. The agents act only through the field's tools,
each call costs one step, and errors are structured like the dungeon's. Every field has a
reference walk computed by code, which sets the step budget and the efficiency score.

**Why this priority**: Without it there is nothing to watch or compare. It is listed second only
because it is invisible on its own.

**Independent Test**: Generate fields for every level and dev seed, check that every cell is
reachable and the deposit count matches the level, play scripted walks against the tools and
check every result, and check that a seeded field is identical across runs.

**Acceptance Scenarios**:

1. **Given** a field, **When** an agent enters a cell, **Then** the result names the cell, says
   whether it holds a deposit, and lists the directions it can move from there.
2. **Given** an agent at the field's edge or in front of a wall, **When** it moves that way,
   **Then** the call fails with a structured error and costs a step.
3. **Given** an agent has walked part of the field, **When** it submits a whole number, **Then**
   the episode ends, and it is a success exactly when the number equals the field's deposit count.
4. **Given** the step budget is used up without a submission, **When** the episode ends, **Then**
   it is a failure, marked as out of budget.
5. **Given** several scouts, **When** one of them, or an orchestrator, submits, **Then** the episode
   ends for all of them, and every tool call by every scout counted toward the one budget.

---

### User Story 3 - Run, continue and report on a chosen problem (Priority: P2)

The experimenter plans and runs episodes on the survey field with the same commands as for the
dungeon, naming the problem. The plan is free and shows the matrix and an estimate; `--execute`
plays it. An interrupted run can be continued. The report covers one problem per run and adds the
survey field's own columns: how often the submitted total was right, how far off it was when
wrong, how many cells were seen, and how many parallel turns the episode took, so that scouts
working at the same time show up as faster.

**Why this priority**: The viewer is enough to see the difference by eye. A run with repeats is
how the experimenter checks whether what they saw holds across seeds.

**Independent Test**: Plan a survey run without `--execute` and check the matrix; play a run with
scripted architectures, interrupt it, continue it, and check the report against the rows.

**Acceptance Scenarios**:

1. **Given** no problem is named, **When** the experimenter plans a run, **Then** it is a dungeon
   run, planned exactly as before this feature.
2. **Given** the survey field is named, **When** the experimenter plans a run without
   `--execute`, **Then** the plan shows the survey levels, seeds, architectures and an estimate,
   and no model is called.
3. **Given** a survey run names an architecture that does not support the survey field, **When**
   it is planned, **Then** it is refused with a message that names the architecture and the
   problem.
4. **Given** a completed survey run, **When** the report is written, **Then** it shows, per
   architecture and level, the share of right totals, the median error of wrong totals, the median
   share of cells seen, steps, parallel turns, tokens and latency.

---

### User Story 4 - The fairness rules hold within each problem (Priority: P2)

The project's rules are restated so they apply to each problem: within one problem every
architecture gets the same model, base prompt, tool descriptions and step budget, and reaches the
world only through that problem's tools. Each problem has its own base prompt and tools; results
from different problems are never combined in one comparison.

**Why this priority**: The lab's results mean nothing if the rules are not checked. The existing
tests that enforce them must keep enforcing them for the dungeon and start enforcing them for the
survey field.

**Independent Test**: The test that limits what architectures may import passes with the survey
field's public tool and result definitions added, and fails for an architecture that reads field
internals.

**Acceptance Scenarios**:

1. **Given** the constitution, **When** this feature is done, **Then** principle II names each
   problem's own tools instead of the dungeon's four, and its version and amendment date are
   updated.
2. **Given** an architecture that imports the survey field's generator, **When** the tests run,
   **Then** the import test fails.
3. **Given** two architectures on the same survey level, **When** their episodes run, **Then**
   both got the same base prompt, tool descriptions and step budget, as recorded in the results.

---

### Edge Cases

- An agent submits before walking anywhere: the episode ends with that total, scored as right or
  wrong like any other.
- An agent submits something that is not a whole number, or a negative one: the call fails with a
  structured error, costs a step, and the episode goes on.
- An agent re-enters a cell it has seen: the result is the same as the first time; the seen count
  does not go up again.
- Two scouts stand in the same cell: allowed; both see the same contents.
- A model reply has no tool call and no submission (a single agent stops talking): the episode ends
  as a failure without a total, marked as given up, as on the dungeon.
- The prompt grows past the model's context window: the episode ends as the architecture's
  failure, as on the dungeon; this is one of the effects the field is meant to show.
- An orchestrator in A7 or A8 submits a total its scouts never reported: allowed; the score is the
  number alone.
- In A9 there is no orchestrator: any scout may submit, and the first submission ends the episode.
- A walled level where a pocket of cells is reachable only through one opening: every cell is
  still reachable; the reference walk includes the detour.
- A dungeon run, report or saved episode from before this feature: it still loads, continues and
  reports as before.

## Requirements *(mandatory)*

### Functional Requirements

**Problems**

- **FR-001**: The lab MUST support more than one problem. A problem MUST define its own tools and
  their descriptions, base prompt, levels, dev and test seeds, reference solution, scoring and step
  budget rule.
- **FR-002**: The dungeon MUST be the first problem and MUST behave exactly as before: same
  dungeons per seed, same tools, prompt, budget, scoring and results format.
- **FR-003**: Every command and the viewer MUST default to the dungeon when no problem is named.
- **FR-004**: Each architecture MUST declare which problems it supports. Planning a run or
  choosing an architecture in the viewer for a problem it does not support MUST be refused with a
  message naming both.
- **FR-005**: A run MUST cover exactly one problem; reports MUST NOT combine results from
  different problems.

**Survey field**

- **FR-006**: A survey field MUST be a square grid of cells, generated from a level and a seed,
  identical every time for the same pair, with every cell reachable from the start cell.
- **FR-007**: The survey field MUST have three levels:

  | Level | Size | Walls | Deposits | Purpose |
  | --- | --- | --- | --- | --- |
  | S1 | 6×6 | none | 6 | Baseline; every architecture should get it right |
  | S2 | 10×10 | none | 15 | Long history for one agent; open regions for scouts |
  | S3 | 10×10 | interior walls with dead-end pockets | 15 | Walls bring back detours, where scouts may lose their lead |

- **FR-008**: Each cell MUST hold at most one deposit. The agent MUST start in a corner cell.
- **FR-009**: Agents MUST act only through these tools, each call costing one step, failed calls
  included:

  | Tool | Returns |
  | --- | --- |
  | `look()` | The current cell's name, whether it holds a deposit, and the directions one can move from it |
  | `move(direction)` | The same description for the new cell, or an error (field edge, wall) |
  | `submit(total)` | Ends the episode with this total, or an error (not a whole number, negative) |

- **FR-010**: Cell names MUST be their grid coordinates (for example "C4"), so that an agent can
  keep track of where it has been.
- **FR-011**: Results and errors MUST be structured data with the same shape as the dungeon's
  (`ok`, `error` with `code` and `message`, `data`).
- **FR-012**: An episode MUST end when a submission succeeds, when the step budget is used up, or
  when the architecture stops without submitting. It MUST be a success exactly when the submitted
  total equals the field's deposit count.
- **FR-013**: Code MUST compute a reference walk for every field: a walk that enters every cell,
  plus one submission. On open levels it MUST be the shortest such walk (cells − 1 moves, plus 1).
  On walled levels it MAY be longer than the shortest, and the results MUST say it is a reference,
  not an optimum.
- **FR-014**: The step budget MUST be 3× the reference walk.
- **FR-015**: Several scouts MUST be able to share one field, each with its own position, as on
  the dungeon: one shared step budget, the episode ending for all on the first successful
  submission. Any node of an architecture, including an orchestrator, MAY call `submit`; that call
  costs one step like any other.

**Runner and report**

- **FR-016**: `apl run` MUST accept a problem; `apl continue` and `apl report` MUST take it from
  the run. A command like `apl dungeon show` MUST print a survey field for a level and seed.
  Without `--execute`, no model is called (constitution VI).
- **FR-017**: Each survey result row MUST record, besides the existing fields: the submitted total
  (or none), the true total, the cells seen by all agents together, the number of cells, and the
  parallel turns.
- **FR-018**: Parallel turns MUST count the groups of tool calls applied between two model calls:
  calls applied together after the scouts' parallel model calls count once. For one agent they
  equal its model turns that made tool calls (its steps, when each turn makes one call).
- **FR-019**: The survey report MUST show per architecture and level: the share of right totals,
  the median absolute error of wrong totals, the median share of cells seen, steps, parallel turns,
  tokens and latency, with the spread across repeats, and the comparison section M4 introduced.

**Viewer**

- **FR-020**: The viewer MUST let the experimenter pick a problem; the level, seed and
  architecture choices MUST follow from it.
- **FR-021**: For the survey field, the viewer MUST draw the field, its deposits, fog per the
  "Agent's view" toggle, each agent's position and trail in its color, and a panel with the true
  total, the deposits seen so far by all agents, and the submitted total with right or wrong.
- **FR-022**: The step slider, replay of saved episodes and the side panel of model turns MUST work
  for the survey field as for the dungeon.

**Rules**

- **FR-023**: The constitution MUST be amended so principle II says architectures reach each
  problem only through that problem's tools, and the other principles apply within a problem.
- **FR-024**: Architectures MUST be allowed to import only the shared kit and each problem's
  public tool and result definitions; the import test MUST enforce this for every problem.
- **FR-025**: Results MUST record the problem with each episode, along with what the dungeon
  already records (prompt fingerprint, model, budget).

**Architectures**

- **FR-026**: A1 (`react`) MUST play the survey field with the field's base prompt and tools, and
  nothing else changed.
- **FR-027**: A7–A9 MUST play the survey field with a scout made for it: the same orchestration as
  on the dungeon, with a field map built only from tool results instead of the dungeon map.
- **FR-028**: A2 (`mapstate`) MUST play the survey field with the same field map the scouts use,
  so the scouts have a single-agent reference on the field as on the dungeon.
- **FR-029**: The agent writes the field versions of A1, A2 and A7–A9 and the field map in
  `src/apl/arch/`, at the experimenter's request; the experimenter reviews them afterwards. Their
  dungeon behavior MUST NOT change.

### Key Entities

- **Problem**: a kind of task the lab can run. Has a name, tools, base prompt, levels, seed sets,
  reference solution, scoring and budget rule. The dungeon and the survey field are problems.
- **Survey field**: a grid of cells generated from a level and a seed; some cells hold a deposit,
  some sides are walls; has a start cell, a deposit count and a reference walk.
- **Cell**: a square of the field with a coordinate name, a deposit or none, and the directions
  one can leave it.
- **Survey outcome**: the result of one survey episode: success, submitted total, true total, cells
  seen, steps, parallel turns, budget hit, and the fields every episode records.
- **Architecture support**: which problems an architecture can play.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every dungeon command from before this feature produces the same output, and every
  existing dungeon test passes without changes to what it checks.
- **SC-002**: For every survey level and every dev and test seed, the generated field is identical
  across runs, has the level's size and deposit count, and every cell is reachable.
- **SC-003**: A scripted agent that follows the reference walk and submits the true total
  succeeds on every survey level and seed, within the reference step count.
- **SC-004**: In the viewer, the experimenter can go from opening the page to watching a four-scout
  survey episode on S2 in under a minute, and can replay it afterwards step by step.
- **SC-005**: Every survey tool result, error and outcome in a saved episode can be checked by code
  against the field, with no free-text parsing.
- **SC-006**: A dry run plan for the survey field never calls a model, and the tests never make a
  paid call.
- **SC-007**: In a scripted episode where four scouts each walk one quarter of an open S2 field,
  the parallel turns are about a quarter of a single agent's reference walk.

## Assumptions

- A2r and A6 stay dungeon-only in this feature. A2 joins, because the scouts need its field map
  anyway and it is their single-agent reference (decided in planning, research R10).
- The survey field's dev and test seed numbers are the same as the dungeon's (dev 1000–1009, test
  2000–2019); they build different worlds because the problem differs.
- Entering a cell shows its contents, so no separate scan tool is needed; this keeps the
  reference walk at about one step per cell.
- The 3× budget leaves room for the revisits a single agent makes without letting a lost agent
  wander for long; it can be tuned on dev seeds before any reported run.
- Scoring is right or wrong on the exact total; the size of the error is reported but does not
  count as partial success.
- The scouts' advantage is expected in parallel turns and latency, and in getting the total right,
  not in total steps: on an open field one agent's snake walk is already the shortest, so scouts
  can at best tie it on steps.
- A9's scouts take turns, so it is not expected to gain in parallel turns; that is part of what
  the field shows.
- This feature includes no paid or local experiment run. Running a comparison and writing findings
  is the experimenter's choice afterwards, with the commands from US3.
- The constitution amendment changes a principle's meaning, so it is a MAJOR version (2.0.0),
  made with `/speckit-constitution` before this feature's plan.
- The visual mock-up linked in the input shows intended behavior; its numbers are illustrative.
