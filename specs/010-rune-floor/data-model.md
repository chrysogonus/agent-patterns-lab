# Data Model: The Rune Floor

Runner-side types live in `src/apl/rune/`; architectures see only `tools` and `results`
(Constitution II). Names follow the signal trace package (specs/009 data-model.md).

## RuneLevel (`model.py`)

| Field | Type | Meaning |
| --- | --- | --- |
| `name` | str | `R0`, `R1`, `R2`, `R3` |
| `columns` | int | 7, 7, 9, 9 |
| `rows` | int | 5, 5, 7, 7 |
| `rule` | str | `none`, `cycle3`, `cycle4`, `rows` (research R4) |

`LEVELS: dict[str, RuneLevel]`, in the order R0, R1, R2, R3.

## Cell (`model.py`)

`tuple[int, int]`: `(x, y)`, 0-based, x east, y south. `name(cell)` gives `A1`-style names;
`parse(name)` the reverse (agent-facing parsing lives in `env`). `COLORS = ("red", "blue",
"green", "yellow")`.

## Rule (`rules.py`)

| Field | Type | Meaning |
| --- | --- | --- |
| `kind` | str | `none`, `cycle`, `rows` |
| `colors` | tuple[str, ...] | the cycle (`cycle`), `(odd-row color, even-row color)` (`rows`), empty (`none`) |
| `traps` | frozenset[Cell] | R0's trap cells; empty otherwise |

Functions: `allows(rule, floor, cell, state) -> bool`; `next_state(rule, state) -> int` (state + 1
modulo the cycle length for `cycle`, 0 otherwise); `describe(rule) -> str` for the experimenter
(`colors cycle: red, blue, green`, `odd rows blue, even rows yellow`, `fixed trap cells`). A
`Rule` never reaches an architecture.

## Floor (`model.py`)

| Field | Type | Meaning |
| --- | --- | --- |
| `level` | RuneLevel \| None | None for a hand-built floor |
| `seed` | int \| None | |
| `columns`, `rows` | int | size |
| `colors` | dict[Cell, str] | every cell but S and G |
| `start`, `goal` | Cell | `(0, rows // 2)`, `(columns − 1, rows // 2)` |
| `rule` | Rule | hidden |
| `reference` | int | moves on the shortest safe path (research R6) |

Derived: `reference_steps = reference`, `budget = 4 × reference`, `reference_is_optimal = True`.

Validation (tests): every cell but S and G has one of `COLORS`; the reference is finite; the
straight row from S to G is not safe (`reference > columns − 1`); R0 floors pass the memory-only
agent (research R7); references within the pinned bounds (≤ 12 on R0–R1, ≤ 16 on R2–R3).

## Search (`rules.py`)

`reference(floor) -> int` and `reference_path(floor) -> list[Cell]`: breadth-first over `(cell,
state)` from `(start, 0)`, ties broken north, east, south, west. `outcome_of(floor, walk_len,
cell) -> "safe" | "trap" | "start" | "goal"` is the one place the move physics live (research R3);
the environment, the frames and the scripted agents use it.

## Action (`model.py`)

`tool` (`look`, `move`, `unknown`) and `args` (strings, as shown); as the other problems'.

## Results (`results.py`, agent-facing)

| Type | `to_dict()` |
| --- | --- |
| `ErrorCode` | `invalid_direction`, `edge`, `unknown_tool`, `episode_over` |
| `FloorView` | `{"columns", "rows", "start", "goal", "position", "floor": [[word, ...], ...]}` |
| `StepView` | `{"position", "color"}` (`color` is `start` back on S) |
| `TrapView` | `{"trap", "color", "position"}` (+ `"attempts_left"` for a retrying architecture with attempts left) |
| `GoalView` | `{"position", "goal": true}` |
| `ToolResult` | `{"ok", "error", "data"}` as on the other problems |

## Episode (`env.py`)

| Field | Meaning |
| --- | --- |
| `floor` | the Floor |
| `position` | the agent's cell |
| `walk` | the cells of the current walk, in order |
| `steps`, `invalid_actions` | as on the other problems |
| `traps` | list of `(cell, state, attempt, step)` |
| `repeated_traps` | count (research R8) |
| `walks` | walks started, the first included |
| `reached_goal` | bool |
| `end_reason` | `goal`, `budget`, `stopped` (shared `EndReason` values where they exist) |
| `log` | `LogEntry(index, step, action, result, attempt, scout=0)` |
| `attempt`, `max_attempts`, `on_step`, `on_restart` | as on the signal trace |

Transitions:

```text
start: position = S, walk = [], walks = 1
move off the floor          → error edge; nothing changes
move onto S                 → position = S, walk = [], walks += 1
move onto G                 → reached_goal, end_reason = goal
move onto a cell, allowed   → position = cell, walk += [cell]
move onto a cell, forbidden → trap recorded (repeated if (cell, state) trapped before);
                              position = S, walk = [], walks += 1;
                              retrying with attempts left: attempt += 1, on_restart fires,
                              result carries attempts_left
steps reach the budget      → end_reason = budget
restart() (A4 after any other failure) → position = S, walk = [], walks += 1, attempt += 1
```

`state` is `rules.next_state` folded over the walk (its length modulo the cycle length on cycle
rules, 0 otherwise).

## Outcome (`env.py`)

`level`, `seed`, `end_reason`, `success` (`reached_goal`), `steps`, `optimal_steps`
(`reference`), `invalid_actions`, `traps`, `repeated_traps`, `walks`, `attempts`,
`reference_is_optimal` (true).

## WalkLog (`src/apl/arch/walk_log.py`, architecture side)

| Field | Meaning |
| --- | --- |
| `columns`, `rows`, `start`, `goal` | from the start view |
| `floor` | rows of color words |
| `position` | the agent's cell |
| `walks` | list of walks; each a list of `(cell, color)` and an ending: `trap at D3`, `back on start`, or open |

`from_start(start_json)`, `apply(name, args, result)` (moves only; `look` refreshes the floor and
position), `render()`, `known` (distinct cells stepped on, traps included), `record(cell)` for
A6: `[(walk step, "safe" | "trap"), ...]`.

## Frames (`frames.py`)

A frame per step: `step`, `action`, `ok`, `error`, `end_reason`, `position`, `walk` (cells),
`walks` (earlier walks, each cells plus how it ended), `traps` (cells with the step and whether
repeated), `attempt`, `traps_count`, `repeated`. `reference_frames(floor)`: the reference path
walked from S.
