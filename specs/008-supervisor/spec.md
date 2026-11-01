# Feature Specification: A5 Supervisor

**Feature Branch**: `008-supervisor` (spec directory; no git branch is created)

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "M8, feature 008: A5 supervisor. Add architecture A5 (supervisor) to
the lab, per plan.md §4 and §7: do subagents help or only add cost? A supervisor hands work to a
navigator and an inventory subagent (subgraphs, handoffs). Done when: A5 can be watched in the
viewer and is added to the comparison on the same seeds. Clarifications already decided by the
experimenter (2026-11-01): the agent writes the A5 graph in src/apl/arch/ and the experimenter
reviews it afterwards; A5 plays the dungeon only; the tools are split by subagent: the navigator
gets look and move, the inventory subagent take and use. No paid or local experiment runs are
started as part of this work unless explicitly requested."

## Clarifications

### Session 2026-11-01

- Q: Who writes the A5 graph in `src/apl/arch/`? → A: The agent, at the experimenter's request,
  as with A3 and A4; the experimenter reviews it afterwards.
- Q: Which problems does A5 play? → A: The dungeon only. The survey field has no items, so an
  inventory subagent would have nothing to do there.
- Q: How are the tools split? → A: By subagent: the navigator gets `look` and `move`, the
  inventory subagent `take` and `use`. The supervisor hands off one task at a time, and the
  subagent reports back.

## Overview

plan.md §4 asks of A5: do subagents help, or do they only add cost? A5 splits one body's work
between a supervisor and two specialists:

| Job | What it does | Tool calls |
| --- | --- | --- |
| Supervisor | Reads the task, the map and the reports so far, and hands one task to one helper, or stops | none |
| Navigator | Carries out a task by looking and moving, then reports | `look`, `move` |
| Inventory | Carries out a task by taking items and using keys, then reports | `take`, `use` |

There is one body in the dungeon: both helpers act as it, so the navigator walks where the
inventory helper then takes a key. A5 builds on A2's map: everyone sees the same map, built from
all tool results, and each helper keeps only its latest turn. So A5 differs from A2 in the split
into specialists and the handoffs between them, and A2 (`mapstate`) is its reference in the
comparison. It differs from A3 in that the work is split by kind (moving versus items), not by
time (one subgoal after another), and each helper can only do its own kind.

Architecture name: `supervisor`.

## User Scenarios & Testing *(mandatory)*

The user of this feature is the experimenter. They want to see whether specialists pay for the
handoffs, first by watching A5, then by comparing it with A2 and the others on the same seeds.

### User Story 1 - A5 plays the dungeon under the fairness rules (Priority: P1)

A5 gets the same model, base prompt, tool descriptions and step budget as every other
architecture on the dungeon. The supervisor makes no tool calls. Each helper may call only its
own tools; every tool call that reaches the dungeon counts toward the one step budget. The
episode ends as for A2: when the exit is entered, when the budget runs out, or when A5 stops.

**Why this priority**: Without a working, fair A5 there is nothing to watch or compare.

**Independent Test**: With scripted models, play A5 episodes on L1–L3 in which the supervisor
hands moving to the navigator and keys to the inventory helper until the exit is reached; check
the outcome rows against a scripted A2 walking the same solution, and check that the recorded
base prompt, tool descriptions and budget equal A2's.

**Acceptance Scenarios**:

1. **Given** a dungeon level and seed, **When** A5's helpers walk the solution, **Then** the
   episode ends as a success with the same steps as A2 walking it, and the supervisor's calls add
   no step.
2. **Given** L3, where a key must be taken and used, **When** the supervisor hands the key work
   to the inventory helper, **Then** the inventory helper's `take` and `use` open the door, and
   the navigator then walks through it.
3. **Given** the navigator tries to call `take` (or the inventory helper `move`), **When** A5
   handles the reply, **Then** the call is not made, costs no step, and the helper is told it is
   not its tool.
4. **Given** the supervisor stops before the exit is reached, **When** A5 ends, **Then** the
   episode ends as given up, as for an A2 that stops talking.
5. **Given** A5's module, **When** the import test runs, **Then** it passes: A5 imports only the
   shared kit, other architectures' modules and the dungeon's public tool and result definitions.

---

### User Story 2 - Watch A5 hand off (Priority: P1)

In the viewer, the experimenter picks a dungeon level and a dev seed, picks `supervisor` and
presses Run. The side panel shows the supervisor's turn with the task it handed off, then the
helper's turns on that task, the supervisor's next turn, and so on. Each turn is marked with its
job, and the helper turns with the task number. On the board, the steps appear as for A2. The
episode is saved and can be replayed.

