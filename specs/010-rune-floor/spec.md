# Feature Specification: The Rune Floor

**Feature Branch**: `010-rune-floor` (spec directory; work happens on git branch `m10-rune-floor`)

**Created**: 2026-11-02

**Status**: Draft

**Input**: User description: "M10, feature 010: the rune floor, the lab's fourth problem (plan.md §9
lists it among the problem mock-ups; visual mock-up: https://claude.ai/artifact/VEDrZX6TuFapmV4rHkTCqB,
section "Rune floor"). The agent crosses a grid floor of colored tiles from a start S to a goal G. A
hidden rule decides which tiles are safe (for example: the colors stepped on must go red, blue,
green, then repeat). Every tile's color is given free at the start, like the signal trace's layout;
only the rule is hidden. Stepping on a tile that breaks the rule is a trap: it sends the agent back
to S, the knowledge it gathered stays with it, and the steps walked are spent. All attempts share
one step budget. The property this board is built to show: a learnable rule. A1 ReAct keeps hitting
the same trap, while A4 Reflexion stops after a trap, writes a note on what the rule might be, and
its next attempt follows the rule to G. For A4 a trap ends its attempt while attempts are left, like
a wrong total on the survey field or a wrong segment on the signal trace. Levels: R1 a small floor
with a 3-color cycle; R2 a larger floor with a longer cycle or a cycle with a repeat; R3 a rule that
is not about color order (for example alternating rows, or a step count); plus R0, a control floor
with no rule (a random safe path), where reflecting can only cost budget, the mock-up's weak side
for A4. Scored by code: success when the agent reaches G, steps against a reference (the shortest
safe path), traps hit, traps hit again on a tile already known to be a trap, invalid actions,
calls, tokens. Architectures A1 react, A2 mapstate, A3 plan_execute, A4 reflexion and A6 hybrid
play it; A2 keeps the tiles tried and their outcomes, A6's code keeps known-safe and known-trap
tiles and offers moves but cannot know the rule. The scouts (A7–A9) and the supervisor (A5) are left
out: one walker on one path. The agent writes the graph changes and the experimenter reviews them.
It plugs into the multi-problem support exactly like the survey field and the signal trace: its own
tools, level ladder, seeds, scoring and step budget; the fairness rules (same model, prompt, tool
descriptions and budget; world access only through the problem's tools; structured results; dev vs
test seeds; no paid call without --execute) apply within the problem; the constitution's tool rule
is amended to name the new tools; the dungeon, the survey field and the signal trace stay
unchanged. apl run, apl continue, apl report and apl serve take it as a problem; the viewer shows
the floor, the trails of earlier attempts faded, traps as crosses, and the current position. Done
when: any rune-floor level and seed can be shown and watched in the viewer, rune-floor runs plan,
continue and report like the other problems, and the existing problems are unchanged. No paid or
local experiment runs are started as part of this work unless explicitly requested."

## Clarifications

### Session 2026-11-02

- Q: What does the agent see, and what happens on a wrong tile? → A: Every tile's color is given
  free at the start; only the rule is hidden. A trap sends the agent back to S and costs the steps
  walked; what the agent learned stays with it. For A4 a trap also ends its attempt while attempts
  are left.
- Q: Which levels? → A: R1–R3 with rules of growing difficulty, plus R0, a control floor with no
  rule.
- Q: Which architectures? → A: A1–A4 and A6, as on the signal trace. A5 and A7–A9 are left out.
- Q: Who writes the rune-floor versions of the architectures in `src/apl/arch/`? → A: The agent, at
  the experimenter's request, as in M5–M9; the experimenter reviews them afterwards.
- Q: Which step budget? → A: 4× the reference (the shortest safe path): about three wrong walks
  and the right one.

## User Scenarios & Testing *(mandatory)*

The user of this feature is the experimenter. Each problem in the lab is built to show one
property: the survey field shows splitting the work, the signal trace shows choosing what to look
at next. The rune floor shows learning from failure. The floor's colors are all visible, but a
hidden rule decides which tiles are safe, and the only way to find the rule is to be trapped by it.
An agent that keeps no lesson from a trap walks into the same trap again; one that stops, writes
down what the trap suggests, and tries again should reach the goal on its second or third walk.
That is the side of A4 Reflexion no other board shows. The control level R0 has no rule to learn,
so there reflecting can only cost calls and tokens: A4's weak side.

