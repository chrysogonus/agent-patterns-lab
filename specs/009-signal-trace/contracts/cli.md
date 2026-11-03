# Contract: CLI Changes

Adds to specs/005 `contracts/cli.md`. Dungeon and survey commands print exactly as before.

## `apl run`

- `--problem` choices come from the problem table: `dungeon` (default), `survey`, `signal`.
- `--level` takes `T1,T2,T3` or `all` for the signal trace.
- `--arch` must play the problem: `react`, `mapstate`, `plan_execute`, `reflexion`, `hybrid`.
  Otherwise exit code 2 with `fanout does not play the signal problem (it plays: dungeon, survey)`.
- The dry-run plan shows `problem  signal`; the estimate uses the signal budgets (research R4).

## `apl continue RUN_DIR`, `apl report RUN_DIR...`

The problem comes from `run.json`, as since specs/005. Signal runs get the signal table
([results.md](results.md)); runs of different problems are refused together, as before.

## `apl signal show --level T2 --seed 1000 [--route reference] [--html OUT]` (new)

```text
Signal trace T2, seed 1000: 64 segments, 1 run; broken segment 41; reference 7 steps (optimal);
budget 64
  S → 1–64
```

T3 prints one line per run (`  18 → 19–30`). With `--route reference`, a last line lists the
reference strategy's probes for this break and the submission:
`reference: 32 wet, 48 dry, 40 wet, 44 dry, 42 dry, 41 dry → submit 41`. With `--html`, writes the
viewer's SVG as a page. Test seeds are allowed, as for the other `show` commands: no model is
called.
