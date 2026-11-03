# Feature Specification: The Warehouse

**Feature Branch**: `012-warehouse` (spec directory; work happens on git branch `m12-warehouse`)

**Created**: 2026-11-02

**Status**: Draft

**Input**: User description: "M12, feature 012: the warehouse, the lab's sixth problem (plan.md §9
lists it among the problem mock-ups as "warehouse robots"; visual mock-up:
https://claude.ai/artifact/VEDrZX6TuFapmV4rHkTCqB, section "Warehouse robots"). A grid warehouse
with shelf rows that form aisles, a drop zone D, and packages placed in the aisles. Up to 4 robots
start at a dock on the west side; the packages are not given at the start: a robot sees what is in
the aisle it stands in, so packages are found by exploring. Each robot carries at most one package;
a package counts as delivered when a robot drops it on D. The episode is a success when every
package is delivered. Tools per robot: look, move(direction), pick, drop. Every tool call of every
robot costs one step from one shared step budget; a single-agent architecture drives one robot. The
property this board is built to show: adapting a split of the work as information arrives. A7
fan-out once splits blindly and never adapts; A8 rounds replans on the merged map and reassigns; A9
blackboard lets robots claim packages without an orchestrator but takes turns. Architectures: A1
react and A2 mapstate (one robot), and A7 fanout, A8 rounds and A9 blackboard with up to 4 robots.
A3–A6 are left out. Scored by code: success, steps against a reference, parallel turns, idle
robot-turns, packages delivered, invalid actions, calls, orchestrator calls, tokens. Levels grow
the floor, the number of packages and the unevenness. Robots may share cells. It plugs into the
multi-problem support like the other problems; the constitution's tool rule is amended; the other
five problems stay unchanged. apl run, continue, report and serve take it; an apl warehouse show
command draws a level and seed; the viewer draws shelves, fog over unseen aisles, the robots in the
scout colors, packages, D and delivered counts; the About card covers each architecture on it.
Done when: any warehouse level and seed can be shown and watched in the viewer, warehouse runs
plan, continue and report like the other problems, and the other problems are unchanged."

## User Scenarios & Testing *(mandatory)*

The user of this feature is the experimenter. Each problem in the lab is built to show one
property: the survey field shows splitting the work, the signal trace choosing what to look at
next, the rune floor learning from failure, the workshop planning ahead. The warehouse shows
**adapting a split of the work as information arrives**. The packages are spread unevenly and are
found only by looking, so a split decided before anyone has looked is often wrong: one robot's
share is empty and it idles, while another's share holds two packages. An orchestrator that splits
once (A7) never finds out; one that replans each round on what every robot has seen (A8) can move a
package to the idle robot; robots that claim work from a shared board (A9) need no orchestrator but
act one at a time. On the survey field the same three architectures could split a field into
regions that never depend on each other. Here the split itself must change during the episode,
which no other board asks for.

The warehouse in one paragraph: a rectangular floor with rows of shelves that leave corridors
between them (the aisles) and two cross corridors at the ends. The floor plan (shelves, corridors,
the dock and the drop zone D) is known from the start; the packages are not. A robot sees every cell
of the corridor it stands in, so a package becomes known when some robot enters its aisle. A robot
carries at most one package, picks it up on its cell and delivers it by dropping it on D. The
episode is a success when every package is delivered.

Architectures in this feature:

| Name | Architecture | On the other problems | On the warehouse |
| --- | --- | --- | --- |
| `react` | A1 ReAct | as before | yes, one robot |
| `mapstate` | A2 map state | as before | yes, one robot, with a floor map in state (corridors seen, packages seen, what it carries, packages delivered; nothing inferred); the scouts' single-agent reference |
| `fanout` | A7 fan-out once | as before | yes: up to 4 robots, tasks decided once before anyone has looked |
| `rounds` | A8 supervisor in rounds | as before | yes: up to 4 robots, short tasks replanned each round on the merged map |
| `blackboard` | A9 shared blackboard | as before | yes: up to 4 robots taking turns on one live map, claiming packages |
| `mapstate_routes`, `plan_execute`, `reflexion`, `supervisor`, `hybrid` | A2r, A3–A6 | as before | no |

### User Story 1 - Watch robots clear the warehouse (Priority: P1)

