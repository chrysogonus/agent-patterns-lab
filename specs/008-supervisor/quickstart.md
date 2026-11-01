# Quickstart: A5 Supervisor

Validation steps for this feature. None of them makes a paid or local model call.

## 1. Checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

Expected: all pass. `tests/arch/test_supervisor.py` covers
[contracts/supervisor.md](contracts/supervisor.md).

## 2. Dry runs (free)

```bash
uv run apl run --arch supervisor --level all --seeds dev --limit 1
uv run apl run --problem survey --arch supervisor --level all --seeds dev --limit 1
```

Expected: the first prints the matrix (3 levels × 1 seed), the estimate and the limits, and ends
without calling a model. The second is refused: `supervisor does not play the survey problem (it
plays: dungeon)`.

## 3. In the viewer (by hand, local model only on request)

```bash
uv run apl serve
```

Open http://127.0.0.1:8765/ and check that `supervisor` is in the dungeon's architecture list and
not in the survey field's. Pressing Run plays an episode on the configured model; this is the
experimenter's choice, not part of the validation. In a played or replayed A5 episode, the side
panel shows a `supervisor` card with the handoff as JSON, then `navigator (task 1)` or
`inventory (task 1)` cards with tool calls, then the next `supervisor` card.

## 4. Joining the M4 comparison (only with `--execute`, the experimenter's choice)

With the M4 settings (`APL_MODEL=openai:gpt-6-luna`, the same token cap and output limit):

```bash
uv run apl run --arch supervisor --level all --seeds dev --limit 1 --execute
uv run apl report results/<new-run-id> results/20261031-221233-react+mapstate+mapstate_routes+hybrid+fanout+rounds+blackboard
```

Expected: the comparison section shows `supervisor` per level with reference `mapstate`. If any
compared setting differs, the report refuses, as it does today.
