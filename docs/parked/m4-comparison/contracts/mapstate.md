# Contract: A2 Map State (`mapstate`)

A2 meets the M2 architecture interface (specs/002-runner-react/contracts/kit.md):
`play(kit: Kit) -> None` in `src/apl/arch/mapstate.py`, registered as `mapstate`.

## Imports

- `mapstate.py` may import from `apl` only `apl.kit`, `apl.dungeon.results` and
  `apl.arch.dungeon_map`. The boundary test in `tests/dungeon/test_boundary.py` enforces this.
- `dungeon_map.py` imports nothing from `apl` except, optionally, `apl.dungeon.results` for the
  error codes.
- Neither module creates a model. Both use `kit.model` (Constitution I).

## Graph

```text
START → agent ─(tool_calls or invalid_tool_calls)→ act → agent
              └─(neither)→ END
```

- `agent` makes one call to `kit.model.bind_tools(kit.tools)` with the input below, and returns
  `{"messages": [reply]}`.
- `act`:
  1. calls `kit.tool_node(state)`;
  2. pairs each reply in order with its call (`tool_calls`, then `invalid_tool_calls`, by
     `tool_call_id`);
  3. calls `map.apply(name, args, json.loads(reply.content))` for each pair;
  4. returns `{"messages": [ai, *replies], "map": map}`.
- `EpisodeEnded` from the tool node is not caught. It ends the graph, and the runner handles it,
  as in A1. The results of that last batch are therefore not applied to the map. No model call
  can follow them, so this is harmless (research R3).
- The graph is invoked with `{"messages": [], "map": DungeonMap.from_start(kit.start)}` and
  `config={"recursion_limit": kit.recursion_limit}`.

## Model input per call

| Position | First turn | Later turns |
| --- | --- | --- |
| 1 | `SystemMessage(kit.base_prompt + "\n\n" + MAP_INSTRUCTIONS)` | same |
| 2 | `HumanMessage(kit.start)` | the previous `AIMessage` and its `ToolMessage`s, unchanged |
| last | `HumanMessage(map.render())` | same |

No other message is sent. In particular, no reply or tool result older than the previous turn is
sent (FR-004, US1/AC5, AC6).

## `MAP_INSTRUCTIONS`

Describes the map only: it is built from the agent's own tool results, it replaces the
conversation history, the latest tool results appear just before it, and it explains what
"unexplored" and "locked (color)" mean. It contains no strategy advice and no digits (research
R5).

## Map text (`DungeonMap.render()`)

- Line 1: `Your map (built from your tool results so far):`
- `You are in: <label>. Inventory: <items, comma-separated, or "nothing">.`
- `Rooms seen:`, then one line per room, in the order first seen:

  ```text
  - <label>[ (you are here)]: <exit>; <exit>; ...[; items: <items>]
  ```

  Each `<exit>` is in north, east, south, west order and is one of:
  - `<direction> -> <label>`: the destination is known;
  - `<direction>: unexplored`: the destination is not known;
  - `<direction>: unexplored, locked (<color>)`: not known and locked.

  A known exit that is still locked cannot occur: the agent could not have gone through it.
- `Doors you opened: <label> <direction> (<color>); ...`. The line is left out when no door has
  been opened.
- `Unexplored exits: <label> <direction>[ (locked, <color>)]; ...`, or `Unexplored exits: none.`

The text never contains step counts, the budget, coordinates or anything that was not in a tool
result.

## Behavior guaranteed by tests

| Spec | Check |
| --- | --- |
| US1/AC1, SC-001 | A scripted model replaying the shortest solution succeeds with efficiency 1.0 on every dev dungeon of L1–L3 |
| US1/AC2, SC-002 | After every step of scripted routes, on at least 5 dungeons including the reference layouts, the map equals the oracle from layout and frames (research R7) |
| US1/AC3 | After `move east` from X to Y, X's east exit leads to Y and Y's west exit leads to X |
| US1/AC4 | After `take` and `use`, the door shows as opened with its color and the key is in the inventory, also several turns later |
| FR-005 | A batch that reaches the exit, and one that reaches the budget, end the episode with `exit` and `budget` |
| US1/AC5, AC6 | The recorded model inputs have exactly the layout above. At step 30 no older reply or result appears |
| US1/AC7 | The boundary test covers `mapstate.py` and `dungeon_map.py` |
| SC-003 | With every room of every L3 dev dungeon seen, `render()` is at most `num_ctx / 4` characters (4,096). Characters bound tokens from above (research R4) |
| FR-005 | A text answer ends the episode as `stopped`; running into the budget ends as `budget` |
