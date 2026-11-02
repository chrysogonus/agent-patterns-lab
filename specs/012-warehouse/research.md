# Research: The Warehouse

Decisions R1–R18 for [spec.md](spec.md). Each: the decision, why, and what else was considered.

## R1 — A package `apl.warehouse`, mirroring the survey field

**Decision**: `src/apl/warehouse/` with the modules every problem has (`model`, `seeds`,
`generator`, `plans`, `env`, `results`, `tools`, `prompt`, `kit`, `frames`, `render_text`,
`render_svg`). The environment follows `apl.survey.env`, the other problem with several bodies:
`add_scout`, a `turn_source`, the log's `scout` and `turn` fields.

**Rationale**: the runner, viewer and orchestrators already handle the survey field's scouts; the
warehouse is the same shape with a different world.

**Alternatives**: extending the survey field with packages. Rejected: it would change the survey
field's worlds and results (FR-020).

## R2 — Floor geometry

**Decision**: a floor of `columns × rows` cells, named as on the survey field (`A1` is the
north-west corner; columns are letters going east, rows numbers going south).

- `k` aisles, `rows = 2k − 1`: rows 1, 3, 5, … (1-based) are aisles; the rows between are shelf rows.
- On a shelf row, columns B to the second-last are shelves; column A is the **west corridor** and
  the last column the **east corridor**, open on every row.
- Aisles are named `aisle 1` … `aisle k`, north to south.
- The **dock** is in the west corridor on the shelf row just north of the middle aisle; **D** is in
  the east corridor on the same row. Neither stands in an aisle, so the start view reveals no
  package.
- Packages stand on aisle cells between the corridors (columns B to the second-last), at most one
  per cell.

| Level | Columns | Aisles (rows) | Packages | Packages per aisle |
| --- | --- | --- | --- | --- |
| P1 | 9 | 3 (5) | 3 | 1, 1, 1 |
| P2 | 9 | 3 (5) | 3 | a shuffle of 0, 1, 2 |
| P3 | 11 | 5 (9) | 6 | a shuffle of 3, 1, 1, 1, 0 or of 3, 2, 1, 0, 0 |

**Rationale**: a single shelf row between aisles keeps the floor small for a 9B model's prompt
while keeping the mock-up's picture (aisles, two cross corridors, D on the east). With the dock and
D off the aisles, every aisle must be entered to be seen.

**Alternatives**: the mock-up's double shelf rows (more cells, nothing gained); D in an aisle
(the start or a delivery would reveal that aisle for free).

## R3 — What a robot sees

**Decision**: a robot stands in one or two corridors: the aisle of its row if the row is an aisle,
and the west or east corridor if it is in column A or the last column. It sees every package
waiting on a cell of those corridors. The view lists the corridors by name and the packages seen
with their cells. Packages carried or delivered are not "seen" on the floor.

**Rationale**: one step into an aisle tells whether it is empty, as in the mock-up; this is what
makes a blind split visibly wrong and a replan possible.

**Alternatives**: seeing only the robot's cell (a survey-style sweep would dominate, and the board
would test mapping, not splitting); seeing neighbors (in-between, no clear gain).

## R4 — Robots, picking and dropping

**Decision**: up to 4 robots (`MAX_SCOUTS = 4`), all starting on the dock. A robot carries at most
one package. `pick()` takes the package on its cell; `drop()` on D delivers the carried package;
both take no arguments, so no package name has to be typed. Robots share cells. In one parallel
turn, calls are applied in robot order (as `apl.arch.scouts.act` already does). No retrying
architecture plays the warehouse: `MAX_ATTEMPTS = 1` and `restart` always refuses.

**Rationale**: the fewest rules that still make the split matter. No-argument tools remove a class
of invalid calls that would measure typing, not coordination.

## R5 — Package names and the free package count

**Decision**: packages are named `package 1` … `package n`, the numbers shuffled by the seed so a
name says nothing about where it stands. The start view and every view give `packages` (how many
there are) and `delivered` (how many are delivered).

**Rationale**: the count tells an agent when everything has been found, not where; without it an
agent could never stop exploring, which would favour sweeping over splitting.

## R6 — Reference and budget

**Decision**: the reference is the step list of a single robot that knows nothing at the start
and, for each aisle in order north to south: goes by a shortest path to the nearest cell of the
aisle (which shows its packages); then, while packages wait in that aisle, goes to the nearest one,
picks it, goes to D, drops it, and goes back to the aisle. Packages seen in other aisles on the
way are left for their aisle's turn. Shortest paths come from breadth-first search; ties go north,
then east. Steps are moves plus picks plus drops. `reference_is_optimal = False`. The budget is
3× the reference.

**Rationale**: a deterministic, simple, plausible single-robot strategy, as the survey field's
greedy walk on walled levels; A1 and A2 must be able to finish with one robot (SC-003).

**Alternatives**: the full-knowledge optimum (a travelling-salesman variant; overkill, and it would
make the budget depend on knowledge no agent has).

