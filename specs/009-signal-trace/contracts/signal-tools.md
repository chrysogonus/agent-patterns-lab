# Contract: Signal Trace Tools and Results

Research R2, R3, R6–R8. The architectures' only surface on the signal trace.

## Base prompt

```text
You are tracing a fault in a pipe. Water flows from a source S through numbered pipe segments.
Exactly one segment is broken: water does not get past it, so the broken segment and every
segment downstream of it are dry, and every other segment is wet. Your goal is to find the broken
segment and submit its number.

You are given the pipe's layout at the start, as runs. A run {"from": F, "first": a, "last": b}
means that F feeds segment a, a feeds a+1, and so on up to b. F is "S" or a segment number. Where
a segment feeds two runs, the pipe branches. Water reaches a segment only if it gets past every
segment between S and that segment.

Use the tools look, probe and submit. Every tool call is one step, and failed calls cost a step
too. You have a limited step budget, so avoid wasted calls. The episode ends when you submit a
segment; you can submit only once.

Tool results are JSON objects with "ok", "error" and "data". When "ok" is false, "error" has a
"code" and a "message" that explain what went wrong.
```

The last two paragraphs are the survey field's, with "segment" for "total". No advice on how to
choose a probe (Constitution I, III: strategy belongs to the graph).

## Tool schemas

Each description ends with " Every call costs one step, including failed calls.", as on the other
problems.

| Tool | Parameters | Description |
| --- | --- | --- |
| `look` | none | Describe the pipe's layout again: the number of segments and the runs. |
| `probe` | `segment`: integer | Check whether water reaches a segment. Error: no_such_segment. |
| `submit` | `segment`: integer | Submit the number of the broken segment. This ends the episode. Error: no_such_segment. |

## Results

Envelope as on the other problems: `{"ok": bool, "error": {"code", "message"} | null, "data": ...
| null}`.

| Data shape | From |
| --- | --- |
| `{"segments": 64, "runs": [{"from": "S", "first": 1, "last": 64}]}` | the start view, `look` |
| `{"segment": 32, "water": true}` | `probe` |
| `{"submitted": 41}` | `submit` |
| `{"submitted": 40, "correct": false, "attempts_left": 2}` | a retrying architecture's wrong submission with attempts left (specs/007 R3) |

A T3 layout, for illustration: `[{"from": "S", "first": 1, "last": 18}, {"from": 18, "first": 19,
"last": 30}, {"from": 30, "first": 31, "last": 37}, {"from": 30, "first": 38, "last": 45},
{"from": 18, "first": 46, "last": 52}, ...]`. Runs are listed in order of `first`.

## Errors

| Code | When | Message |
| --- | --- | --- |
| `no_such_segment` | not an integer 1..N or a string of digits in that range (`0`, `65`, `"S"`, `1.5`) | `'S' is not a segment; segments are numbered 1 to 64.` |
| `unknown_tool` | another tool name | `There is no tool named 'scan'. The tools are look, probe and submit.` |
| `episode_over` | any call after the end; not counted | `The episode is over.` |

## What a result never shows

The broken segment except through probe answers, the reference probes, the budget, and whether a
probe was wasted. The boundary test checks shapes with random calls on every level and dev seed,
and that the start and `look` results are identical for one layout with any broken segment
(research R14).
