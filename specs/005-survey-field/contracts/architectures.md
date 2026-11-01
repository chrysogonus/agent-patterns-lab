# Contract: Architectures on the Survey Field

Research R10, R14. Written by the agent at the experimenter's request (spec FR-029); the dungeon
behavior of every architecture stays exactly as it is.

## A1 `react`

No change. It already uses only `kit.tools`, `kit.base_prompt`, `kit.start` and
`kit.tool_node`.

## The field map (`apl/arch/field_map.py`)

Built from the start view and each call's result, never from the environment.

Render, for a 6×6 field after a few moves:

```text
Your map (built from your tool results so far):
You are in: C2. Field: 6 columns (A–F) × 6 rows (1–6).
   A B C D E F
1  . o . ? ? ?
2  . . @ ? ? ?
3  ? ? ? ? ? ?
4  ? ? ? ? ? ?
5  ? ? ? ? ? ?
6  ? ? ? ? ? ?
@ you, o deposit, . seen without deposit, ? not seen yet.
Cells seen: 6 of 36. Deposits seen: 1.
Walls seen: B2 east.
Unseen cells next to seen ones: D1, D2, A3, B3, C3.
```

`@` replaces `o` when the viewer stands on a deposit; the deposits line counts it. Walls are listed
as "<cell> <direction>" for each wall side a seen cell reports, edges excluded. With several scouts
(`SharedMap`), other scouts are shown by number (`0`–`3`) in the picture and listed as on the
dungeon.

## A2 `mapstate`

Same graph. With `kit.problem == "survey"` it builds a `FieldMap` and uses
`FIELD_MAP_INSTRUCTIONS`, which explain the map's symbols and lines only, as `MAP_INSTRUCTIONS`
does for the dungeon.

## Shared scout (`scouts.py`)

`SharedMap` works with either map. Scout and orchestrator texts have a survey variant: the field
instead of the dungeon, no keys or inventories, and that a scout ends its task by answering without
a tool call with a short report (A7, A8) or by submitting (A9).

## A7 `fanout`

Dungeon: unchanged. Survey: `orchestrate` → scouts → `collect` → `END`.

- `collect` calls the orchestrator with each scout's report (or "used up its steps") and asks for
  `{"total": <whole number>}`. A missing or bad answer is re-asked up to `MAX_MISSES` times; then
  the episode ends without a submission.
- The graph submits by calling scout 0's tool node with a `submit` call. It costs one step and is
  logged as scout 0's call.

## A8 `rounds`

Dungeon: unchanged. Survey: the stop answer is `{"total": <whole number>}` instead of
`{"done": true}`; the graph submits it as in A7.

## A9 `blackboard`

Dungeon: unchanged. Survey task text: count all deposits in the field together; the board shows
what all scouts have seen; claim an unseen cell next to a seen one with `claim: <cell>
<direction>`; when the board shows every cell, submit the total. Any scout's successful submission
ends the episode.

Both problems: a claim belongs in a reply that also makes a tool call. A reply with a claim and no
tool call keeps the scout going, up to three in a row (specs/004 contracts/orchestrators.md). In the
first gpt-6-luna runs, three of the four scouts sent their claim alone and left on their first turn.
