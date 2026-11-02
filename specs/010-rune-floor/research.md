# Research: The Rune Floor

Decisions for specs/010, in the order the plan needs them. Each says what was chosen, why, and
what else was considered. "M9" refers to specs/009-signal-trace, whose shape this feature follows.

## R1. Package and problem name

**Decision**: the problem is named `rune` (CLI, run records, results). Its code lives in a new
package `src/apl/rune/` with the signal trace's modules: `model`, `generator`, `rules` (the rule
families and the reference search, the counterpart of `strategy`), `env`, `tools`, `results`,
`prompt`, `kit`, `frames`, `render_text`, `render_svg`, `seeds`, `__init__`.

**Rationale**: the same layout keeps the problem table, the import test and the viewer uniform.
`rune` shadows no standard library module (unlike `signal`, M9 R1).

**Alternatives**: `apl.rune_floor` (longer, no benefit).

## R2. The floor, cells and the free start view

**Decision**: a floor is a rectangle of `columns × rows` cells, named as on the survey field: column
letter and row number, `A1` the north-west corner. S is the west edge's middle cell
(`A{rows // 2 + 1}`), G the east edge's middle cell on the same row. Every other cell has one of
four colors: `red`, `blue`, `green`, `yellow`. The kit's `start` is the floor as a `look` result:
size, S, G, the agent's cell, and the floor as rows of words, `start` and `goal` in place of a
color. `look()` returns the same for one step.

**Rationale**: the board tests learning a rule, not exploring, so the colors are free (spec
Clarifications). Rows of color words are exact and easy to read; one-letter codes clash (`G` is
both green and the goal). The survey's cell names are already in the lab's prompts.

**Alternatives**: fog with a neighbours-only `look` (mixes exploration into the measure; declined
by the experimenter); a dict of 35–63 cells (longer and hides the rows).

## R3. Steps, walks and the rule state

**Decision**: `move(direction)` takes one of `north`, `east`, `south`, `west`. A *walk* is the
sequence of colored cells stepped on since the agent last stood on S; it starts empty. Each move:

- off the floor: error `edge`, the agent stays, the walk is unchanged;
- onto S: the agent is back on S and a new walk starts; no trap;
- onto G: the episode ends as a success, whatever the rule;
- onto a colored cell: the rule judges it with the walk so far. Safe: the cell joins the walk.
  Forbidden: a trap; the agent is back on S and a new walk starts.

The *rule state* is what the rule needs from the walk: the walk's length modulo the cycle length
for cycle rules, nothing for the others. Stepping back onto a cell already in the walk is judged
like any other step and counts toward the walk's length.

**Rationale**: these are the physics the spec describes, with the corner cases settled so code can
score them. Treating S as a reset keeps "walk" well defined; it costs a step, as every call does.

## R4. Levels and rule families

**Decision**:

| Level | Floor | Rule | Example |
| --- | --- | --- | --- |
| R0 | 7×5 | none: a fixed set of trap cells (about a third of the cells off the planted path) | — |
| R1 | 7×5 | a cycle of 3 distinct colors, starting with the walk's first cell | red, blue, green, red, … |
| R2 | 9×7 | a cycle of 4 with one color doubled: `a, a, b, c` | red, red, blue, green, red, red, … |
| R3 | 9×7 | by row: odd rows (1, 3, 5, 7) allow only color `a`, even rows only color `b` | row 1 blue, row 2 yellow, … |

The colors in a rule are drawn from the four per seed. On R0 the colors are drawn at random and
mean nothing; on R1–R3 the fourth (R1), the unused (R2) or the other two (R3) colors are never
safe.

**Rationale**: R1 is the mock-up's rule and can be read off one walk of three safe steps. R2's
doubled color breaks the "next color is a different one" guess and needs more than one trap. R3
depends on where a cell is, not on the order of steps, so the obvious guess (a color order) is
wrong, and what is learned carries over to cells never stepped on. R0 has nothing to learn beyond
"not that cell": the control.

**Alternatives**: a step-count rule for R3 ("every third step must be green": still a sequence
rule, too close to R1–R2); rules mixing order and place (too hard to read off a 7-step budget
margin); five colors (bigger prompts, little gain).

## R5. Generation and its guarantees

**Decision**: `random.Random(f"rune:{level}:{seed}")`. Per draw: pick the rule; walk a random
self-avoiding path from S to G biased east (east weighted 3, north and south 1), at most
`columns − 1 + 6` moves; color its cells so the rule allows them in order; color every other cell
at random; on R0 make about 35% of the cells off the path traps. Accept the draw when:

