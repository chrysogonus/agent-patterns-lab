# Contract: Survey Field Tools and Results

Research R4–R7. The architectures' only surface on the survey field.

## Base prompt

```text
You are surveying a field: a grid of square cells. Some cells hold an ore deposit. Your goal is
to find out how many deposits the field holds and submit that number.

You only see the cell you are in. Cells are named by column letter and row number: A1 is the
north-west corner, columns go east (A, B, C, ...), rows go south (1, 2, 3, ...). Every result
tells you the field's number of columns and rows. Some neighboring cells are separated by walls.

Use the tools look, move and submit. Every tool call is one step, and failed calls cost a step
too. You have a limited step budget, so avoid wasted calls. The episode ends when you submit a
total; you can submit only once.

Tool results are JSON objects with "ok", "error" and "data". When "ok" is false, "error" has a
"code" and a "message" that explain what went wrong.
```

## Tool schemas

Each description ends with " Every call costs one step, including failed calls.", as on the
dungeon.

| Tool | Parameters | Description |
| --- | --- | --- |
| `look` | none | Describe the current cell: its name, whether it holds a deposit, the directions you can move, and the field's size. |
| `move` | `direction`: `north`, `east`, `south`, `west` | Move to the neighboring cell in a direction and describe it. Errors: invalid_direction, wall. |
| `submit` | `total`: integer | Submit the number of deposits in the whole field. This ends the episode. Error: invalid_total. |

## Results

Envelope as on the dungeon: `{"ok": bool, "error": {"code", "message"} | null, "data": ... |
null}`.

| Data shape | From |
| --- | --- |
| `{"cell": "C4", "deposit": true, "exits": ["north", "east"], "columns": 10, "rows": 10}` | `look`, `move`, the start view |
| `{"submitted": 12}` | `submit` |

`exits` lists directions in the order north, east, south, west.

## Errors

| Code | When | Message |
| --- | --- | --- |
| `invalid_direction` | not one of the four | `'up' is not a direction; use north, east, south or west.` |
| `wall` | a wall or the field's edge | `There is a wall to the north.` |
| `invalid_total` | not an integer ≥ 0 or a string of digits | `'about 12' is not a whole number of deposits.` |
| `unknown_tool` | another tool name | `There is no tool named 'scan'. The tools are look, move and submit.` |
| `episode_over` | any call after the end; not counted | `The episode is over.` |

## What a result never shows

Any cell but the current one, the true total, the budget, the reference walk, other scouts'
positions. The boundary test checks this for every level and dev seed with random calls.
