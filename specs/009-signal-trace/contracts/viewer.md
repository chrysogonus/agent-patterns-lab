# Contract: Viewer

Research R13. Adds to specs/005 `contracts/viewer.md`.

## `GET /api/signal?level=T2&seed=1000`

```json
{"problem": "signal", "level": "T2", "seed": 1000, "segments": 64,
 "runs": [{"from": "S", "first": 1, "last": 64}], "broken": 41, "budget": 64,
 "optimal_steps": 7, "reference_is_optimal": true, "svg": "<svg ...>",
 "solution": [<frame>, ...]}
```

Test seeds: 403, as for the other problems. Unknown level or bad seed: 400. `solution` is the
reference strategy's run as frames (data-model.md).

## `GET /api/options`

`problems.signal` lists levels `T1–T3`, dev seeds, and the architectures that play it.

## Episodes

`POST /api/episodes` with `"problem": "signal"`. Events keep their shape; `start` adds
`"problem": "signal", "segments": N, "broken": k`; `step` and `restart` carry signal frames.
`episode.json` records the problem.

## The page

- Problem `signal`: drawn as in the problem mock-up. Each run snakes 8 segments a row
  (`.seg[data-seg]` boxes, small segment numbers) with a grey pipe line through the centres;
  runs are stacked, each starting at an inlet left of its first segment labelled "S" or
  "from 18", so no line crosses the board.
- Per frame: the water line runs from S along every segment known to be wet; a probe is a dot
  where water was found and a cross where it was not, the latest one larger; suspects are shaded,
  and the last one left turns red; the broken segment's dashed ring hides under "Agent's view";
  the reference toggle ("Reference probes") numbers the reference's probes.
- Stats: `Pipe T2 seed 1000`, steps against budget and reference, probes, suspects left, wasted,
  broken (unless "Agent's view"), and at the end `Submitted 41 — right` or `— wrong`.
