# Data Model: Harder Top Levels (specs/013)

No new type. Two entries are added to existing level tables; every derived value comes from the
existing code.

## Signal level T4 (`apl.signal_trace.model.LEVELS`)

| Field | T3 (unchanged) | T4 (new) |
| --- | --- | --- |
| `segments` | 64 | 256 |
| `ends` | 4 | 8 |
| `min_run` | 4 | 4 |

Derived for every pipe (`apl.signal_trace.generator.generate`), with the existing rules:

- `runs`: 15 on every dev and test seed (T3: 7).
- `reference_probes` (worst case of the probe strategy): 11–12; `reference_steps` = probes + 1.
- `reference_is_optimal`: `False` (a tree).
- `budget` = `max(3 × reference_steps, segments)` = 256.

Validation (tests): 256 segments, 8 pipe ends, every run ≥ 4, no segment feeds more than two, S
feeds one, `1 ≤ broken ≤ 256`, the same pipe for the same seed, and the strategy finds every
possible broken segment within `reference_probes`.

## Workshop level W4 (`apl.workshop.model.LEVELS`)

| Field | W3 (unchanged) | W4 (new) |
| --- | --- | --- |
| `craftables` | 8 | 12 |
| `depth` | 4 | 5 |
| `conflicts` | 2 | 3 |

Derived for every workshop (`apl.workshop.generator.generate`), with the existing rules:

- 3 tempting items with two recipes, 3 scarce raw materials with stock 1, 4 plentiful ones.
- `reference` (steps of the reference plan): 36–41; `budget` = 3 × reference = 108–123.
- The greedy first-recipe plan ends stuck; the reference plan crafts the goal.

Validation (tests): the existing `SHAPE` check with `(12, 5, 3, 3)` (craftables, depth,
alternatives, scarce), `BOUND` 48, the reference crafts the goal in exactly `reference` steps, the
greedy plan gets stuck, the scripted planner fits the budget.

## Unchanged

- T1–T3 and W1–W3: same pipes, workshops, references and budgets for every seed (pinned, R4).
- Saved runs: `run.json` keeps its resolved `levels` list; nothing is migrated.
- Episode rows, outcomes and report columns: the same fields as on the existing levels.
