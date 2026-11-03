# Contract: Viewer

Research R14. Adds to specs/010 `contracts/viewer.md`.

## `GET /api/workshop?level=W2&seed=1000`

```json
{"problem": "workshop", "level": "W2", "seed": 1000, "goal": "lantern",
 "stock": {"coal": 1, ...}, "scarce": ["coal"], "recipes": {"frame": [["iron bar"], ["wood", "resin"]], ...},
 "reference_choice": {"frame": 2}, "budget": 45, "optimal_steps": 15,
 "reference_is_optimal": true, "svg": "<svg ...>", "solution": [<frame>, ...]}
```

Test seeds: 403. Unknown level or bad seed: 400. `solution` is the reference plan played as frames.

## `GET /api/options`

`problems.workshop` lists levels `W1–W3`, dev seeds, and the architectures that play it.

## Episodes

`POST /api/episodes` with `"problem": "workshop"`. `start` adds `"problem": "workshop", "goal",
"stock", "scarce"`; `step` and `restart` carry workshop frames. `episode.json` records the problem.
The episode-id pattern accepts levels `W1–W3`.

## The page

- Problem `workshop`: the tree as in the mock-up, one box per item (`[data-item]`) in layers by
  depth under the goal, edges to the inputs (second recipes dashed), raw materials as leaves
  labelled with their stock; groups the page fills per frame.
- Per frame: under "Agent's view", an uninspected craftable shows `?` and its edges are hidden;
  stock counts update and a scarce material at 0 turns red; held items show a count badge; the
  goal box fills when crafted. Under the truth view the reference plan's edges are outlined.
- Stats: `Workshop W2 seed 1000`, steps against budget and reference, inspected, wasted, attempt,
  and at the end `Crafted lantern`, `Stuck` or `Out of budget`.
