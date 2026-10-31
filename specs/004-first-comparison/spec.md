# Feature Specification: First Comparison, with Orchestrator Architectures

**Feature Branch**: `004-first-comparison` (spec directory; no git branch is created)

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "M4: first comparison of A1 ReAct (react), A2 map state (mapstate),
A2r map state with routes (mapstate_routes) and A6 hybrid (hybrid) on the same dev/test seeds,
levels L1–L3, with the 6× step budget (constitution v1.1.0) and the local vLLM qwen3.5-9b model.
Continuable runs, a comparison report and a written conclusion; the episode count is decided
here. Build on the parked design in docs/parked/m4-comparison/ (which assumed A1 vs A2 and 180
episodes at the old 3× budget)."

## Clarifications

### Session 2026-10-31

- Q: Should the orchestrator patterns be part of M4? → A: Yes, as additional architectures next to
  the four existing ones, with one episode per level each.
- Q: How do the orchestrator patterns play in a dungeon with one agent position? → A: Several
  scouts in the dungeon, each with its own position, sharing one step budget; the goal is still
  reaching the exit.
- Q: Which seeds, repeats and model? → A: One dev seed per level, one episode per architecture and
  level, on `openai:gpt-6-luna` for speed.
- Q: One episode at a time, or several at once? → A: One at a time.
- Q: Should the agent write A7–A9 (`scouts.py`, `fanout.py`, `rounds.py`, `blackboard.py`)? → A: Yes,
  as with A2r and A6; the experimenter reviews them afterwards.

## User Scenarios & Testing *(mandatory)*

The user of this feature is the experimenter, who runs the comparison and writes up what it
shows. Seven architectures take part:

| Name | Architecture | Scouts | What the model does itself |
| --- | --- | --- | --- |
| `react` | A1 ReAct | 1 | Everything, remembering only through the message history |
| `mapstate` | A2 map state | 1 | Everything, from a map built from its tool results |
| `mapstate_routes` | A2r map state with routes | 1 | Chooses and walks routes the map lists for it |
| `hybrid` | A6 hybrid | 1 | Only picks a target; code walks there |
| `fanout` | A7 fan-out once | several | An orchestrator splits the dungeon once; scouts explore to the end |
| `rounds` | A8 supervisor in rounds | several | An orchestrator hands out short tasks each round and replans on the merged map |
| `blackboard` | A9 shared blackboard | several | No planner: scouts take one step each in turn and claim frontiers on a shared map |

The first four answer three questions from plan.md: does explicit memory beat history (A1 vs
A2), does a planning aid help a small model (A2 vs A2r), and how much of the work needs a model at
all (A2r vs A6). The three orchestrators ask whether splitting the exploration between several
scouts helps, and which way of coordinating them works best. Their scout is A2's map-state agent,
so A2 is their single-agent reference.

M4 is a first look, not a measurement: each architecture plays one dev dungeon per level, once.

### User Story 1 - Several scouts in one dungeon (Priority: P1)

An episode can have several scouts. Each scout has its own position and inventory, and acts only
through the four tools. Opened doors stay open and taken items are gone for every scout. Every
tool call of every scout counts toward the episode's one step budget, and the episode ends as soon
as any scout enters the exit room. The single-agent architectures play exactly as before, as an
episode with one scout.

**Why this priority**: The three orchestrator architectures cannot exist without it, and it must
not change how the four existing ones play or score.

**Independent Test**: Play scripted scouts on generated dungeons and check positions, inventories,
doors, the shared step count and the end of the episode after every call; replay the saved log and
compare.

**Acceptance Scenarios**:

1. **Given** an episode with two scouts in the start room, **When** scout 1 moves east and scout 2
   moves north, **Then** each scout is in its own new room, and the episode has used 2 steps.
2. **Given** scout 1 holds the red key, **When** scout 2 uses the red key on the red door, **Then**
   it fails with "not in inventory", costs a step, and the door stays locked.