1. a safe path exists (the reference, R6, is finite);
2. the straight row from S to G, the only shortest route, is not safe: the reference is longer than
   `columns − 1`;
3. on R0 only: the memory-only agent of R7 reaches G within the budget.

Otherwise draw again, up to `MAX_TRIES = 1000`.

A simulation (2026-11-02, the sketch of this decision over the 30 dev and test seeds per level):
every level was accepted within 7 draws; references were R0 8–10, R1 8–12, R2 10–14, R3 10–14
moves. Tests pin the bounds: a reference of at most 12 on R0–R1 and 16 on R2–R3 on every dev and
test seed.

**Rationale**: planting a path guarantees a solution; random colors off the path make an alternative
safe route rare (each cell is right with probability ¼), so the reference stays close to the
planted path. Condition 2 is the spec's "the shortest route that ignores the rule springs a trap"
(FR-003, SC-002): S and G share a row, so the straight row is the one shortest route.

**Alternatives**: hand-designed floors (few, and seeds would repeat them); unbounded path length
(the reference and budget grow with no gain).

## R6. Reference and budget

**Decision**: the reference is a breadth-first search over `(cell, rule state)` from `(S, 0)`,
with the moves of R3: onto S resets the state, onto G ends, onto a forbidden cell is not taken.
The reference is the number of moves to G, and is optimal (`reference_is_optimal` is always true).
`reference_path(floor)` returns one shortest path (lowest direction order on ties: north, east,
south, west) for `show --route` and the viewer. The budget is 4× the reference (spec FR-009):
R0 32–40, R1 32–48, R2 40–56, R3 40–56 in the simulation.

**Rationale**: the state space is at most 63 cells × 4 states, so the search is instant. A
reference that is the exact optimum makes efficiency comparable across levels.

## R7. The scripted agents behind the guarantees

**Decision**: two scripted agents in the tests, and one in the generator:

- *learner* (SC-004): walks the straight row until the first trap, then follows
  `reference_path`. It reaches G within the budget on every floor: its first walk is shorter than
  `columns − 1` moves, so it needs fewer than 2× the reference.
- *repeater* (SC-004): walks the straight row again and again. It never reaches G and runs out of
  budget on every floor.
- *memory-only* (R5 condition 3, and a test on R1–R3): knows no rule, remembers every cell that
  trapped it together with the walk's length at that moment, and walks the shortest route that
  avoids what it remembers (unknown cells treated as safe). On R0 it is required to finish. On R1–R3
  it is reported, not required: in the simulation it finished about half the floors within 4×
  (R1 16/30, R2 14/30, R3 16/30) against 27/30 on R0 before condition 3, which is the gap the board
  is built to show: remembering traps is enough on R0 and not on R1–R3.

**Rationale**: the guarantees are about behaviour, so the tests check them with agents that have
exactly the knowledge in question.

## R8. Traps and repeated traps

**Decision**: a trap is a successful call, not an error, and not an invalid action. Its result
says where it sprang and that the agent is back on S; it never states the rule. A trap is
*repeated* when an earlier trap in the same episode, any attempt, sprang on the same cell in the
same rule state (on R0 and R3, the same cell). The episode counts `traps`, `repeated_traps` and
`walks` (walks started, the first included).

**Rationale**: "the same mistake again" has to follow the rule: on R1–R2 a cell can be safe at one
point of a walk and a trap at another, so the same cell alone would count honest experiments as
repeats. Counting by the rule's state is exact and reproducible from the saved steps (SC-006).

## R9. Tool arguments and errors

**Decision**: `move(direction)` takes exactly one of the four words, as on the survey field. Errors: `invalid_direction` (anything else), `edge` (off the floor),
`unknown_tool`, `episode_over`; each costs a step except `episode_over`, and each is an invalid
action. Results: a safe step `{"position": "C3", "color": "blue"}`; back on S
`{"position": "A3", "color": "start"}`; a trap `{"trap": "D3", "color": "yellow", "position":
"A3"}`; the goal `{"position": "G3", "goal": true}`. A retrying architecture's trap with attempts
left adds `"attempts_left": n`.

## R10. Episode, attempts and scouts

**Decision**: one agent: `Kit.add_scout` returns None. `MAX_ATTEMPTS = 3`. For a retrying
architecture with attempts left, a trap ends the attempt: the environment restarts itself (the agent
is already on S; the attempt number goes up), as it does after a wrong total or segment, and the
result carries `attempts_left`. With no attempt left, a trap is an ordinary trap and the episode
goes on. A restart costs no step. The episode ends at G, at the budget, or when the architecture
stops. No `turn_source`.

