# Contract: Results Additions

Adds to specs/002 and 004's `contracts/results.md`. All additions are optional on read, so every
run folder written before this feature still loads, continues and reports as before.

## `run.json`

| Field | Type | Missing in older runs means |
| --- | --- | --- |
| `problem` | str | `"dungeon"` |

The settings record's `prompt_fingerprint` is the run's problem's fingerprint.

## `episodes.jsonl` rows

| Field | Dungeon rows | Survey rows |
| --- | --- | --- |
| `problem` | `"dungeon"` | `"survey"` |
| `optimal_steps` | shortest solution (unchanged) | reference steps |
| `efficiency` | unchanged | `optimal_steps / steps` on success |
| `submitted_total` | `null` | int or `null` (no submission) |
| `true_total` | `null` | int |
| `cells_seen` | `null` | int, all scouts together |
| `cells` | `null` | int |
| `parallel_turns` | `null` | int (research R11) |
| `reference_is_optimal` | `null` | bool |

`end_reason` on survey rows: `submitted`, `budget` or `stopped`. `success` is true only for
`submitted` with `submitted_total == true_total`.

## The survey report

Main table, per architecture and level:

| Column | Meaning |
| --- | --- |
| Right | share of completed episodes with the right total |
| Off by | median absolute error of the wrong totals (`—` if none) |
| Seen | median share of cells seen |
| Steps | median steps |
| Turns | median parallel turns |
| Tokens | median input + output tokens |
| Latency | median seconds |

The spread table shows min–max of Right, Steps and Turns across repeats. The comparison section
(M4) works as before, with Δ right and Δ turns added for survey runs; its reference pairs are
`mapstate → react` and each scout architecture → `mapstate`.
