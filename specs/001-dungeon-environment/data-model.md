# Data Model: Dungeon Generator, Environment, Tools and Solver

The types are frozen dataclasses unless they are marked mutable. A room is identified internally
by its grid position `Pos = (x, y)`: `x` is the column, `y` the row, and `(0, 0)` is the
north-west corner, so `north` means `y − 1`. Positions never appear in agent-facing results;
agents only see labels.

## Internal types (runner, scorer, tests and renderers only)

### Direction (StrEnum)

`north`, `east`, `south`, `west`, in that fixed order, which tie-breaking also uses. Each has
a `(dx, dy)` and an opposite.

### Level

| Field | Type | Rule |
| --- | --- | --- |
| `name` | `str` | `L1`, `L2`, `L3` |
| `size` | `int` | 3, 4, 5 |
| `locks` | `int` | 0, 1, 2 |
| `extra_doors` | `int` | 1, 2, 3 |
| `min_dead_ends` | `int` | 0, 0, 2 |

`LEVELS: dict[str, Level]` is the only source of these numbers (FR-010).

### Edge

An unordered pair of neighboring positions, stored with the smaller position first, so that
`Edge(a, b) == Edge(b, a)`. Validation: the two positions differ by exactly 1 in x or in y.

### Layout

Everything about a dungeon except its level, seed and solution. Hand-built reference dungeons
are Layouts too.

| Field | Type | Rule |
| --- | --- | --- |
| `size` | `int` | ≥ 2 |
| `doors` | `frozenset[Edge]` | Every edge lies inside the grid |
| `locks` | `Mapping[Edge, str]` | Keys are a subset of `doors`; the values are distinct colors |
| `keys` | `Mapping[str, Pos]` | One key per lock color; each key lies in a room |
| `start`, `exit` | `Pos` | Inside the grid; different |
| `labels` | `Mapping[Pos, str]` | Exactly one per room; unique |

`Layout.validate()` checks these structural rules only. The level rules are checked by
`check_level_rules(layout, level)` (FR-001 to FR-008), which the generator and the tests share.

### Dungeon

| Field | Type | Rule |
| --- | --- | --- |
| `level` | `Level \| None` | `None` for a hand-built dungeon |
| `seed` | `int \| None` | ≥ 0; `None` for a hand-built dungeon |
| `layout` | `Layout` | Passes `check_level_rules` when generated |
| `solution` | `Solution` | From the solver; never `None` (FR-013) |
| `budget` | `int` (property) | `3 × solution.length` (FR-020) |

`generate(level_name, seed) -> Dungeon` raises `ValueError` for an unknown level, a negative
seed or a seed that isn't an `int` (edge cases). `Dungeon.from_layout(layout)` builds a
hand-built dungeon (level and seed `None`). It solves the layout and raises `ValueError` if
the layout is unsolvable.

### Action

| Field | Type | Rule |
| --- | --- | --- |
| `tool` | `"look" \| "move" \| "take" \| "use"` | |
| `args` | `tuple[str, ...]` | 0 arguments for `look`, 1 for `move` and `take`, 2 for `use` |

### Solution

| Field | Type | Rule |
| --- | --- | --- |
| `actions` | `tuple[Action, ...]` | Only `move`, `take`, `use` |
| `length` | `int` | `== len(actions)` (FR-012) |

`solve(layout) -> Solution | None`. `None` means unsolvable.

### Episode (mutable)

| Field | Type | Notes |
| --- | --- | --- |
| `dungeon` | `Dungeon` | |
| `position` | `Pos` | Starts at `layout.start` |
| `inventory` | `list[str]` | Key colors, in pick-up order; keys stay after use (FR-019) |
| `opened` | `set[Edge]` | Locked doors that have been opened; they stay open from both sides |
| `steps` | `int` | Counted tool calls |
| `invalid_actions` | `int` | Counted calls that returned an error |
| `end_reason` | `EndReason \| None` | `None` while running |
| `log` | `list[LogEntry]` | Every call, including `episode_over` calls |

