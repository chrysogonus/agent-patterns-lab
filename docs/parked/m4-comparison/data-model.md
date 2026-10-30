# Data Model: A2 Map State and the First Comparison

M2's types (specs/002-runner-react/data-model.md) are unchanged unless listed here.

## DungeonMap (`apl.arch.dungeon_map`)

A2's explicit memory. It is built only from tool results ([research.md](research.md) R3). It is
mutable: `act` updates it in place and returns it as the new state value.

| Field | Type | Meaning |
| --- | --- | --- |
| `rooms` | `dict[str, RoomNote]` | Rooms seen, by label, in the order first seen |
| `current` | `str` | Label of the room the agent is in |
| `inventory` | `tuple[str, ...]` | Item names, as the last room or inventory view showed them |
| `opened` | `list[tuple[str, str, str]]` | (room label, direction, color) of every door opened with `use`, in order; the color comes from the `DoorOpened` result, because the exit's lock is cleared |

### RoomNote

| Field | Type | Meaning |
| --- | --- | --- |
| `exits` | `dict[str, str \| None]` | Direction → lock color as last seen (`None`: no lock), in north, east, south, west order |
| `leads_to` | `dict[str, str]` | Direction → label of the room behind it, once known |
| `items` | `list[str]` | Items in the room as last seen, minus the ones taken since |

**Derived**:

- `unexplored(label)` is the list of exits in `exits` that have no entry in `leads_to`.
- `render()` returns the text of research R4.

**Operations**:

- `DungeonMap.from_start(start_json: str)` builds the map from `kit.start`: one room, which is
  the current room.
- `apply(name: str, args: Mapping, result: Mapping)` applies one tool call with its parsed result
  (research R3). Results with `ok: false` change nothing. A `move` with `ok` but an unexpected
  data shape raises `ValueError`, because that can only be a bug.

**Invariants**:

- `current` is in `rooms`.
- Every `leads_to` target is in `rooms`.
- If `rooms[a].leads_to[d] == b`, then `rooms[b].leads_to[opposite(d)] == a`.
- An exit in `opened` has lock `None`.
- No field holds a position, a step count or a budget.

## MapState (A2 graph state, `apl.arch.mapstate`)

| Key | Type | Reducer | Meaning |
| --- | --- | --- | --- |
| `messages` | `list[BaseMessage]` | none (replaced on each write) | The latest turn only: `[AIMessage]` after `agent`; `[AIMessage, ToolMessage...]` after `act`; `[]` at the start |
| `map` | `DungeonMap` | none | The map |

The model input per turn is described in research R2:

```text
[System(base_prompt + MAP_INSTRUCTIONS), Human(start) | *messages, Human(map.render())]
```

The first turn is the one where `messages == []`.

## EpisodeKey order (`apl.runner.spec`)

`RunSpec.episodes()` yields keys in the order level → seed → repeat → architecture (research
R8). The fields are unchanged.

## RunRecord (`run.json`)

There are no new fields. Continuing a run (research R9) changes only `completed` (to `true`) and
`ended` when the last episode is done.

| Field | Who reads it for continuing |
| --- | --- |
| `architectures`, `levels`, `seed_set`, `seeds`, `repeats` | Rebuild the planned `RunSpec` |
| `settings` | Compared field by field with the current `settings.record()` |
| `versions` | Compared with the current package versions |
| `code.commit`, `code.dirty` | Must equal the current commit; `dirty` must be `false` then and now |

## ContinuationPlan (`apl.runner.run`)

| Field | Type | Meaning |
| --- | --- | --- |
| `path` | `Path` | The run folder |
| `record` | `RunRecord` | From `run.json` |
| `spec` | `RunSpec` | Rebuilt from the record |
| `done` | `int` | Rows already present |
| `remaining` | `list[EpisodeKey]` | Planned keys without a row, in run order |
| `partial_last_row` | `bool` | The last line of `episodes.jsonl` is cut off. Planning only reports it; `continue_run` removes it with `--execute`, after all checks have passed |

`plan_continuation(path, settings)` returns this plan or raises `ValueError` naming every
difference (exit code 2).

## Run loop outcome

`RunOutcome.exit_code` gains code 4: "stopped after 3 infrastructure errors in a row" (research
R11). The streak counts consecutive rows with `status == "error"`, and any completed row resets
it.

## Comparison (`apl.runner.compare`)

All values are built from `EpisodeRow`s by code.

### LevelComparison: one per level, for architectures `a` (the baseline) and `b`

| Metric | Value per architecture | Spread | Difference |
| --- | --- | --- | --- |
| Success rate | Share of completed episodes with `success` | min–max of per-repeat rates | `b − a`, in percentage points |
| Efficiency | Median over successful episodes | min–max of per-repeat medians | `b − a` |
| Tokens | Median of `input_tokens + output_tokens` over rows with usage | min–max of per-repeat medians | `b − a` |
| Latency | Median `latency_s` | min–max of per-repeat medians | `b − a` |

A value with no data (for example, no success at all) is shown as `—`, and its difference is
`—` too.

### DungeonComparison: one per level

| Field | Meaning |
| --- | --- |
| `pairs` | (seed, repeat) where both `a` and `b` have a completed row |
| `left_out` | Planned or present (seed, repeat) for which at least one side lacks a completed row, counted with the reason |
| `success` | `(higher, same, lower)`: seeds by `b`'s success rate over the kept repeats against `a`'s |
| `efficiency` | `(higher, same, lower)` over seeds where both have at least one success among the kept repeats, comparing median efficiencies |
| `p_success`, `p_efficiency` | Exact two-sided sign test on (higher, lower); `None` if every seed is a tie |

A seed with no kept pair is left out of `success` and counted under `left_out`.