3. **Given** scout 1 opened a door, **When** scout 2 reaches that door, **Then** it can move
   through it.
4. **Given** several scouts, **When** any of them enters the exit room, **Then** the episode ends
   as a success, and the steps of all scouts count toward its efficiency.
5. **Given** the step budget is used up by the scouts together, **When** another scout calls a
   tool, **Then** the episode has already ended as out of budget.
6. **Given** an architecture tries to create more scouts than allowed, **When** it asks for one,
   **Then** it is refused and the episode goes on.
7. **Given** any of the four existing architectures, **When** it plays a seed, **Then** its tool
   results, steps and outcome are the same as before this feature.
8. **Given** a saved multi-scout episode, **When** it is replayed, **Then** every scout's position,
   inventory and every door match the log at every step.

---

### User Story 2 - Three orchestrator architectures (Priority: P2)

The experimenter can pick `fanout`, `rounds` and `blackboard` like any other architecture, in the
runner and in the viewer.

- **Fan-out once**: the orchestrator is called once with the start room, decides how many scouts
  to send and gives each a task and a share of the budget. The scouts explore in turn until their
  task is done or their share is used up, never hearing from each other. If no scout reached the
  exit by then, the episode ends as stopped.
- **Supervisor in rounds**: each round the orchestrator sees the merged map of all scouts and the
  steps left, and gives each scout a short task (for example "explore the frontier at k7" or
  "bring the red key to the red door at m2"). Scouts report back, their maps are merged, and the
  next round starts, until a scout reaches the exit or the orchestrator gives up.
- **Shared blackboard**: there is no planner. Scouts take turns, one tool call each. After each
  call, what the scout saw is added to one shared map, which every scout sees on its next turn,
  together with which frontier each scout has claimed. A scout picks an unclaimed frontier and
  claims it.

**Why this priority**: These are the new architectures this milestone adds; they need Story 1.

**Independent Test**: Play each orchestrator with scripted orchestrator and scout answers on dev
dungeons of every level, and check which scouts were created, what each model call was shown, and
that the merged map matches the tool results of all scouts.

**Acceptance Scenarios**:

1. **Given** each orchestrator architecture and scripted answers that lead a scout to the exit,
   **When** it plays a dev dungeon of each level, **Then** every episode succeeds.
2. **Given** any orchestrator architecture, **When** its maps are merged, **Then** the merged map
   contains exactly what the tool results of all scouts revealed, and nothing else.
3. **Given** the fan-out architecture, **When** it plays, **Then** the orchestrator is called exactly
   once, and no scout's input contains another scout's results.
4. **Given** the supervisor architecture, **When** a round starts, **Then** the orchestrator's input
   contains the merged map and the number of steps left.
5. **Given** the blackboard architecture, **When** a scout is called, **Then** its input contains
   the shared map with every scout's position and every claimed frontier.
6. **Given** the architecture source files, **When** the boundary checks run, **Then** the
   orchestrator architectures reach the dungeon only through the four tools of their scouts.

---

### User Story 3 - Watch several scouts in the viewer (Priority: P3)

In the viewer, a multi-scout episode shows every scout's position and trail in its own color, and
each model turn says whether it was the orchestrator or which scout. "Agent's view" shows the
rooms any scout has been in. Saved multi-scout episodes replay like the others.

**Why this priority**: plan.md requires every architecture to be watchable; without it the
orchestrators' behavior can only be read from logs.

**Independent Test**: Play a scripted two-scout episode in the viewer, then replay it, and check
the positions, trails and turn labels at several steps.

**Acceptance Scenarios**:

1. **Given** a running multi-scout episode, **When** a scout moves, **Then** its marker and trail
   update, and the other scouts' markers stay where they are.
2. **Given** a model turn of a multi-scout episode, **When** it is shown, **Then** it is labelled
   "orchestrator" or "scout N".
