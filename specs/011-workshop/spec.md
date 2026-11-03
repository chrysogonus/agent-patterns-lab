# Feature Specification: The Workshop

**Feature Branch**: `011-workshop` (spec directory; work happens on git branch `m11-workshop`)

**Created**: 2026-11-02

**Status**: Draft

**Input**: User description: "M11, feature 011: the workshop, the lab's fifth problem (plan.md §9
lists it among the problem mock-ups; visual mock-up: https://claude.ai/artifact/VEDrZX6TuFapmV4rHkTCqB,
section "Workshop"). The agent must craft one goal item (for example a lantern). Items are made from
recipes that form a tree: the goal needs intermediate items, which need other items or raw
materials. Raw materials sit in a world stock with a fixed count each, some of them scarce (for
example only 2 coal). Recipes are hidden: the start view names the goal and the raw materials in
stock with their counts, and the agent sees an item's recipe only by inspecting it, one step each.
Some items have two alternative recipes, and the first-listed one uses a scarce raw material that
another branch of the tree also needs (for example Frame from iron bar plus coal, or from wood), so
crafting greedily with the first recipe found later leaves the other branch without coal, while an
agent that inspects the tree first and plans saves it. Every workshop is solvable, and code computes
the shortest plan. The property this board is built to show: dependent steps under scarcity, where
planning ahead pays off. A1 ReAct crafts as soon as it can and gets stuck; A3 plan-and-execute
inspects the tree, reserves the scarce materials and finishes. A5 supervisor plays it with a
researcher subagent (inspect) and a crafter subagent (gather, craft): the mock-up names the workshop
as A5's strong spot. Scored by code: success when the goal item is crafted, steps against a
reference, scarce materials wasted (used on a recipe the shortest plan avoids or on items not
needed), stuck episodes (a needed raw material exhausted), invalid actions, calls, tokens. Levels
grow the tree and the number of conflicts: a small tree with no conflict (baseline), a tree with
one scarce material and one tempting alternative, a deeper tree with two conflicts. Architectures
A1 react, A2 mapstate, A3 plan_execute, A4 reflexion, A5 supervisor and A6 hybrid play it; A2 keeps
the known recipes, stock and inventory in state; A6's code keeps the known tree and offers the
actions; the scouts (A7–A9) are left out. The agent writes the graph changes and the experimenter
reviews them. It plugs into the multi-problem support exactly like the other problems: its own
tools, level ladder, seeds, scoring and step budget; the fairness rules (same model, prompt, tool
descriptions and budget; world access only through the problem's tools; structured results; dev vs
test seeds; no paid call without --execute) apply within the problem; the constitution's tool rule
is amended to name the new tools; the dungeon, the survey field, the signal trace and the rune
floor stay unchanged. apl run, apl continue, apl report and apl serve take it as a problem; the
viewer shows the recipe tree as it is discovered, the inventory and stock, scarce materials turning
red when exhausted, and the crafted goal. Done when: any workshop level and seed can be shown and
watched in the viewer, workshop runs plan, continue and report like the other problems, and the
existing problems are unchanged. No paid or local experiment runs are started as part of this work
unless explicitly requested."

## Clarifications

### Session 2026-11-02

- Q: What makes crafting greedily fail? → A: Alternative recipes: some items have two, and the
  first-listed one uses a scarce raw material another branch needs. Every workshop stays solvable,
  and code computes the shortest plan.
- Q: What does the agent know at the start? → A: The goal and the raw materials in stock with
  their counts. Recipes are hidden; `inspect` shows one item's recipes for one step.
- Q: Which architectures? → A: A1–A6. A5 supervisor plays it with a researcher (inspect) and a
  crafter (gather, craft). The scouts (A7–A9) are left out.
- Q: Who writes the workshop versions of the architectures in `src/apl/arch/`? → A: The agent, at
  the experimenter's request, as in M5–M10; the experimenter reviews them afterwards.

## User Scenarios & Testing *(mandatory)*