The rune floor in one paragraph: a rectangle of colored tiles with a start S on one side and a goal
G on the other. The agent moves one tile at a time. Some steps are safe and some are traps,
according to a rule the agent is not told; for example, the tiles stepped on since S must follow
the colors red, blue, green, red, blue, green, and so on. A trap sends the agent back to S. The
episode is a success when the agent reaches G.

Architectures in this feature:

| Name | Architecture | On the other problems | On the rune floor |
| --- | --- | --- | --- |
| `react` | A1 ReAct | as before | yes |
| `mapstate` | A2 map state | as before | yes, with a walk log in state (every walk's tiles and how it ended; nothing inferred) |
| `plan_execute` | A3 plan-and-execute | as before | yes, with A2's walk log |
| `reflexion` | A4 Reflexion | as before | yes: a trap ends an attempt while attempts are left, and A4 reflects on it |
| `hybrid` | A6 hybrid | as before | yes: code keeps what happened on each tile and offers the moves; the model picks one |
| `mapstate_routes`, `supervisor`, `fanout`, `rounds`, `blackboard` | A2r, A5, A7–A9 | as before | no |

### User Story 1 - Watch an architecture cross a rune floor (Priority: P1)

In the viewer, the experimenter picks the rune floor, a level and a dev seed, and sees the floor.
They pick an architecture and press Run. Every step appears on the floor as it happens: the current
walk is drawn as a bold trail from S, earlier walks stay as faded trails, and each trap is marked
with a cross where it sprang. A panel shows the attempt or walk number, the steps against the
reference and the budget, the traps hit and how many of them repeated an earlier trap, and, at the
end, whether G was reached. For A4 the reflection notes appear in the side panel with the model
turns. Episodes are saved and can be replayed.

**Why this priority**: Watching the trails pile up on the same trap, or turn aside after a note,
is the point of the board. It needs the problem itself (US2) and is the first thing the
experimenter will use.

**Independent Test**: Start the viewer, open the rune floor R1 seed 1000, play a scripted agent
that hits one trap and then follows the rule to G, and check that the trails, the trap cross, the
counts and the replay all match the saved events.

**Acceptance Scenarios**:

1. **Given** the viewer is open, **When** the experimenter picks the rune floor, level R1 and seed
   1000, **Then** the floor is shown with every tile's color, S and G, the rule written out and the
   reference path outlined; with "Agent's view" on, the rule and the reference path are hidden.
2. **Given** an episode is running, **When** the agent steps on a safe tile, **Then** the current
   trail grows by that tile and the position marker moves.
3. **Given** an episode is running, **When** the agent steps on a trap, **Then** a cross marks the
   tile, the walk's trail fades, the marker returns to S, and the trap counter grows (and the
   repeated-trap counter, when the same mistake was made before).
4. **Given** an episode ends, **When** the experimenter looks at the panel, **Then** it shows
   whether G was reached, the steps against the reference, the traps and repeated traps.
5. **Given** an architecture that does not play the rune floor, **When** the experimenter looks at
   the architecture list for this problem, **Then** it cannot be chosen.
6. **Given** a test seed, **When** the experimenter enters it, **Then** the viewer refuses it, as
   it does for the other problems.

---

### User Story 2 - The rune-floor problem (Priority: P1)

A seed and a level always build the same floor with the same rule. The agent acts only through
the rune floor's tools, each call costs one step, and errors are structured like the other
problems'. Every floor has a reference computed by code, which sets the step budget and the
efficiency score.

**Why this priority**: Without it there is nothing to watch or compare. It is listed second only
because it is invisible on its own.

**Independent Test**: Generate floors for every level and every dev and test seed, check that each
has a safe path from S to G under its rule and that the obvious straight route is not safe, play
scripted walks against the tools and check every result, and check that a seeded floor is
identical across runs.

**Acceptance Scenarios**:

1. **Given** a floor, **When** an episode starts, **Then** the agent is given the floor free, as
   the other problems give their start view: its size, every tile's color, where S and G are, and
   where the agent stands. `look` returns the same view again for one step.
2. **Given** the agent moves onto a tile the rule allows, **When** the call returns, **Then** the
   agent stands on that tile and the result says so, with the tile's color.
3. **Given** the agent moves onto a tile the rule forbids, **When** the call returns, **Then** the
   result says it was a trap and where, the agent stands on S again, and the walk starts over;
   the result does not state the rule.
4. **Given** the agent moves off the floor, **When** the call returns, **Then** it fails with a
   structured error, costs a step, and the agent does not move.
5. **Given** the agent steps onto G, **When** the call returns, **Then** the episode ends as a
   success.
