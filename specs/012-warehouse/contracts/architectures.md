# Contract: Architectures on the Warehouse

Research R12, R13, R17. Written by the agent at the experimenter's request (FR-024).

## A1 `react`

Unchanged: the warehouse's base prompt, tools and start view; drives robot 0.

## The floor map (`apl.arch.floor_map.FloorMap`)

- `FloorMap.from_start(start_json)`: the floor plan, aisles, total, the robot's cell and its first
  view.
- `apply(name, args, result)`: a robot view replaces the packages recorded on the cells of the
  corridors it shows with the packages it lists, marks those corridors seen and sets the cell,
  carrying and delivered count; `picked` sets `carrying` and removes the package; a
  `delivered_package` clears `carrying`, records the delivery and sets `delivered`. Failed calls
  change nothing.
- `render(others=None, *, here=True)`:

```text
Your map (built from your tool results so far):
You are in: A2 (west corridor). You carry: nothing. Delivered: 0 of 3 packages.
   A B C D E F G H I
1  ? ? ? ? ? ? ? ? ?
2  @ # # # # # # # D
3  . . . P . . . . .
...
@ you, digits other robots, # shelf, P package, . seen, ? not seen yet, S dock, D drop zone.
Corridors seen: west corridor, aisle 2. Not seen yet: aisle 1, aisle 3, east corridor.
Packages seen: package 3 at D3.
```

It draws no conclusion (no "aisle 1 is probably empty"), as the other logs.

## A2 `mapstate`

`FLOOR_MAP_INSTRUCTIONS` (explains the map, no strategy), picks `FloorMap` on `warehouse`.

## Scouts (`apl.arch.scouts`)

- `SharedMap` accepts a `FloorMap`: `from_start` recognizes a warehouse start view by its `floor`
  key; `positions` and a per-robot `carried` are kept outside the map, set on the map before a
  robot's call is applied or the map is rendered for it, as for the dungeon's inventories.
- `scout_messages` on `warehouse`: `FLOOR_MAP_INSTRUCTIONS` and `ROBOT_INSTRUCTIONS` ("You are one
  of several robots in the same warehouse; each has its own cell and carries its own package …").
- Claims on the warehouse use `_ROBOT_CLAIM = ^claim: (package \d+|aisle \d+)`; the dungeon and
  survey field keep `_CLAIM`. A claim is stored as `(target, "")` and rendered `robot n → target`.

## A7 `fanout`

`WAREHOUSE_FANOUT_INSTRUCTIONS`: send 1–4 robots from the dock, each with a task and a step limit,
decided once; robots never hear from each other; every call of every robot costs a step from the
shared budget. No collect step: the graph ends when every robot is done (or the last delivery ends
the episode).

## A8 `rounds`

`WAREHOUSE_ROUNDS_INSTRUCTIONS`: lead up to 4 robots, numbered 0–3; each round see the merged map,
where each robot is and what it carries, and how the last round went; give some robots a short task
with a step limit; `{"done": true}` stops.

## A9 `blackboard`

Every robot gets `WAREHOUSE_TASK`: deliver every package; other robots work on the same floor; the
board shows what all have seen and what each has claimed; to claim, add `claim: package <n>` or
`claim: aisle <n>` to a reply that also makes the next tool call.

## Not on the warehouse

`mapstate_routes`, `plan_execute`, `reflexion`, `supervisor`, `hybrid` refuse it through
`SUPPORTS`.

## About card (`apl.viewer.about`)

`TOOLS`, `MEMORY` and `ENDS` gain `warehouse`; the scouts card's survey-only "Who submits" row is
not shown; `tests/viewer/test_about.py` covers the new pairs through `SUPPORTS`.
