# Contract: Several scouts (environment and kit)

This adds to specs/002-runner-react/contracts/kit.md and specs/001-dungeon-environment's tool
contract. Everything not listed here is unchanged. Research R1–R3.

## What an architecture gets

```python
@dataclass(frozen=True, slots=True)
class Scout:  # apl.kit
    number: int  # 1, 2 or 3
    tool_node: ToolNode  # runs the last AI message's tool calls as this scout
    start: str  # JSON of {"ok": true, "error": null, "data": RoomView} for this scout


class Kit:
    ...  # model, tools, tool_node, base_prompt, start, recursion_limit
    add_scout: Callable[[], Scout | None]  # a new scout in the start room; None at the limit
```

- `kit.tool_node` and `kit.start` are scout 0's. A single-agent architecture never sees anything
  else.
- `add_scout()` costs no step and is not logged. It returns `None` when the episode already has 4
  scouts; the episode goes on.
- `Scout.start` describes the start room as that scout sees it at creation: its own empty
  inventory, and doors opened so far shown as open. It reveals nothing a `look` would not.
- A scout's `tool_node` has exactly the contract of `kit.tool_node`: it runs every tool call of the
  last AI message in order, answers unparsable calls with an error, and raises `EpisodeEnded` once
  the episode is over.
- All tool nodes of an episode share one lock: a call is applied completely before the next one
  starts, whichever thread makes it.

## Rules of the world with several scouts

| Thing | Per scout | Shared |
| --- | --- | --- |
| Position | ✓ | |
| Inventory (keys held) | ✓ | |
| Opened doors | | ✓ |
| Keys still lying in rooms | | ✓ (a key taken by any scout is gone for all) |
| Step count, budget, invalid actions | | ✓ |
| End of the episode | | ✓ |

- `use` checks the acting scout's inventory: a key held by another scout fails with
  `not_in_inventory` and costs a step.
- `move` through a door another scout opened works.
- The episode ends with `exit` when the acting scout enters the exit room, otherwise with `budget`
  when the shared step count reaches the budget. Any later call by any scout returns
  `episode_over` and costs no step.
- `steps` and `efficiency` count the calls of all scouts. `optimal_steps` is the single-agent
  shortest solution.

## The log

Every log entry names its scout:

```json
{"index": 7, "step": 8, "scout": 2, "action": {"tool": "move", "args": ["east"]}, "result": {...}}
```

`"scout"` is left out when it is 0, so single-agent logs are unchanged. Entries are in the order the
calls were applied.

## Boundary

- The architecture import rule is unchanged: `apl.kit`, `apl.dungeon.tools`,
  `apl.dungeon.results`, and other `apl.arch` modules.
- `tests/dungeon/test_boundary.py` also covers `apl/arch/scouts.py`, `fanout.py`, `rounds.py` and
  `blackboard.py`.