6. **Given** the step budget is used up before G, **When** the episode ends, **Then** it is a
   failure, marked as out of budget.

---

### User Story 3 - Run, continue and report on the rune floor (Priority: P2)

The experimenter plans and runs rune-floor episodes with the same commands as for the other
problems, naming the problem. The plan is free and shows the matrix and an estimate; `--execute`
plays it. An interrupted run can be continued. The report adds the rune floor's own columns: how
often G was reached, the steps against the reference, the traps hit, and the traps that repeated an
earlier mistake.

**Why this priority**: The viewer shows the difference on one seed. A run with repeats is how the
experimenter checks whether it holds across seeds.

**Independent Test**: Plan a rune-floor run without `--execute` and check the matrix; play a run
with scripted architectures, interrupt it, continue it, and check the report against the rows.

**Acceptance Scenarios**:

1. **Given** the rune floor is named, **When** the experimenter plans a run without `--execute`,
   **Then** the plan shows the rune-floor levels, seeds, architectures and an estimate, and no model
   is called.
2. **Given** a rune-floor run names an architecture that does not play it, **When** it is planned,
   **Then** it is refused with a message that names the architecture and the problem.
3. **Given** an interrupted rune-floor run, **When** the experimenter continues it, **Then** only
   the missing episodes are planned, as for the other problems.
4. **Given** a completed rune-floor run, **When** the report is written, **Then** it shows, per
   architecture and level, the success share, median steps, median efficiency, median traps, median
   repeated traps, budget hits, tokens and latency, with the spread across repeats, and the
   comparison section.

---

### User Story 4 - The fairness rules hold on the rune floor (Priority: P2)

Within the rune floor every architecture gets the same model, base prompt, tool descriptions and
step budget, and reaches the floor only through its tools. The rule, the trap tiles and the
reference path are never visible to an architecture except through the results of its own moves.
Results from the rune floor are never combined with results from another problem.

**Why this priority**: The lab's results mean nothing if the rules are not checked. The import test
and the recorded fingerprints must cover the new problem.

**Independent Test**: The test that limits what architectures may import passes with the rune
floor's public tool and result definitions added, and fails for an architecture that reads the
floor's generator or its rule.

**Acceptance Scenarios**:

1. **Given** the constitution, **When** this feature is done, **Then** principle II names the rune
   floor's tools, the Experiment Setup describes its floors, rules, reference and budget, the
   attempt rule covers a trap, and the version and amendment date are updated.
2. **Given** an architecture that imports the rune floor's generator or rule, **When** the tests
   run, **Then** the import test fails.
3. **Given** two architectures on the same rune-floor level, **When** their episodes run, **Then**
   both got the same base prompt, tool descriptions and step budget, as recorded in the results.

---

### Edge Cases

- The agent walks back onto S during a walk: S is not a colored tile; the walk starts over from S
  without a trap, and the step is spent.
- The agent steps back onto a tile it already stepped on in the same walk: the rule judges that
  step like any other (a color-order rule counts it as the next tile in the sequence).
- The same tile can be safe at one point of a walk and a trap at another under a color-order rule;
  a repeated trap is the same tile in the same situation under the rule (for a color-order rule, at
  the same point in the sequence), not merely the same tile.
- A move into a wall of the floor (off the edge) or an unknown direction: the call fails with a
  structured error, costs a step, and the agent stays where it is; it is not a trap.
- G is next to the last safe tile: stepping onto G always ends the episode as a success, whatever
  the rule.
- The step budget runs out in the middle of a walk: the episode ends as a failure, marked out of
  budget.
- A model reply has no tool call: the episode ends as a failure, marked as given up, as on the
  other problems.
- A4 hits a trap while attempts are left: the attempt ends with a result that says only that it
  was a trap and where; the floor and its rule are unchanged; every step of every attempt counts
  toward the one budget. With no attempt left, a trap sends A4 back to S like any other
  architecture and the episode goes on.
- On R0 there is no rule to learn: each trap tile is a trap whenever it is stepped on, so the only
  lesson is "not that tile".
- Dungeon, survey and signal-trace runs, reports and saved episodes from before this feature still
  load, continue and report as before.

## Requirements *(mandatory)*

### Functional Requirements

**The rune floor**

- **FR-001**: The rune floor MUST be a fourth problem next to the dungeon, the survey field and the
  signal trace, with its own tools and their descriptions, base prompt, levels, dev and test
  seeds, reference, scoring and step budget rule.
