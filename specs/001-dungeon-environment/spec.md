# Feature Specification: Dungeon Generator, Environment, Tools and Solver

**Feature Branch**: `001-dungeon-environment` (spec directory; no git branch is created)

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "M1 dungeon generator, environment, tools and solver"

## User Scenarios & Testing *(mandatory)*

The users of this feature are the experimenter, who runs and inspects experiments, and the
agent architectures built in later milestones, which play episodes through the four tools.
M1 involves no model. Everything here is exercised by code and tests.

### User Story 1 - Generate a solvable dungeon from a seed (Priority: P1)

The experimenter asks for a dungeon at level L1, L2 or L3 with a given seed. The same request
always gives the same dungeon. Each dungeon is solvable and comes with its shortest solution,
so later results can be scored against it.

**Why this priority**: Every later milestone runs on these dungeons. Without them there is
nothing to play, score or compare.

**Independent Test**: Generate dungeons for many seeds on every level. Check each against the
level rules, confirm it is solvable, and confirm the same seed reproduces the same dungeon.

**Acceptance Scenarios**:

1. **Given** level L2 and seed 7, **When** the dungeon is generated twice, **Then** both
   dungeons are identical: rooms, doors, locks, keys, start and exit.
2. **Given** any level and seed, **When** the dungeon is generated, **Then** it satisfies that
   level's rules (grid size, number of locks, extra doors, dead ends) and the solver reports
   it solvable with a shortest solution length.
3. **Given** level L3, **When** a dungeon is generated, **Then** the second key lies behind the
   first locked door, and the exit cannot be reached without opening both doors.

---

### User Story 2 - Play an episode through the four tools (Priority: P2)

An architecture starts an episode on a dungeon. It receives a description of the start room
and then acts only through `look`, `move`, `take` and `use`. Every call costs one step and
returns a structured result. The episode ends when the exit is reached, the step budget runs
out, or the caller stops. The result is a structured outcome record.

**Why this priority**: This is the surface every architecture uses, and it produces the raw
facts that scoring is built on.

**Independent Test**: Script sequences of tool calls by hand, including invalid ones, and check
every result, the step count and the final outcome record.

**Acceptance Scenarios**:

1. **Given** a fresh episode, **When** it starts, **Then** the caller receives the start room's
   description at no step cost, in the same form `look` returns.
2. **Given** a room with no door to the east, **When** the agent calls `move("east")`, **Then**
   the result is an error with code `no_door`, the agent stays put, and one step is counted.
3. **Given** a locked red door to the north and a red key in the inventory, **When** the agent
   calls `use("red key", "north")` and then `move("north")`, **Then** the door opens, the move
   succeeds, and two steps are counted.
4. **Given** an agent that enters the exit room, **When** the move completes, **Then** the
   episode ends with success, and any further call returns an `episode_over` error without
   counting a step or changing state.
5. **Given** an agent that uses its last allowed step without reaching the exit, **When** that
   call completes, **Then** the episode ends with the budget marked as hit.
6. **Given** an agent that leaves a room and later comes back by another route, **When** it
   arrives, **Then** the description shows the same room label as on the first visit.

---

### User Story 3 - Trust the shortest solution (Priority: P3)

The experimenter needs the solver's length to be the true shortest length, and needs it to
match what an agent can actually do through the tools. Two checks establish this. First, the
solver is run on hand-built reference dungeons whose shortest lengths were worked out
independently. Second, the solver's solution for each generated dungeon is replayed through the
tools.

**Why this priority**: Efficiency scores and step budgets both come from this number. If the
solver returned a valid route that was too long, every score would be wrong without anything
failing. It depends on Stories 1 and 2.

**Independent Test**: Solve the reference dungeons and compare each result with its known
optimum. Then replay the solution for every dungeon in the dev and test seed sets and compare
the step count with the reported length.

**Acceptance Scenarios**:

1. **Given** a hand-built dungeon where an all-open route and a shorter route through a locked
   door compete, the shorter one counting the key detour, `take` and `use`, **When** it is
   solved, **Then** the reported length equals the hand-worked optimum and uses the locked route.
2. **Given** the same layout with the key moved far enough away that the open route becomes
   shorter, **When** it is solved, **Then** the reported length equals the hand-worked optimum
   and uses the open route.
3. **Given** a hand-built dungeon with two chained keys, **When** it is solved, **Then** the
   reported length equals the hand-worked optimum.
4. **Given** a hand-built dungeon whose only key lies behind its own locked door, **When** it is
   solved, **Then** the solver reports it unsolvable.
5. **Given** any generated dungeon, **When** its shortest solution is replayed as tool calls,
   **Then** every call succeeds and the episode ends with success after exactly the reported
   number of steps.

---

### User Story 4 - Inspect a dungeon and a route as a text map (Priority: P4)