The user of this feature is the experimenter. Each problem in the lab is built to show one
property: the survey field shows splitting the work, the signal trace choosing what to look at
next, the rune floor learning from failure. The workshop shows planning ahead. Its steps depend on
each other, a scarce raw material is needed in two places, and the obvious way to make one part
uses it up. An agent that crafts whatever it can as soon as it can uses the scarce material on the
wrong recipe and later finds the other part impossible to make. An agent that first inspects the
recipes it needs, notices the conflict and picks the other recipe finishes. That is the side of A3
plan-and-execute, and of A5 supervisor's researcher and crafter, that no other board shows.

The workshop in one paragraph: the agent must make one goal item. It starts with an empty
inventory and a stock of raw materials, some plentiful and some scarce. Every other item is made
from a recipe that turns items from the inventory into a new one. The agent does not know any
recipe until it inspects the item. Gathering takes one raw material from the stock into the
inventory; crafting turns a recipe's inputs into its output. The episode is a success when the goal
item is crafted.

Architectures in this feature:

| Name | Architecture | On the other problems | On the workshop |
| --- | --- | --- | --- |
| `react` | A1 ReAct | as before | yes |
| `mapstate` | A2 map state | as before | yes, with a workshop log in state (recipes seen, stock, inventory; nothing inferred) |
| `plan_execute` | A3 plan-and-execute | as before | yes, with A2's workshop log |
| `reflexion` | A4 Reflexion | as before | yes: getting stuck ends an attempt while attempts are left |
| `supervisor` | A5 supervisor | as before (dungeon) | yes: a researcher (inspect) and a crafter (gather, craft) |
| `hybrid` | A6 hybrid | as before | yes: code keeps the known tree, stock and inventory and offers the actions; the model picks one |
| `mapstate_routes`, `fanout`, `rounds`, `blackboard` | A2r, A7–A9 | as before | no |

### User Story 1 - Watch an architecture build the goal item (Priority: P1)

In the viewer, the experimenter picks the workshop, a level and a dev seed, and sees the workshop:
the goal, the raw materials in stock with their counts, and the recipe tree. They pick an
architecture and press Run. Every step appears as it happens: an inspected item's recipes appear
in the tree, a gathered material moves from the stock to the inventory, a crafted item appears in
the inventory and its inputs leave it. A scarce material turns red when its stock runs out. A panel
shows the steps against the reference and the budget, the scarce materials wasted, and at the end
whether the goal was crafted or the episode got stuck. The side panel shows each model turn as for
the other problems. Episodes are saved and can be replayed.

**Why this priority**: Watching an agent burn the scarce material on the wrong recipe, or reserve
it, is the point of the board. It needs the problem itself (US2) and is the first thing the
experimenter will use.

**Independent Test**: Start the viewer, open the workshop W2 seed 1000, play a scripted agent that
follows the reference plan, and check that the tree, stock and inventory and the replay all match
the saved events; play a scripted greedy agent and check that the scarce material turns red and
the episode ends stuck.

**Acceptance Scenarios**:

1. **Given** the viewer is open, **When** the experimenter picks the workshop, level W2 and seed
   1000, **Then** the goal, the stock with counts and the whole recipe tree are shown, with the
   reference plan marked; with "Agent's view" on, only the goal and the stock are shown and the
   tree is hidden until items are inspected.
2. **Given** an episode is running, **When** the agent inspects an item, **Then** that item's
   recipes appear in the tree under "Agent's view".
3. **Given** an episode is running, **When** the agent gathers or crafts, **Then** the stock and
   the inventory change accordingly, and a scarce material whose stock reaches zero turns red.
4. **Given** an episode ends, **When** the experimenter looks at the panel, **Then** it shows
   whether the goal was crafted or the episode got stuck, the steps against the reference, and the
   scarce materials wasted.
5. **Given** an architecture that does not play the workshop, **When** the experimenter looks at
   the architecture list for this problem, **Then** it cannot be chosen.
6. **Given** a test seed, **When** the experimenter enters it, **Then** the viewer refuses it, as
   it does for the other problems.

