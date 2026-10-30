# Contract: The architecture interface (`apl.kit`)

What an architecture receives and what it must provide. This is the only runner-side module an
architecture may import, besides `apl.dungeon.tools` and `apl.dungeon.results` (research R15).

## An architecture

A module `src/apl/arch/<name>.py`, written by the experimenter, with:

```python
from apl.kit import Kit


def play(kit: Kit) -> None:
    """Build the graph with StateGraph, invoke it, return when done."""
```

- The runner calls `play` once per episode, with a fresh `Kit`.
- `play` returns when the architecture is done. If the episode has not ended by then, the runner
  ends it as `stopped` (FR-008).
- `play` does not need to detect the end of an episode. When the episode ends, the next model call
  or the tool node raises `EpisodeEnded`, which the runner catches. An architecture MUST NOT catch
  `EpisodeEnded` (or a bare `Exception` around `invoke`) and keep going.
- Any other exception from `play` ends the episode as `stopped` and is recorded as `arch_error`;
  it counts as a failure (research R7).
- Registered names (`src/apl/runner/registry.py`): `react` → `apl.arch.react`. Later milestones
  add theirs.

## `Kit`

Frozen; built by the runner for one episode.

| Attribute | Type | Meaning |
| --- | --- | --- |
| `model` | LangChain chat model | The run's model, with the meter attached (research R3). Use `kit.model.bind_tools(kit.tools)` to let it call tools. Do not create another model |
| `tools` | `list[dict]` | The four tool schemas (name, description, JSON-schema parameters) from the shared tool descriptions. For `bind_tools` only; they cannot be executed directly |
| `tool_node` | graph node | Runs the last AI message's tool calls in order through the episode; returns `{"messages": [ToolMessage, ...]}` (research R4) |
| `base_prompt` | `str` | The shared system prompt. Node-specific instructions go on top of it, never in place of it |
| `start` | `str` | The free start-room description: the M1 `ToolResult` as JSON, the same form `look` returns |
| `recursion_limit` | `int` | Pass as `config={"recursion_limit": kit.recursion_limit}` to `invoke` (research R6) |

`EpisodeEnded` is also exported from `apl.kit`, for type checks and documentation only.

## `kit.tool_node`

- Input: a graph state with a `messages` list (a dict with key `"messages"` or an object with a
  `messages` attribute), whose last message is an AI message with tool calls.
- For each tool call, in order:
  - `look`, `move`, `take`, `use` with valid arguments → the episode's tool;
  - a known tool with missing, extra or non-string arguments → called after the normalization in
    research R5, so the environment returns its usual error;
  - an unknown name → `Episode.unknown(name)`, error `unknown_tool`.
  Every call costs one step (FR-003).
- Output: `{"messages": [ToolMessage(content=<result JSON>, tool_call_id=..., name=...,
  status="success" | "error")]}`, one per tool call.
- If a call ends the episode, the node raises `EpisodeEnded` right after it; remaining calls of
  that turn are not carried out.
- If the episode has already ended when the node runs (for example the token cap was passed by
  the model call that produced these tool calls), it raises `EpisodeEnded` without carrying out
  any call.

## Tool result as the model sees it

The `ToolMessage` content is `json.dumps(result.to_dict())` with the M1 shape
(specs/001-dungeon-environment/contracts/tools.md), for example:

```json
{"ok": false, "error": {"code": "locked", "message": "The door to the north is locked (red)."}, "data": null}
```

M2 adds one error code, `unknown_tool` ("There is no tool named 'open'. The tools are look,
move, take and use.").

## Tool schemas (`kit.tools`)

| Name | Parameters | Description (summary; exact text in `src/apl/kit.py`) |
| --- | --- | --- |
| `look` | none | Describe the current room: label, exits with lock colors, items, inventory, whether it is the exit |
| `move` | `direction`: `north` \| `east` \| `south` \| `west` | Go through the door in that direction. Errors: `invalid_direction`, `no_door`, `locked` |
| `take` | `item`: string, e.g. `"red key"` | Pick up an item in the current room. Error: `no_such_item` |
| `use` | `item`: string, `direction`: as for `move` | Unlock the door in that direction with a key you hold. Errors: `invalid_direction`, `no_door`, `not_in_inventory`, `wrong_key`, `not_locked` |

Each description also says that every call costs one step, including failed ones.

## Base prompt (content, not wording)

- Goal: find and enter the exit room of a dungeon of rooms connected by doors.
- You only see the room you are in. Room labels are names, not coordinates.
- Every tool call is one step; failed calls cost a step too; there is a step budget (its value is
  not given).
- Locked doors open with the key of the same color; keys stay in your inventory after use.
- Tool results are JSON with `ok`, `error` and `data`.
- When you are in the exit room the episode ends by itself.

It never contains the budget, the shortest length, coordinates or the layout (FR-004).

## A1 ReAct (behavior the experimenter's graph must show)

- One model node calling `kit.model.bind_tools(kit.tools)` with the message history: the
  `base_prompt` as system message, `kit.start` as the first user message, then the conversation.
- `kit.tool_node` as the tool node; a conditional edge back to the model while the last AI message
  has tool calls, otherwise to `END`.
- No memory other than the message history (FR-011).
- Tests in `tests/arch/test_react.py` check SC-008 and the scenarios of User Story 4.
