# Contract: Agent-facing tools

Module: `apl.dungeon.tools`, with the result types in `apl.dungeon.results`. Architectures may
import only these two modules from `apl.dungeon` (Constitution II; enforced by a test, see
research R5).

```python
episode = start_episode(dungeon)          # runner side
tools = AgentTools(episode)               # handed to the architecture
first: ToolResult = tools.start           # free start-room description (FR-014)
tools.look() -> ToolResult
tools.move(direction: str) -> ToolResult
tools.take(item: str) -> ToolResult
tools.use(item: str, direction: str) -> ToolResult
```

`AgentTools` has no other public attributes. Every result's `to_dict()` returns the JSON shapes
below, with keys in this order.

## Result envelope (FR-018)

```json
{"ok": true,  "error": null, "data": { ... }}
{"ok": false, "error": {"code": "no_door", "message": "There is no door to the east."}, "data": null}
```

## Room description (`look`, `move`, start)

```json
{
  "ok": true,
  "error": null,
  "data": {
    "label": "k3",
    "exits": [
      {"direction": "north", "lock": null},
      {"direction": "east", "lock": "red"}
    ],
    "items": ["blue key"],
    "inventory": [],
    "is_exit": false
  }
}
```

- `exits` lists only directions with a door, in the order north, east, south, west.
- `lock` is the color while the door is locked, and `null` once it has been opened or if it was
  never locked.
- Items and inventory entries are named `"<color> key"`.
- Nothing about any other room appears: not its label, contents, or distance (SC-007).

## `take` success

```json
{"ok": true, "error": null, "data": {"inventory": ["blue key"]}}
```

## `use` success

```json
{"ok": true, "error": null, "data": {"direction": "east", "color": "red"}}
```

## Errors

Every error counts one step, except `episode_over` (FR-018, edge cases).

| Code | Tool | When |
| --- | --- | --- |
| `invalid_direction` | `move`, `use` | Direction is not one of `north`, `east`, `south`, `west` |
| `no_door` | `move`, `use` | No door in that direction |
| `locked` | `move` | Door is locked; the message names the color |
| `no_such_item` | `take` | The item is not in this room |
| `not_in_inventory` | `use` | The agent does not hold that item |
| `wrong_key` | `use` | The key's color doesn't match the lock; the door stays locked |
| `not_locked` | `use` | The door is open, or was never locked |
| `episode_over` | all | The episode has ended; no step counted, no state change |

When more than one error applies, the first matching row in this table wins. For example,
`use("red key", "up")` returns `invalid_direction` even if the agent has no red key.

## Episode end (runner side, not agent-facing)

- Entering the exit room ends the episode with `exit`. The `move` result is still a normal room
  description with `"is_exit": true`.
- The counted call that uses up the budget ends it with `budget`, unless that call reached the
  exit.
- `episode.stop()` ends it with `stopped`. That does not count as a step.
