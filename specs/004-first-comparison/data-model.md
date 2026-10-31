# Data Model: First Comparison, with Orchestrator Architectures

Additions to the M1–M3 models. Everything not named here is unchanged. File formats are in
[contracts/results.md](contracts/results.md).

## Environment (runner side)

### Scout (`apl.dungeon.env`)

| Field | Type | Notes |
| --- | --- | --- |
| `position` | `Pos` | Starts at the layout's start |
| `inventory` | `list[str]` | Key colors in pick-up order; this scout's only |

### Episode (changed)

| Field | Change |
| --- | --- |
| `scouts` | New: `list[Scout]`, scout 0 created with the episode |
| `position`, `inventory` | Now properties of scout 0 (read and write) |
| `keys_in_rooms` | Leaves out keys held by any scout |
| `add_scout()` | New: appends a scout in the start room, returns its number; `None` at `MAX_SCOUTS` (4) |
| `look/move/take/use/unknown` | New keyword `scout: int = 0`; an unknown number raises `ValueError` |
| `describe(scout=0)` | Describes that scout's room and inventory |

Rules (research R1):

- A call by scout k uses scout k's position and inventory; doors, items, steps and the budget are
  shared.
- After the call: if scout k is in the exit room, `end_reason = exit`; else if the budget is used
  up, `end_reason = budget`.
- Calls after the end return `episode_over`, cost no step, and are logged, as before.

### LogEntry (changed)

| Field | Type | Notes |
| --- | --- | --- |
| `scout` | `int` | New, default 0; in JSON only when not 0 |

### Outcome (changed)

| Field | Type | Notes |
| --- | --- | --- |
| `scouts` | `int` | New: scouts that made at least one tool call; in JSON only when above 1 |

## Kit (architecture side, `apl.kit`)

### Scout (new)

| Field | Type | Notes |
| --- | --- | --- |
| `number` | `int` | 1–3 (scout 0 is the kit's own) |
| `tool_node` | `ToolNode` | Same contract as `kit.tool_node`, acting as this scout |
| `start` | `str` | JSON of a successful `look` result for this scout, at creation |

### Kit (changed)

| Field | Type | Notes |
| --- | --- | --- |
| `add_scout` | `Callable[[], Scout \| None]` | Costs no step; `None` at the limit |

The kit's tool node and every scout's tool node share one lock (research R3).

## Architectures (`apl.arch`)

### SharedMap (`apl.arch.scouts`, new)

| Field | Type | Notes |
| --- | --- | --- |
| `map` | `DungeonMap` | Rooms, exits, connections, items and opened doors seen by all scouts |
| `positions` | `dict[int, str]` | Room label per scout |
| `inventories` | `dict[int, tuple[str, ...]]` | Per scout |
| `claims` | `dict[int, tuple[str, str]]` | Blackboard only: (room, direction) per scout |

`apply(scout, name, args, result)` switches the map's `current` and `inventory` to that scout's,
applies the call with `DungeonMap.apply`, and stores them back (research R8).

### ScoutState (`apl.arch.scouts`, new)

| Field | Type | Notes |
| --- | --- | --- |
| `number` | `int` | 0–3 |
| `task` | `str` | From the orchestrator; a fixed sentence on the blackboard |
| `steps_left` | `int \| None` | The task's step limit; `None` on the blackboard |
| `last_turn` | `list[BaseMessage]` | Its previous reply and that reply's tool results |
| `own_map` | `DungeonMap` | Fan-out only: built from this scout's results |
| `turns` | `int` | Model turns taken; the blackboard's round robin picks the fewest |
| `done` | `bool` | Set when it answers without a tool call or its limit is used up |

### Graph states (one per architecture)

| Architecture | State |
| --- | --- |
| `fanout` (A7) | `scouts: list[ScoutState]`, `replies` (reducer: list concatenation), `misses` |
| `rounds` (A8) | `board: SharedMap`, `scouts`, `replies`, `note`, `misses`, `round` |
| `blackboard` (A9) | `board: SharedMap`, `scouts`, `replies` |

`replies` collects `(scout number, AIMessage)` pairs from the parallel scout calls of one turn; the
`act` node sorts them by scout number and clears them (research R3).

## Runner

### EpisodeRow (changed)

| Field | Type | Notes |
| --- | --- | --- |
| `scouts` | `int \| None` | From `Outcome.scouts` (1 for single-agent episodes); `None` in older rows |
| `orchestrator_calls` | `int \| None` | Model calls with role `orchestrator`; 0 for single-agent episodes; `None` in older rows |

### Meter (changed)

- Counts every call, as before, and orchestrator calls separately.
- Records `role` in a transcript call when the call's metadata has one.
- Guards all of its state with a lock (research R5).

### RunSpec (changed)

- `episodes()` yields level → seed → repeat → architecture (research R10).

### Continue plan (new, `apl.runner.run`)

| Field | Type | Notes |
| --- | --- | --- |
| `record` | `RunRecord` | Read from `run.json` |
| `done` | `set[EpisodeKey]` | Keys with a row |
| `left` | `list[EpisodeKey]` | Planned keys without a row, in run order |
| `cut_off` | `bool` | The last line of `episodes.jsonl` has no newline |
| `refusals` | `list[str]` | Empty when continuing is allowed (research R11, R12) |

## Report (`apl.runner.compare`, new)

### Comparison row

One per (level, architecture) of the completed rows: success rate, median efficiency, median steps,
median tokens, median orchestrator calls and scout calls (`llm_calls − orchestrator_calls`), median
latency, median scouts, and the success and efficiency differences to the reference
(research R14).