The experimenter prints a text map of a dungeon for a given level and seed. The map shows
rooms, doors, locks, keys, start and exit. Optionally, a route is drawn on top: either the
solver's shortest solution or the recorded actions of an episode. This makes it possible to
see by eye where an agent went, where it looped and where it got stuck.

**Why this priority**: It helps with debugging and learning but no scoring depends on it.

**Independent Test**: Render dungeons for a few seeds with and without the solver's route, and
check that every door, lock, key, start and exit appears, and that every room on the route is
marked in order.

**Acceptance Scenarios**:

1. **Given** level L3 and a seed, **When** the map is rendered, **Then** it shows the grid with
   each door, each locked door's color, each key's room, and the start and exit rooms.
2. **Given** a dungeon and its shortest solution, **When** the map is rendered with that route,
   **Then** every room on the route is marked with its visit order, and the steps where a key is
   taken and a door is opened are marked.
3. **Given** a recorded episode that revisits rooms and ends without reaching the exit, **When**
   the map is rendered with its route, **Then** revisited rooms show all their visit numbers,
   failed actions are marked where they happened, and the room the episode ended in is marked.

---

### User Story 5 - Watch a route play back as an animation (Priority: P5)

The experimenter produces a picture of a dungeon, with or without a route, and opens it in a
web browser. It shows the same information as the text map, drawn as a grid of rooms with
doors, colored locks and keys. With a route, the picture becomes an animation: the agent
moves through the dungeon step by step, keys disappear from rooms when taken, doors open when
used, and failed actions flash where they happen. Playback controls let the experimenter play,
pause, step and jump to any step.

**Why this priority**: Long, looping routes are much easier to understand when watched in order
than when read as a list of numbers. It builds on the same information as Story 4.

**Independent Test**: Produce animations for a few dungeons and routes, open them in a browser,
play them through, step back and forth, and check that the state shown at each step matches the
route.

**Acceptance Scenarios**:

1. **Given** level L3, a seed and the shortest solution, **When** the animation is produced,
   **Then** it is a single file that opens in a current web browser without network access, and
   it shows every room, door, lock color, key, the start and the exit.
2. **Given** that animation, **When** it is played, **Then** the agent's position moves one step
   at a time in route order, and the current step number, the action and its result are shown.
3. **Given** a step where a key is taken or a door is opened, **When** playback reaches it,
   **Then** the key leaves the room and joins the shown inventory, or the door is drawn open,
   and both stay that way for later steps.
4. **Given** a recorded episode with failed actions, **When** playback reaches a failed action,
   **Then** it is highlighted at the room where it happened and the agent does not move.
5. **Given** a paused animation, **When** the experimenter steps forward, steps back or jumps to
   a step, **Then** the dungeon shows exactly the state after that step, the same as if it had
   played there from the start.
6. **Given** a dungeon without a route, **When** the picture is produced, **Then** it is a still
   picture of the dungeon with no playback controls.
7. **Given** the same dungeon and route, **When** the file is produced twice, **Then** both
   files are identical.

---

### Edge Cases

- A tool is called with an unknown direction (for example `up`): error `invalid_direction`,
  one step counted.
- `take` names an item that is not in the room: error `no_such_item`, one step counted.
- `use` names a key the agent does not hold: error `not_in_inventory`.
- `use` with a key of the wrong color: error `wrong_key`; the door stays locked.
- `use` toward a direction with no door: error `no_door`.
- `use` on a door that is already open, or was never locked: error `not_locked`.
- `move` through a locked door: error `locked`, with the lock color.
- A tool is called after the episode ended for any reason: error `episode_over`, no step
  counted, no state change.
- The exit room is reached on the very last step of the budget: the outcome is success, and the
  budget is not marked as hit.
- A seed is given that is negative or not a whole number: generation is refused with a clear
  error.
- A requested level does not exist: generation is refused with a clear error.

## Requirements *(mandatory)*

### Functional Requirements

**Generation**

- **FR-001**: The generator MUST build an N×N grid of rooms, where doors only join rooms that
  are horizontal or vertical neighbors.
- **FR-002**: The generator MUST first join all rooms with a random spanning tree, so every room
  is reachable when locks are ignored, and then add the level's number of extra doors to create
  loops.
- **FR-003**: The start and exit MUST be different rooms, at least 2·(N−1) moves apart when locks
  are ignored.
- **FR-004**: Each locked door MUST have a color and open only with the key of that color.
  Colors within one dungeon MUST be distinct.
- **FR-005**: Every locked door MUST be necessary: with that door treated as a wall, the exit
  MUST be unreachable from the start. Extra doors therefore never bypass a lock.
