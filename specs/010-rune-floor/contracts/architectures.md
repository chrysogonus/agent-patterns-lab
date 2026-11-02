# Contract: Architectures on the Rune Floor

Research R12. Written by the agent at the experimenter's request; reviewed by the experimenter.
Behaviour on the dungeon, the survey field and the signal trace does not change.

## Registry (`src/apl/runner/registry.py`)

`SUPPORTS` gains `rune` for `react`, `mapstate`, `plan_execute`, `reflexion`, `hybrid`.

## WalkLog (`src/apl/arch/walk_log.py`)

- `WalkLog.from_start(start_json)`: size, start, goal, floor rows and position from the start view.
- `apply(name, args, result)`: a successful `move` either extends the current walk (a safe step),
  closes it as `trap at D3` (and opens a new, empty one), closes it as `back on start` (and opens a
  new one), or ends at the goal; `look` refreshes the floor and the position; failed calls change
  nothing.
- `render()`, for example:

  ```text
  Floor: 7 columns × 5 rows. Start A3, goal G3.
  Row 1: yellow blue red green yellow blue red
  Row 2: ...
  Row 3: start red blue yellow green red goal
  ...
  You are on C3.
  Walks so far:
  1. B3 red, C3 blue → trap at D3 (yellow)
  2. B3 red, B2 blue → back on start
  3. (current) B3 red, C3 blue
  ```

  A walk that ended before its first safe cell shows `none` (`4. none → trap at A2 (yellow)`);
  the current walk before its first cell shows `(current) none yet`.

  No conclusions about the rule, and no list of "dangerous" cells.
- `known`: distinct cells stepped on, traps included (A4's staleness counter).
- `record(cell)`: every `(walk step, "safe" | "trap")` for that cell, for A6 only. The walk step is
  the cell's place in its walk (1 for the first cell after the start).

Instructions for A2, A3 and A4 (`WALK_LOG_INSTRUCTIONS`), explaining the log only:

```text
You do not see the earlier conversation. Instead, every turn ends with your walk log. It is built
from your own tool results so far: the floor, the cell you are on, and every walk from the start,
with the tiles you stepped on in order and how the walk ended. Your previous reply and its tool
results come just before the log.
```

## A6 on the rune floor (`src/apl/arch/hybrid.py`, a `kit.problem == "rune"` branch)

Instructions (`RUNE_HYBRID_INSTRUCTIONS`):

```text
In this setup you do not call the tools yourself. Every turn you see your walk log and a numbered
list of moves. Code carries out the move you choose with one tool call. For each move, the option
says what happened on that tile before: at which step of a walk it was safe or a trap. Answer with
the number of one option and nothing else.
```

Options: the moves from the agent's cell that stay on the floor, in the order north, east, south,
west, each with the walk step the move would be and the tile's record, as
`move east to C3 (blue), walk step 3: safe at walk step 2 (twice); trap at walk step 4 (once)`, or
`move east to C3 (blue), walk step 1: never stepped on`; a move onto the start or the goal says so
(`move west to the start`, `move east to the goal`). Counts read `once`, `twice`, `3 times`; the
record lists each (outcome, walk step) pair in order of walk step, safe before trap. Answer parsing, re-asks (no step) and
`MAX_MISSES` as on the dungeon.

## A3 and A4

Both take the walk log and its instructions on `rune`. On `rune` only, A4's actor instructions
end with one more sentence, so the other problems' prompts stay as they were: `On this floor an
attempt also fails when a step springs a trap.` (`RUNE_ATTEMPT`). A4's failure reason after a trap with
attempts left is `trap`, detected from `attempts_left` in a trap result; `RESTARTED` gains it, so
the `restart` node skips `kit.restart()`. Its staleness counter (`_size`) uses `known`. A4's walk
log starts empty each attempt (as its map does elsewhere); the reflector sees the failed attempt's
log and writes a note.

A trap's attempt ending is known only from its result, so `_until_submit` cannot cut the reply in
advance. On `rune`, A4's `act` node therefore runs the reply's calls one at a time (each as a
one-call message through `kit.tool_node`, as A6 does) and stops after the first result that
carries `attempts_left`. The calls after it are not run and cost no step: the reply is kept with
only the calls that ran (as `_until_submit` keeps the calls up to a submission), so no call is left
unanswered, and the graph goes to the reflector before any further move. Otherwise a batch such as
`[east, east, east]` whose first move traps would run its other moves in the next attempt, from S,
before the reflection, and could spring and restart again while the graph counted one attempt. With
no attempt left, a trap carries no `attempts_left` and the batch runs on, as for the other
architectures.

Tests:

- a scripted A4 on R1 walks into a trap once, then follows the reference path: the graph's and the
  episode's attempt both go from 1 to 2, exactly one `restart` event is emitted, the reflector is
  called once, and the steps of both attempts add up in one budget;
- a scripted A4 reply with three moves whose first traps: only the first move runs (one step), the
  episode's position is S, the graph's and the episode's attempt are both 2, the kept reply has one
  call and one tool message, and the next model call is the reflector's.
