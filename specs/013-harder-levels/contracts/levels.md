# Contract: Where the New Levels Appear (specs/013)

The tools, results, prompts and architecture interfaces are unchanged (FR-014); only the level
lists below grow.

## Command line

| Command | Before | After |
| --- | --- | --- |
| `apl signal show --level <L> --seed <n> [--route reference] [--html OUT]` | `T1`, `T2`, `T3` | `T1`, `T2`, `T3`, `T4` |
| `apl workshop show --level <L> --seed <n> [--route reference] [--html OUT]` | `W1`, `W2`, `W3` | `W1`, `W2`, `W3`, `W4` |
| `apl run --problem signal --level all …` | plans T1–T3 | plans T1–T4, T4 last |
| `apl run --problem workshop --level all …` | plans W1–W3 | plans W1–W4, W4 last |
| `apl run --problem signal --level T4 …` / `--problem workshop --level W4 …` | refused (unknown level) | plans that level only |
| `apl continue results/<run-id>` | plans the run's saved levels | unchanged: the saved levels only |
| `apl report results/<run-id>` | one row and one comparison section per level | unchanged; T4 and W4 get theirs when present |

An unknown level is still refused, with the valid levels listed.

## Viewer (`/api/options`)

`problems.signal.levels` becomes `["T1", "T2", "T3", "T4"]` and `problems.workshop.levels`
becomes `["W1", "W2", "W3", "W4"]`. The `/api/signal` and `/api/workshop` endpoints accept the new
level with the same response shape; the T4 pipe's SVG uses 24 segments a row and a wider label column
(research R8); T1–T3 keep theirs.

## Text and pictures

`apl signal show --level T4` prints the 15 runs as it prints T3's 7; `--html` writes the wider
pipe drawing. `apl workshop show --level W4` prints the recipe tree and stock like W3, with the
reference plan under `--route reference`.
