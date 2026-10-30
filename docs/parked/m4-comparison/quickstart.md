# Quickstart: A2 Map State and the First Comparison

How to check that M3 works end to end. The interfaces are in [contracts/](contracts/), and the
types are in [data-model.md](data-model.md).

## Prerequisites

- The M2 setup: `uv sync`, and a local Ollama with `qwen3:8b`. The settings are the M2 defaults,
  or `.env` as in specs/002-runner-react/quickstart.md.
- A clean, committed working tree before step 5 (research R10).

## 1. Checks (free)

```bash
uv run pytest
uv run ruff check . && uv run ruff format --check . && uv run mypy
```

Expected: everything passes, including `tests/arch/test_dungeon_map.py`,
`tests/arch/test_mapstate.py`, the continue tests and the comparison tests. The network stays
blocked.

## 2. Look at A2's map on a real dungeon (free)

```bash
uv run pytest tests/arch/test_mapstate.py -k render -s
```

Expected: the map text of a scripted L3 route is printed in the format of
contracts/mapstate.md. Every label in it belongs to a room the route entered.

## 3. Dry run of the comparison (free)

```bash
uv run apl run --arch react,mapstate --level all --seeds dev --repeats 3
```

Expected:

- `episodes 180`;
- both architectures listed, neither marked "not written yet";
- the `seeds` line ending in "development only, must not be reported";
- a `code` line with the commit and no "uncommitted changes" warning;
- nothing under `results/`.

## 4. Small paired run (free on the local model)

```bash
uv run apl run --arch react,mapstate --level all --seeds dev --limit 1 --execute
```

Expected:

- six progress lines alternating `react` and `mapstate`;
- `report.md` with the M2 tables plus "Comparison: mapstate vs react" and "Per dungeon"
  (contracts/report.md).

In `episodes/mapstate-L2-1000-r1.conversation.json`, every call's input has at most the
system message, the previous turn and the map. It does not grow with the history the way A1's
input does.

## 5. Interrupt and continue (free on the local model)

```bash
uv run apl run --arch react,mapstate --level L1 --seeds dev --limit 2 --execute   # Ctrl-C after 2 lines
uv run apl continue results/<run-id>              # dry run: done 2 of 4, left 2
uv run apl continue results/<run-id> --execute    # plays the 2 missing episodes
uv run apl continue results/<run-id>              # "already complete"
```

Expected: `episodes.jsonl` ends with 4 rows, one per key. `run.json` has `completed: true`.

To see the refusals:

- edit any tracked file and run `apl continue results/<run-id>` again. It refuses because of
  uncommitted changes, then `git checkout` the file;
- run it with `APL_TOKEN_CAP=1000`. It refuses because the setting `token_cap` differs.

## 6. The comparison run (about 8–9 h on the local model)

```bash
uv run apl run --arch react,mapstate --level all --seeds dev --repeats 3 --execute
```

If it stops with exit code 3, 4 or 130, fix the cause and continue:
`uv run apl continue results/<run-id> --execute`.

Expected:

- 180 rows;
- infrastructure errors, if any, listed separately and under 5% (SC-006);
- `report.md` with the comparison sections.

## 7. Write the conclusion

Draft `docs/findings/m3-map-state.md` from `results/<run-id>/report.md` (research R14). Then
check it:

```bash
uv run apl report results/<run-id>
```

Expected: each table and number quoted in the conclusion appears unchanged in this output
(SC-007).