- **FR-006**: Each key MUST be reachable from the start before its door is opened. It MUST NOT be
  in the start room, and MUST NOT lie on the shortest lock-ignoring route from the start to its
  door, so that getting it requires a detour.
- **FR-007**: On L3, the second key MUST lie behind the first locked door, so the doors must be
  opened in order.
- **FR-008**: On L3, the dungeon MUST contain at least 2 dead ends: rooms with exactly one door
  that are not the start or exit and hold no key.
- **FR-009**: Generation MUST be deterministic: the same level and seed MUST give an identical
  dungeon on every run and every machine.
- **FR-010**: The levels MUST be as follows:

  | Level | Grid | Locked doors | Extra doors | Dead ends (min) |
  | --- | --- | --- | --- | --- |
  | L1 | 3×3 | 0 | 1 | none |
  | L2 | 4×4 | 1 | 2 | none |
  | L3 | 5×5 | 2, chained | 3 | 2 |

**Solver**

- **FR-011**: The solver MUST search over the state (room, keys held, doors opened) and MUST
  return either "unsolvable" or a shortest action sequence and its length in steps. It MUST
  accept hand-built dungeons as well as generated ones, so that it can be checked against
  reference dungeons with known answers.
- **FR-012**: Shortest length MUST count `move`, `take` and `use` actions, one step each. The
  free starting description is not counted, and no `look` is needed in an optimal solution.
- **FR-013**: Every dungeon handed out by the generator MUST have been confirmed solvable by
  the solver, with its shortest length recorded.

**Environment and tools**

- **FR-014**: An episode MUST start in the start room with an empty inventory, and MUST give the
  caller the start room's description at no step cost.
- **FR-015**: The agent-facing surface MUST offer exactly four tools:

  | Tool | Success result | Possible errors |
  | --- | --- | --- |
  | `look()` | The current room's description | `episode_over` |
  | `move(direction)` | The new room's description | `invalid_direction`, `no_door`, `locked`, `episode_over` |
  | `take(item)` | The updated inventory | `no_such_item`, `episode_over` |
  | `use(item, direction)` | Confirmation that the door opened | `invalid_direction`, `no_door`, `not_in_inventory`, `wrong_key`, `not_locked`, `episode_over` |

- **FR-016**: A room description MUST list the room's label (FR-017), its doors (direction,
  plus lock color for a locked door), the items in the room, the inventory, and whether this
  room is the exit. Directions are `north`, `south`, `east` and `west`.
- **FR-017**: Each room description MUST include the room's label. Labels MUST be unique within
  the dungeon, the same every time the room is entered, and reproducible from the seed. They
  MUST be drawn at random from the seed, without repeats, from a fixed pool of at least 100
  labels, independent of position and layout, so that any label can land on any room. A label
  MUST NOT be derived from coordinates, door layout, distance to the exit, or the order in which
  rooms were generated.
- **FR-018**: Every tool result MUST be structured data with a fixed shape: whether it
  succeeded, an error code and a short message on failure, and the payload on success. Every
  tool call before the episode ends counts as one step, including invalid calls.
- **FR-019**: An opened door MUST stay open from both sides for the rest of the episode. A key
  MUST stay in the inventory after use.
- **FR-020**: The step budget MUST be 3 × the shortest length. The episode MUST end with success
  when the agent enters the exit room, with budget hit when the budget is used up first, or
  with "stopped" when the caller ends it early.
- **FR-021**: When an episode ends, the environment MUST produce a structured outcome record with
  at least: level, seed, success, end reason, steps taken, shortest length, invalid actions and
  budget hit. It MUST also keep the ordered log of every tool call and its result, so that the
  episode's route can be drawn (FR-025).
- **FR-022**: The agent-facing surface MUST NOT expose the dungeon layout, the solver result
  (including the shortest length), or any room other than the current one. Only the runner and
  scoring code may read those.

**Seeds and inspection**

- **FR-023**: There MUST be fixed, disjoint sets of dev seeds and test seeds for every level.
- **FR-024**: The experimenter MUST be able to render a dungeon as a text map that shows rooms,
  doors, lock colors, keys, start and exit. The map is a debugging aid, not part of the
  agent-facing surface.
- **FR-025**: The text map MUST optionally draw a route on top of the dungeon. A route is either a
  solver solution or an episode's recorded log. The overlay MUST mark each visited room with its
  visit numbers (all of them for revisited rooms), the steps where a key was taken or a door
  opened, each failed action at the room where it happened, and the room where the route ends.
- **FR-026**: The experimenter MUST be able to produce a picture of a dungeon, with or without a
  route, that shows the same information as the text map and its overlay. The picture MUST be a
  single self-contained file that opens in a current web browser without network access, and
  the same input MUST always produce an identical file.
- **FR-027**: The text map and the picture MUST be produced from the same underlying description
  of dungeon and route, so that they cannot disagree. Neither is part of the agent-facing
  surface.