**State transitions**:

```text
running ──move into exit room──────────────────────────────▶ ended(exit)      success
running ──counted call with steps == budget, not at exit───▶ ended(budget)    budget_hit
running ──stop()───────────────────────────────────────────▶ ended(stopped)
ended   ──any tool call─▶ ended   error episode_over, not counted, no state change
```

The exit check happens before the budget check, so reaching the exit on the last step is a
success (edge case). `stop()` on an episode that has already ended does nothing.

### LogEntry

| Field | Type | Notes |
| --- | --- | --- |
| `index` | `int` | Position in the log, starting at 0 |
| `step` | `int \| None` | Step number (1-based) when counted; `None` for `episode_over` |
| `action` | `Action` | |
| `result` | `ToolResult` | Exactly what the agent received |

### Outcome

The record of a finished episode. Its shape is in [contracts/outcome.md](contracts/outcome.md).
Fields: `level`, `seed`, `success`, `end_reason`, `steps`, `optimal_steps`, `budget`,
`invalid_actions`, `budget_hit`, `log`. It is only available after the episode has ended.

### Frame

One snapshot used for drawing. It is built by replaying a route (research R7).

| Field | Type | Notes |
| --- | --- | --- |
| `step` | `int` | 0 for the start state |
| `action` | `Action \| None` | `None` in frame 0 |
| `ok` | `bool` | |
| `error_code` | `ErrorCode \| None` | |
| `position` | `Pos` | |
| `inventory` | `tuple[str, ...]` | |
| `keys_in_rooms` | `Mapping[str, Pos]` | Keys not yet taken |
| `opened` | `frozenset[Edge]` | |
| `end_reason` | `EndReason \| None` | Set in the frame where the episode ended |

`build_frames(dungeon, actions) -> list[Frame]` gives `len(actions) + 1` frames. With
`expected_results`, as for an episode log, it raises `ValueError` if a replayed result differs
from the logged one. With the logged `end_reason`, a `stopped` end is applied to the last frame
after the replay, because stopping is not a tool call. Any other mismatch raises `ValueError`.
`parse_route_file(data) -> RouteFile` reads both route-file formats in contracts/cli.md.

### SeedSet

`DEV_SEEDS = range(1000, 1010)` and `TEST_SEEDS = range(2000, 2020)`, used for every level.
Invariant: the two sets are disjoint (FR-023).

## Agent-facing types (`apl.dungeon.results`)

These are the only types an architecture receives. They contain the current room only
(FR-022). The shapes and examples are in [contracts/tools.md](contracts/tools.md).

| Type | Fields |
| --- | --- |
| `ExitView` | `direction: Direction`, `lock: str \| None` (the color while locked, `None` when open or never locked) |
| `RoomView` | `label: str`, `exits: tuple[ExitView, ...]` (direction order), `items: tuple[str, ...]` (e.g. `"red key"`), `inventory: tuple[str, ...]`, `is_exit: bool` |
| `ToolError` | `code: ErrorCode`, `message: str` |
| `ToolResult` | `ok: bool`, `error: ToolError \| None`, `data: RoomView \| InventoryView \| DoorOpened \| None` |
| `InventoryView` | `inventory: tuple[str, ...]` |
| `DoorOpened` | `direction: Direction`, `color: str` |

`ErrorCode` (StrEnum): `invalid_direction`, `no_door`, `locked`, `no_such_item`,
`not_in_inventory`, `wrong_key`, `not_locked`, `episode_over`.

`EndReason` (StrEnum): `exit`, `budget`, `stopped`.

## Relationships

```text
Level 1──* Dungeon 1──1 Layout
Dungeon 1──1 Solution
Dungeon 1──* Episode 1──* LogEntry ──1 ToolResult
Episode ──end──▶ Outcome (contains the log)
(Dungeon, [Action]) ──build_frames──▶ [Frame] ──▶ text map | HTML picture/animation
```
