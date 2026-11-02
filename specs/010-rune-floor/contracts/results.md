# Contract: Results and Report

Research R11. Adds to specs/009 `contracts/results.md`.

## Row fields (results.jsonl)

| Field | Type | On rune rows | Elsewhere |
| --- | --- | --- | --- |
| `problem` | str | `"rune"` | unchanged |
| `traps` | int \| null | traps sprung, every attempt | null |
| `repeated_traps` | int \| null | traps on a cell in a rule state that trapped before (research R8) | null |
| `walks` | int \| null | walks started, the first included | null |
| `reference_is_optimal` | bool \| null | true | as before |

The new fields are appended after the signal trace's, so earlier keys keep their order.
`optimal_steps` holds the reference, `efficiency` is `optimal_steps / steps` on success, as on the
other problems. Older rows load unchanged (missing fields are null). Infrastructure-error rows carry
`optimal_steps` and null counts.

## Report: the rune table

```text
# Report: hybrid, mapstate, react on the rune floor

| Arch | Level | Episodes | Success | Steps (median) | Traps (median) | Repeated (median) | Efficiency (median) | Budget hit | Tokens (median) | Latency (median) |
```

With repeats, `## Spread across repeats` has `| Arch | Level | Success (min–max) | Traps (min–max) |`.
`## Attempts` and the infrastructure-error table appear as on the other problems.

## Comparison section

The dungeon's columns. References as in `REFERENCES`, with the signal trace's override extended to
the rune floor: `hybrid` → `mapstate` (A2r does not play it).
