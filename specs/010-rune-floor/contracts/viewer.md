# Contract: Viewer

Research R14. Adds to specs/009 `contracts/viewer.md`.

## `GET /api/rune?level=R1&seed=1000`

```json
{"problem": "rune", "level": "R1", "seed": 1000, "columns": 7, "rows": 5,
 "start": "A3", "goal": "G3", "floor": [["yellow", ...], ...],
 "rule": "colors cycle: red, blue, green", "budget": 40, "optimal_steps": 10,
 "reference_is_optimal": true, "svg": "<svg ...>", "solution": [<frame>, ...]}
```

Test seeds: 403, as for the other problems. Unknown level or bad seed: 400. `solution` is the
reference path walked from S, as frames (data-model.md). The rule text is for the experimenter's
truth view; the page hides it under "Agent's view".

## `GET /api/options`

`problems.rune` lists levels `R0–R3`, dev seeds, and the architectures that play it.

## Episodes

`POST /api/episodes` with `"problem": "rune"`. Events keep their shape; `start` adds
`"problem": "rune", "columns", "rows", "start", "goal"`; `step` and `restart` carry rune frames.
`episode.json` records the problem. The episode-id pattern accepts levels `R0–R3`.

## The page

- Problem `rune`: the floor's cells in soft fills of their colors (`.tile[data-cell]`), `S` and `G`
  labelled, and groups the page fills per frame: `#trails`, `#traps`, `#agent`.
- Per frame: the current walk as a bold line from S, earlier walks as faded lines, a cross on every
  trap (the latest larger), the agent's marker. Under the truth view the rule is written above the
  board (with R0's trap cells marked faintly); "Agent's view" hides both. The reference toggle
  ("Reference path") outlines the reference path while the truth is shown.
- Stats: `Floor R1 seed 1000`, steps against budget and reference, walk and attempt, traps and
  repeated traps, the rule (unless "Agent's view"), and at the end `Reached G` or `Out of budget`.