**Why this priority**: This is how the experimenter will first judge the architecture, and the
plan's done-when names it first.

**Independent Test**: With a scripted model, play `supervisor` on L3 seed 1002 through the
viewer; check that supervisor, navigator and inventory turns appear in order with their roles,
and that the replay shows the same.

**Acceptance Scenarios**:

1. **Given** the viewer is open on any dungeon level and dev seed, **When** the experimenter looks
   at the architecture list, **Then** `supervisor` can be chosen; on the survey field it is not
   offered.
2. **Given** an A5 episode is running, **When** the supervisor answers, **Then** its turn appears
   marked `supervisor`, showing the helper and task it chose.
3. **Given** a helper is working on a task, **When** it calls a tool, **Then** the step appears
   on the board as A2's would, and its turn is marked with the helper and task number.
4. **Given** a finished A5 episode, **When** the experimenter replays it, **Then** every turn and
   step appears as it did live.

---

### User Story 3 - A5 in runs, reports and the comparison (Priority: P2)

The experimenter plans, runs, continues and reports A5 episodes with the same commands as every
other architecture. The comparison section places A5 next to its reference A2. An A5 run on the
M4 conditions (same model and settings, dev seed 1000 of L1–L3) can be reported together with the
M4 run, so that A5 joins that comparison without rerunning the others.

**Why this priority**: The comparison is how the experimenter checks what they saw, and it is the
plan's done-when for M8.

**Independent Test**: Plan an A5 run without `--execute` and check the matrix; play a scripted A5
run, interrupt and continue it, and report it together with a scripted run of the other dungeon
architectures; check A5's comparison row and its reference.

**Acceptance Scenarios**:

1. **Given** `supervisor` is named, **When** a dungeon run is planned without `--execute`,
   **Then** the plan shows the matrix and the usual estimate, and no model is called.
2. **Given** `supervisor` is named for the survey field, **When** a run is planned, **Then** it
   is refused with the usual message naming the problems A5 plays.
3. **Given** an interrupted A5 run, **When** it is continued, **Then** only the missing episodes
   are planned.
4. **Given** an A5 run and an earlier run with the same conditions, **When** they are reported
   together, **Then** the comparison shows A5 with `mapstate` as its reference, and the calls
   column shows supervisor calls apart from helper calls.

---

### Edge Cases

- The supervisor's reply is unusable (no JSON, unknown helper, empty task): it is asked again
  with a note saying why; after a fixed number of unusable replies in a row, A5 stops and the
  episode ends as given up.
- A helper makes no tool call on a task (it reports at once that it is done or impossible): the
  supervisor gets that report. A fixed number of handoffs in a row without a tool call stops A5,
  so a supervisor–helper loop cannot spend tokens without ever acting.
- A helper never reports: after a fixed number of its turns on one task, the task goes back to
  the supervisor as unfinished. The number is a constant, not derived from the budget
  (constitution II).
- A helper calls the other helper's tool, alone or among its own calls: only that call is
  refused (no step, no tool call counted); its own calls in the same reply run as usual, in order.
- A helper's reply has unparsable calls or calls to tools that do not exist: they go to the
  dungeon like every architecture's, cost a step, and get the dungeon's error back.
- The episode ends in the middle of a task (exit entered, budget used up): it ends at once, with
  no further supervisor call.
- A run or saved episode from before this feature: it loads, continues and reports as before.

## Requirements *(mandatory)*

### Functional Requirements

**The architecture**

- **FR-001**: The lab MUST have an architecture A5 named `supervisor`, registered for the dungeon
  only.
- **FR-002**: A5 MUST have three jobs: a supervisor that hands one task at a time to one helper or
  stops, a navigator that works on a task with `look` and `move`, and an inventory helper that
  works on a task with `take` and `use`. Each helper MUST run as its own subgraph, and the
  supervisor's choice MUST be a handoff to that subgraph.
- **FR-003**: Each helper MUST be offered only its own tools, with the dungeon's tool descriptions
  unchanged. A call by a helper to a tool of the other helper MUST NOT reach the dungeon; it MUST
  be answered by A5 with a short text saying whose tool it is, and MUST cost no step.
- **FR-004**: Each helper MUST keep its memory the way A2 does: its latest reply with that reply's
  tool results, and the map, not the message history. It MUST be told its current task on every
  turn, and the start result on the episode's first helper turn.
- **FR-005**: There MUST be one map, built from every tool result of both helpers, and the
  supervisor and both helpers MUST see it.
