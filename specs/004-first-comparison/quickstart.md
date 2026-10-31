# Quickstart: validating M4

Run from the repository root. Steps 1–5 are free; step 6 spends money.

## 1. The four checks

```bash
uv sync
uv run pytest && uv run ruff check . && uv run ruff format --check . && uv run mypy
```

Expected: all pass. The tests cover the several-scout rules ([contracts/scouts.md](contracts/scouts.md)),
the orchestrators with scripted answers ([contracts/orchestrators.md](contracts/orchestrators.md)),
continuing, and the comparison section ([contracts/results.md](contracts/results.md)).

## 2. Single-agent architectures are unchanged (SC-001)

The test suite replays every dev dungeon with the scripted models of M2 and M3 and compares the
outcomes with those written before this feature. A saved M3 viewer episode still replays:

```bash
uv run apl dungeon show --level L1 --seed 1000 \
  --route results/viewer/<an M3 episode>/outcome.json
```

Expected: the same map and route as before M4.

## 3. Watch the orchestrators (local model, free)

```bash
uv run apl serve
```

In the browser (http://127.0.0.1:8765/), pick L2, seed 1000, `blackboard`, model `vllm:qwen3.5-9b`,
and press Run. Expected ([contracts/viewer.md](contracts/viewer.md)):

- four markers in four colors, each walking room by room;
- turn cards headed `· scout 1` to `· scout 3` (and `· scout 0`);
- with "Agent's view" on, every room any scout entered is clear.

Repeat with `fanout` and `rounds`: their first card is `· orchestrator`. After the episode, pick it
under "saved" and move the slider: every scout is where it was at that step.

## 4. Plan the M4 run (free)

Commit everything first, so the run can be continued. Then:

```bash
APL_MODEL=openai:gpt-6-luna uv run apl run \
  --arch react,mapstate,mapstate_routes,hybrid,fanout,rounds,blackboard \
  --level all --seeds dev --limit 1
```

Expected ([contracts/cli.md](contracts/cli.md)): 21 episodes, the seven architectures, seed 1000,
"development only", a `code` line without "uncommitted changes", and a cost upper bound from the
token cap. If that bound is too high, set a lower `APL_TOKEN_CAP` in `.env` for the whole run.

## 5. Try continuing on a scripted run (free)

The test suite does this (SC-004). By hand, with the local model: start the step-4 command with
`APL_MODEL=vllm:qwen3.5-9b` and `--execute`, press Ctrl-C after a few episodes, then

```bash
uv run apl continue results/<run-id>
uv run apl continue results/<run-id> --execute
```

Expected: the dry run shows how many are done and left; the second command plays only the rest and
writes `report.md`. Editing any tracked file and running `apl continue` again is refused with
"the working tree has uncommitted changes".

## 6. The M4 run (paid)

```bash
APL_MODEL=openai:gpt-6-luna uv run apl run \
  --arch react,mapstate,mapstate_routes,hybrid,fanout,rounds,blackboard \
  --level all --seeds dev --limit 1 --execute
```

If it stops (exit code 3, 4 or 130), run the `continue with:` line it prints. Expected: 21 rows and
a `report.md` with the "Comparison" section: one table per level, seven rows each.

## 7. The conclusion (SC-007)

Write `docs/findings/m4-first-comparison.md` from `results/<run-id>/report.md` (research R15). Check
it by running `uv run apl report results/<run-id>` again and comparing every number the conclusion
quotes.
