# Data Model: A3 Plan-and-Execute

A3 adds graph state only. Results, run records and saved episodes keep their schema; the only
change is which roles count into `orchestrator_calls` (research R7).

## Graph state `PlanState` (in `src/apl/arch/plan_execute.py`)

No reducers: each write replaces the value, as in A2's `MapState`.

| Field | Type | Meaning |
| --- | --- | --- |
| `messages` | `list[BaseMessage]` | The executor's latest turn only: its reply and that reply's tool results (A2's rule) |
| `map` | `DungeonMap \| FieldMap` | One map for the episode, built from tool results only |
| `plan` | `list[str]` | Subgoals still to do; `plan[0]` is the current one |
| `finished` | `list[Outcome]` | Subgoals worked on so far, in order |
| `subgoal` | `int` | Subgoals started in the episode, from 1 (the role's N) |
| `turns` | `int` | Executor turns on the current subgoal |
| `acted` | `bool` | Whether the current subgoal has made any tool call |
| `idle` | `int` | Subgoals in a row that ended without a tool call |
| `misses` | `int` | Unusable planner or replanner answers in a row |
| `note` | `str` | Why the last answer was not used, shown on the next planning call; else "" |
| `steps` | `int` | Tool calls applied so far, shown to the replanner as `Steps used so far: N` |
| `started` | `bool` | Whether the executor has had its first turn (the start result is shown once) |
| `stop` | `bool` | The replanner answered `{"done": true}` |

### `Outcome`

| Field | Type | Meaning |
| --- | --- | --- |
| `subgoal` | `str` | The subgoal's text |
| `status` | `"done"` \| `"unfinished"` | `done`: the executor answered without a tool call; `unfinished`: `MAX_TURNS` reached |
| `report` | `str` | The executor's last reply text |

Rendered for the replanner as `1. <subgoal>: done: <report>` or
`1. <subgoal>: unfinished after 20 turns: <report>`.

## Transitions

| From | Condition | To | State change |
| --- | --- | --- | --- |
| `START` | — | `planner` | — |
| `planner` | usable plan | `executor` | `plan` set, `subgoal` = 1, `misses` = 0, `note` = "" |
| `planner` | unusable, `misses` + 1 < 3 | `planner` | `misses` += 1, `note` set |
| `planner` | unusable, `misses` + 1 = 3 | `END` | — |
| `executor` | reply has tool calls (valid or invalid) | `act` | `messages` = [reply], `turns` += 1 |
| `executor` | reply has no tool call, `idle` stays < 3 | `replanner` | outcome `done` appended, `plan` pops its head; `idle` += 1 if not `acted`, else 0 |
| `executor` | reply has no tool call, `idle` reaches 3 | `END` | — |
| `act` | `turns` < `MAX_TURNS` | `executor` | map updated, `messages` = [reply, results], `acted` = true, `steps` += results |
| `act` | `turns` = `MAX_TURNS` | `replanner` | outcome `unfinished` appended, `plan` pops its head, `idle` = 0 |
| `replanner` | `{"plan": [...]}` usable | `executor` | `plan` replaced, `subgoal` += 1, `turns` = 0, `acted` = false, `messages` = [], `misses` = 0 |
| `replanner` | `{"done": true}` | `END` | `stop` = true |
| `replanner` | unusable, `misses` + 1 < 3 | `replanner` | `misses` += 1, `note` set |
| `replanner` | unusable, `misses` + 1 = 3 | `END` | — |

Any tool call that ends the episode (exit entered, total submitted, budget used up) raises
`EpisodeEnded` inside `act`; the graph ends there, with no further model call.

## Validation rules

- A plan is a list of 1 to `MAX_SUBGOALS` (8) strings, each non-empty after stripping.
- `{"done": true}` is valid only for the replanner.
- An answer with both `plan` and `done` is read as `done` only when `done` is `true`; anything
  else is unusable with a note saying why.

## Model-call roles (transcript, viewer, meter)

| Role | Counted in `orchestrator_calls` |
| --- | --- |
| `planner` | yes |
| `replanner` | yes |
| `executor (subgoal N)` | no |
| `orchestrator` (A7, A8, unchanged) | yes |
| `scout N` (A7–A9, unchanged) | no |
