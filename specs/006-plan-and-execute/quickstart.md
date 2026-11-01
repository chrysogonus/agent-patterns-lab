# Quickstart: A3 Plan-and-Execute

Validation steps for this feature. None of them makes a paid or local model call.

## 1. Checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

Expected: all pass. `tests/arch/test_plan_execute.py` covers [contracts/plan-execute.md](contracts/plan-execute.md);
`tests/runner/test_meter.py` and `tests/runner/test_compare.py` cover
[contracts/runner-viewer.md](contracts/runner-viewer.md).

## 2. Dry runs on both problems (free)

```bash
uv run apl run --arch plan_execute --level all --seeds dev --limit 1
uv run apl run --problem survey --arch plan_execute --level all --seeds dev --limit 1
```

Expected: each prints the matrix (3 levels × 1 seed), the estimate and the limits, and ends
without calling a model.

## 3. A3 next to the others (free dry run)

```bash
uv run apl run --arch react,mapstate,plan_execute --level L3 --seeds dev --limit 1
```

Expected: the plan lists all three architectures; `plan_execute` is not marked "not written yet".

## 4. In the viewer (by hand, local model only on request)

```bash
uv run apl serve
```

Open http://127.0.0.1:8765/, pick each problem and check that `plan_execute` is in the
architecture list. Pressing Run plays an episode on the configured model; this is the
experimenter's choice, not part of the validation. In a played or replayed A3 episode, the side
panel shows a `planner` card with the plan as JSON, `executor (subgoal 1)` cards with tool calls,
then a `replanner` card with the finished subgoal's report.

## 5. Joining the M4 comparison (only with `--execute`, the experimenter's choice)

With the M4 settings (`APL_MODEL=openai:gpt-6-luna`, the same token cap and output limit):

```bash
uv run apl run --arch plan_execute --level all --seeds dev --limit 1 --execute
uv run apl report results/<new-run-id> results/20261031-221233-react+mapstate+mapstate_routes+hybrid+fanout+rounds+blackboard
```

Expected: the comparison section shows eight architectures per level, `plan_execute` with
reference `mapstate`. If any compared setting differs, the report refuses, as it does today.