In the viewer, the experimenter picks the warehouse, a level and a dev seed, and sees the floor: the
shelves, the corridors, the dock, D and every package. They pick an architecture and press Run.
Every step appears as it happens: robots move in the scout colors, a package shows on the robot
that carries it, a delivered package leaves the floor and the delivered count goes up. With
"Agent's view" on, corridors no robot has stood in yet are dimmed and their packages hidden. A
panel shows packages delivered, steps against the reference and the budget, parallel turns and idle
robot-turns, and at the end whether every package was delivered. The side panel shows each model
turn, with the orchestrator's and each robot's turns marked as for the scouts on the other
problems, and the About card shows the architecture's graph on the warehouse. Episodes are saved
and can be replayed.

**Why this priority**: Watching a robot sit idle in an empty aisle while another walks back and
forth, or watching A8 reassign a package, is the point of the board. It needs the problem itself
(US2) and is the first thing the experimenter will use.

**Independent Test**: Start the viewer, open warehouse P2 seed 1000, play a scripted single robot
that follows the reference and a scripted A7 whose split leaves one robot in the empty aisle, and
check that the floor, the robots, the carried packages, the delivered count and the replay all
match the saved events.

**Acceptance Scenarios**:

1. **Given** the viewer is open, **When** the experimenter picks the warehouse, level P2 and seed
   1000, **Then** the floor, the dock, D and every package are shown, with the reference walk
   drawn when asked; with "Agent's view" on, packages in corridors no robot has stood in are hidden.
2. **Given** an episode is running, **When** a robot enters a corridor, **Then** that corridor and
   its packages become visible under "Agent's view".
3. **Given** an episode is running, **When** a robot picks a package or drops it on D, **Then** the
   package moves with the robot or leaves the floor, and the delivered count changes.
4. **Given** an episode with several robots, **When** the experimenter steps through it, **Then**
   each robot is drawn in its scout color, and the panel shows parallel turns and idle robot-turns.
5. **Given** an architecture that does not play the warehouse, **When** the experimenter looks at
   the architecture list for this problem, **Then** it cannot be chosen.
6. **Given** a test seed, **When** the experimenter enters it, **Then** the viewer refuses it, as it
   does for the other problems.

---

### User Story 2 - The warehouse problem (Priority: P1)

A seed and a level always build the same warehouse. Robots act only through the warehouse's tools,
each call costs one step from the one budget, and errors are structured like the other problems'.
Every warehouse has a reference computed by code, which sets the step budget and the efficiency
score.

**Why this priority**: Without it there is nothing to watch or compare. It is listed second only
because it is invisible on its own.

**Independent Test**: Generate warehouses for every level and every dev and test seed and check
them (every package reachable, the level's spread of packages, the reference walk delivers every
package within the budget); play scripted sequences of calls for one and for several robots and
check every result; check that a seeded warehouse is identical across runs.

**Acceptance Scenarios**:

1. **Given** a warehouse, **When** an episode starts, **Then** the first robot is given the floor
   plan, its cell, what it sees in its corridor, what it carries and the packages delivered so far,
   free, as the other problems give their start view. `look` returns the same view for one step.
2. **Given** a robot, **When** it moves into a corridor cell, **Then** the result is the new view;
   moving into a shelf or off the floor fails with a structured error and the robot stays.
3. **Given** a robot carrying nothing on a cell with a package, **When** it picks, **Then** it
   carries that package; with no package there, or while already carrying one, the call fails with
   a structured error.
4. **Given** a robot carrying a package on D, **When** it drops, **Then** the package is delivered;
   dropping anywhere else, or carrying nothing, fails with a structured error.
5. **Given** the last package is delivered, **When** the call returns, **Then** the episode ends as
   a success.
6. **Given** the step budget is used up first, **When** the episode ends, **Then** it is a failure,
   marked as out of budget, with the number of packages delivered recorded.

---

### User Story 3 - Run, continue and report on the warehouse (Priority: P2)

The experimenter plans and runs warehouse episodes with the same commands as for the other
problems, naming the problem. The plan is free and shows the matrix and an estimate; `--execute`
plays it. An interrupted run can be continued. The report adds the warehouse's own columns: how
often every package was delivered, the median packages delivered, steps against the reference,
parallel turns and idle robot-turns.

**Why this priority**: The viewer shows the difference on one seed. A run with repeats is how the
experimenter checks whether it holds across seeds.

**Independent Test**: Plan a warehouse run without `--execute` and check the matrix; play a run with
scripted architectures, interrupt it, continue it, and check the report against the rows.

