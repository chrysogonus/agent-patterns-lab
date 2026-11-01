# Feature Specification: A3 Plan-and-Execute

**Feature Branch**: `006-plan-and-execute` (spec directory; no git branch is created)

**Created**: 2026-11-01

**Status**: Draft

**Input**: User description: "M6, feature 006: A3 plan-and-execute. Add architecture A3
(plan-and-execute) to the lab, per plan.md §4 and §7: a planner node sets subgoals, an executor
runs them through the problem's tools, a replanner reacts to what the executor found (multiple
nodes, cycles). It runs on both problems, the dungeon and the survey field, under the fairness
rules (same model, temperature, base prompt, tool descriptions and step budget; only the graph
differs). Done when: A3 can be watched in the viewer on any dungeon and survey level and seed,
runs plan/continue/report like the other architectures, and is added to the comparison on the
same seeds as M4 and M5. Clarifications already decided by the experimenter (2026-11-01): the agent
writes the A3 graph in src/apl/arch/, as with A7–A9 in M4 and the survey versions in M5, and the
experimenter reviews it afterwards; A3 runs on both the dungeon and the survey field. No paid or
local experiment runs are started as part of this work unless explicitly requested."

## Clarifications

### Session 2026-11-01

- Q: Who writes the A3 graph in `src/apl/arch/`? → A: The agent, at the experimenter's request,
  as with A7–A9 in M4 and the field versions in M5; the experimenter reviews it afterwards.
- Q: Which problems does A3 play? → A: Both, the dungeon and the survey field.

## Overview

plan.md §4 asks of A3: does planning help, above all on L3, where keys and locked doors make the
order of the work matter? A3 splits one agent's work into three jobs:

| Job | What it does | Tool calls |
| --- | --- | --- |
| Planner | Reads the task and what is known so far, and writes a short ordered list of subgoals | none |
| Executor | Works on one subgoal at a time through the problem's tools, then reports how it went | all of them |
| Replanner | After each subgoal, reads the report and the map, and keeps, changes or ends the plan | none |

A3 builds on A2's map (as plan.md and the M4 design intended): the executor works like A2, with
the map built from its own tool results instead of the message history, and the planner and
replanner see the same map. So A3 differs from A2 in one job, planning, and A2 (`mapstate`) is
its reference in the comparison.

Architecture name: `plan_execute`.

## User Scenarios & Testing *(mandatory)*

The user of this feature is the experimenter. They want to see whether a written plan changes how
one agent explores, first by watching it, then by comparing it with A2 and the others on the same
seeds.

### User Story 1 - Watch A3 plan and execute (Priority: P1)

In the viewer, the experimenter picks a problem, a level and a dev seed, picks `plan_execute` and
presses Run. The side panel shows the planner's turn with the plan it wrote, then the executor's
turns on the first subgoal, the replanner's turn with the updated plan, and so on. Each planner
and replanner turn is marked as such, and the current plan with its finished subgoals can be read
at any step. On the board, the steps appear as for A2. The episode is saved and can be replayed.

**Why this priority**: This is how the experimenter will first judge the architecture, and the
plan's done-when names it first.

**Independent Test**: With a scripted model, play `plan_execute` on dungeon L1 seed 1000 and on
survey S1 seed 1000 through the viewer; check that the planner, executor and replanner turns
appear in order with their roles, that the plan shown matches the scripted one, and that the
replay shows the same.

**Acceptance Scenarios**:

1. **Given** the viewer is open on any dungeon or survey level and dev seed, **When** the
   experimenter looks at the architecture list, **Then** `plan_execute` can be chosen.
2. **Given** an A3 episode is running, **When** the planner or replanner answers, **Then** its
   turn appears in the side panel marked with its role, showing the plan it wrote.
3. **Given** the executor is working on a subgoal, **When** it calls a tool, **Then** the step
   appears on the board as A2's would, and the panel shows which subgoal it is working on.
4. **Given** a finished A3 episode, **When** the experimenter replays it, **Then** every turn and
   step appears as it did live.

---

### User Story 2 - A3 plays both problems under the fairness rules (Priority: P1)

A3 gets the same model, base prompt, tool descriptions and step budget as every other
architecture on the problem. The planner and replanner make no tool calls; only the executor acts
on the world, and every one of its calls counts toward the one step budget. The episode ends the
way it ends for A2: on the dungeon when the exit is entered, on the survey field when a total is
submitted, and on either when the budget runs out or the architecture stops.

**Why this priority**: Without a working, fair A3 there is nothing to watch or compare.

**Independent Test**: With scripted models, play A3 episodes that reach the dungeon exit through
a locked door on L3, that submit the right total on S1, that run out of budget, and that stop
early; check the outcome rows, and check that the recorded base prompt, tool descriptions and
budget equal A2's on the same level and seed.

**Acceptance Scenarios**:

1. **Given** a dungeon level and seed, **When** A3's executor enters the exit room, **Then** the
   episode ends as a success, with steps counting every executor tool call.
