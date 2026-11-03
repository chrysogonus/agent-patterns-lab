# Contract: Workshop Tools and Results

Research R2, R5, R8–R10. The architectures' only surface on the workshop.

## Base prompt

```text
You are in a workshop and must craft one goal item. Items are made from recipes: a recipe turns
items you hold into a new item. Some items have two recipes. Raw materials are not crafted: you
gather them from the stock, one unit per call, and the stock of each is limited.

You are given the goal, the stock and your inventory at the start. You do not know any recipe
until you inspect the item. Crafting takes the recipe's inputs out of your inventory. If the goal
can no longer be made from your inventory and the stock, the episode ends.

Use the tools look, inspect, gather and craft. Every tool call is one step, and failed calls cost a
step too. You have a limited step budget, so avoid wasted calls. The episode ends when you craft the
goal.

Tool results are JSON objects with "ok", "error" and "data". When "ok" is false, "error" has a
"code" and a "message" that explain what went wrong.
```

The last two paragraphs follow the other problems. No advice on planning, inspecting first or which
recipe to choose (Constitution I, III).

## Tool schemas

Each description ends with " Every call costs one step, including failed calls.", as on the other
problems.

| Tool | Parameters | Description |
| --- | --- | --- |
| `look` | none | Describe the workshop again: the goal, the stock and your inventory. |
| `inspect` | `item`: string | Show an item's recipes, or that it is a raw material. Error: unknown_item. |
| `gather` | `item`: string | Take one unit of a raw material from the stock. Errors: unknown_item, not_raw, out_of_stock. |
| `craft` | `item`: string, `recipe`: integer | Make an item with one of its recipes (1 or 2), using the inputs from your inventory. Errors: unknown_item, no_such_recipe, missing_inputs. |

## Results

Envelope as on the other problems. Data shapes as in research R9:

| Data shape | From |
| --- | --- |
| `{"goal": "lantern", "stock": {"coal": 1, "iron ore": 2, …}, "inventory": {}}` | the start view, `look` |
| `{"item": "frame", "recipes": [["iron bar"], ["wood", "resin"]]}` | `inspect` a craftable |
| `{"item": "coal", "raw": true}` | `inspect` a raw material |
| `{"gathered": "coal", "stock": 0, "inventory": {"coal": 1}}` | `gather` |
| `{"crafted": "frame", "recipe": 2, "inventory": {…}}` | `craft` |
| `{"crafted": "lantern", "recipe": 1, "inventory": {…}, "goal": true}` | `craft` the goal; the episode ends |
| `{"crafted": "iron bar", "recipe": 1, "inventory": {…}, "stuck": true}` | a craft that leaves the goal impossible; the episode ends |
| the same with `"attempts_left": 2` | a retrying architecture's stuck craft with attempts left; the workshop restarts |

Stock and inventory list items in a fixed order (the stock's order, then crafted items by name);
an item with count 0 is left out of the inventory but kept in the stock.

## Errors

| Code | When | Message |
| --- | --- | --- |
| `unknown_item` | a name that is no item of this workshop | `'nails' is not an item here.` |
| `not_raw` | gather a craftable | `'frame' is crafted, not gathered.` |
| `out_of_stock` | gather with none left | `There is no coal left in the stock.` |
| `no_such_recipe` | craft a raw material, or a recipe number the item does not have | after inspecting: `'frame' has 2 recipes; recipe 3 does not exist.`; before: `'frame' has no recipe 3.`; a raw material: `'coal' is a raw material; gather it.` |
| `missing_inputs` | an input not held | after inspecting: `Missing for frame (recipe 2): resin.`; before: `Missing inputs for frame (recipe 2).` |
| `unknown_tool` | another tool name | `There is no tool named 'build'. The tools are look, inspect, gather and craft.` |
| `episode_over` | any call after the end; not counted | `The episode is over.` |

Before an item is inspected, its errors name neither its inputs nor how many recipes it has, so a
failed `craft` cannot stand in for `inspect` (FR-006). Whether a recipe number exists still shows
in the error code, at a step per try.

## What a result never shows

A recipe of an item not inspected, the reference plan or choices, which materials are scarce, the
budget, why the goal can no longer be made, and the waste count. The boundary test checks this
(research R15).
