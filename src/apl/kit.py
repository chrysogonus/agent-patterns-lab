"""What an architecture gets for one episode (contracts/kit.md). Architectures may import this.

Besides this module, architectures may import only `apl.dungeon.tools` and `apl.dungeon.results`.
"""

import copy
import hashlib
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import ToolMessage

from apl.dungeon.env import Episode
from apl.dungeon.results import ToolResult
from apl.dungeon.tools import AgentTools

BASE_PROMPT = """\
You are exploring a dungeon: a grid of rooms connected by doors. Your goal is to find the exit \
room and enter it. The episode ends by itself as soon as you are in the exit room.

You only see the room you are in. Each room has a label; labels are names, not coordinates. \
Use the tools look, move, take and use to explore and act.

Every tool call is one step, and failed calls cost a step too. You have a limited step budget, \
so avoid wasted calls.

Some doors are locked with a color. A locked door opens with the key of the same color: take \
the key, then use it on the door. Keys stay in your inventory after use, and opened doors stay \
open.

Tool results are JSON objects with "ok", "error" and "data". When "ok" is false, "error" has a \
"code" and a "message" that explain what went wrong."""

_COST = " Every call costs one step, including failed calls."
_DIRECTION = {
    "type": "string",
    "enum": ["north", "east", "south", "west"],
    "description": "The direction of the door.",
}
_ITEM = {"type": "string", "description": 'The item, for example "red key".'}


def _schema(name: str, description: str, properties: dict[str, Any]) -> dict[str, Any]:
    parameters = {"type": "object", "properties": properties, "required": list(properties)}
    return {
        "type": "function",
        "function": {"name": name, "description": description + _COST, "parameters": parameters},
    }


TOOL_SCHEMAS: list[dict[str, Any]] = [
    _schema(
        "look",
        "Describe the current room: its label, its exits with their lock colors, the items in "
        "it, your inventory, and whether it is the exit.",
        {},
    ),
    _schema(
        "move",
        "Go through the door in a direction and describe the new room. Errors: "
        "invalid_direction, no_door, locked.",
        {"direction": _DIRECTION},
    ),
    _schema(
        "take",
        "Pick up an item in the current room and return your inventory. Error: no_such_item.",
        {"item": _ITEM},
    ),
    _schema(
        "use",
        "Unlock the door in a direction with a key you hold. Errors: invalid_direction, "
        "no_door, not_in_inventory, wrong_key, not_locked.",
        {"item": _ITEM, "direction": _DIRECTION},
    ),
]

# LangGraph's default of 25 super-steps would stop a ReAct loop long before the step budget. A
# constant, because a value derived from the budget would reveal the optimum (Constitution II).
RECURSION_LIMIT = 1000


def prompt_fingerprint() -> str:
    """Identifies the base prompt and tool schemas; runs with different ones are not compared."""
    data = json.dumps({"prompt": BASE_PROMPT, "tools": TOOL_SCHEMAS}, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()[:12]


class EpisodeEnded(Exception):  # noqa: N818 (an event, not an error)
    """The episode is over. The runner catches this; architectures must not."""


ToolNode = Callable[[Any], dict[str, list[ToolMessage]]]


@dataclass(frozen=True, slots=True)
class Kit:
    model: BaseChatModel
    tools: list[dict[str, Any]]
    tool_node: ToolNode
    base_prompt: str
    start: str
    recursion_limit: int


def _arg(args: object, name: str) -> str:
    # Arguments come from a model: missing ones become "", non-strings their JSON text, so the
    # environment answers with its usual error and counts the step.
    value = args.get(name, "") if isinstance(args, Mapping) else ""
    return value if isinstance(value, str) else json.dumps(value)


def build_kit(episode: Episode, model: BaseChatModel) -> Kit:
    tools = AgentTools(episode)

    def call(name: str, args: object) -> ToolResult:
        match name:
            case "look":
                return tools.look()
            case "move":
                return tools.move(_arg(args, "direction"))
            case "take":
                return tools.take(_arg(args, "item"))
            case "use":
                return tools.use(_arg(args, "item"), _arg(args, "direction"))
            case _:
                return episode.unknown(name)

    def tool_node(state: Any) -> dict[str, list[ToolMessage]]:
        """Runs the last AI message's tool calls one by one, in order (research R4)."""
        messages = state["messages"] if isinstance(state, Mapping) else state.messages
        last = messages[-1]
        # Unparsable calls are answered too: the provider rejects a turn with unanswered calls.
        calls = [*getattr(last, "tool_calls", []), *getattr(last, "invalid_tool_calls", [])]
        replies = []
        for tool_call in calls:
            if episode.end_reason is not None:
                raise EpisodeEnded
            result = call(tool_call["name"] or "", tool_call["args"])
            replies.append(
                ToolMessage(
                    json.dumps(result.to_dict()),
                    tool_call_id=tool_call["id"],
                    name=tool_call["name"],
                    status="success" if result.ok else "error",
                )
            )
        if episode.end_reason is not None:
            raise EpisodeEnded
        return {"messages": replies}

    return Kit(
        model=model,
        tools=copy.deepcopy(TOOL_SCHEMAS),
        tool_node=tool_node,
        base_prompt=BASE_PROMPT,
        start=json.dumps(tools.start.to_dict()),
        recursion_limit=RECURSION_LIMIT,
    )
