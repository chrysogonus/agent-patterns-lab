# Research: The Workshop

Decisions for specs/011, in the order the plan needs them. Each says what was chosen, why, and what
else was considered. "M10" refers to specs/010-rune-floor, whose shape this feature follows.

## R1. Package and problem name

**Decision**: the problem is named `workshop` (CLI, run records, results). Its code lives in a new
package `src/apl/workshop/` with the rune floor's modules: `model`, `generator`, `plans` (the stuck
check, the reference plan and the waste count, the counterpart of `rules`), `env`, `tools`,
`results`, `prompt`, `kit`, `frames`, `render_text`, `render_svg`, `seeds`, `__init__`.

**Rationale**: the same layout keeps the problem table, the import test and the viewer uniform.

## R2. Items, the start view and `look`

**Decision**: every item is named by a word or two from two fixed lists, drawn per seed: craftable
items (`lantern`, `frame`, `lens`, `iron bar`, `glass`, `wick`, `handle`, `hinge`, …, 20 names) and
raw materials (`coal`, `iron ore`, `sand`, `wood`, `resin`, `clay`, …, 14 names). The free start
view, and `look`, return `{"goal": "lantern", "stock": {"coal": 1, "sand": 3, …}, "inventory": {}}`:
the goal, every raw material with its count (in a fixed order), and what the agent holds.

**Rationale**: the stock is part of the world an agent must see to begin; listing every raw
material also tells it which names are raw. Names are assigned to tree positions at random, so they
carry no hint of the tree's shape (`glass` may need `seeds`).

**Alternatives**: meaningful hand-made trees (few, and seeds would repeat them); symbolic names
(`item7`; harder to read in the viewer, no gain).

## R3. Recipes and the tree