3. **Given** a saved multi-scout episode, **When** the slider is moved to step k, **Then** every
   scout is shown where it was after step k.

---

### User Story 4 - Run the comparison as one fair, continuable run (Priority: P4)

The experimenter runs all seven architectures in one run: the levels L1–L3, the first dev seed,
one repeat, the same model and settings for all. An interrupted run can be continued, playing only
the missing episodes, and a run whose model provider keeps failing stops instead of filling up
with error rows.

**Why this priority**: It produces the rows for the report. Continuing matters less with 21
episodes than with hundreds, but a paid run that fails half-way should not be paid for twice.

**Independent Test**: Start a scripted seven-architecture run, interrupt it twice, continue it each
time, and check that the finished run holds every planned episode exactly once, with rows equal to
an uninterrupted run of the same scripted episodes.

**Acceptance Scenarios**:

1. **Given** the comparison run, **When** it is planned without `--execute`, **Then** the dry run
   shows 21 episodes, upper bounds on model calls, tokens and cost, all seven architectures under
   one set of settings, and the code version it will record.
2. **Given** the comparison run, **When** it plays, **Then** the episodes go level by level, and
   within a level all seven architectures play before the next level starts.
3. **Given** an interrupted run, **When** the experimenter continues it, **Then** only the missing
   episodes are played, the finished ones are kept unchanged, and the run is marked complete at
   the end.
4. **Given** an interrupted run, **When** the experimenter tries to continue it with different
   settings, a different code version or uncommitted changes, **Then** continuing is refused with
   a message naming each difference, and nothing is played or written.
5. **Given** a run, **When** 3 episodes in a row end in infrastructure errors, **Then** the run
   stops, stays incomplete, and says how to continue it once the provider is back.

---

### User Story 5 - Compare the architectures and write down what it shows (Priority: P5)

The report shows all seven architectures side by side per level: success, efficiency, steps,
tokens, model calls (split into orchestrator and scout calls) and latency, plus the number of
scouts used. The experimenter writes a conclusion: the questions, the setup, the table, what it
suggests per question and level, why one episode per cell cannot settle anything, and what to run
next.

**Why this priority**: The milestone is done when the conclusion exists (plan.md M4). It depends
on all other stories.

**Independent Test**: Build the report from hand-written runs with known outcomes and check every
figure by hand; check every number in the conclusion against the cited run's report.

**Acceptance Scenarios**:

1. **Given** rows of several architectures, **When** the report is built, **Then** per level it
   shows each architecture's success, efficiency, steps, tokens, model calls by role, latency and
   scouts used, with a difference column against each architecture's reference (A1 for A2, A2 for
   A2r, A2r for A6, A2 for A7–A9).
2. **Given** rows of one architecture, **When** the report is built, **Then** it is as in M2.
3. **Given** a finished comparison run, **When** the conclusion is written, **Then** it names the
   run, the model and settings and the seed, says it is a development result from one episode per
   cell, and every number it quotes matches the report.
4. **Given** the conclusion, **When** it is read, **Then** it addresses each question per level,
   states at least one limitation and one next step, and records the episode count and why it was
   chosen.

---

### Edge Cases

- Two scouts are in the same room: both may act there; a key taken by one is gone for the other.
- A scout tries to use a key another scout holds: it fails as "not in inventory" and costs a step.
- A scout enters the exit while other scouts still have calls planned: the episode ends at once,
  and later calls are not played.
- An orchestrator creates no scout at all: the episode ends as stopped with 0 steps.
- A scout of the fan-out architecture uses up its share of the budget: it stops; the others go on.
- The orchestrator's answer names no valid task: it is asked again at no step cost, and after 3
  such answers in a row the episode ends as stopped (as A6 does).
- Merged maps disagree (a scout saw a door locked that another has since opened): the newer
  observation wins.
