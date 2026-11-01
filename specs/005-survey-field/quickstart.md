# Quickstart: Checking the Survey Field

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

Expected: all pass, including the pinned dungeon outputs (research R16).

## 2. The dungeon is unchanged

```bash
uv run apl run --arch react --level all --seeds dev --limit 2
uv run apl dungeon show --level L3 --seed 1000 --route solution
```

Expected: the same output as before this feature; the `prompt` line still reads `ff9afb3b9f66`;
no `problem` line.

## 3. A field

```bash
uv run apl survey show --level S1 --seed 1000
uv run apl survey show --level S3 --seed 1000 --route reference
```

Expected: S1 is a 6×6 grid with 6 deposits and no walls; S3 shows walls and a reference walk that
enters every cell. Running the same command twice prints the same field.

## 4. A survey plan, and refusals

```bash
uv run apl run --problem survey --arch react,mapstate,fanout,rounds,blackboard \
  --level all --seeds dev --limit 1
uv run apl run --problem survey --arch hybrid --level S1 --seeds dev --limit 1
```

Expected: the first prints a plan with a `problem  survey` line, levels S1, S2, S3, 15 episodes,
and no model is called. The second exits with `hybrid does not play the survey problem (it plays:
dungeon)`.

## 5. Watching it (local model, by the experimenter)

```bash
uv run apl serve   # http://127.0.0.1:8765/
```

1. Pick "survey", S1, seed 1000: the field shows; with "Agent's view" on, every cell but A1 is
   under fog.
2. Run `react`: fog lifts cell by cell; "Seen so far" counts up; at the end "Submitted" shows the
   total with right or wrong.
3. Run `fanout` on S2: up to four trails in the scout colors; the side panel shows the
   orchestrator's plan, the scouts' turns and the collect answer.
4. Reopen both from "Saved episodes" and drag the slider.
5. Enter seed 2000: the viewer refuses it.

## 6. Interrupt and continue

With scripted architectures this is covered by the tests (US3). By hand: start a small survey run
with `--execute` on the local model, stop it with Ctrl+C, then:

```bash
uv run apl continue results/<run-id>
uv run apl continue results/<run-id> --execute
uv run apl report results/<run-id>
```

Expected: the plan names the episodes left; the report has the survey table.
