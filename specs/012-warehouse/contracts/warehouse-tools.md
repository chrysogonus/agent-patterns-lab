# Contract: Warehouse Tools, Results and Prompt

Research R3–R5, R11. Results use the shared envelope `{"ok": bool, "error": {"code", "message"} |
null, "data": {...} | null}`.

## Base prompt (`apl.warehouse.prompt.BASE_PROMPT`)

Explains, without strategy: the floor (shelves, aisles numbered north to south, the west and east
corridors, the dock S, the drop zone D), cell names (`A1` north-west, letters east, numbers south),
that a robot sees the packages of the corridors it stands in, that it carries one package at a
time, picks the package on its cell and delivers it by dropping it on D, that the episode ends when
every package is delivered, that every call is one step and failed calls cost a step, the budget,
and the result envelope.

## Tool schemas

| Tool | Parameters | Description (each ends with the shared cost sentence) |
| --- | --- | --- |
| `look` | none | Describe the robot's cell, the corridors it stands in, the packages it sees, what it carries, whether it is on D, and the packages delivered. |
| `move` | `direction`: `north`, `east`, `south`, `west` | Move one cell and describe it. Errors: invalid_direction, shelf, edge. |
| `pick` | none | Pick up the package on the robot's cell. Errors: no_package, already_carrying. |
| `drop` | none | Drop the carried package on D, which delivers it. Errors: not_on_drop, not_carrying. |

## Start view (free) and `look`

```json
{"ok": true, "error": null, "data": {
  "cell": "A2", "corridors": ["west corridor"], "packages_seen": [],
  "carrying": null, "on_drop": false, "delivered": 0, "packages": 3,
  "columns": 9, "rows": 5,
  "floor": [".........", "S#######D", ".........", ".#######.", "........."],
  "aisles": ["aisle 1", "aisle 2", "aisle 3"]}}
```

`floor` and `aisles` appear in the start view only (the plan does not change). In `floor`, `#` is a
shelf, `.` an open cell, `S` the dock and `D` the drop zone; packages are never drawn in it.

## `move` (success)

The robot view: `cell`, `corridors`, `packages_seen` (`[{"package": "package 2", "cell": "D3"}]`,
waiting packages on cells of those corridors, north to south, then west to east), `carrying`,
`on_drop`, `delivered`, `packages`, `columns`, `rows`.

## `pick`, `drop` (success)

```json
{"ok": true, "error": null, "data": {"picked": "package 2", "cell": "D3"}}
{"ok": true, "error": null, "data": {"delivered_package": "package 2", "delivered": 2, "packages": 3}}
```

## Errors

| Code | When | Message (example) |
| --- | --- | --- |
| `invalid_direction` | not one of the four directions | `'up' is not a direction; use north, east, south or west.` |
| `shelf` | the neighbor is a shelf | `There is a shelf to the north.` |
| `edge` | the neighbor is off the floor | `The floor ends to the west.` |
| `no_package` | `pick` on a cell with no waiting package | `There is no package on D3.` |
| `already_carrying` | `pick` while carrying | `You already carry package 2.` |
| `not_on_drop` | `drop` away from D | `You can drop only on D.` |
| `not_carrying` | `drop` with nothing carried | `You carry nothing.` |
| `unknown_tool` | any other tool name | `There is no tool named 'push'. The tools are look, move, pick and drop.` |
| `episode_over` | any call after the end (uncounted) | `The episode is over.` |

Results never show a package on a cell of a corridor the robot is not standing in, and never the
reference.
