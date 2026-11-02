# Contract: Results and Report

Research R8–R10. Adds to specs/011 `contracts/results.md`.

## Row fields (episodes.jsonl)

| Field | Type | On warehouse rows | Elsewhere |
| --- | --- | --- | --- |
| `problem` | str | `"warehouse"` | unchanged |
| `delivered` | int \| null | packages delivered | null |
| `packages` | int \| null | packages in the warehouse | null |
| `idle_robot_turns` | int \| null | R8 | null |
| `parallel_turns` | int \| null | R8 (shared with the survey field) | as before |
| `scouts` | int \| null | robots that made a call | as before |
| `reference_is_optimal` | bool \| null | false | as before |

Appended after the workshop's fields. `end_reason` gains `delivered`. Infrastructure-error rows
carry `optimal_steps` and null counts. Older rows load unchanged.

## Report: the warehouse table

```text
# Report: blackboard, fanout, mapstate, react, rounds on the warehouse

| Arch | Level | Episodes | Success | Delivered (median) | Steps (median) | Efficiency (median) | Turns (median) | Idle (median) | Robots (median) | Budget hit | Tokens (median) | Latency (median) |
```

Efficiency is the reference against the steps, on successful episodes. With repeats,
`## Spread across repeats` has `| Arch | Level | Success (min–max) | Turns (min–max) |`. The
infrastructure-error table appears as on the other problems; there is no `## Attempts` section
(no retrying architecture).

## Comparison section

The survey field's variant (with parallel turns); A7, A8 and A9 are compared with `mapstate`, as on
the survey field.
