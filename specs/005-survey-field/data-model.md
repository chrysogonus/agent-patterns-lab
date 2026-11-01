# Data Model: Several Problems, and the Survey Field

Entities for [plan.md](plan.md). Dungeon entities (specs 001–004) are unchanged unless listed.

## Problem

A kind of task the lab can run ([contracts/problems.md](contracts/problems.md)).

| Field | Type | Rule |
| --- | --- | --- |
| `name` | str | `"dungeon"` or `"survey"`; unique |
| `levels` | mapping name → level | dungeon L1–L3, survey S1–S3 |
| `dev_seeds`, `test_seeds` | ranges | dev 1000–1009, test 2000–2019 for both |
| `generate(level, seed)` | → world | deterministic; the world has `budget` and `reference_steps` |
| `start_episode(world)` | → episode | a fresh episode with scout 0 at the start |
| `build_kit(episode, model)` | → `Kit` | the problem's prompt, tools and tool node |
| `prompt_fingerprint()` | → str | 12 hex digits over the problem's base prompt and tool schemas |

`DEFAULT = "dungeon"`. The registry is runner-side; architectures never import it.

## SurveyLevel

| Field | Type | Rule |
| --- | --- | --- |
| `name` | str | `S1`, `S2`, `S3` |
| `size` | int | 6 or 10 (square) |
| `deposits` | int | 6 or 15; fewer than the cells |
| `walls` | int | interior wall segments: 0, 0, 18 |
| `min_dead_ends` | int | cells with exactly one exit: 0, 0, 3 |

## Field (a survey world)

| Field | Type | Rule |
| --- | --- | --- |
| `level` | SurveyLevel | |
| `seed` | int | |
| `size` | int | columns = rows = size |
| `walls` | frozenset of cell pairs | each pair is two neighbors; never splits the field |
| `deposits` | frozenset of cells | `len == level.deposits`; never the start |
| `start` | cell | `(0, 0)`, named `A1` |
| `walk` | tuple of directions | the reference walk; legal from `start`; enters every cell |
| `reference_steps` | int | `len(walk) + 1` (the submission) |
| `reference_is_optimal` | bool | true on open levels |
| `budget` | int | `3 × reference_steps` |

Cell names: column letter (`A` = west) then row number (`1` = north): `name((col, row)) =
"ABCDEFGHIJ"[col] + str(row + 1)`.

Validation (tested for every level and seed): every cell reachable from `start`; deposit count;
on S3 the wall count and dead-end minimum; the walk is legal and enters every cell; on open levels
`reference_steps == size²`.

## Survey Episode

| Field | Type | Rule |
| --- | --- | --- |
| `field` | Field | |
| `scouts` | list of positions | scout 0 at `start`; at most 4; `add_scout()` puts one at `start`, no step |
| `seen` | set of cells | every cell a scout has stood in, start included |
| `steps` | int | every counted call, failed ones included |
| `invalid_actions` | int | failed calls |
| `submitted` | int or None | set by the first successful `submit` |
| `end_reason` | `submitted` / `budget` / `stopped` / None | |
| `log` | list of LogEntry | as on the dungeon, plus `turn` |
| `turn_source` | callable → int, optional | set by the runner to the meter's model-call count (R11) |
| `on_step` | callable, optional | the viewer's observer |

State transitions:

```text
running ──submit(valid)──▶ ended: submitted   (success iff submitted == len(deposits))
running ──steps == budget──▶ ended: budget    (a submission on the last step counts first)
running ──stop()──▶ ended: stopped
ended ──any call──▶ episode_over error, not counted (step None)
```

## LogEntry (survey)

`index`, `step` (None for uncounted calls), `scout` (only when not 0), `action` (`look`,
`move <direction>`, `submit <raw total>`, `unknown <name>`), `result` (the result envelope),
`turn` (int or None when no `turn_source`).

## Survey Outcome

The dungeon `Outcome`'s fields — `level`, `seed`, `end_reason`, `steps`, `optimal_steps` (here the
reference steps), `budget`, `invalid_actions`, `log`, `scouts`, `success`, `budget_hit` — plus:

| Field | Rule |
| --- | --- |
| `submitted_total` | int or None |
| `true_total` | `len(deposits)` |
| `cells_seen`, `cells` | `len(seen)`, `size²` |
| `parallel_turns` | distinct `turn` values among counted calls; `steps` when no `turn_source` |
| `reference_is_optimal` | from the field |

## FieldMap (architecture side)

Built only from survey tool results ([contracts/architectures.md](contracts/architectures.md)).

| Field | Rule |
| --- | --- |
| `columns`, `rows` | from the first view |
| `cells` | name → (deposit, exits), in the order first seen |
| `current` | the name of the cell the viewer of the map stands in |

`apply(name, args, result)` ignores failed calls; a `move` or `look` view records the cell and
sets `current`; `submit` changes nothing.

## EpisodeRow and RunRecord additions

See [contracts/results.md](contracts/results.md): `problem` on rows and `run.json`; survey-only
row fields `submitted_total`, `true_total`, `cells_seen`, `cells`, `parallel_turns`,
`reference_is_optimal`.

## Architecture support

`SUPPORTS[arch]` → set of problem names. A run or viewer episode for a pair outside the table is
refused before anything is played.