---

### User Story 2 - The workshop problem (Priority: P1)

A seed and a level always build the same workshop. The agent acts only through the workshop's
tools, each call costs one step, and errors are structured like the other problems'. Every
workshop has a reference computed by code, which sets the step budget and the efficiency score.

**Why this priority**: Without it there is nothing to watch or compare. It is listed second only
because it is invisible on its own.

**Independent Test**: Generate workshops for every level and every dev and test seed and check
them (solvable, the conflicts the level calls for, the greedy plan gets stuck); play scripted
sequences of calls against the tools and check every result; check that a seeded workshop is
identical across runs.

**Acceptance Scenarios**:

1. **Given** a workshop, **When** an episode starts, **Then** the agent is given the goal, the
   raw materials in stock with their counts, and its empty inventory free, as the other problems
   give their start view. `look` returns the same kind of view, with the current stock and
   inventory, for one step.
2. **Given** an item, **When** the agent inspects it, **Then** the result lists its recipes (one or
   two, in a fixed order, each with its inputs and counts), or says it is a raw material.
3. **Given** a raw material in stock, **When** the agent gathers it, **Then** one unit moves from
   the stock to the inventory; with none left, the call fails with a structured error.
4. **Given** the inputs of one of an item's recipes are in the inventory, **When** the agent crafts
   the item with that recipe, **Then** the inputs leave the inventory and the item enters it;
   without the inputs, the call fails with a structured error that names what is missing.
5. **Given** the agent crafts the goal item, **When** the call returns, **Then** the episode ends
   as a success.
6. **Given** the goal can no longer be made from the inventory and the stock, **When** the step
   that caused it returns, **Then** the episode ends as stuck (for a retrying architecture with
   attempts left, the attempt ends instead and the workshop restarts).
7. **Given** the step budget is used up first, **When** the episode ends, **Then** it is a failure,
   marked as out of budget.

---

### User Story 3 - Run, continue and report on the workshop (Priority: P2)

The experimenter plans and runs workshop episodes with the same commands as for the other
problems, naming the problem. The plan is free and shows the matrix and an estimate; `--execute`
plays it. An interrupted run can be continued. The report adds the workshop's own columns: how
often the goal was crafted, how often an episode got stuck, the steps against the reference, and
the scarce materials wasted.

**Why this priority**: The viewer shows the difference on one seed. A run with repeats is how the
experimenter checks whether it holds across seeds.

**Independent Test**: Plan a workshop run without `--execute` and check the matrix; play a run with
scripted architectures, interrupt it, continue it, and check the report against the rows.

**Acceptance Scenarios**:

1. **Given** the workshop is named, **When** the experimenter plans a run without `--execute`,
   **Then** the plan shows the workshop levels, seeds, architectures and an estimate, and no model
   is called.
2. **Given** a workshop run names an architecture that does not play it, **When** it is planned,
   **Then** it is refused with a message that names the architecture and the problem.
3. **Given** an interrupted workshop run, **When** the experimenter continues it, **Then** only the
   missing episodes are planned, as for the other problems.
4. **Given** a completed workshop run, **When** the report is written, **Then** it shows, per
   architecture and level, the success share, the stuck share, median steps, median efficiency,
   median scarce materials wasted, budget hits, tokens and latency, with the spread across
   repeats, and the comparison section.

---

### User Story 4 - The fairness rules hold on the workshop (Priority: P2)

Within the workshop every architecture gets the same model, base prompt, tool descriptions and step
budget, and reaches the workshop only through its tools. The recipes are never visible to an
architecture except through its own inspections, and the reference plan never. Results from the
workshop are never combined with results from another problem.

**Why this priority**: The lab's results mean nothing if the rules are not checked. The import test
and the recorded fingerprints must cover the new problem.

**Independent Test**: The test that limits what architectures may import passes with the
workshop's public tool and result definitions added, and fails for an architecture that reads the
workshop's generator or its recipes.

**Acceptance Scenarios**:

1. **Given** the constitution, **When** this feature is done, **Then** principle II names the
   workshop's tools, the Experiment Setup describes its workshops, reference and budget, the
   attempt rule covers getting stuck, and the version and amendment date are updated.
2. **Given** an architecture that imports the workshop's generator or recipes, **When** the tests
   run, **Then** the import test fails.
3. **Given** two architectures on the same workshop level, **When** their episodes run, **Then**
   both got the same base prompt, tool descriptions and step budget, as recorded in the results.

---

### Edge Cases

- The agent crafts an item it never inspected: allowed, if it names a recipe that exists and the
  inputs are in the inventory; inspecting only shows the recipes.
- The agent crafts with a recipe number the item does not have, or crafts a raw material, or
  gathers an item that is not a raw material: the call fails with a structured error, costs a step,
  and nothing changes.
- The agent crafts an item the goal does not need, or crafts a needed item twice: allowed; the
  inputs are spent, and any scarce material among them counts as wasted.
- The agent uses the scarce material on the tempting recipe but enough is left for the other use:
  the episode goes on; it is stuck only when the goal can no longer be made.
- The agent gathers more of a plentiful material than it needs: allowed, it costs steps; it is not
  counted as waste (only scarce materials are).
- An item the inventory already holds is needed: it is used, the agent need not craft it again.
- A4 gets stuck while attempts are left: the attempt ends with a result that says only that the
  goal can no longer be made; the workshop restarts (stock refilled, inventory emptied); every
  step of every attempt counts toward the one budget.
- A model reply has no tool call: the episode ends as a failure, marked as given up, as on the
  other problems.
- Item names are matched exactly as the results write them; anything else is an unknown item.
- Dungeon, survey, signal-trace and rune-floor runs, reports and saved episodes from before this
  feature still load, continue and report as before.

## Requirements *(mandatory)*

### Functional Requirements

**The workshop**

- **FR-001**: The workshop MUST be a fifth problem next to the dungeon, the survey field, the signal
  trace and the rune floor, with its own tools and their descriptions, base prompt, levels, dev and
  test seeds, reference, scoring and step budget rule.
- **FR-002**: A workshop MUST be generated from a level and a seed, identical every time for the
  same pair. It MUST consist of a goal item, craftable items with one or two recipes each, and raw
  materials with a stock count each; every recipe's inputs are items or raw materials of the same
  workshop, and recipes form a tree under the goal with no cycles.
- **FR-003**: Every workshop MUST be solvable from its start, and on levels with conflicts the
  greedy plan (always the first-listed recipe) MUST get stuck, so the conflict cannot be ignored.
- **FR-004**: The workshop MUST have three levels:

  | Level | Tree | Conflicts | Purpose |
  | --- | --- | --- | --- |
  | W1 | small (about 5 items) | none: every first recipe works | Baseline; every architecture should finish |
  | W2 | medium (about 8 items) | one scarce material needed in two branches, one tempting first recipe | The mock-up's lantern: planning saves the coal |
  | W3 | larger (about 12 items, deeper) | two scarce materials, two tempting first recipes | The conflicts interact; a plan must hold both |

  The exact tree shapes, item names, counts and generator rules are settled in the plan.

- **FR-005**: Agents MUST act only through these tools, each call costing one step, failed calls
  included:

  | Tool | Returns |
  | --- | --- |
  | `look()` | The goal, the raw materials in stock with their counts, and the inventory |
  | `inspect(item)` | The item's recipes (one or two, each with its inputs), or that it is a raw material; or an error (unknown item) |
  | `gather(item)` | One unit of a raw material moved from the stock to the inventory; or an error (unknown item, not a raw material, none left) |
  | `craft(item, recipe)` | The item made with that recipe, its inputs taken from the inventory; or an error (unknown item, no such recipe, inputs missing) |

  The goal, the stock and the empty inventory are also given free at the start of the episode, as
  the other problems give their start view.