- **FR-002**: A floor MUST be generated from a level and a seed, identical every time for the same
  pair. It MUST be a rectangle of colored tiles with a start S on the left edge and a goal G on the
  right edge, and a hidden rule that decides whether each step is safe.
- **FR-003**: Every floor MUST have at least one safe path from S to G under its rule, and the
  shortest route that ignores the rule MUST NOT be safe, so the rule cannot be ignored.
- **FR-004**: The rune floor MUST have four levels:

  | Level | Floor | Rule | Purpose |
  | --- | --- | --- | --- |
  | R0 | small (about 7×5) | none: a fixed set of trap tiles, with a safe path left open | Control: nothing to learn beyond "not that tile", so reflecting can only cost |
  | R1 | small (about 7×5) | a cycle of 3 colors: the tiles stepped on since S must follow it | Baseline rule; one trap shows most of it |
  | R2 | larger (about 9×7) | a longer cycle, or a cycle that repeats a color | The rule takes more than one trap to pin down |
  | R3 | larger (about 9×7) | a rule about where a tile lies rather than the order of colors | The obvious guess (a color order) is wrong |

  The exact rule families, floor sizes and color counts are settled in the plan.

- **FR-005**: Agents MUST act only through these tools, each call costing one step, failed calls
  included:

  | Tool | Returns |
  | --- | --- |
  | `look()` | The floor again: its size, every tile's color, S, G, and where the agent stands |
  | `move(direction)` | The tile moved onto and its color, a trap (where, and that the agent is back on S), the goal reached, or an error (off the floor, unknown direction) |

  The floor is also given free at the start of the episode, as the other problems give their start
  view, so an agent never needs `look` to begin.

- **FR-006**: Results and errors MUST be structured data with the same shape as the other problems'
  (`ok`, `error` with `code` and `message`, `data`). A trap is a successful call whose result says
  it was a trap, not an error. No result MUST ever state the rule.
- **FR-007**: An episode MUST end when the agent reaches G, when the step budget is used up, or
  when the architecture stops. It MUST be a success exactly when G was reached.
- **FR-008**: Code MUST compute a reference for every floor: the number of moves on the shortest
  safe path from S to G under its rule.
- **FR-009**: The step budget MUST be 4× the reference: room for about three wrong walks and the
  right one, which matches A4's three attempts, while an agent that keeps repeating a long wrong
  walk runs out.
- **FR-010**: A retrying architecture (A4) MUST be able to restart the floor up to 3 attempts per
  episode, as on the other problems: a trap ends its attempt while attempts are left, a restart
  costs no step, the floor and its rule are unchanged, and all attempts share one budget.

**Runner and report**

- **FR-011**: `apl run` MUST accept the rune floor as a problem; `apl continue` and `apl report`
  MUST take it from the run. A show command MUST print a floor for a level and seed, with an option
  to show the rule and the reference path. Without `--execute`, no model is called (constitution
  VI).
- **FR-012**: Each rune-floor result row MUST record, besides the fields every episode records:
  whether G was reached, the reference, the traps hit, the repeated traps, and the number of walks.
- **FR-013**: A trap MUST count as repeated when the agent was already trapped on the same tile in
  the same situation under the rule earlier in the episode (for a color-order rule, at the same
  point in the sequence; on R0, on the same tile).
- **FR-014**: The rune-floor report MUST show per architecture and level: the success share, median
  steps, median efficiency (steps against the reference), median traps, median repeated traps,
  budget hits, tokens and latency, with the spread across repeats, and the comparison section M4
  introduced.

**Viewer**

- **FR-015**: The viewer MUST offer the rune floor as a problem; its levels, seeds and the
  architectures that play it MUST follow from that choice.
- **FR-016**: For the rune floor, the viewer MUST draw every tile in its color, S and G, the current
  walk as a trail, earlier walks as faded trails, every trap as a cross where it sprang, the
  agent's position, the rule and the reference path unless "Agent's view" hides them, and a panel
  with the walk number, steps against the reference and the budget, traps and repeated traps, and
  whether G was reached.
- **FR-017**: The step slider, replay of saved episodes and the side panel of model turns MUST work
  for the rune floor as for the other problems.

**Rules**

- **FR-018**: The constitution MUST be amended: principle II names the rune floor's tools and
  forbids reading the rule, the trap tiles and the reference path; the Experiment Setup gains the
  rune floor's generation, rules, reference and budget; the attempt rule covers a trap on the rune
  floor.
- **FR-019**: Architectures MUST be allowed to import only the shared kit and each problem's public
  tool and result definitions; the import test MUST enforce this for the rune floor.
