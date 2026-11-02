# Quickstart: Checking the Workshop

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

Expected: all pass, including the pinned dungeon, survey, signal and rune outputs.

## 2. The other problems are unchanged

```bash
uv run apl run --arch react --level all --seeds dev --limit 2
uv run apl run --problem rune --arch react --level all --seeds dev --limit 1
```

Expected: the same plans as before this feature, with the same `prompt` fingerprints.

## 3. A workshop

```bash
uv run apl workshop show --level W1 --seed 1000
uv run apl workshop show --level W2 --seed 1000 --route reference
uv run apl workshop show --level W3 --seed 1000
```

Expected: W1 has no `!` recipe; W2 one and W3 two, each with a scarce material of stock 1; the
budget is 3× the reference; the same command prints the same workshop every time.

## 4. A workshop plan, and refusals

```bash
uv run apl run --problem workshop --arch react,mapstate,plan_execute,reflexion,supervisor,hybrid \
  --level all --seeds dev --limit 1
uv run apl run --problem workshop --arch fanout --level W1 --seeds dev --limit 1
```

Expected: the first prints a plan with `problem  workshop`, levels W1–W3, 18 episodes, and no model
is called. The second exits with code 2.

## 5. Watching it (local model, by the experimenter)

```bash
uv run apl serve   # http://127.0.0.1:8765/
```

1. Pick "workshop", W2, seed 1000: the tree with the reference edges outlined; with "Agent's view"
   on, only the goal and the stock show, the rest is `?`.
2. Run `react` and `plan_execute`: watch inspections open the tree, gathers move stock to the
   inventory, and whether the scarce material turns red before it is needed.
3. Run `supervisor`: the side panel shows the researcher's and the crafter's turns.
4. Reopen from "Saved episodes" and drag the slider. Enter seed 2000: refused.

## 6. Interrupt and continue

Covered by the tests with scripted architectures (US3).