- A1's history outgrows the model's context window: the episode ends as A1's failure and is scored.
- The paid provider rejects requests permanently (for example an invalid key): the run stops at
  once, as in M2.
- A run is continued after the code changed, was started with uncommitted changes, or is already
  complete: continuing is refused, or does nothing and says so.

## Requirements *(mandatory)*

### Functional Requirements

**Several scouts**

- **FR-001**: An episode MUST support up to 4 scouts. Each scout MUST have its own position and
  inventory and start in the start room. The doors, the items left in rooms and the step budget
  MUST be shared.
- **FR-002**: Every scout MUST act only through `look`, `move`, `take` and `use`
  (Constitution II). Creating a scout MUST NOT cost a step and MUST NOT reveal anything beyond the
  start room's description.
- **FR-003**: Every tool call of every scout MUST count toward the episode's one step budget
  (Constitution III). The episode MUST end when any scout enters the exit room or the budget is
  used up. Efficiency MUST remain the shortest solution divided by the steps of all scouts.
- **FR-004**: Tool calls MUST be applied one at a time in a fixed order, so that an episode plays
  and replays the same way. The episode log MUST record which scout made each call.
- **FR-005**: An episode with one scout MUST behave and be recorded exactly as before, so the four
  existing architectures and earlier saved episodes are unaffected.

**Orchestrator architectures**

- **FR-006**: The architectures `fanout` (A7), `rounds` (A8) and `blackboard` (A9) MUST be
  selectable by name in the runner and the viewer, as described in User Story 2.
- **FR-007**: All three MUST use the same scout: A2's map-state agent with its instructions, given a
  task. Merged maps MUST be built only from the scouts' tool results (Constitution II).
- **FR-008**: The orchestrators MUST use the shared model, like every architecture
  (Constitution I), and MUST pass the same boundary checks.
- **FR-009**: Every model call MUST be recorded with its role: orchestrator, or the scout's number.

**Viewer**

- **FR-010**: The viewer MUST show each scout's marker and trail in its own color, label each model
  turn with its role, include every scout's rooms in "Agent's view", and replay saved multi-scout
  episodes step by step.

**Comparison run**

- **FR-011**: The comparison MUST be one run with all seven architectures on levels L1–L3, dev seed
  1000, one repeat (21 episodes), on `openai:gpt-6-luna`, with the 6× step budget. It MUST need
  `--execute` (Constitution VI), and its report and conclusion MUST be headed as a development
  result that must not be reported (Constitution V).
- **FR-012**: Episodes MUST be played one at a time, in the order level, seed, repeat, then
  architecture.
- **FR-013**: The dry run MUST show the code version the run will record and say when uncommitted
  changes would make the run impossible to continue.
- **FR-014**: An interrupted run MUST be continuable: continuing plays only the episodes without a
  row, keeps the finished rows and files unchanged, and marks the run complete at the end.
  Continuing without `--execute` MUST be a dry run.
- **FR-015**: Continuing MUST be refused, naming every difference, if the settings, the prompt
  fingerprint, the package versions or the code version differ from the run's record, if the tree
  has uncommitted changes, if the run started with uncommitted changes, or if an architecture of
  the run is no longer available.
- **FR-016**: An episode interrupted mid-way MUST leave no row that counts as finished.
- **FR-017**: After 3 infrastructure-error episodes in a row, the run MUST stop, stay incomplete,
  exit with a distinct exit code and print how to continue it.

**Report and conclusion**

- **FR-018**: For rows of two or more architectures, the report MUST show per level each
  architecture's success, efficiency, steps, tokens, model calls by role, latency and scouts used,
  and the difference to its reference architecture (A1 for A2, A2 for A2r, A2r for A6, A2 for
  A7–A9). With one architecture it MUST stay as in M2. All figures MUST be computed by code from the
  rows (Constitution IV), and the same rows MUST give the same report byte for byte.