- **FR-006**: The supervisor MUST see the task (the base prompt and the start result), every
  finished handoff with its helper, task, outcome and report, the steps used so far, and the map.
  It MUST NOT see anything that tool results have not revealed (constitution II).
- **FR-007**: The instructions A5 adds on top of the base prompt MUST explain each job's setup,
  input and expected answer only, with no strategy advice.
- **FR-008**: A task MUST end when the helper replies without a tool call (its report), or after a
  fixed number of helper turns (unfinished). A5 MUST stop, ending the episode as given up, when
  the supervisor answers that it is done, after a fixed number of unusable supervisor replies in
  a row, or after a fixed number of handoffs in a row without a tool call. All limits MUST be
  constants.
- **FR-009**: A5's model calls MUST be marked by job: `supervisor`, and `navigator (task n)` or
  `inventory (task n)` for the helpers, where n counts handoffs.
- **FR-010**: The agent writes A5 in `src/apl/arch/` at the experimenter's request; the
  experimenter reviews it afterwards. A5 MUST reuse A2's dungeon map; no other architecture's
  behavior and no problem, kit or prompt MUST change.

**Runner and report**

- **FR-011**: `apl run`, `apl continue` and `apl report` MUST accept `supervisor` on the dungeon as
  they accept the other architectures, and refuse it on the survey field. Without `--execute`, no
  model is called (constitution VI).
- **FR-012**: The comparison section MUST list A5 with `mapstate` as its reference.
- **FR-013**: Supervisor calls MUST count as lead calls, apart from helper calls, as orchestrator
  and planner calls do.
- **FR-014**: An A5 run made under the same conditions as an earlier run MUST be reportable
  together with it, so A5 joins the M4 comparison without rerunning the others.

**Viewer**

- **FR-015**: The viewer MUST offer `supervisor` on every dungeon level and not on the survey
  field; its turns MUST show their roles; A5 episodes MUST be saved and replayable.

**Docs**

- **FR-016**: plan.md (§4 table, §7 status) and the README's architecture table and roadmap MUST
  list A5 as built, on the dungeon.

### Key Entities

- **Handoff**: the supervisor's choice of a helper and a task in words, for example "go to the
  room with the red key".
- **Task report**: the helper's last reply on a task, with the outcome: done (it replied without a
  tool call) or unfinished (it reached the turn limit).
- **Helper**: the navigator or the inventory helper; a subgraph with its own tools that acts as
  the one body.
- **Role**: the job a model call belongs to, recorded with each call.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A scripted A5 whose helpers follow the shortest solution on L1, L2 and L3 succeeds
  with the same step count as a scripted A2 doing the same.
- **SC-002**: On the same level and seed, A5's recorded prompt fingerprint, tool descriptions and
  budget equal A2's in 100% of checked episodes.
- **SC-003**: In 100% of A5 episodes, the steps counted equal the helpers' calls that reached the
  dungeon; supervisor calls and refused calls add no step.
- **SC-004**: No scripted A5 episode runs without end, including ones whose supervisor never gives
  a usable answer, whose helpers never call a tool, or whose helper only calls the other's tool.
- **SC-005**: For every dungeon level, an A5 episode with a scripted model can be started in the
  viewer, watched to its end and replayed, with every turn shown in order with its role.
- **SC-006**: An A5 dry run calls no model, and the tests make no paid call.
- **SC-007**: A report of a scripted A5 run together with a scripted run of the dungeon's other
  architectures shows A5 per level with `mapstate` as its reference.
- **SC-008**: Every test, lint, format and type check passes, and every existing test still
  checks what it checked before.

## Assumptions

- A5 builds on A2's map, as A3 and A4 do, so its difference from A2 is the split into specialists
  and A2 is its reference.
- The supervisor answers in structured text (one JSON object), as A3's planner does; it costs
  model calls and tokens but no steps.
- The fixed limits (unusable supervisor replies, helper turns per task, handoffs without a tool
  call) are constants and may be tuned on dev seeds only (constitution V). They take A3's values,
  so the two are bounded alike.
- A refused call is answered by A5 itself: the text says only whose tool it is and reveals nothing
  about the world, so constitution II holds. It is not a tool call: it is not counted as a step,
  an invalid action or a tool call.
- "Added to the comparison on the same seeds" means A5 can be run and reported with the M4 run
  (dev seed 1000 of L1–L3, `openai:gpt-6-luna`). No such run is part of this feature.
- No local or paid experiment run is started as part of this work unless the experimenter asks.
- The constitution needs no amendment: principle III already says every node's tool calls count
  toward the one budget, and offering a node a subset of the tools is "what each node is told".
