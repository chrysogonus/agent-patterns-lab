# Data Model: The Signal Trace

Runner-side types live in `src/apl/signal_trace/`; architectures see only `tools` and `results`
(Constitution II). Names follow the survey package (specs/005 data-model.md).

## SignalLevel (`model.py`)

| Field | Type | Meaning |
| --- | --- | --- |
| `name` | str | `T1`, `T2`, `T3` |
| `segments` | int | 16, 64, 64 |
| `ends` | int | pipe ends: 1, 1, 4 |
| `min_run` | int | shortest run allowed: 16, 64, 4 (a single run is the whole pipe) |

`LEVELS: dict[str, SignalLevel]`. Each segment feeds at most two (R4).

## Run (`model.py`)

A straight piece of pipe: `feeder` (0 for S, else a segment), `first`, `last`. `feeder` feeds
`first`, each segment the next, up to `last`. Runs end at a junction (a segment that feeds two) or
at a pipe end. Preorder numbering makes each run a contiguous range (R3).

## Pipe (`model.py`)

| Field | Type | Meaning |
| --- | --- | --- |
| `level` | SignalLevel \| None | None for a hand-built pipe |
| `seed` | int \| None | |
| `feeder` | tuple[int, ...] | `feeder[k − 1]` is segment k's feeder, 0 for S; always `< k` |
| `runs` | tuple[Run, ...] | in order of `first` |
| `broken` | int | the broken segment, 1..N |
| `reference_probes` | int | worst case of the strategy (R5) |
| `reference_is_optimal` | bool | true when the pipe is one run |

Derived: `segments` (N), `reference_steps = reference_probes + 1`, `budget = max(3 ×
reference_steps, N)` (N = N−1 probes + 1 submission), `upstream(k)` (k and its feeders, up to S),
`wet(k) = broken not in upstream(k)`.

Validation (tests): `1 ≤ broken ≤ N`; every feeder lower than its segment; at most two segments
per feeder; the number of pipe ends equals `level.ends`; every run at least `level.min_run` long;
T3 `reference_probes ≤ 8`.

## Suspects (`strategy.py`)

`suspects(pipe_layout, answers) -> frozenset[int]`: every segment consistent with all `(k, wet)`
answers (R6). `informative(suspects, k)`: some suspect is in `upstream(k)` and some is not.
`choose(suspects)`: the informative k minimising `max(|dry part|, |wet part|)`, lowest k on a tie.
`worst_case(layout)`: the most probes `choose` needs over every possible broken segment.
`reference_run(pipe)`: the strategy's probes and answers for this pipe's break, then the submission
(for `show --route` and the viewer's reference frames).

## Action (`model.py`)

`tool` (`look`, `probe`, `submit`, `unknown`) and `args` (strings, as shown); as the survey's.

## Results (`results.py`, agent-facing)

| Type | `to_dict()` |
| --- | --- |
| `ErrorCode` | `no_such_segment`, `unknown_tool`, `episode_over` |
| `EndReason` | `submitted`, `budget`, `stopped` |
| `LayoutView` | `{"segments": N, "runs": [{"from": "S" \| k, "first": a, "last": b}, ...]}` |
| `ProbeView` | `{"segment": k, "water": bool}` |
| `Submitted` | `{"submitted": k}`, or with `"correct": false, "attempts_left": n` (R8) |
| `ToolError` | `{"code": ..., "message": ...}` |
| `ToolResult` | `{"ok": bool, "error": ToolError \| null, "data": LayoutView \| ProbeView \| Submitted \| null}` |

## LogEntry and Episode (`env.py`)

`LogEntry`: `index`, `step` (None for uncounted `episode_over` calls), `action`, `result`,
`attempt` (shown when > 1), `wasted` (shown when true, for successful probes only).

`Episode` state: `pipe`, `steps`, `invalid_actions`, `answers` (this attempt's `(k, wet)`),
`probes`, `wasted_probes`, `submitted`, `end_reason`, `log`, `attempt`, `max_attempts` (1, or
`MAX_ATTEMPTS = 3` for a retrying architecture), `on_step`, `on_restart`. Methods: `describe()`
(the free layout), `look()`, `probe(raw)`, `submit(raw)`, `unknown(name)`, `restart()`, `stop()`,
`outcome()`, `suspects()`.

Transitions:

```text
running --probe/look/invalid--> running            (step +1; end at budget)
running --submit right--------> ended(submitted)
running --submit wrong, A4 with attempts left--> restart: answers cleared, attempt +1, still running
running --submit wrong, otherwise--> ended(submitted)
running --steps == budget------> ended(budget)     (a submission on the last step counts first)
running --stop----------------> ended(stopped)
ended   --any call------------> episode_over error, no step
```

## Outcome (`env.py`)

`level`, `seed`, `end_reason`, `steps`, `optimal_steps` (the reference steps), `budget`,
`invalid_actions`, `log`, `submitted_segment`, `broken_segment`, `segments`, `probes`,
`wasted_probes`, `reference_is_optimal`, `attempts`; `success` is a submission equal to the broken
segment; `budget_hit`. `to_dict()` in the survey outcome's style.

## Result row additions (`apl/runner/results.py`)

Nullable, None on dungeon and survey rows: `submitted_segment`, `broken_segment`, `segments`,
`probes`, `wasted_probes`. `reference_is_optimal` is shared with the survey field. An
infrastructure error on the signal trace still records `broken_segment` and `segments`.

## Frame (`frames.py`, viewer)

```json
{"step": 3, "action": {"tool": "probe", "args": ["32"]}, "ok": true, "error": null,
 "end_reason": null, "answers": [[32, true], [48, false]], "suspects": [33, 34, "..."],
 "probes": 2, "wasted": 0, "submitted": null, "attempt": 2}
```

`attempt` only when > 1. `answers` and `suspects` are the current attempt's.

## ProbeLog (`src/apl/arch/probe_log.py`, architecture side)

Built from `Kit.start` (a layout result) and updated by `apply(name, args, result)` from the result
JSON only. Holds `segments`, `runs`, `answers` (in order). `render()` shows the runs and the answers
(`wet: 3, 10 · dry: 20`) and draws no conclusion; `known` is the number of distinct segments
probed. `suspects()` (used by A6 only) applies R6 to the runs and answers.
