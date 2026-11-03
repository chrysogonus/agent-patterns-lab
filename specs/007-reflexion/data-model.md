# Data Model: A4 Reflexion

All additions are optional on disk: a value is written only when it differs from "one attempt",
so logs, outcomes, frames and events of every other architecture stay byte-identical (R4).

## Episode (both problems)

| Field | Type | Meaning |
| --- | --- | --- |
| `attempt` | `int` | The current attempt, from 1 |
| `max_attempts` | `int` | 1, or `MAX_ATTEMPTS` (3) for a retrying architecture; set before the kit is built |
| `on_restart` | `Callable[[], None] \| None` | An observer called after each restart (the viewer) |
| `seen_ever` | `set[Cell]` | Survey only: every cell any attempt entered |

`restart() -> bool`: refused when `end_reason is not None` or `attempt >= max_attempts`;
otherwise resets the world (R1), `attempt += 1`, calls `on_restart`, returns True.

### Restart, field by field

| Problem | Reset to the start | Kept |
| --- | --- | --- |
| Dungeon | `scouts = [Scout(start, [])]`, `opened = set()` (keys back in rooms, derived) | `steps`, `invalid_actions`, `log`, `end_reason` (None) |
| Survey | `scouts = [start]`, `seen = {start}`, `submitted = None` | `steps`, `invalid_actions`, `log`, `seen_ever` |

## LogEntry (both problems)

`attempt: int = 1`; `to_dict` adds `"attempt": n` only when n > 1.

## Outcome (both problems)

`attempts: int = 1` (the attempt the episode ended in); `to_dict` adds `"attempts": n` only when
n > 1. Survey `cells_seen` = `len(seen_ever)`, which equals `len(seen)` when there was one attempt.

## Survey submit result

| Case | Data | Episode |
| --- | --- | --- |
| `max_attempts == 1`, any total | `{"submitted": N}` | ends (`submitted`) |
| right total | `{"submitted": N}` | ends (`submitted`) |
| wrong total, last attempt | `{"submitted": N}` | ends (`submitted`) |
| wrong total, attempts left | `{"submitted": N, "correct": false, "attempts_left": k}` | goes on; world restarted, `attempt += 1` |

## Frames

Dungeon `Frame.attempt: int = 1` and survey snapshots: `"attempt": n` in `to_dict` only when n > 1.

## Kit

| Field | Type | Default | Meaning |
| --- | --- | --- | --- |
| `restart` | `Callable[[], bool]` | always False | Restart the world for the next attempt (costs no step) |
| `max_attempts` | `int` | 1 | The episode's attempt cap |

## EpisodeRow

`attempts: int | None = None`: the outcome's attempts for a retrying architecture; None
otherwise, for older rows and for infrastructure errors. Reports read None as 1.

## A4 graph state `ReflexionState` (in `src/apl/arch/reflexion.py`)

No reducers.

| Field | Type | Meaning |
| --- | --- | --- |
| `messages` | `list[BaseMessage]` | The actor's latest turn only (A2's rule) |
| `map` | `DungeonMap \| FieldMap` | This attempt's map, from its tool results only |
| `notes` | `list[str]` | Notes from earlier attempts, in order |
| `attempt` | `int` | The current attempt, from 1 |
| `stale` | `int` | Actor turns in a row whose results added no room or cell to the map |
| `started` | `bool` | Whether this attempt's first actor turn has happened (start result shown once) |
| `failure` | `str` | Why the attempt ended: `gave up`, `nothing new for 12 turns`, `wrong total` |
| `last_reply` | `str` | The actor's last reply text in the attempt |

### Transitions

| From | Condition | To |
| --- | --- | --- |
| `START` | — | `actor` |
| `actor` | reply has tool calls | `act` |
| `actor` | no tool call | `failure = "gave up"` → `reflector` if `attempt < max_attempts`, else `END` |
| `act` | a submit result has `"correct": false` | `failure = "wrong total"` → `reflector` (attempts are left, or the episode would have ended) |
| `act` | `stale >= MAX_STALE` (12) | `failure = "nothing new for 12 turns"` → `reflector` if `attempt < max_attempts`, else `END` |
| `act` | otherwise | `actor` |
| `reflector` | — | `restart` (note appended if non-empty) |
| `restart` | failure was `wrong total`, or `kit.restart()` is True | `actor`, with map from `kit.start`, `messages = []`, `stale = 0`, `started = False`, `attempt += 1` |
| `restart` | `kit.restart()` is False | `END` |

Reaching the exit, a right total, a last wrong total or the budget raise `EpisodeEnded` inside
`act`; the graph stops there.
