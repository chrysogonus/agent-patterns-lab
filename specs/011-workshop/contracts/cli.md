# Contract: CLI Changes

Adds to specs/010 `contracts/cli.md`. The other problems' commands print exactly as before.

## `apl run`

- `--problem` choices come from the problem table, now with `workshop`.
- `--level` takes `W1,W2,W3` or `all` for the workshop.
- `--arch` must play the problem: `react`, `mapstate`, `plan_execute`, `reflexion`, `supervisor`,
  `hybrid`. Otherwise exit code 2 with `fanout does not play the workshop problem (it plays:
  dungeon, survey)`.

## `apl continue RUN_DIR`, `apl report RUN_DIR...`

The problem comes from `run.json`; workshop runs get the workshop table.

## `apl workshop show --level W2 --seed 1000 [--route reference] [--html OUT]` (new)

```text
Workshop W2, seed 1000: goal lantern; reference 15 steps (optimal); budget 45
stock: coal 1 (scarce), iron ore 3, sand 2, wood 2, resin 1, seeds 2
  lantern: frame, lens, oil
  frame: ! iron bar | * wood, resin
  iron bar: coal, iron ore
  lens: glass
  glass: sand, coal
  oil: seeds
```

One line per craftable, depth first from the goal; two recipes are separated by `|`, the reference's
choice marked `*`, a tempting first recipe `!`. With `--route reference`, a last line lists the
reference plan's calls: `reference: inspect lantern, inspect frame, gather wood, …, craft lantern 1`.
With `--html`, writes the viewer's SVG as a page. Test seeds are allowed.