2. **Given** a survey level and seed, **When** A3's executor submits a total, **Then** the episode
   ends and is scored like any other survey episode.
3. **Given** any episode, **When** the planner or replanner answers, **Then** no step is counted,
   and its model call and tokens are counted apart from the executor's.
4. **Given** the replanner decides the task is done but the episode has not ended (exit not
   reached, no total submitted), **When** A3 stops, **Then** the episode ends as given up, as for
   an A2 that stops talking.
5. **Given** A3's module, **When** the import test runs, **Then** it passes: A3 imports only the
   shared kit and the problems' public tool and result definitions.

---

### User Story 3 - A3 in runs, reports and the comparison (Priority: P2)

The experimenter plans, runs, continues and reports A3 episodes with the same commands as every
other architecture, on either problem. The comparison section places A3 next to its reference A2.
An A3 run on the M4 conditions (same model and settings, dev seed 1000 of L1–L3) can be reported
together with the M4 run, so that A3 joins that comparison without rerunning the others; the same
holds on the survey field for any run made under the same conditions.

**Why this priority**: The viewer shows single episodes. The comparison is how the experimenter
checks what they saw, and it is the plan's done-when for M6.

**Independent Test**: Plan an A3 run on both problems without `--execute` and check the matrix
and estimate; play a scripted A3 run, interrupt and continue it, and report it together with a
scripted run of the other architectures; check A3's comparison row and its reference.

**Acceptance Scenarios**:

1. **Given** `plan_execute` is named, **When** a run is planned without `--execute`, **Then** the
   plan shows the matrix and the usual estimate of model calls with hard bounds on tokens and
   cost, and no model is called.
2. **Given** an interrupted A3 run, **When** it is continued, **Then** only the missing episodes
   are planned, as for any other architecture.
3. **Given** an A3 run and an earlier run with the same conditions, **When** they are reported
   together, **Then** the comparison section shows A3 next to the others for each level, with
   `mapstate` as its reference and its Δ columns filled.
4. **Given** an A3 run and a run with different conditions (model, settings or prompt
   fingerprint), **When** they are reported together, **Then** the report refuses, as it does
   today.
5. **Given** the report for an A3 run, **When** the experimenter reads the calls column, **Then**
   it shows planner and replanner calls apart from executor calls.

---

### Edge Cases

- The planner's reply has no usable plan (empty, no subgoals, unreadable): it is asked again a
  small fixed number of times; then A3 stops and the episode ends as given up.
- The executor makes no tool call on a subgoal (it says the subgoal is done or impossible right
  away): the replanner is called with that report. A fixed number of subgoals in a row without a
  tool call stops A3, so a planner–replanner loop cannot spend tokens without ever acting.
- The executor never finishes a subgoal: after a fixed number of executor turns on one subgoal,
  the subgoal is handed back to the replanner as unfinished. That number is a constant, not
  derived from the step budget, because the budget would reveal the shortest solution
  (constitution II).
- The episode ends in the middle of a subgoal (exit entered, total submitted, budget used up): it
  ends at once, with no further planner or replanner call.
- The executor submits a survey total, or reaches the dungeon exit, during a subgoal that was
  about something else: the episode ends as for any other architecture; the plan does not matter.
- The replanner returns the same plan again unchanged: allowed; the executor goes on with its next
  open subgoal.
- The planner's or replanner's prompt grows past the model's context window: the episode ends as
  the architecture's failure, as for every architecture.
- A run or saved episode from before this feature: it still loads, continues and reports as
  before.

## Requirements *(mandatory)*

### Functional Requirements

**The architecture**

- **FR-001**: The lab MUST have an architecture A3 named `plan_execute`, registered for both the
  dungeon and the survey field.
- **FR-002**: A3 MUST have three jobs: a planner that writes an ordered list of subgoals at the
  start, an executor that works on one subgoal at a time through the problem's tools, and a
  replanner that, after each subgoal, keeps, changes or ends the plan.
- **FR-003**: The executor MUST keep its memory the way A2 does: a map built only from its own
  tool results, with its latest reply and that reply's tool results, not the message history. It
  MUST be told its current subgoal on every turn.
- **FR-004**: The planner and replanner MUST see the task (the problem's base prompt and the start
  result), the same map, and for the replanner the plan so far with each finished subgoal's report.
  They MUST NOT see anything that tool results have not revealed (constitution II).
- **FR-005**: Only the executor MUST make tool calls. Every tool call counts toward the episode's
  single step budget, failed calls included (constitution III).
- **FR-006**: The instructions A3 adds on top of the base prompt MUST explain each job's input
  and expected answer only; they MUST NOT give strategy advice beyond what planning itself is, so
  that A3's difference from A2 is the planning structure (as A2's map instructions explain the map
  and not where to go).
- **FR-007**: A3 MUST stop, ending the episode as given up, when the replanner ends the plan
  before the episode has ended, when the planner fails to give a usable plan after a fixed number
  of tries, or when a fixed number of subgoals in a row pass without a tool call.
