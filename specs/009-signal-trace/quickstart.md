# Quickstart: Checking the Signal Trace

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

Expected: all pass, including the pinned dungeon and survey outputs.

## 2. The other problems are unchanged

```bash
uv run apl run --arch react --level all --seeds dev --limit 2
uv run apl run --problem survey --arch react --level all --seeds dev --limit 1
```

Expected: the same plans as before this feature, with the same `prompt` fingerprints.

## 3. A pipe

```bash
uv run apl signal show --level T1 --seed 1000
uv run apl signal show --level T2 --seed 1000 --route reference
uv run apl signal show --level T3 --seed 1000 --route reference
```

Expected: T1 is one run `S → 1–16` with budget 16 and a reference of 5 steps (optimal); T2 one run
of 64, budget 64, reference 7, and a reference line of 6 probes ending at the broken segment; T3
about seven runs, budget 64, a reference of at most 9 steps marked "a reference". The same command
prints the same pipe every time ([contracts/cli.md](contracts/cli.md)).

## 4. A signal plan, and refusals

```bash
uv run apl run --problem signal --arch react,mapstate,plan_execute,reflexion,hybrid \
  --level all --seeds dev --limit 1
uv run apl run --problem signal --arch fanout --level T1 --seeds dev --limit 1
```

Expected: the first prints a plan with `problem  signal`, levels T1, T2, T3, 15 episodes, and no
model is called. The second exits with code 2: `fanout does not play the signal problem (it plays:
dungeon, survey)`.

## 5. Watching it (local model, by the experimenter)

```bash
uv run apl serve   # http://127.0.0.1:8765/
```

1. Pick "signal", T2, seed 1000: the pipe shows with the broken segment ringed; with "Agent's view"
   on, the ring is hidden and every segment is shaded as a suspect.
2. "Reference probes" numbers the reference's six probes.
3. Run `hybrid`: each probe turns its box wet or dry and the shaded band shrinks; the side panel
   shows the option list and the chosen number; at the end "Submitted" shows right or wrong.
4. Run `react` on the same seed and compare probes and wasted probes in the stats.
5. Reopen both from "Saved episodes" and drag the slider. Enter seed 2000: refused.

## 6. Interrupt and continue

Covered by the tests with scripted architectures (US3). By hand: start a small signal run with
`--execute` on the local model, stop it with Ctrl+C, then:

```bash
uv run apl continue results/<run-id>
uv run apl continue results/<run-id> --execute
uv run apl report results/<run-id>
```

Expected: the plan names the episodes left; the report has the signal table
([contracts/results.md](contracts/results.md)).
