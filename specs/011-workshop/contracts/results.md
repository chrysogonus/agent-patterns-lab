# Contract: Results and Report

Research R11. Adds to specs/010 `contracts/results.md`.

## Row fields (results.jsonl)

| Field | Type | On workshop rows | Elsewhere |
| --- | --- | --- | --- |
| `problem` | str | `"workshop"` | unchanged |
| `stuck` | bool \| null | whether the episode ended stuck | null |
| `wasted` | int \| null | scarce units consumed beyond the reference's use for the same item (research R8) | null |
| `inspected` | int \| null | distinct items inspected | null |
| `crafted` | int \| null | successful crafts, every attempt | null |
| `reference_is_optimal` | bool \| null | true | as before |

Appended after the rune floor's fields. `end_reason` gains `stuck` (and `goal`, shared with the
rune floor). Infrastructure-error rows carry `optimal_steps` and null counts. Older rows load
unchanged.

## Report: the workshop table

```text
# Report: hybrid, mapstate, plan_execute, react on the workshop

| Arch | Level | Episodes | Success | Stuck | Steps (median) | Wasted (median) | Efficiency (median) | Budget hit | Tokens (median) | Latency (median) |
```

With repeats, `## Spread across repeats` has `| Arch | Level | Success (min–max) | Steps (min–max) |`.
`## Attempts` and the infrastructure-error table appear as on the other problems.

## Comparison section

The dungeon's columns; `PROBLEM_REFERENCES["workshop"] = {"hybrid": "mapstate"}`.