## R11. Results and report

**Decision**: new nullable row fields `traps`, `repeated_traps`, `walks`; `reference_is_optimal`
is shared (true on every rune row). `optimal_steps` holds the reference, `efficiency` is
`optimal_steps / steps` on success. The report's rune table: Success, Steps, Traps, Repeated,
Efficiency, Budget hit, Tokens, Latency (medians), and a spread table Success and Traps (min–max)
with repeats. The comparison section uses the dungeon's columns with the M9 override for A6:
`hybrid` → `mapstate`.

## R12. Architectures on the rune floor

**Decision**:

- A1 `react`: unchanged; the floor is its first message.
- A2 `mapstate`, A3 `plan_execute`, A4 `reflexion`: a `WalkLog` (new `src/apl/arch/walk_log.py`,
  the rune floor's counterpart of `ProbeLog`) built only from tool results: the floor, the agent's
  cell, and every walk as its cells and colors in order with how it ended (trap at a cell, back on
  start, current). It draws no conclusion. Its `known` count (distinct cells stepped on, traps
  included) feeds A4's staleness check. As with the probe log, A4's walk log starts empty each
  attempt; its notes carry the lessons across.
- A4: the failure reason after a trap with attempts left is `trap`; it joins `RESTARTED`, so the
  `restart` node skips `kit.restart()` (the environment already restarted). Because a trap is known
  only from its result, A4's `act` runs a reply's calls one at a time on `rune` and stops after the
  first trap that carries `attempts_left`; the calls after it are dropped from the reply and never
  run, so a batch of moves cannot spill into the next attempt before the reflection
  (contracts/architectures.md).
- A6 `hybrid`: a rune branch. Code keeps, per cell, what happened each time it was stepped on:
  safe or trap, and at which step of the walk. Options are the moves from the agent's cell that
  stay on the floor, each with that record: `move east to C3 (blue): safe at walk step 2 (twice);
  trapped you at walk step 4 (once)`, or `never stepped on`. The model answers with an option
  number; code makes the call. Code never guesses the rule (spec FR-024).
- A2r, A5, A7–A9: not registered for `rune`.

**Rationale**: matches the spec and the M9 precedent. A6's record per walk step is the most code can
keep without knowing the rule; on R1–R2 it is often misleading (safe at step 2 says nothing about
step 5), which is the mock-up's A6 weak spot ("only as good as the code someone wrote for it").

**Alternatives**: A6 offering whole routes (code would need a model of safety, i.e. the rule);
showing A2 which cells are "dangerous" (an inference, which would make A2 a hybrid).

## R13. CLI

**Decision**: `apl rune show --level R1 --seed 1000 [--route reference] [--html OUT]` prints the
floor as rows of letters with a legend (`r b g y`, `S`, `*` for the goal), the rule in words, the
reference and the budget; `--route reference` adds the reference path as cells; `--html` writes
the viewer's SVG as a page. `apl run --problem rune` and `--level R0,R1,R2,R3|all`.

**Rationale**: the terminal print is for the experimenter, who knows the rule; letters keep a 9×7
floor on nine short lines. The agent never sees this print.

## R14. Viewer

**Decision**: `GET /api/rune?level=&seed=` returns the floor (size, S, G, colors, rule text,
reference, budget, SVG, reference frames). The SVG draws the cells in their colors (soft fills),
`S` and `G`, and empty groups the page fills: `#trails`, `#traps`, `#agent`. Per frame the page
draws the current walk as a bold line from S, earlier walks as faded lines, a cross on every trap
(larger for the latest), and the agent's marker. Under the truth view the rule is written above the
board and the reference path is outlined; "Agent's view" hides both. Stats: steps against budget
and reference, walk and attempt, traps and repeated traps, and at the end "Reached G" or "Out of
budget". The viewer's episode-id pattern widens to `[LSTR][0-3]`.

## R15. Fairness checks

**Decision**: the import test's allowed list gains `apl.rune.tools` and `apl.rune.results`, and a
test shows `apl.rune.generator`, `env` and `rules` are forbidden. A boundary test plays random
calls and checks every result's shape, and that no result depends on the rule beyond what the
moves show: the start and `look` results are identical for one floor's colors under any rule, and
no result contains a rule's name or a cycle. AGENTS.md lists the new imports and tools.