**Acceptance Scenarios**:

1. **Given** the warehouse is named, **When** the experimenter plans a run without `--execute`,
   **Then** the plan shows the warehouse levels, seeds, architectures and an estimate, and no model
   is called.
2. **Given** a warehouse run names an architecture that does not play it, **When** it is planned,
   **Then** it is refused with a message that names the architecture and the problem.
3. **Given** an interrupted warehouse run, **When** the experimenter continues it, **Then** only the
   missing episodes are planned, as for the other problems.
4. **Given** a completed warehouse run, **When** the report is written, **Then** it shows, per
   architecture and level, the success share, median packages delivered, median steps, median
   efficiency, median parallel turns, median idle robot-turns, robots used, budget hits, tokens and
   latency, with the spread across repeats, and the comparison section.

---

### User Story 4 - The fairness rules hold on the warehouse (Priority: P2)

Within the warehouse every architecture gets the same model, base prompt, tool descriptions and
step budget, and reaches the warehouse only through its tools. Package positions are never visible
to an architecture except through its robots' own views, and the reference never. Results from the
warehouse are never combined with results from another problem.

**Why this priority**: The lab's results mean nothing if the rules are not checked. The import test
and the recorded fingerprints must cover the new problem.

**Independent Test**: The test that limits what architectures may import passes with the
warehouse's public tool and result definitions added, and fails for an architecture that reads the
warehouse's generator or its package positions.

**Acceptance Scenarios**:

1. **Given** the constitution, **When** this feature is done, **Then** principle II names the
   warehouse's tools, the Experiment Setup describes its floors, reference and budget, and the
   version and amendment date are updated.
2. **Given** an architecture that imports the warehouse's generator or package positions, **When**
   the tests run, **Then** the import test fails.
3. **Given** two architectures on the same warehouse level, **When** their episodes run, **Then**
   both got the same base prompt, tool descriptions and step budget, as recorded in the results.

---

### Edge Cases

- Two robots stand on the same cell: allowed; robots never block each other in this feature.
- Two robots try to pick the same package in the same parallel turn: the calls are applied in robot
  order, as the scouts' calls are on the other problems; the first gets it and the second's call
  fails because no package is there any more.
- A robot picks a package another robot's task named: allowed; tasks are the architecture's
  business, the warehouse only knows who carries what.
- A robot drops a package anywhere but D: the call fails, costs a step, and the robot keeps carrying
  it; packages are never left on the floor away from their start.
- A robot in a cross corridor sees that corridor; packages stand only in the aisles between shelves.
- A single-agent architecture never adds a robot; its episode has one robot and no idle
  robot-turns.
- An orchestrator asks for more than 4 robots: as on the other problems, no robot is added beyond
  the limit and the architecture is told so.
- The budget runs out while a robot carries a package: the package counts as not delivered.
- A model reply has no tool call: the robot (or the single agent) stops, as on the other problems.
- Directions and package names are matched exactly as the results write them; anything else is an
  error.
- Dungeon, survey, signal-trace, rune-floor and workshop runs, reports and saved episodes from
  before this feature still load, continue and report as before.

## Requirements *(mandatory)*

### Functional Requirements

**The warehouse**

- **FR-001**: The warehouse MUST be a sixth problem next to the dungeon, the survey field, the
  signal trace, the rune floor and the workshop, with its own tools and their descriptions, base
  prompt, levels, dev and test seeds, reference, scoring and step budget rule.
- **FR-002**: A warehouse MUST be generated from a level and a seed, identical every time for the
  same pair. It MUST consist of a rectangular floor with shelf rows that leave aisles between them,
  a cross corridor at each end, a dock on the west side where robots start, a drop zone D on the
  east side, and packages, each on an aisle cell. Every package MUST be reachable from the dock and
  D.
- **FR-003**: The warehouse MUST have three levels:

  | Level | Floor | Packages | Spread | Purpose |
  | --- | --- | --- | --- | --- |
  | P1 | small (about 3 aisles) | 3 | one in every aisle | Baseline; every architecture should finish |
  | P2 | small (about 3 aisles) | 3 | one aisle empty, one aisle with two | The mock-up: a blind split leaves a robot idle |
  | P3 | larger (about 5 aisles) | about 6 | uneven, with an empty aisle and a crowded one | More robots worth sending, more to reassign |

  The exact floor sizes, counts and generator rules are settled in the plan.

