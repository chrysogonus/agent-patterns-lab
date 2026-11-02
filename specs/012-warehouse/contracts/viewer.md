# Contract: Viewer

Research R14. Adds to specs/011 `contracts/viewer.md`.

## `GET /api/warehouse?level=P2&seed=1000`

```json
{"problem": "warehouse", "level": "P2", "seed": 1000, "columns": 9, "rows": 5,
 "budget": 114, "optimal_steps": 38, "reference_is_optimal": false, "packages": 3,
 "cell": 40, "margin": 12, "svg": "<svg …>", "solution": [<frame>, …]}
```

Test seeds are refused (403), unknown levels and bad seeds 400, as for the other problems. The
`solution` frames are the reference's.

## SVG

Shelves as wall rects; each open cell a `.cell` rect plus a `.room` overlay with id `room-<x>-<y>`
(the fog, as on the dungeon and survey field); the dock `S` and D marked; one `.package` element
per package with `data-package="<name>"`, drawn by the page at its frame position; the trail and
agent elements the page already uses.

## Frames

The survey field's frame keys (`step`, `action`, `ok`, `error`, `position`, `inventory`, `keys`,
`opened`, `end_reason`, `scouts` when more than one robot), plus:

| Key | Meaning |
| --- | --- |
| `seen` | corridor cells seen so far, `[[x, y], …]`; the page fogs every other open cell |
| `packages` | `[{"name", "cell": [x, y] \| null, "carrier": robot \| null, "delivered": bool}]` |
| `delivered` | packages delivered |
| `parallel_turns`, `idle_robot_turns` | so far |

In `scouts`, each robot has `position` and `carrying` (a package name or null).

## Episode events

The start event adds `"problem": "warehouse"`, `"packages"` (the count) and the floor's size. Step,
turn, thinking and end events are as for the other problems; the end row carries the warehouse row
fields.

## Page

- The problem select offers the warehouse; its levels, dev seeds and architectures follow.
- The floor is drawn from the SVG; robots in the scout colors; a waiting package on its cell, a
  carried one on its robot; delivered packages hidden.
- "Agent's view" fogs open cells not in `seen` and hides packages on them.
- Stats rows: `Warehouse P2 seed 1000`, steps against the reference and budget, `Delivered n / N`,
  `Parallel turns`, `Idle robot-turns`.
- The About card shows each architecture on the warehouse.