- **FR-008**: A subgoal MUST end when the executor replies without a tool call (with its report),
  or after a fixed number of executor turns. All such limits MUST be constants, not derived from
  the step budget or any other value that reveals the solution.
- **FR-009**: On the survey field, submitting the total MUST be the executor's job like any other
  tool call; A3 MUST play the survey field with the field map A2 uses there.
- **FR-010**: A3's model calls MUST be marked by job, so that results, the report and the viewer
  can tell planner and replanner calls from executor calls.
- **FR-011**: The agent writes A3 in `src/apl/arch/`, at the experimenter's request; the
  experimenter reviews it afterwards. A3 MUST reuse the existing dungeon and field maps; the other
  architectures' behavior MUST NOT change.

**Runner and report**

- **FR-012**: `apl run`, `apl continue` and `apl report` MUST accept `plan_execute` on both
  problems as they accept the other architectures. Without `--execute`, no model is called
  (constitution VI).
- **FR-013**: The dry-run plan MUST list A3 like any other architecture. Its estimate of model
  calls MAY leave out planner and replanner calls, as it already leaves out orchestrator calls;
  tokens and cost MUST stay hard bounds through the token cap.
- **FR-014**: The comparison section MUST list A3 with `mapstate` as its reference.
- **FR-015**: The calls column of the report MUST show A3's planner and replanner calls apart from
  its executor calls, as it already shows orchestrator calls apart from scout calls.
- **FR-016**: An A3 run made under the same conditions as an earlier run MUST be reportable
  together with it, so A3 joins the M4 comparison (dev seed 1000 of L1–L3) and any survey
  comparison without rerunning the other architectures.

**Viewer**

- **FR-017**: The viewer MUST offer `plan_execute` on every dungeon and survey level.
- **FR-018**: The side panel MUST show planner and replanner turns marked by role, with the plan
  each wrote, and MUST show which subgoal the executor is on during its turns.
- **FR-019**: A3 episodes MUST be saved and replayable like every other episode.

**Docs**

- **FR-020**: plan.md (§4 table, §7 status) and the README's architecture table MUST list A3 as
  built, on both problems.

### Key Entities

- **Plan**: an ordered list of subgoals written by the planner and updated by the replanner; each
  subgoal is open, done or unfinished, and a finished one carries the executor's report.
- **Subgoal**: a short piece of work in words (for example "get the red key, then open the red
  door"), worked on by the executor until it reports or reaches the turn limit.
- **Executor report**: the executor's last reply on a subgoal, saying what it did and found.
- **Role**: the job a model call belongs to (planner, replanner, executor), recorded with each
  call.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every dungeon and survey level, an A3 episode with a scripted model can be
  started in the viewer, watched to its end and replayed, with every planner, replanner and
  executor turn shown in order.
- **SC-002**: A scripted A3 that follows the shortest solution on every dungeon level, and the
  reference walk plus the right total on every survey level, succeeds within the same step count as
  a scripted A2 doing the same.
- **SC-003**: On the same level and seed, A3's recorded base prompt fingerprint, tool descriptions
  and step budget equal A2's in 100% of checked episodes.
- **SC-004**: In 100% of A3 episodes, the steps counted equal the executor's tool calls, and
  planner and replanner calls add no step.
- **SC-005**: No scripted A3 episode, including ones whose planner never gives a usable plan or
  whose executor never calls a tool, runs without end; each ends within the fixed limits.
- **SC-006**: An A3 dry run on either problem calls no model, and the tests make no paid call.
- **SC-007**: On the dungeon, a report of a scripted A3 run together with a scripted run of the
  seven earlier architectures shows all eight per level; on the survey field, with the five that
  play it, all six. A3's reference is `mapstate` in both.
- **SC-008**: Every test, lint, format and type check passes, and every existing test still
  checks what it checked before.

## Assumptions

- A3 builds on A2's map, as plan.md and the M4 design (docs/parked/m4-comparison) intended, so it
  differs from A2 in planning alone and A2 is its reference. A ReAct executor (history memory)
  would mix a memory effect into the planning effect.
- The planner and replanner answer in plain structured text or a structured reply, not through
  the problem's tools; how exactly is a planning decision. They cost model calls and tokens but no
  steps, as orchestrator calls do for A7–A9.
- The fixed limits (planner tries, executor turns per subgoal, subgoals in a row without a tool
  call) are constants chosen in planning and may be tuned on dev seeds only (constitution V).
- "Added to the comparison on the same seeds" means A3 can be run and reported with the M4 run
  (dev seed 1000 of L1–L3, `openai:gpt-6-luna`) and with survey runs under the same conditions.
  No such run is part of this feature: running it and writing findings is the experimenter's
  choice afterwards, with `--execute`.
- No local or paid experiment run is started as part of this work unless the experimenter asks.
- The constitution needs no amendment: principle III already says every node's tool calls count
  toward the one budget.
- A4 Reflexion and A5 supervisor are later features (M6+), one per feature.
