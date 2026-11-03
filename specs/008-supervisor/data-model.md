# Data Model: A5 Supervisor

A5 adds no stored data: rows, transcripts, route files and viewer episodes keep their formats.
The only new structure is the graph state.

## SupervisorState (graph state, no reducers)

| Key | Type | Meaning |
| --- | --- | --- |
| `messages` | `list[BaseMessage]` | the current helper's latest turn only; emptied at each handoff |
| `map` | `DungeonMap` | A2's map, from every tool result that reached the dungeon |
| `helper` | `"navigator" \| "inventory" \| ""` | the helper of the current handoff |
| `task` | `str` | the current handoff's task |
| `finished` | `list[Report]` | every finished handoff, in order |
| `handoffs` | `int` | handoffs so far; the n in the helper's role |
| `turns` | `int` | helper turns on the current handoff |
| `acted` | `bool` | whether a call of the current handoff reached the dungeon |
| `idle` | `int` | finished handoffs in a row with `acted` false |
| `misses` | `int` | unusable supervisor answers in a row |
| `note` | `str` | why the last supervisor answer was not used |
| `steps` | `int` | calls that reached the dungeon so far |
| `started` | `bool` | whether a helper has seen the start result |

## Report

`Report(helper, task, status: "done" | "unfinished", report: str)`; rendered for the supervisor
as `n. <helper>: <task>: done: <report>` or `n. <helper>: <task>: unfinished after 20 turns:
<report>`.

## Transitions

```text
START → supervisor
supervisor --{"to": h, "task": t}--> h            (handoffs + 1, turns 0, acted false, messages [])
supervisor --unusable, misses < 3--> supervisor   (note set)
supervisor --{"done": true} or misses = 3--> END  (episode ends as stopped)
h (subgraph):  helper --calls--> act --turns < 20--> helper
               helper --no calls--> end of subgraph (Report done)
               act --turns = 20--> end of subgraph (Report unfinished)
h --idle = 3--> END
h --otherwise--> supervisor
```

`EpisodeEnded` from the tool node ends the whole graph at once, wherever it is raised.
