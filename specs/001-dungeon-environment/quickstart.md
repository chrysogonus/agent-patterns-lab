# Quickstart: Validate M1

Proves the feature end to end. No API key or network is needed, and no model is called.

## Prerequisites

- uv installed; Python 3.12 is pinned by `.python-version`.
- `uv sync` run once.

## 1. All checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

Expected: everything passes. The test suite covers SC-001 to SC-012. These groups map to the
spec:

| Tests | Proves |
| --- | --- |
| Level rules over dev, test and 1,000 extra seeds per level | SC-001, SC-004 |
| Golden fingerprints and double generation | SC-003, FR-009 |
| Reference dungeons with hand-worked answers | SC-008 |
| Replaying the solution for every dev and test dungeon | SC-002 |
| One test per error code, with step counting | SC-005 |
| Shape check on tool results and the `apl.dungeon` import boundary | SC-007, Constitution II |
| Label uniqueness, stability and spread | SC-009 |
| Map and picture content, byte-identical output, frames vs. environment | SC-010 to SC-012 |
| Timing of the full seed sets | SC-006 (< 10 s) |

## 2. Look at a dungeon

```bash
uv run apl dungeon show --level L3 --seed 1000
```

Expected: a 5×5 text map with labels, `S`, `E`, two locked doors (uppercase color letters) and
two keys (lowercase letters).

## 3. Overlay the shortest solution

```bash
uv run apl dungeon show --level L3 --seed 1000 --route solution
```

Expected: the map with `*` on the route, then a step table ending with `end: <label> at step
<n> (exit)`, where `n` is the reported shortest length.

## 4. Watch it as an animation

```bash
uv run apl dungeon show --level L3 --seed 1000 --route solution --html /tmp/l3-1000.html
```

Open `/tmp/l3-1000.html` in a browser with the network turned off. Expected:

- The dungeon is drawn with colored locks and keys.
- Play moves the agent one step at a time. Keys move into the inventory, and doors open after
  `use`.
- Pause, ← and →, the slider and the speed select all work.
- Jumping with the slider to the last step shows the same state as playing to the end.

## 5. A scripted episode with mistakes

Write `route.json` with a few deliberately wrong actions, for example moving into a wall or
using a key that isn't held:

```json
{"actions": [
  {"tool": "move", "args": ["up"]},
  {"tool": "use", "args": ["red key", "north"]},
  {"tool": "look", "args": []}
]}
```

```bash
uv run apl dungeon show --level L2 --seed 1000 --route route.json --html /tmp/l2-errors.html
```

Expected: the step table shows `invalid_direction` and `not_in_inventory` (or `no_door`,
depending on the layout) at the start room. In the animation those steps are highlighted and
the agent stays put.

## 6. Still picture without a route

```bash
uv run apl dungeon show --level L1 --seed 1000 --html /tmp/l1.html
```

Expected: a still SVG of the dungeon with no controls.
