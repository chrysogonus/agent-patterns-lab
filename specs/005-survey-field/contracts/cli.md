# Contract: CLI Changes

Adds to specs/002, 003 and 004's `contracts/cli.md`. Without `--problem`, every command behaves
and prints exactly as before (SC-001).

## `apl run`

- `--problem NAME`: `dungeon` (default) or `survey`.
- `--level` takes that problem's levels: `S1,S2,S3` or `all` for the survey.
- `--arch` names must support the problem (contracts/problems.md); otherwise exit code 2 with
  `hybrid does not play the survey problem (it plays: dungeon)`.
- The dry-run plan gains a `problem` line after `architectures` only for problems other than the
  dungeon:

  ```text
  Plan (dry run, nothing is sent or written)
    architectures  react, mapstate, fanout, rounds, blackboard
    problem        survey
    levels         S1, S2, S3
    seeds          dev: 1000 (1 of 10)  -> development only, must not be reported
    ...
  ```

- The model-call estimate uses the survey budgets (3× reference walk).

## `apl continue RUN_DIR`

Reads the problem from `run.json` (missing: `dungeon`). No new options.

## `apl report RUN_DIR...`

Refuses runs of different problems: `these runs are on different problems (dungeon, survey);
report them separately`. Survey runs get the survey table ([results.md](results.md)).

## `apl survey show --level S2 --seed 1000 [--route reference] [--html OUT]` (new)

The counterpart of `apl dungeon show`: prints the field (deposits, walls, start) as text, with
`--route reference` the reference walk, and with `--html` writes the board as a picture. Test
seeds are allowed here, as for `apl dungeon show`, since showing a world calls no model.