- **FR-006**: Results and errors MUST be structured data with the same shape as the other problems'
  (`ok`, `error` with `code` and `message`, `data`). No result MUST show a recipe the agent has not
  inspected, or the reference plan.
- **FR-007**: An episode MUST end when the goal is crafted, when the goal can no longer be made from
  the inventory and the stock (stuck), when the step budget is used up, or when the architecture
  stops. It MUST be a success exactly when the goal was crafted.
- **FR-008**: Code MUST compute a reference for every workshop: the fewest steps of a plan that
  inspects every craftable item it uses, gathers the raw materials and crafts the goal, with the
  recipe choices that avoid every conflict.
- **FR-009**: The step budget MUST be 3× the reference, as on the survey field; the plan checks
  that a full inspection of the tree followed by the reference plan fits within it.
- **FR-010**: A retrying architecture (A4) MUST be able to restart the workshop up to 3 attempts
  per episode, as on the other problems: getting stuck ends its attempt while attempts are left, a
  restart refills the stock and empties the inventory, it costs no step, and all attempts share one
  budget.

**Runner and report**

- **FR-011**: `apl run` MUST accept the workshop as a problem; `apl continue` and `apl report` MUST
  take it from the run. A show command MUST print a workshop for a level and seed, with an option
  to show the reference plan. Without `--execute`, no model is called (constitution VI).
- **FR-012**: Each workshop result row MUST record, besides the fields every episode records:
  whether the episode got stuck, the scarce materials wasted, the items inspected, and the items
  crafted.
- **FR-013**: A unit of a scarce material MUST count as wasted when a craft of an item consumed it
  beyond what the reference plan's crafts of that same item consume of it (counted per attempt), so
  the greedy recipe's intermediate, crafts of unneeded items and repeated crafts all count.
- **FR-014**: The workshop report MUST show per architecture and level: the success share, the
  stuck share, median steps, median efficiency (steps against the reference), median scarce
  materials wasted, budget hits, tokens and latency, with the spread across repeats, and the
  comparison section M4 introduced.

**Viewer**

- **FR-015**: The viewer MUST offer the workshop as a problem; its levels, seeds and the
  architectures that play it MUST follow from that choice.
- **FR-016**: For the workshop, the viewer MUST draw the goal, the stock with counts (a scarce
  material red once exhausted), the inventory, and the recipe tree: the whole tree with the
  reference plan's recipes marked under the truth view, and only the inspected items' recipes
  under "Agent's view"; and a panel with steps against the reference and the budget, scarce
  materials wasted, and whether the goal was crafted or the episode got stuck.
- **FR-017**: The step slider, replay of saved episodes and the side panel of model turns MUST work
  for the workshop as for the other problems.

**Rules**

- **FR-018**: The constitution MUST be amended: principle II names the workshop's tools and forbids
  reading the recipes except through `inspect`, the reference plan and the stuck check; the
  Experiment Setup gains the workshop's generation, reference and budget; the attempt rule covers
  getting stuck.
- **FR-019**: Architectures MUST be allowed to import only the shared kit and each problem's public
  tool and result definitions; the import test MUST enforce this for the workshop.
- **FR-020**: The dungeon, the survey field, the signal trace and the rune floor MUST behave exactly
  as before: same worlds per seed, tools, prompts, budgets, scoring and results format.

**Architectures**

- **FR-021**: A1 (`react`) MUST play the workshop with its base prompt and tools and nothing else
  changed.
- **FR-022**: A2 (`mapstate`) MUST play the workshop with a workshop log in its state, rendered each
  turn: the goal, the stock, the inventory and every recipe inspected so far, with no inference
  drawn from them.
- **FR-023**: A3 (`plan_execute`) and A4 (`reflexion`) MUST play the workshop with the same log as
  A2; A4 reflects after getting stuck as it does after a wrong total on the survey field.
- **FR-024**: A5 (`supervisor`) MUST play the workshop with two subagents on A2's log: a researcher
  that may only inspect, and a crafter that may only gather and craft; the supervisor hands tasks
  to them as it does on the dungeon.
