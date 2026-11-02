# Contract: Architectures on the Signal Trace

Research R11. Written by the agent at the experimenter's request; reviewed by the experimenter.
Behaviour on the dungeon and the survey field does not change.

## Registry (`src/apl/runner/registry.py`)

`SUPPORTS` gains `signal` for `react`, `mapstate`, `plan_execute`, `reflexion`, `hybrid`.

## ProbeLog (`src/apl/arch/probe_log.py`)

- `ProbeLog.from_start(start_json)`: the runs and the number of segments from the start view.
- `apply(name, args, result)`: a successful `probe` adds `(segment, water)`; a `look` replaces the
  runs; anything else changes nothing.
- `render()`, for example:

  ```text
  Pipe: 64 segments.
  Runs: S → 1–18; 18 → 19–30; 30 → 31–37; 30 → 38–45; 18 → 46–52; ...
  Probes so far (3, in order): 32 dry, 18 wet, 25 dry.
  ```

  No suspects, no conclusions.
- `known`: distinct segments probed (A4's staleness counter).
- `suspects()`: research R6 over the runs and answers; for A6 only.

Instructions for A2, A3 and A4 (`PROBE_LOG_INSTRUCTIONS`), explaining the log only:

```text
You do not see the earlier conversation. Instead, every turn ends with your probe log. It is built
from your own tool results so far: the pipe's runs and every probe answer, in the order you got
them. Your previous reply and its tool results come just before the log.
```

## A6 on the signal trace (`src/apl/arch/hybrid.py`, a `kit.problem == "signal"` branch)

Instructions (`SIGNAL_HYBRID_INSTRUCTIONS`):

```text
In this setup you do not call the tools yourself. Every turn you see your probe log and a numbered
list of options. Code carries out the option you choose with one tool call. For each probe, the
option says how many segments could still be the broken one after each answer. Answer with the
number of one option and nothing else.
```

Options: the 8 informative probes with the smallest `max(left if wet, left if dry)`, ties lowest
segment first, as `probe 32: leaves 32 if wet, 32 if dry`; then `submit k` for each suspect when at
most 4 remain. One suspect left: the only option is `submit k`. Answer parsing, re-asks (no step)
and `MAX_MISSES` as on the dungeon.

## A3 and A4

Both take the probe log and its instructions on `signal`. A4's failure reason after a wrong
submission is `wrong segment` (the survey's is `wrong total`); its staleness counter (`_size`) uses
`known`.

A wrong submission has already restarted the environment (data-model.md transitions), so A4's
`restart` node MUST skip `kit.restart()` for both automatic-restart reasons, `wrong total` and
`wrong segment` (today it checks only `WRONG_TOTAL`, `reflexion.py` `restart`); otherwise one
wrong segment would use two attempts. Test: a scripted A4 on T1 submits a wrong segment once, then
the right one: the graph's and the episode's attempt both go from 1 to 2, exactly one `restart`
event is emitted, and the steps of both attempts add up in one budget.
