# Contract: Rune Floor Tools and Results

Research R2, R3, R8–R10. The architectures' only surface on the rune floor.

## Base prompt

```text
You are crossing a rune floor: a grid of colored tiles. You start on the tile marked start and your
goal is to reach the tile marked goal. Cells are named by column letter and row number: A1 is the
north-west corner, columns go east (A, B, C, ...), rows go south (1, 2, 3, ...).

You are given the whole floor at the start: every tile's color, and where the start and the goal
are. A hidden rule decides which tiles are safe to step on. A step the rule forbids is a trap: it
sends you back to the start. The rule never changes during the episode.

Use the tools look and move. Every tool call is one step, and failed calls cost a step too. You
have a limited step budget, so avoid wasted calls. The episode ends when you reach the goal.

Tool results are JSON objects with "ok", "error" and "data". When "ok" is false, "error" has a
"code" and a "message" that explain what went wrong.
```

The cell naming is the survey field's; the last two paragraphs follow the other problems. No hint
of what the rule is about, and no advice on how to find it (Constitution I, III). The same prompt
on every level, R0 included, where the hidden rule is a fixed set of trap tiles.

## Tool schemas

Each description ends with " Every call costs one step, including failed calls.", as on the other
problems.

| Tool | Parameters | Description |
| --- | --- | --- |
| `look` | none | Describe the floor again: its size, every tile's color, the start, the goal and the cell you are on. |
| `move` | `direction`: `north` \| `east` \| `south` \| `west` | Step onto the neighboring tile in a direction. Errors: invalid_direction, edge. |

## Results

Envelope as on the other problems: `{"ok": bool, "error": {"code", "message"} | null, "data": ...
| null}`.

| Data shape | From |
| --- | --- |
| `{"columns": 7, "rows": 5, "start": "A3", "goal": "G3", "position": "A3", "floor": [["yellow", "blue", ...], ..., ["start", "red", ..., "goal"], ...]}` | the start view, `look` |
| `{"position": "C3", "color": "blue"}` | a safe step |
| `{"position": "A3", "color": "start"}` | a step back onto the start |
| `{"trap": "D3", "color": "yellow", "position": "A3"}` | a trap: where it sprang, and that you are on the start again |
| `{"trap": "D3", "color": "yellow", "position": "A3", "attempts_left": 2}` | a retrying architecture's trap with attempts left (research R10) |
| `{"position": "G3", "goal": true}` | the goal; the episode ends |

`floor` lists the rows from row 1 (north) down, each from column A (west) east.

## Errors

| Code | When | Message |
| --- | --- | --- |
| `invalid_direction` | not one of the four directions | `'up' is not a direction; use north, east, south or west.` |
| `edge` | off the floor | `There is no tile north of A1.` |
| `unknown_tool` | another tool name | `There is no tool named 'jump'. The tools are look and move.` |
| `episode_over` | any call after the end; not counted | `The episode is over.` |

A trap is not an error: `ok` is true and it is not an invalid action.

## What a result never shows

The rule, its kind or colors, the trap cells of R0 before they spring, the reference path, the
reference, the budget, and whether a trap repeated an earlier one. The boundary test checks shapes
with random calls on every level and dev seed, and that the start and `look` results are the same
for one floor's colors under any rule (research R15).
