# Contract: CLI Changes

Adds to specs/009 `contracts/cli.md`. Dungeon, survey and signal commands print exactly as before.

## `apl run`

- `--problem` choices come from the problem table: `dungeon` (default), `survey`, `signal`, `rune`.
- `--level` takes `R0,R1,R2,R3` or `all` for the rune floor.
- `--arch` must play the problem: `react`, `mapstate`, `plan_execute`, `reflexion`, `hybrid`.
  Otherwise exit code 2 with `fanout does not play the rune problem (it plays: dungeon, survey)`.
- The dry-run plan shows `problem  rune`; the estimate uses the rune budgets (research R6).

## `apl continue RUN_DIR`, `apl report RUN_DIR...`

The problem comes from `run.json`. Rune runs get the rune table ([results.md](results.md)); runs of
different problems are refused together, as before.

## `apl rune show --level R1 --seed 1000 [--route reference] [--html OUT]` (new)

```text
Rune floor R1, seed 1000: 7×5; rule: colors cycle red, blue, green; reference 10 steps (optimal);
budget 40
    A B C D E F G
  1 y b r g y b r
  2 g y g r b y g
  3 S r b y g r *
  4 b g r g y b y
  5 r y b r g g b
legend: r red, b blue, g green, y yellow, S start, * goal
```

On R0 a last line before the route lists the trap cells: `traps: B2, C4, …`.

With `--route reference`, a last line lists the reference path:
`reference: A3 → B3 → B2 → C2 → … → G3 (10 moves)`. With `--html`, writes the viewer's SVG as a
page. Test seeds are allowed, as for the other `show` commands: no model is called.