**Decision**: a recipe is a list of input names, one unit each. Every craftable item has one recipe,
except the tempting items of R4 (and W1's one harmless alternative), which have two, always listed
in the same order. Inputs are craftable items (each used in one place, so the craftables form a
tree under the goal) or raw materials (shared freely between branches).

| Level | Craftables in the tree | Depth | Conflicts | Alternatives |
| --- | --- | --- | --- | --- |
| W1 | 3 | 2 | 0 | one harmless second recipe |
| W2 | 5 (+1 behind the tempting recipe) | 3 | 1 | one tempting item |
| W3 | 8 (+2) | 4 | 2 | two tempting items |

The generator grows the tree by attaching each craftable to a random earlier one that still has
room (depth below the level's, at most 3 craftable inputs), then gives every craftable 0–2 raw
inputs (1–2 for a craftable with no craftable input), drawn from 4 plentiful raw materials.

**Rationale**: small trees keep the episode short and the picture readable; depth is what makes the
conflict hide one level down.

## R4. Conflicts, and why the greedy plan gets stuck

**Decision**: for each conflict the generator takes a new scarce raw material `s` (stock 1), and two
craftables `X` and `T` other than the goal, `T` before `X` in depth-first recipe order, neither an
ancestor of the other, and no ancestor of `X` with two recipes. It adds `s` to `X`'s recipe. It
gives `T` a new first recipe that uses a new craftable `M` (made from `s` and a plentiful raw), plus
sometimes a plentiful raw; `T`'s old recipe becomes its second. W1's harmless alternative is a
second recipe of plentiful raws only, listed second.

The *greedy plan* (inspect as it goes, depth first, always the first recipe) crafts `M` before `X`
and so uses the one unit of `s`; from then on `X`, and so the goal, can no longer be made. The
*reference plan* takes the second recipe of every tempting item.

**Rationale**: this is the mock-up's lantern (Frame from an iron bar that needs coal, or from wood;
the glass needs the coal). Hiding `s` one level down, inside `M`, means an agent sees the conflict
only if it inspects `M` or plans before crafting. The ordering and ancestor rules guarantee that the
greedy plan meets the conflict before it reaches `X` and that no other recipe choice rescues it.

A simulation (2026-11-02, the sketch of R3–R4 over the 30 dev and test seeds per level): every draw
was valid; the greedy plan was stuck on 30/30 W2 and 30/30 W3 workshops; references were W1 8–11,
W2 14–18, W3 24–29 steps.

**Alternatives**: several scarce units with several uses (harder to guarantee "stuck"); conflicts
without an intermediate (the first inspection would show the coal, which makes planning trivial).

## R5. The stuck check

**Decision**: after every successful `craft` (the only call that consumes anything), code checks
whether the goal can still be made: for every combination of recipe choices still open (at most
2² on W3, plus W1's one), it counts what the goal needs, taking held items first, and compares the
raw materials needed with the stock plus the held raw materials. If no combination works, the
episode ends `stuck` (for a retrying architecture with attempts left, the attempt ends; R10).

**Rationale**: an exact answer from a tiny search; ending at once saves the budget an agent could
only waste, and makes "stuck" a clean count. `gather` moves a unit, it never loses one, so only
`craft` can make the goal impossible.

## R6. Reference and budget

**Decision**: the reference is the step count of the reference plan: one `inspect` of every
craftable item it crafts, one `gather` per raw unit it uses, and one `craft` per item it makes. The
budget is 3× the reference (spec FR-009): W1 24–33, W2 42–54, W3 72–87 in the simulation.
`reference_is_optimal` is true: no plan that inspects what it crafts is shorter.

**Rationale**: an agent must inspect before it can know a recipe, so a reference without
inspections would be unreachable. In the simulation, inspecting every craftable in the workshop
first and then following the reference took at most 1.08× the reference, well inside 3×.

## R7. Scripted agents behind the guarantees

**Decision**: three scripted agents in the tests:

- *reference*: the reference plan's calls in order; it crafts the goal in exactly the reference
  steps with no waste (SC-003);
- *greedy*: depth first, inspect each craftable when first reached, always recipe 1, gather what
  is missing, craft; it gets stuck on every W2 and W3 workshop and succeeds on W1 (SC-004);
- *planner*: inspect every craftable reachable through any recipe, then choose recipes with a
  search over the open choices and follow them; it crafts the goal within the budget everywhere
  (SC-004).

## R8. Waste

**Decision**: a unit of a scarce material is wasted when a craft of an item consumes it beyond what
the reference plan's crafts of that same item consume of it; the counts start again each attempt.
The episode counts `wasted` (scarce units, every attempt), `inspected` (distinct items inspected)
and `crafted` (craft calls that succeeded).

**Rationale**: exact, computable from the saved steps alone (SC-006), and it catches the tempting
recipe's intermediate (the greedy plan's one unit of coal goes into the iron bar, which the
reference never crafts), crafts of unneeded items and repeated crafts. A count against the
reference's total use would miss the greedy plan, which uses no more coal than the reference, only
on the wrong item. Plentiful materials are not counted: using more of
them costs steps, which efficiency already shows.

## R9. Tool arguments, results and errors

**Decision**: `inspect(item)` and `gather(item)` take a name exactly as the results write it;
`craft(item, recipe)` takes a name and the recipe number, a JSON integer or a string of digits
(1 or 2). Results:

| Call | Data |
| --- | --- |
| start, `look` | `{"goal", "stock": {name: count}, "inventory": {name: count}}` |
| `inspect` a craftable | `{"item": "frame", "recipes": [["iron bar"], ["wood", "resin"]]}` |
| `inspect` a raw material | `{"item": "coal", "raw": true}` |
| `gather` | `{"gathered": "coal", "stock": 0, "inventory": {…}}` |
| `craft` | `{"crafted": "frame", "recipe": 2, "inventory": {…}}` |
| `craft` the goal | `{"crafted": "lantern", "recipe": 1, "inventory": {…}, "goal": true}` |
| a `craft` that leaves the goal impossible | adds `"stuck": true` (and `"attempts_left": n` for a retrying architecture with attempts left) |

Errors (each costs a step and is an invalid action): `unknown_item`, `not_raw` (gather a
craftable), `out_of_stock`, `no_such_recipe` (a raw material, or a number the item does not have),
`missing_inputs`, `unknown_tool`; `episode_over` costs nothing. Once the item has been inspected,
`missing_inputs` names what is missing and `no_such_recipe` how many recipes there are; before, both
say neither, so a failed craft never reveals a recipe that `inspect` would (FR-006).

## R10. Episode, attempts and scouts

**Decision**: one body: `Kit.add_scout` returns None. `MAX_ATTEMPTS = 3`. For a retrying
architecture with attempts left, getting stuck ends the attempt: the environment restarts itself
(stock refilled, inventory emptied, recipes still hidden from the new attempt's log) and the result
carries `attempts_left`. With no attempt left, getting stuck ends the episode. A restart costs no
step. The episode ends at the goal, stuck, at the budget, or when the architecture stops.

## R11. Results and report

**Decision**: new nullable row fields `stuck` (bool), `wasted`, `inspected`, `crafted`;
`reference_is_optimal` is shared. The report's workshop table: Success, Stuck, Steps, Wasted,
Efficiency, Budget hit, Tokens, Latency (medians or shares), and a spread table Success and Steps
(min–max) with repeats. The comparison uses the dungeon's columns with the A6 override `hybrid` →
`mapstate`.

## R12. Architectures on the workshop

**Decision**:

- A1 `react`: unchanged; the start view is its first message.
- A2 `mapstate`, A3 `plan_execute`, A4 `reflexion`: a `WorkshopLog` (new
  `src/apl/arch/workshop_log.py`) built only from tool results: the goal, the stock, the inventory
  and every recipe inspected, rendered as text. It draws no conclusion (no plan, no conflict
  warning). Its `progress` count (new inspections plus successful gathers and crafts) feeds A4's
  staleness check, so a long production phase after the inspections is not taken for a stale
  attempt.
- A4: the failure reason after getting stuck with attempts left is `stuck`; it joins `RESTARTED`;
  the workshop uses the rune floor's one-call-at-a-time `act`, stopping after the first result with
  `attempts_left`, so no call spills into the next attempt.
- A5 `supervisor`: its helpers become per-problem. On the workshop, a researcher (`look`,
  `inspect`) and a crafter (`gather`, `craft`), both on the workshop log; the supervisor's and the
  helpers' texts name them and the workshop instead of the dungeon. The dungeon's helpers, texts and
  behaviour stay as they are.
- A6 `hybrid`: a workshop branch. Code keeps the workshop log and offers every action it can take
  now: `inspect X` for each craftable named in the goal or a seen recipe and not yet inspected,
  `gather R (n left)` for each raw material in stock, `craft X with recipe k (uses a, b)` for each
  seen recipe whose inputs are held. The model answers with an option number. Code never chooses a
  recipe or a plan.
- A2r, A7–A9: not registered for `workshop`.

**Rationale**: matches the spec and the M9–M10 precedent; A5's split follows the workshop's two
kinds of work, finding out and making, as the mock-up suggests.

## R13. CLI

**Decision**: `apl workshop show --level W2 --seed 1000 [--route reference] [--html OUT]` prints the
goal, the stock, the tree (one line per craftable with its recipes, the reference's choice marked
`*`, tempting recipes marked `!`), the reference and the budget; `--route reference` adds the
reference plan's calls in order; `--html` writes the viewer's SVG.

## R14. Viewer

**Decision**: `GET /api/workshop?level=&seed=` returns the workshop (goal, stock, recipes, scarce
materials, reference steps, budget, SVG, reference frames). The SVG draws the tree as in the
mock-up: one box per item in layers by depth under the goal, an edge from each item to each input,
second recipes' edges dashed, raw materials as leaves with their stock. Boxes carry `data-item`.
Per frame the page shows the inspected items (under "Agent's view" an uninspected craftable's box
shows `?` and its recipe edges are hidden), the stock counts (a scarce material red at 0), the
held counts as badges, and the crafted goal. Under the truth view the reference plan's edges are
outlined. Stats: steps against budget and reference, inspected, wasted, and at the end `Crafted
lantern`, `Stuck` or `Out of budget`. The episode-id pattern widens to `W[1-3]`.

## R15. Fairness checks

**Decision**: the import test's allowed list gains `apl.workshop.tools` and
`apl.workshop.results`; `apl.workshop.generator`, `env`, `plans` and `model` are forbidden. A
boundary test plays random calls and checks every result's shape, that no result shows a recipe
before its item was inspected, and that the start and `look` results are identical for workshops
that differ only in their recipes. AGENTS.md lists the new imports and tools.
