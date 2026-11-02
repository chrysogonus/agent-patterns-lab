# Contract: Results and Report

Research R10. Adds to specs/005 `contracts/results.md`.

## Row fields (results.jsonl)

| Field | Type | On signal rows | Elsewhere |
| --- | --- | --- | --- |
| `problem` | str | `"signal"` | unchanged |
| `submitted_segment` | int \| null | the last submission, null without one | null |
| `broken_segment` | int \| null | the broken segment (also on infrastructure-error rows) | null |
| `segments` | int \| null | N (also on infrastructure-error rows) | null |
| `probes` | int \| null | successful probe calls, every attempt | null |
| `wasted_probes` | int \| null | probes whose answer was implied (research R7) | null |
| `reference_is_optimal` | bool \| null | true on T1, T2; false on T3 | as before |

`optimal_steps` holds the reference steps (probes + 1), `efficiency` is `optimal_steps / steps` on
success, as on the other problems. Older rows load unchanged (missing fields are null).

## Report: the signal table

```text
# Report: hybrid, mapstate, react on the signal trace

| Arch | Level | Episodes | Right | Probes (median) | Wasted (median) | Efficiency (median) | Budget hit | Tokens (median) | Latency (median) |
```

With repeats, `## Spread across repeats` has `| Arch | Level | Right (min–max) | Probes (min–max) |`.
`## Attempts` and the infrastructure-error table appear as on the other problems.

## Comparison section

The dungeon's columns. References as in `REFERENCES`, with one override on the signal trace:
`hybrid` → `mapstate` (A2r does not play it).