## R7 — Scripted agents and the built-in gap

**Decision**: three scripted agents, used by tests and by the generator's acceptance check:

- **reference**: plays the reference (SC-003).
- **blind split**: one robot per aisle, assigned before anyone looks; each robot walks to its
  aisle and delivers that aisle's packages, then stops.
- **replanning split**: the same start, but after the first parallel turn in which every aisle has
  been seen, robots without work take the nearest waiting package that no robot is heading for.

A P2 or P3 draw is accepted only if the blind split leaves at least one robot idle while packages
remain and the replanning split finishes in fewer parallel turns. These agents drive the episode
directly; they are test and generator code, not architectures.

**Rationale**: SC-004 by construction, as the workshop's greedy plan is stuck by construction.

## R8 — Parallel turns and idle robot-turns

**Decision**: parallel turns as on the survey field (`Outcome.parallel_turns`: distinct `turn`
values of counted calls, or one per counted call without a turn source). The episode records the
turn at which each robot was added (`added_turn`; robot 0 at turn 0). Idle robot-turns sum, over
the parallel turns, the robots added at or before that turn that made no counted call in it.

**Rationale**: the runner already sets `turn_source` for any episode that has one (`episode.py`).
A single robot has no idle turns; A9's round robin shows its idle robots, as the spec expects.

## R9 — Result rows

**Decision**: new row fields `delivered`, `packages`, `idle_robot_turns`; shared fields
`parallel_turns`, `scouts`, `reference_is_optimal`. `end_reason` gains `delivered` for success.
Older rows load unchanged.

## R10 — Report and comparison

**Decision**: the warehouse table

`| Arch | Level | Episodes | Success | Delivered (median) | Steps (median) | Efficiency (median) | Turns (median) | Idle (median) | Robots (median) | Budget hit | Tokens (median) | Latency (median) |`

and, with repeats, `| Arch | Level | Success (min–max) | Turns (min–max) |`. The comparison section
uses the survey field's variant with parallel turns; A7–A9 are compared with A2, as on the survey
field.

## R11 — Base prompt and tool schemas

**Decision**: `apl.warehouse.prompt` with `BASE_PROMPT` (the floor, the corridors, what a robot
sees, carrying and delivering, steps and budget, the result envelope; no strategy) and four schemas
(`look`, `move` with the direction enum, `pick`, `drop`), plus `prompt_fingerprint`, as every
problem.

## R12 — The floor map (A2 and the scouts)

**Decision**: `apl.arch.floor_map.FloorMap`, built only from tool results: the floor plan, the
corridors seen, the packages seen and their cells, what the robot carries, delivered out of the
total, and the robot's cell. It renders a grid (`#` shelf, `.` seen corridor cell, `?` corridor
cell not seen yet, `P` package waiting, `D`, `S` dock, `@` you, digits other robots) and lists the
packages seen and the corridors not seen yet. It draws no conclusion. `SharedMap` gains it, with
each robot's cell and carried package, so A7–A9 work unchanged in structure.

## R13 — A7–A9 on the warehouse

**Decision**: warehouse versions of the orchestrators' and scouts' texts (setup and answer format
only, no advice). A7: one decision, no collect step; the graph ends when the robots are done. A8:
`{"done": true}` stops, as on the dungeon. A9: one task for every robot; a claim line
`claim: package <n>` or `claim: aisle <n>`, matched by a warehouse-only pattern so the dungeon's and
the survey field's claims are unchanged. The episode also ends by itself on the last delivery.

## R14 — Viewer

**Decision**: `/api/warehouse` with the floor's SVG (shelves, corridor cells as `.room` rects for
the fog, dock, D) and the reference frames. Frames have the survey field's shape plus `seen`
(corridor cells seen so far), `packages` (each with cell, carrier and delivered), `delivered`,
`parallel_turns` and `idle_robot_turns`. The page fogs by `seen` when a frame has it, draws each
waiting package on its cell and each carried one on its robot, and adds warehouse rows to the stats
panel.

## R15 — `apl warehouse show`

**Decision**: a text map (`#`, `.`, `S`, `D`, digits for packages by number), a header with the
reference and budget, and with `--route reference` a last line listing the reference's calls;
`--html` writes the viewer's SVG.

## R16 — Boundary and allowed imports

**Decision**: the import test and AGENTS.md add `apl.warehouse.tools` and `apl.warehouse.results`;
`generator`, `env`, `plans` and `model` stay forbidden.

## R17 — About card

**Decision**: `SUPPORTS` gains `warehouse` for `react`, `mapstate`, `fanout`, `rounds`,
`blackboard`; `apl.viewer.about` gains the warehouse's memory, tools and end texts, and its scouts
card says who delivers instead of who submits.

## R18 — What stays unchanged

**Decision**: the other five problems' modules are touched only where a problem table or a
per-problem branch is extended. A pin test records the workshop's fingerprint and dry-run plan
before any change, next to the existing pins (SC-001).
