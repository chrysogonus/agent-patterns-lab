# Quickstart: Runner, Results Format, Report and A1 ReAct

How to check that M2 works end to end. The interfaces are in [contracts/](contracts/) and the
types in [data-model.md](data-model.md).

## Prerequisites

- `uv sync` (installs LangGraph, LangChain and the OpenAI integration).
- For the paid step only: `.env` in the repository root with `OPENAI_API_KEY=...`. Optional:

  ```bash
  APL_MODEL=openai:gpt-6-luna
  APL_PRICE_INPUT=0.10     # USD per 1M input tokens: confirm on OpenAI's pricing page
  APL_PRICE_OUTPUT=0.50    # USD per 1M output tokens
  ```

## 1. Checks (free)

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

Expected: everything passes. The tests block outgoing network connections, so no test can reach a
provider. `tests/arch/test_react.py` and the arch boundary guard are skipped until
`src/apl/arch/react.py` exists.

## 2. Dry run (free)

```bash
uv run apl run --arch react --level all --seeds dev --limit 2
```

Expected: the plan from contracts/cli.md: 6 episodes, model `openai:gpt-6-luna`, at most 228 model
calls and 3,600,000 tokens, and a cost line if prices are set. Nothing appears under `results/`.
Also try an unknown architecture (`--arch nope`) and `--only 5`: both exit with code 2 and a
message.

## 3. Write A1

Write `src/apl/arch/react.py` with `play(kit)` as described in contracts/kit.md. Then:

```bash
uv run pytest tests/arch tests/dungeon/test_boundary.py
```

Expected: the A1 tests pass (scripted model replays the shortest solution on L1–L3; a text answer
ends the episode as stopped) and the boundary guard now runs and passes.

## 4. Small paid run (costs money)

```bash
uv run apl run --arch react --level all --seeds dev --limit 2 --execute
```

Expected: six progress lines, a new folder `results/<run-id>/` with `run.json`
(`completed: true`), `episodes.jsonl` with 6 rows, 12 files under `episodes/`, and `report.md`
printed at the end, headed as a development result.

## 5. Look at an episode

```bash
uv run apl dungeon show --level L2 --seed 1001 \
  --route results/<run-id>/episodes/react-L2-1001-r1.outcome.json --html l2-react.html
```

Expected: the step table ends with the same step and end reason as the episode's row, and the HTML
animation plays the agent's actual route.

## 6. Report again, or combine runs

```bash
uv run apl report results/<run-id>
uv run apl report results/<run-a> results/<run-b>
```

Expected: the same table as at the end of the run. Combining runs with a different model, sampling
settings, token cap, prompt fingerprint or seed set exits with code 2 and names the differences.