- **FR-028**: With a route, the picture MUST animate it step by step: the agent's position, the
  current step number, the action and its result, the inventory, keys leaving rooms when taken,
  doors opening when used, and failed actions highlighted at their room. It MUST offer play,
  pause, step forward, step back, jump to any step and a playback speed control, and the state
  shown after any step MUST be the same however that step was reached. Without a route, the
  picture is a still image.

### Key Entities

- **Level**: A named difficulty (L1–L3) with a grid size, a number of locked doors, a number of
  extra doors, and a minimum number of dead ends.
- **Dungeon**: A generated grid for one level and seed: rooms, doors, locked doors with colors,
  keys and their rooms, start room, exit room, and the solver's shortest solution.
- **Room**: One grid cell with an opaque label. It has up to four doors and may hold keys.
- **Door**: A connection between two neighboring rooms. It is open, or locked with a color.
- **Key**: An item with a color that opens the locked door of the same color.
- **Episode**: One play-through of a dungeon: current room, inventory, opened doors, steps taken,
  invalid actions, budget, and end reason.
- **Tool result**: The structured answer to one tool call: success flag, error code and message,
  or payload.
- **Outcome record**: The structured summary of a finished episode used for scoring, plus the
  ordered log of tool calls and results.
- **Route**: An ordered list of actions on one dungeon, taken from a solver solution or an
  episode log, with the room each action happened in and whether it succeeded.
- **Seed set**: A named, fixed list of seeds (dev or test) per level.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For every seed in the dev and test sets, and for at least 1,000 additional seeds per
  level, 100% of generated dungeons satisfy every level rule and are confirmed solvable.
- **SC-002**: For every dungeon in the dev and test sets, replaying the shortest solution reaches
  the exit in exactly the reported number of steps, in 100% of cases. This shows the solver and
  the environment agree. SC-008 shows the length is actually the shortest.
- **SC-003**: Generating the same level and seed twice, in separate runs, gives identical
  dungeons in 100% of the checked cases.
- **SC-004**: Across 100 seeds per level, at least 95 distinct dungeons are produced.
- **SC-005**: Every error code listed in FR-015 is produced by at least one test, and every one
  of those tests also shows that the step was counted, or not counted for `episode_over`.
- **SC-006**: Generating and solving the full dev and test seed sets for all three levels takes
  under 10 seconds on a normal laptop.
- **SC-007**: No result an agent can receive contains information about rooms other than the
  current one; this is checked by tests that inspect every tool result shape.
- **SC-008**: On at least 5 hand-built reference dungeons with independently worked-out answers
  (competing open and locked routes in both directions, chained keys, and at least one
  unsolvable case), the solver's result matches the known answer in 100% of cases.
- **SC-009**: Room labels are unique in every generated dungeon, identical when the same level and
  seed are generated again, and identical on every revisit within an episode, in 100% of checked
  cases. Across 100 seeds per level, every grid position receives at least 10 different labels,
  which rules out any fixed mapping from position to label. A design review confirms that labels
  come only from the seeded random draw in FR-017.
- **SC-010**: For every dungeon in the dev seed sets, the text map and the picture both show 100%
  of the dungeon's doors, lock colors, keys, start and exit, and with the shortest solution drawn
  they mark 100% of the route's rooms in visit order.
- **SC-011**: Producing the text map or the picture twice from the same input gives identical
  output in 100% of checked cases, and each picture opens in a current web browser without
  network access.
- **SC-012**: For the shortest solution of every dev dungeon, the state the animation shows after
  each step (position, inventory, keys in rooms, open doors) matches the environment's state
  after the same step, in 100% of steps. Jumping straight to a step shows the same state as
  playing up to it.

## Assumptions

- The only items in M1 are keys. Distractor items may come in a later milestone.
- "Give up" is not a fifth tool. The runner ends an episode as "stopped" when an architecture
  finishes without reaching the exit. Ending it does not cost a step.
- The starting description is free, so a perfect agent could in principle reach an efficiency
  of 1.0.
- Seed sets: 10 dev seeds and 20 test seeds per level. Plan.md's M3 comparison uses 10 dev
  seeds. The test set size can grow before the first reported result without breaking
  anything.
- Extra-door counts per level (1, 2, 3) are this spec's reading of "a few extra doors".
- Tool descriptions written for the model, the runner, the results file and the report belong
  to M2.
- No paid model calls happen in this feature.
- The animation shows one route at a time. Comparing two architectures' routes side by side
  can come with the report in a later milestone.
- Playback speed has a sensible default and a simple speed control. Exact timing is not
  specified.
- In M1, routes come from solver solutions and from hand-scripted episodes. Agent episodes
  start producing logs in M2, which then reuses the same overlay and picture.