- **FR-019**: The conclusion MUST be a document in the repository, linked from the README, that
  names the run id, the model and settings, the seed and that it must not be reported, includes the
  report's table, addresses each question per level, states that one episode per cell cannot
  separate a real difference from luck, and gives at least one next step and the reason for the
  episode count. Every number it quotes MUST match the report.

### Key Entities

- **Scout**: One body in an episode: a number, a position and an inventory. Single-agent
  architectures have exactly one.
- **Episode log entry**: One tool call with its result, now also naming the scout that made it.
- **Model call record**: One model call with its role (orchestrator or scout N), tokens and
  latency.
- **Merged map**: The union of what all scouts' tool results revealed, as seen by an orchestrator
  or on the blackboard.
- **Comparison run**: One run with seven architectures, three levels, one seed and one repeat;
  continuable after an interruption.
- **Conclusion**: The written result of the milestone, tied to one run.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On every dev dungeon of all three levels, the four existing architectures with their
  scripted test models produce the same results as before this feature, in 100% of episodes.
- **SC-002**: Scripted multi-scout episodes on at least 5 dungeons replay with every scout's
  position and inventory and every door matching the log at 100% of steps.
- **SC-003**: Each orchestrator architecture with scripted answers succeeds on a dev dungeon of
  each level, and its merged map matches all scouts' tool results at 100% of steps.
- **SC-004**: A scripted seven-architecture run interrupted at least twice and continued each time
  ends with all 21 episodes exactly once, with rows equal to an uninterrupted run.
- **SC-005**: Every figure of the report built from hand-written runs matches a hand calculation.
- **SC-006**: The comparison run completes all 21 episodes, with infrastructure errors (if any)
  listed separately.
- **SC-007**: The written conclusion exists, cites the run, and 100% of the numbers it quotes match
  that run's report.

## Assumptions

- The model is `openai:gpt-6-luna` for all seven architectures, with the current settings for a
  non-vLLM provider (4,096 output tokens per call, a token cap of 2,000,000 per episode, a
  300-second timeout). The prices in `.env` give the dry run's cost estimate. Local vLLM stays the
  default for development and tests.
- Seven saved viewer episodes on `gpt-6-luna` averaged about 46 seconds and 31,000 tokens, against
  about 180 seconds and 69,000 tokens on the local model. Single-agent episodes should therefore
  take about a minute; orchestrator episodes make more model calls and take longer. The whole run
  should take well under two hours.
- The seed is the first dev seed (1000) of each level. With one episode per cell, M4 shows
  tendencies only. The per-dungeon comparison and sign test of the parked design are left for a
  later run with several seeds and repeats, because with one seed they add nothing to the
  side-by-side table.
- At most 4 scouts per episode, a limit set by the shared setup, not by each architecture, so that
  all orchestrators work under the same limit.
- Inventories are per scout, so handing a key from one region to another is a real coordination
  task, which is what the supervisor and blackboard patterns are meant to test.
- The shortest solution stays the single-agent one, so efficiency compares all architectures on the
  same scale: several scouts can reach the exit sooner in time, but not in total steps.
- A7–A9 are written by the agent at the experimenter's request, as A2r and A6 were; the
  experimenter may write them instead. A2r and A6 were also written before their milestones; they
  are part of this comparison, and plan.md's milestone table and architecture list are updated to
  include A7–A9.
- Several scouts may need a constitution amendment (Principle III speaks of "the episode's single
  step budget", which still holds, but the Experiment Setup assumes one agent); `/speckit-plan`'s
  Constitution Check decides.
- Results from before constitution v1.1.0 (the 3× budget) are not compared with this run.
- The conclusion is written by the experimenter. An agent may draft it from the report, and the
  experimenter checks and edits it. No LLM judges anything.
- The parked design in `docs/parked/m4-comparison/` is the starting point for continuing, code
  identity, the interleaved order and stopping on provider failures (its research R8–R11).
