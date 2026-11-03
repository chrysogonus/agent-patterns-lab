# Contract: CLI Changes

Adds to specs/011 `contracts/cli.md`. The other problems' commands print exactly as before.

## `apl run`

- `--problem` choices come from the problem table, now with `warehouse`.
- `--level` takes `P1,P2,P3` or `all` for the warehouse.
- `--arch` must play the problem: `react`, `mapstate`, `fanout`, `rounds`, `blackboard`. Otherwise
  exit code 2 with `hybrid does not play the warehouse problem (it plays: dungeon, rune, signal,
  workshop)`.

## `apl continue RUN_DIR`, `apl report RUN_DIR...`

The problem comes from `run.json`; warehouse runs get the warehouse table.

## `apl warehouse show --level P2 --seed 1000 [--route reference] [--html OUT]` (new)

```text
Warehouse P2, seed 1000: 3 packages; reference 38 steps (not optimal); budget 114
   A B C D E F G H I
1  . . . . 2 . . . .
2  S # # # # # # # D
3  . . . . . . . . .
4  . # # # # # # # .
5  . 1 . . . . 3 . .
aisles: aisle 1 (row 1): 1 package; aisle 2 (row 3): none; aisle 3 (row 5): 2 packages
```

Digits are packages by number. With `--route reference`, a last line lists the reference's calls:
`reference: move north, move east, …, pick, …, drop`. With `--html`, writes the viewer's SVG as a
page. Test seeds are allowed. (The numbers above are illustrative.)