- **FR-025**: A6 (`hybrid`) MUST play the workshop with code that keeps the known recipes, the stock
  and the inventory, and offers the possible actions (inspect an item not yet inspected, gather a
  raw material in stock, craft an item whose inputs are held); the model picks the action. Code
  MUST work only with what earlier tool results revealed, and MUST NOT plan the recipe choices.
- **FR-026**: The agent writes the workshop versions of A1–A6 in `src/apl/arch/`, at the
  experimenter's request; the experimenter reviews them afterwards. Their behavior on the other
  problems MUST NOT change.

### Key Entities

- **Workshop**: a goal item, the craftable items with their recipes, the raw materials with their
  stock, generated from a level and a seed, with a reference and a step budget.
- **Recipe**: one way to make an item: its inputs, each an item or raw material with a count.
- **Stock**: the raw materials left in the world and how many of each; some are scarce.
- **Inventory**: what the agent holds: gathered raw materials and crafted items.
- **Conflict**: a scarce material needed by two branches where an item's first recipe uses it too;
  the reason the greedy plan gets stuck.
- **Workshop outcome**: the result of one episode: success, stuck, steps, reference, scarce
  materials wasted, items inspected, items crafted, budget hit, and the fields every episode
  records.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every dungeon, survey, signal-trace and rune-floor command from before this feature
  produces the same output, and every existing test passes without changes to what it checks.
- **SC-002**: For every workshop level and every dev and test seed, the generated workshop is
  identical across runs, solvable, and has the level's number of conflicts; on W2 and W3 the
  greedy plan gets stuck.
- **SC-003**: A scripted agent that follows the reference plan crafts the goal on every level and
  seed in exactly the reference number of steps, with no scarce material wasted.
- **SC-004**: On every W2 and W3 seed, a scripted greedy agent (inspect as it goes, always the first
  recipe) gets stuck, and a scripted planner (inspect the whole tree first, then choose recipes
  that avoid conflicts) crafts the goal within the budget. The gap the board is built to show
  exists by construction.
- **SC-005**: In the viewer, the experimenter can go from opening the page to watching a W2 episode
  in under a minute, and can replay it afterwards step by step.
- **SC-006**: Every workshop tool result, error and outcome in a saved episode can be checked by
  code against the workshop, with no free-text parsing; the wasted count and the stuck moment are
  reproduced from the saved steps alone.
- **SC-007**: A dry-run plan for the workshop never calls a model, and the tests never make a paid
  call.

## Assumptions

- Problem name `workshop`, levels W1–W3; the seed numbers are the other problems' (dev 1000–1009,
  test 2000–2019), keyed by the problem name, so the workshops are unrelated to the other worlds.
- The goal and the stock are free at the start because every agent needs them to begin; the
  recipes are hidden because deciding to look before acting is part of what the board measures.
- Items are named by words (`iron bar`, `lantern`), drawn per seed from a fixed vocabulary so
  names carry no hint of the tree's shape beyond common sense; the plan settles the vocabulary.
- An item's recipes are always listed in the same order, and on conflict levels the first-listed
  recipe of a tempting item is the one that uses the scarce material.
- The stuck check is done by code after every step; the result that ends the episode says only
  that the goal can no longer be made, not why.
- The budget of 3× the reference is the default of the newest problems with a fixed plan; the plan
  checks it against the scripted agents and may raise it, recording why.
- A7–A9 are left out: the workshop has no regions to split between scouts. A2r is left out because
  the workshop has no routes.
- A5's supervisor, researcher and crafter use A2's workshop log, as its navigator and inventory
  helper use A2's map on the dungeon.
- This feature includes no paid or local experiment run. Running a comparison and writing findings
  is the experimenter's choice afterwards, with the commands from US3.
- The constitution amendment adds a problem without changing a principle's meaning, so it is a
  MINOR version (2.4.0), made with `/speckit-constitution` before this feature's plan.
- The visual mock-up linked in the input shows intended behavior; its numbers are illustrative.