- **FR-004**: Robots MUST act only through these tools, each call costing one step from the shared
  budget, failed calls included:

  | Tool | Returns |
  | --- | --- |
  | `look()` | The robot's cell, the corridors it stands in and the packages it sees there, what it carries, whether it is on D, and the packages delivered out of the packages in the warehouse |
  | `move(direction)` | The same view after one step north, east, south or west; or an error (shelf, edge of the floor, unknown direction) |
  | `pick()` | That the robot now carries the package on its cell; or an error (no package here, already carrying one) |
  | `drop()` | That the carried package is delivered; or an error (not on D, carrying nothing) |

  The floor plan (shelves, corridors, dock, D), the number of packages in the warehouse and the
  first robot's view are given free at the start of the episode, as the other problems give their
  start view.

- **FR-005**: Results and errors MUST be structured data with the same shape as the other problems'
  (`ok`, `error` with `code` and `message`, `data`). No result MUST show a package in a corridor the
  robot is not standing in, or the reference.
- **FR-006**: An architecture with scouts MUST be able to add robots up to 4, as on the other
  problems: each added robot starts on the dock with its own view, its tool calls count toward the
  one budget, and the robots' calls in one parallel turn are applied in robot order.
- **FR-007**: An episode MUST end when every package is delivered, when the step budget is used up,
  or when the architecture stops. It MUST be a success exactly when every package was delivered.
- **FR-008**: Code MUST compute a reference for every warehouse: the steps of a single robot that
  knows nothing at the start, walks the aisles in a fixed order, and carries each package to D as
  soon as it sees it before going on. It is marked as a reference, not an optimum.
- **FR-009**: The step budget MUST be 3× the reference, as on the survey field, the same for every
  architecture and every number of robots.

**Runner and report**

- **FR-010**: `apl run` MUST accept the warehouse as a problem; `apl continue` and `apl report`
  MUST take it from the run. `apl warehouse show` MUST print a warehouse for a level and seed, with
  an option to show the reference. Without `--execute`, no model is called (constitution VI).
- **FR-011**: Each warehouse result row MUST record, besides the fields every episode records: the
  packages delivered, the packages in the warehouse, the robots used, the parallel turns, and the
  idle robot-turns.
- **FR-012**: Parallel turns MUST be counted as on the survey field: the groups of tool calls
  applied between two model calls, where calls applied together after the robots' parallel model
  calls count once. For one robot they equal its model turns that made tool calls.
- **FR-013**: Idle robot-turns MUST count, for every parallel turn, the robots already in the
  episode that made no tool call in it, while undelivered packages remain.
- **FR-014**: The warehouse report MUST show per architecture and level: the success share, median
  packages delivered, median steps, median efficiency (the reference against the steps), median
  parallel turns, median idle robot-turns, median robots used, budget hits, tokens and latency,
  with the spread across repeats, and the comparison section M4 introduced.

**Viewer**

- **FR-015**: The viewer MUST offer the warehouse as a problem; its levels, seeds and the
  architectures that play it MUST follow from that choice.
- **FR-016**: For the warehouse, the viewer MUST draw the shelves, the corridors, the dock, D, the
  packages, and every robot in its scout color with the package it carries; under "Agent's view"
  it MUST dim the corridors no robot has stood in and hide their packages; and a panel with packages
  delivered, steps against the reference and the budget, parallel turns, idle robot-turns, and
  whether every package was delivered.
- **FR-017**: The step slider, replay of saved episodes, the side panel of model turns and the About
  card MUST work for the warehouse as for the other problems.

**Rules**

- **FR-018**: The constitution MUST be amended: principle II names the warehouse's tools and forbids
  reading package positions except through the robots' views, and the reference; the Experiment
  Setup gains the warehouse's generation, reference and budget.
- **FR-019**: Architectures MUST be allowed to import only the shared kit and each problem's public
  tool and result definitions; the import test MUST enforce this for the warehouse.
- **FR-020**: The dungeon, the survey field, the signal trace, the rune floor and the workshop MUST
  behave exactly as before: same worlds per seed, tools, prompts, budgets, scoring and results
  format.

**Architectures**

- **FR-021**: A1 (`react`) MUST play the warehouse with one robot, its base prompt and tools and
  nothing else changed.
- **FR-022**: A2 (`mapstate`) MUST play the warehouse with one robot and a floor map in its state,
  rendered each turn: the floor plan, the corridors seen, the packages seen and where, what the
  robot carries, and the packages delivered, with no inference drawn from them.
