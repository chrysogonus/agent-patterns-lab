# Quickstart: Checking the Harder Levels (specs/013)

Nothing here makes a paid call: the dry runs plan only, and the viewer check uses the scripted
model or a replay.

## 1. The checks

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

All four pass. The pinned tests show T1–T3 and W1–W3 unchanged (research R4, R5).

## 2. Show the new levels

```bash
uv run apl signal show --level T4 --seed 1000 --route reference
uv run apl workshop show --level W4 --seed 1000 --route reference
uv run apl signal show --level T4 --seed 1000 --html /tmp/t4.html
```

Expected: T4 lists 15 runs over 256 segments, a reference of 11–12 probes plus the submission and
a budget of 256; W4 shows 12 craftables over 5 levels, 3 scarce materials with stock 1 and a
reference plan of 36–41 steps. The T4 picture is about square (24 segments a row).

## 3. Plan runs

```bash
uv run apl run --problem signal --arch react --level all --seeds dev --limit 1
uv run apl run --problem workshop --arch react --level all --seeds dev --limit 1
uv run apl run --problem signal --arch react --level T4 --seeds dev --limit 1
```

Expected: the first two list 4 levels each, the new one last; the third plans T4 only.

## 4. Earlier runs are unchanged

```bash
uv run apl continue results/20261103-112849-react+mapstate+hybrid+plan_execute+reflexion+retry
```

Expected: nothing left to play (the run is complete) and no T4 episode is added. (If that
directory is not present, any saved three-level signal or workshop run will do.)

## 5. In the viewer

```bash
uv run apl serve
```

Open http://127.0.0.1:8765/, pick the signal trace: the level list ends with T4; T4 seed 1000
draws readably without a long scroll. Pick the workshop: W4 seed 1000 draws without overlapping
boxes.

Live play and replay on the new levels are checked by the viewer tests with a scripted model
(`tests/viewer/test_signal.py`, `tests/viewer/test_workshop.py`), as for the existing levels.
Pressing Run in the browser calls a real model (the local vLLM server or a paid provider), so it is
done only when the experimenter asks for it.
