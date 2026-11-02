# Data Model: The Workshop

Runner-side types live in `src/apl/workshop/`; architectures see only `tools` and `results`
(Constitution II). Names follow the rune floor package (specs/010 data-model.md).

## WorkshopLevel (`model.py`)

| Field | Type | Meaning |
| --- | --- | --- |
| `name` | str | `W1`, `W2`, `W3` |
| `craftables` | int | craftable items in the tree: 3, 5, 8 (research R3) |
| `depth` | int | 2, 3, 4 |
| `conflicts` | int | 0, 1, 2 (research R4) |

`LEVELS: dict[str, WorkshopLevel]`, in the order W1, W2, W3. `CRAFTABLE_NAMES` (20) and
`RAW_NAMES` (14) are the fixed vocabularies.

## Workshop (`model.py`)

| Field | Type | Meaning |
| --- | --- | --- |
| `level` | WorkshopLevel \| None | None for a hand-built workshop |
| `seed` | int \| None | |
| `goal` | str | the item to craft |
| `recipes` | dict[str, tuple[tuple[str, ...], ...]] | every craftable's recipes, in their fixed order |
| `stock` | dict[str, int] | every raw material's starting count, in a fixed order |
| `scarce` | frozenset[str] | raw materials with a conflict (stock 1) |
| `reference_choice` | dict[str, int] | the reference plan's recipe (1-based) for every craftable with two |
| `reference` | int | steps of the reference plan (research R6) |

Derived: `reference_steps = reference`, `budget = 3 × reference`, `reference_is_optimal = True`,
`raw(name)` (in the stock), `craftable(name)` (has recipes).

Validation (tests): every input is a craftable or a raw material of the same workshop; the
craftables under the goal form a tree with no cycle; the reference plan is feasible from the start;
on W2 and W3 the greedy plan gets stuck and on W1 it succeeds; the level's numbers of craftables,
depth and conflicts hold; every scarce material has stock 1.

## Plans (`plans.py`)

- `feasible(workshop, stock, inventory) -> bool`: whether the goal can still be made (research R5).
- `reference_calls(workshop) -> list[tuple[str, dict]]`: the reference plan as tool calls, in
  order (inspect each craftable when first reached, gather what is missing, craft), depth first.
- `greedy_calls(workshop)` and `planner_calls(workshop)`: the scripted plans of research R7, as
  calls (`greedy_calls` stops where the greedy plan crafts the item that leaves it stuck).
- `reference_use(workshop) -> dict[tuple[str, str], int]`: (item, raw material) → units the
  reference plan's crafts of that item consume, for waste (research R8).

## Action (`model.py`)

`tool` (`look`, `inspect`, `gather`, `craft`, `unknown`) and `args` (strings, as shown).

## Results (`results.py`, agent-facing)

| Type | `to_dict()` |
| --- | --- |
| `ErrorCode` | `unknown_item`, `not_raw`, `out_of_stock`, `no_such_recipe`, `missing_inputs`, `unknown_tool`, `episode_over` |
| `EndReason` | `goal`, `stuck`, `budget`, `stopped` |
| `StoreView` | `{"goal", "stock", "inventory"}` (start, `look`) |
| `RecipesView` | `{"item", "recipes": [[input, ...], ...]}` |
| `RawView` | `{"item", "raw": true}` |
| `GatheredView` | `{"gathered", "stock", "inventory"}` |
| `CraftedView` | `{"crafted", "recipe", "inventory"}` (+ `"goal": true`; + `"stuck": true` and, for a retrying architecture with attempts left, `"attempts_left"`) |
| `ToolResult` | `{"ok", "error", "data"}` as on the other problems |

## Episode (`env.py`)

| Field | Meaning |
| --- | --- |
| `workshop` | the Workshop |
| `stock`, `inventory` | current counts |
| `inspected` | items inspected, in order (the episode's, every attempt) |
| `crafted` | successful crafts (every attempt) |
| `wasted` | scarce units consumed beyond the reference plan's use for the same item (research R8) |
| `steps`, `invalid_actions`, `end_reason`, `log` | as on the other problems |
| `attempt`, `max_attempts`, `on_step`, `on_restart` | as on the rune floor |

Transitions:

```text
start: stock = workshop.stock, inventory = {}
inspect(item)        → recipes or raw; nothing else changes
gather(raw)          → stock[raw] − 1, inventory[raw] + 1
craft(item, k)       → inputs leave the inventory, item enters it; scarce inputs beyond the
                       reference use count as wasted; then
                       item is the goal          → end_reason = goal
                       goal no longer feasible   → retrying with attempts left: result carries
                                                   stuck and attempts_left, stock and inventory
                                                   reset, attempt + 1, on_restart fires;
                                                   otherwise end_reason = stuck
steps reach the budget → end_reason = budget (crafting the goal on the last step counts first)
restart() (A4 after any other failure) → stock and inventory reset, attempt + 1
```

## Outcome (`env.py`)

`level`, `seed`, `end_reason`, `success` (goal crafted), `steps`, `optimal_steps` (`reference`),
`budget`, `invalid_actions`, `stuck` (end_reason is `stuck`), `wasted`, `inspected` (distinct),
`crafted`, `attempts`, `reference_is_optimal` (true), `log`.

## WorkshopLog (`src/apl/arch/workshop_log.py`, architecture side)

| Field | Meaning |
| --- | --- |
| `goal` | from the start view |
| `stock`, `inventory` | the latest counts seen |
| `recipes` | item → its recipes, for every item inspected; raw materials seen as raw |

`from_start(start_json)`, `apply(name, args, result)`, `render()`, `known` (items inspected),
`progress` (new inspections plus successful gathers and crafts; A4's staleness counter),
`options()` for A6 (research R12).

`render()`, for example:

```text
Goal: lantern.
Stock: coal 1, iron ore 2, sand 3, wood 2, resin 1.
Inventory: sand 1.
Recipes seen (2):
- lantern: frame, lens, oil
- frame: recipe 1: iron bar; recipe 2: wood, resin
```

## Frames (`frames.py`)

A frame per step: `step`, `action`, `ok`, `error`, `end_reason`, `stock`, `inventory`, `inspected`
(names), `crafted` (count), `wasted`, `attempt` (when > 1). `reference_frames(workshop)`: the
reference plan played from the start.
