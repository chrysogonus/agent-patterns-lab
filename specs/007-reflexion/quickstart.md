# Quickstart: A4 Reflexion

No step makes a paid or local model call.

## 1. Checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

Expected: all pass, including the pinned dungeon outputs from specs/005 unchanged.

## 2. Dry runs (free)

```bash
uv run apl run --arch reflexion --level all --seeds dev --limit 1
uv run apl run --problem survey --arch reflexion --level all --seeds dev --limit 1
```

Expected: `reflexion` is listed (not "not written yet"); no model is called.

## 3. Replay a saved A4 dungeon episode (after one is played in the viewer)

```bash
uv run apl dungeon show --level L1 --seed 1000 --route results/viewer/<episode-id>/outcome.json
```

Expected: the replay rebuilds every restart and ends with the logged end reason.

## 4. Viewer (by hand; playing an episode is the experimenter's choice)

`uv run apl serve`, open http://127.0.0.1:8765/, pick `reflexion` on either problem. In a played or
replayed episode: actor cards labelled `actor (attempt n)`, a `reflector` card with its note after
a failed attempt, an "Attempt 2 starts" card, the marker back at the start, the first attempt's
trail dashed and faded, and "Attempt 2 / 3" in the stats.

## 5. Joining the M4 comparison (only with `--execute`)

```bash
uv run apl run --arch reflexion --level all --seeds dev --limit 1 --execute
uv run apl report results/<new-run-id> results/20261031-221233-react+mapstate+mapstate_routes+hybrid+fanout+rounds+blackboard
```

Expected: A4 per level with reference `mapstate`, and an "Attempts" section.