- **FR-023**: A7 (`fanout`), A8 (`rounds`) and A9 (`blackboard`) MUST play the warehouse with up to
  4 robots, each robot a scout (A2's map-state agent with a task) on the warehouse's floor map:
  A7's orchestrator decides the tasks once from the start view; A8's orchestrator gives short tasks
  each round from the map merged from every robot; A9's robots take turns on one live map and claim
  packages or corridors on it. Their graphs and their behavior on the dungeon and the survey field
  MUST NOT change.
- **FR-024**: The agent writes the warehouse versions of these architectures in `src/apl/arch/`, at
  the experimenter's request; the experimenter reviews them afterwards. Their behavior on the other
  problems MUST NOT change.
- **FR-025**: The viewer's About card MUST describe each of these architectures on the warehouse,
  and its tests MUST cover the new pairs.

### Key Entities

- **Warehouse**: a floor with shelves, aisles, cross corridors, a dock and D, and packages on aisle
  cells, generated from a level and a seed, with a reference and a step budget.
- **Corridor**: an aisle between two shelf rows, or a cross corridor; a robot sees all of the one it
  stands in.
- **Robot**: a body on the floor with a cell and at most one carried package; up to 4 per episode.
- **Package**: an item on an aisle cell, carried by at most one robot, delivered when dropped on D.
- **Warehouse outcome**: the result of one episode: success, packages delivered, packages in the
  warehouse, robots used, steps, reference, parallel turns, idle robot-turns, budget hit, and the
  fields every episode records.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every dungeon, survey, signal-trace, rune-floor and workshop command from before this
  feature produces the same output, and every existing test passes without changes to what it
  checks.
- **SC-002**: For every warehouse level and every dev and test seed, the generated warehouse is
  identical across runs, every package is reachable, and the packages follow the level's spread;
  on P2 and P3 at least one aisle is empty and at least one holds two or more packages.
- **SC-003**: A scripted single robot that follows the reference delivers every package on every
  level and seed in exactly the reference number of steps.
- **SC-004**: On every P2 seed, a scripted split that sends one robot per aisle before looking
  leaves at least one robot idle while packages remain, and a scripted replanning split delivers
  every package in fewer parallel turns. The gap the board is built to show exists by construction.
- **SC-005**: In the viewer, the experimenter can go from opening the page to watching a P2 episode
  in under a minute, and can replay it afterwards step by step.
- **SC-006**: Every warehouse tool result, error and outcome in a saved episode can be checked by
  code against the warehouse, with no free-text parsing; the delivered count, the parallel turns
  and the idle robot-turns are reproduced from the saved steps alone.
- **SC-007**: A dry-run plan for the warehouse never calls a model, and the tests never make a paid
  call.

## Assumptions

- Problem name `warehouse`, levels P1–P3 ("P" for packages, since "W" is the workshop's); the seed
  numbers are the other problems' (dev 1000–1009, test 2000–2019), keyed by the problem name, so the
  warehouses are unrelated to the other worlds.
- The number of packages is free at the start, as a warehouse knows how many orders it has; it
  tells an agent when every package has been found, not where.
- The floor plan is free at the start because the board measures how work is split over unknown
  packages, not mapping; the rune floor gives its floor free for the same reason. The packages are
  hidden because finding them is what a split must adapt to.
- A robot sees the whole corridor it stands in, as in the mock-up, so one step into an aisle tells
  it whether the aisle is empty. Seeing only nearby cells is left for a later level.
- Capacity is one package per robot, and packages are dropped only on D; both keep the rules short.
- Robots never block each other in this feature; narrow aisles where they do, and packages that
  appear partway through, are later levels or features.
- The step budget counts every robot's calls, so more robots do not buy more steps; their advantage
  is expected in parallel turns and latency. A9's robots act one at a time, so it is not expected to
  gain in parallel turns; that is part of what the board shows, as on the survey field.
- A single robot is the reference for the budget because A1 and A2 must be able to finish with one
  robot; 3× the reference leaves room for an architecture that explores before it carries.
- The orchestrators' prompts are the warehouse versions of their survey and dungeon texts: they
  explain the setup and the answer format, with no advice on how to split the work.
- No retrying architecture plays the warehouse in this feature, so the attempt rule needs no change.
- No paid or local experiment runs are started as part of this work unless explicitly requested.