- **FR-020**: The dungeon, the survey field and the signal trace MUST behave exactly as before:
  same worlds per seed, tools, prompts, budgets, scoring and results format.

**Architectures**

- **FR-021**: A1 (`react`) MUST play the rune floor with its base prompt and tools and nothing else
  changed.
- **FR-022**: A2 (`mapstate`) MUST play the rune floor with a walk log in its state, rendered each
  turn: the floor, and every walk so far as its tiles in order and how it ended, with no inference
  drawn from them.
- **FR-023**: A3 (`plan_execute`) and A4 (`reflexion`) MUST play the rune floor with the same walk
  log as A2, since both build on A2's memory; A4 reflects after a trap as it does after a wrong
  total on the survey field.
- **FR-024**: A6 (`hybrid`) MUST play the rune floor with code that keeps what happened each time a
  tile was stepped on (safe or trap, and at which step of the walk) and offers the possible moves
  with that record; the model picks the move. Code MUST work only with what earlier tool results
  revealed, and MUST NOT guess the rule.
- **FR-025**: The agent writes the rune-floor versions of A1–A4 and A6 in `src/apl/arch/`, at the
  experimenter's request; the experimenter reviews them afterwards. Their behavior on the other
  problems MUST NOT change.

### Key Entities

- **Floor**: a rectangle of colored tiles with S and G, generated from a level and a seed, with a
  hidden rule, a reference and a step budget.
- **Rule**: what decides whether a step is safe: a color cycle over the walk (R1, R2), a rule about
  a tile's place (R3), or a fixed set of trap tiles (R0).
- **Walk**: the tiles stepped on since the agent last stood on S; it ends at a trap, at S, or at G.
- **Trap**: a step the rule forbids: where it sprang, in which walk, and whether it repeated an
  earlier mistake.
- **Rune-floor outcome**: the result of one episode: success, steps, reference, traps, repeated
  traps, walks, budget hit, and the fields every episode records.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every dungeon, survey and signal-trace command from before this feature produces the
  same output, and every existing test passes without changes to what it checks.
- **SC-002**: For every rune-floor level and every dev and test seed, the generated floor is
  identical across runs, has a safe path from S to G under its rule, and the shortest route that
  ignores the rule springs a trap.
- **SC-003**: A scripted agent that knows the rule and walks the reference path reaches G on every
  level and seed in exactly the reference number of steps.
- **SC-004**: On every level and seed, a scripted agent that walks the shortest route, is trapped
  once, and then knows the rule reaches G within the budget; a scripted agent that never learns
  and repeats its first walk runs out of budget. The gap the board is built to show exists by
  construction.
- **SC-005**: In the viewer, the experimenter can go from opening the page to watching an R1
  episode in under a minute, and can replay it afterwards step by step.
- **SC-006**: Every rune-floor tool result, error and outcome in a saved episode can be checked by
  code against the floor, with no free-text parsing; the trap and repeated-trap counts are
  reproduced from the saved steps alone.
- **SC-007**: A dry-run plan for the rune floor never calls a model, and the tests never make a
  paid call.

## Assumptions

- Problem name `rune`, levels R0–R3; the seed numbers are the other problems' (dev 1000–1009, test
  2000–2019), keyed by the problem name, so the floors are unrelated to the other worlds.
- The floor's colors are public and given free at the start, because the board tests learning the
  rule, not exploration. `look()` repeats the view for one step, like every tool call (constitution
  III), for an agent that has lost it.
- The base prompt says that a hidden rule decides which steps are safe and that a trap sends the
  agent back to S; it is the same on every level, R0 included, where the "rule" is a fixed set of
  trap tiles. It never states or hints at a rule's content.
- A trap is a normal tool result, not an error, so it does not count as an invalid action; a move
  off the floor does.
- Moves are the four compass directions, as on the dungeon and the survey field.
- A5 and A7–A9 are left out: there is one walker on one path, so scouts would only take turns on
  it, and a supervisor would split nothing. A2r is left out because the floor has no routes to
  precompute.
- A4's 3 attempts mean up to two reflections in an episode; with no attempt left it plays on like
  any other architecture.
- This feature includes no paid or local experiment run. Running a comparison and writing findings
  is the experimenter's choice afterwards, with the commands from US3.
- The constitution amendment adds a problem without changing a principle's meaning, so it is a
  MINOR version (2.3.0), made with `/speckit-constitution` before this feature's plan.
- The visual mock-up linked in the input shows intended behavior; its numbers are illustrative.
