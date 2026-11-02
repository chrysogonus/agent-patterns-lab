# Data Model: The Warehouse

Entities for [spec.md](spec.md); decisions in [research.md](research.md).

## WarehouseLevel (`apl.warehouse.model`)

| Field | Type | Meaning |
| --- | --- | --- |
| `name` | str | `P1`, `P2`, `P3` |
| `columns` | int | 9, 9, 11 |
| `aisles` | int | 3, 3, 5 (`rows = 2 × aisles − 1`) |
| `spreads` | tuple of tuples | the allowed packages-per-aisle multisets; one is drawn and shuffled |

`LEVELS: dict[str, WarehouseLevel]`.

## Floor (`apl.warehouse.model`)

| Field | Type | Meaning |
| --- | --- | --- |
| `level` | WarehouseLevel \| None | None for hand-built floors in tests |
| `seed` | int \| None | |
| `columns`, `rows` | int | |
| `dock`, `drop` | Cell `(x, y)`, 0-based | west and east corridor, the shelf row north of the middle aisle |
| `packages` | tuple of (name, Cell) | `package 1` … in shuffled order |
| `reference` | tuple of Action | the reference's calls (R6) |

Derived: `shelf(cell)`, `open(cell)`, `corridors(cell)` (names of the corridors a cell is in),
`corridor_cells(name)`, `neighbor(cell, direction)`, `budget = 3 × len(reference)`,
`reference_steps = len(reference)`, `reference_is_optimal = False`.

Validation (generator, `MAX_TRIES`): packages on distinct aisle cells between the corridors, every
aisle's count from the drawn spread; on P2 and P3 the blind split leaves a robot idle and the
replanning split takes fewer parallel turns (R7).

## Action (`apl.warehouse.model`)

`Action(tool: str, args: tuple[str, ...])`, `to_dict()`, as on the other problems. Tools: `look`,
`move` (direction), `pick`, `drop`, `unknown` (name).

## Robot state (`apl.warehouse.env.Episode`)

| Field | Type | Meaning |
| --- | --- | --- |
| `robots` | list[Cell] | each robot's cell; robot 0 first |
| `carrying` | list[str \| None] | the package each robot carries |
| `added_turn` | list[int] | the turn at which each robot was added (robot 0: 0) |

## Package state (`Episode`)

`waiting: dict[str, Cell]` (on the floor), carried (in `carrying`), `delivered: list[str]` in
delivery order. A package is in exactly one of these.

## Episode (`apl.warehouse.env`)

Fields as the survey field's: `steps`, `invalid_actions`, `end_reason`, `log`, `on_step`,
`turn_source`, `attempt = 1`, `max_attempts = 1`, `on_restart`; plus `seen: set[Cell]` (corridor
cells any robot has stood in a corridor with) and the robot and package state above.

Transitions (each counted call costs one step; an error changes nothing but the counters):

| Call | Condition | Effect |
| --- | --- | --- |
| `move(d)` | `d` a direction and the neighbor open | robot moves; its corridors' cells join `seen` |
| `move(d)` | otherwise | error `invalid_direction`, `shelf` or `edge` |
| `pick()` | not carrying and a package waits on its cell | the package moves to `carrying` |
| `pick()` | otherwise | error `no_package` or `already_carrying` |
| `drop()` | carrying and on D | the package is delivered |
| `drop()` | otherwise | error `not_on_drop` or `not_carrying` |
| any | the episode is over | error `episode_over`, uncounted |

After a call: every package delivered → `end_reason = delivered`; else steps ≥ budget →
`budget`. `stop()` → `stopped`. `add_scout()` adds a robot on the dock (up to 4) and records its
turn. `restart()` returns False.

## Outcome (`apl.warehouse.env`)

`level`, `seed`, `end_reason`, `steps`, `optimal_steps` (the reference), `budget`,
`invalid_actions`, `log`, `delivered`, `packages`, `added_turns` (the turn each robot was added
at, saved so idle robot-turns can be rebuilt from the saved outcome), `reference_is_optimal`,
`attempts = 1`, and the
properties `success` (`end_reason == delivered`), `budget_hit`, `scouts` (robots that made a call),
`parallel_turns`, `idle_robot_turns` (R8). `to_dict()` adds them all.

## Views (`apl.warehouse.results`)

- `RobotView`: `cell`, `corridors` (names), `packages_seen` (list of `{package, cell}`),
  `carrying` (name or null), `on_drop`, `delivered`, `packages`, `columns`, `rows`.
- `StartView`: `RobotView` fields plus `floor` (rows of `#`, `.`, `S`, `D`) and `aisles`.
- `Picked(package, cell)`, `Dropped(package, delivered, packages)`.
- `ErrorCode`: `invalid_direction`, `shelf`, `edge`, `no_package`, `already_carrying`,
  `not_on_drop`, `not_carrying`, `unknown_tool`, `episode_over`.
- `EndReason`: `delivered`, `budget`, `stopped`.
- `ToolResult`: the shared envelope (`ok`, `error`, `data`).

## FloorMap (`apl.arch.floor_map`, architecture side)

Built from tool results only: `columns`, `rows`, `floor` rows, `aisles`, `seen_corridors`,
`packages` (name → cell, waiting as last seen), `carrying`, `delivered`, `total`, `current`.
`apply(name, args, result)` updates from one result; `render(others, here=True)` draws the grid and
lists. `SharedMap` keeps one `FloorMap` with per-robot `positions` and `carried`.
