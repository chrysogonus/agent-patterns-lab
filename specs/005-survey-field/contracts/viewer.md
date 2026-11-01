# Contract: Viewer Changes

Adds to specs/003 `contracts/viewer-api.md` and specs/004 `contracts/viewer.md`. Dungeon requests
and responses stay as they are.

## API

### `GET /api/options`

Existing fields unchanged. New:

```json
"problems": {
  "dungeon": {"levels": ["L1", "L2", "L3"], "dev_seeds": [1000, ...], "test_seeds": [2000, 2019],
              "architectures": ["react", "mapstate", ...]},
  "survey":  {"levels": ["S1", "S2", "S3"], "dev_seeds": [1000, ...], "test_seeds": [2000, 2019],
              "architectures": ["react", "mapstate", "fanout", "rounds", "blackboard"]}
}
```

### `GET /api/survey?level=S2&seed=1000` (new; the counterpart of `/api/dungeon`)

```json
{"problem": "survey", "level": "S2", "seed": 1000, "size": 10, "budget": 300,
 "optimal_steps": 100, "reference_is_optimal": true, "true_total": 15, "start": [0, 0],
 "cell": 40, "margin": 24, "svg": "<svg ...>", "solution": [<frame>, ...]}
```

Keys follow `/api/dungeon` so the page draws both the same way: `optimal_steps` holds the reference
steps, `solution` the reference walk's frames, and the SVG has the dungeon's `#fail`, `.room`,
`#trail` and `#agent` elements. Deposits and walls are drawn in the SVG.

Test seeds: 403, as for the dungeon.

### `POST /api/episodes`

Body gains `"problem"` (default `"dungeon"`). An architecture that does not play the problem:
400 with the contracts/problems.md message.

### Events

The `start` event gains `"problem"`, and for the survey `"true_total"`. A survey `step` event's
`frame` has the dungeon frame's keys (`position`, `scouts` with `position`, empty `inventory`,
`keys`, `opened`, `end_reason`, …) plus:

```json
{"deposits_seen": 4, "submitted": null}
```

The `end` event's row carries the survey fields (`submitted_total`, `true_total`, `success`, …).
`/api/episodes` lists each episode with its `problem`.

## Page

- A problem picker before the level picker; levels, seeds and architectures follow it.
- Survey board: grid, deposits, walls; "Agent's view" puts fog on every cell not in `seen`;
  scouts' markers and trails in the existing scout colors.
- Tally panel: "True total", "Seen so far" (`deposits_seen`), and after the end "Submitted"
  with right or wrong.
- Step slider, side panel of model turns, Stop and saved episodes as for the dungeon; a saved
  episode reopens with its problem.
