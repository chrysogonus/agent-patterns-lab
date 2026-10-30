# Quickstart: Browser Viewer and A2 Map State

How to check that M3 works end to end. The interfaces are in [contracts/](contracts/), and the
types are in [data-model.md](data-model.md).

## Prerequisites

- `uv sync`.
- The vLLM server from research R9 running on `http://localhost:8001/v1` with
  `qwen3.5-9b`. Check it with `curl -s localhost:8001/v1/models`.
- In `.env`, `APL_MODEL=vllm:qwen3.5-9b`, or no `APL_MODEL` at all, since that is the new
  default.

## 1. Checks (free)

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

Expected: everything passes, including `tests/viewer/`, `tests/arch/test_dungeon_map.py` and
`tests/arch/test_mapstate.py`. The network stays blocked; one viewer test opens a loopback
connection only.

## 2. Start the viewer

```bash
uv run apl serve
```

Expected: `Viewer: http://127.0.0.1:8765/ (model vllm:qwen3.5-9b; Ctrl-C to stop)`. Open the URL
in a browser.

## 3. Browse dungeons (US1)

1. Pick L3 and seed 1000, then Generate. The map shows the rooms, doors, locks, keys, start, exit,
   the budget and the optimal steps.
2. Enter seed 4242 and Generate: a different dungeon. Seed 1000 again: identical to step 1.
3. Turn on "shortest solution": a dashed route from the start to the exit, including the key
   detours.
4. Enter 2003: refused, with a message about test seeds. Enter `-1` or `abc`: a message, and the
   map stays.
5. Press "random" a few times: never a seed from 2000 to 2019.

## 4. Watch A1 (US2)

1. Pick L1, seed 1000, architecture `react`, and press Run.
2. Expected:
   - "waiting for the model" appears with a timer;
   - each tool call moves the agent within a second;
   - each turn card shows the reasoning (collapsed), the tool calls and their results;
   - the stats count up.
3. Drag the step slider back: the map shows that step, and "follow live" turns off. Turn it back
   on: the map jumps to the newest step.
4. Turn on "agent's view": rooms not yet visited are dimmed.
5. Reload the page during the run: within 2 seconds everything so far is back, and it keeps
   following.
6. Press Run again during the run: refused, because one episode runs at a time.
7. Start A1 on L3 1001 and press Stop after a few steps. The current turn finishes, then the
   episode ends `stopped`.

## 5. Watch A2 (US3)

1. Pick `mapstate` on L2 1003 and Run.
2. Expected: from the second turn on, each turn card's "new input" shows A2's map in the format of
   contracts/mapstate.md. Its input never contains older turns. Compare with an A1 card, whose
   history keeps growing.

## 6. Replay (US4)

1. Open "saved episodes" and pick the A1 episode from step 4. It replays with the same steps,
   turns and stats. Play, Pause, speed and the slider work.
2. `ls results/viewer/` shows a folder per episode with `events.jsonl`, `outcome.json`,
   `conversation.json` and `episode.json`. This command animates the same route:

   ```bash
   uv run apl dungeon show --level L1 --seed 1000 \
     --route results/viewer/<id>/outcome.json --html replay.html
   ```

## 7. Paid-provider guard (FR-016)

```bash
APL_MODEL=openai:gpt-6-luna uv run apl serve
```

Expected: the page shows dungeons and replays, but Run is disabled with an explanation, and no
request reaches OpenAI. `apl serve --execute` would enable it; do not run that unless you mean
to pay.

## 8. Context overflow (R10)

Run A1 on an L3 dev seed until the end. If its history outgrows the 8,192-token context, the
episode ends `stopped` with "context window exceeded" in the result. It does not end as an error,
and the viewer keeps working.
