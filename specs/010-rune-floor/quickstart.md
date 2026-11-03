# Quickstart: Checking the Rune Floor

Validation steps for [plan.md](plan.md). None of them makes a paid call. Step 5 uses the local
vLLM server and is run by the experimenter.

## 1. The four checks

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

Expected: all pass, including the pinned dungeon, survey and signal outputs.

## 2. The other problems are unchanged

```bash
uv run apl run --arch react --level all --seeds dev --limit 2
uv run apl run --problem survey --arch react --level all --seeds dev --limit 1
uv run apl run --problem signal --arch react --level all --seeds dev --limit 1
```

Expected: the same plans as before this feature, with the same `prompt` fingerprints.

## 3. A floor

```bash
uv run apl rune show --level R0 --seed 1000
uv run apl rune show --level R1 --seed 1000 --route reference
uv run apl rune show --level R3 --seed 1000 --route reference
```

Expected: R0 and R1 are 7×5, R3 is 9×7; each prints its rule in words (R0: fixed trap cells), a
reference marked optimal with a budget of 4× it, and with `--route reference` a path from S to G
that leaves the straight row. The same command prints the same floor every time
([contracts/cli.md](contracts/cli.md)).

## 4. A rune plan, and refusals

```bash
uv run apl run --problem rune --arch react,mapstate,plan_execute,reflexion,hybrid \
  --level all --seeds dev --limit 1
uv run apl run --problem rune --arch fanout --level R1 --seeds dev --limit 1
```

Expected: the first prints a plan with `problem  rune`, levels R0–R3, 20 episodes, and no model is
called. The second exits with code 2: `fanout does not play the rune problem (it plays: dungeon,
survey)`.

## 5. Watching it (local model, by the experimenter)

```bash
uv run apl serve   # http://127.0.0.1:8765/
```

1. Pick "rune", R1, seed 1000: the floor shows in its colors with S and G, the rule above the
   board and the reference path outlined; with "Agent's view" on, both are hidden.
2. "Reference path" steps the marker along the reference.
3. Run `reflexion`: each step extends the bold trail; a trap draws a cross, fades the walk and
   puts the marker back on S; the side panel shows the reflector's note; the stats count traps and
   repeated traps.
4. Run `react` on the same seed and compare traps, repeated traps and steps.
5. Reopen both from "Saved episodes" and drag the slider. Enter seed 2000: refused.

## 6. Interrupt and continue

Covered by the tests with scripted architectures (US3). By hand: start a small rune run with
`--execute` on the local model, stop it with Ctrl+C, then:

```bash
uv run apl continue results/<run-id>
uv run apl continue results/<run-id> --execute
uv run apl report results/<run-id>
```

Expected: the plan names the episodes left; the report has the rune table
([contracts/results.md](contracts/results.md)).
