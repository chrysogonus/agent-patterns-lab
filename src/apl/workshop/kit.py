"""What an architecture gets for one rune-floor episode (specs/011 contracts/problems.md).

Runner side.
"""

import copy
import json
import threading
from collections.abc import Mapping

from langchain_core.language_models import BaseChatModel

from apl.kit import RECURSION_LIMIT, Kit, Scout, ToolNode, _tool_node
from apl.workshop.env import Episode
from apl.workshop.prompt import BASE_PROMPT, TOOL_SCHEMAS
from apl.workshop.results import ToolResult
from apl.workshop.tools import AgentTools


def _no_scout() -> Scout | None:
    return None  # one body in the workshop (research R10)


def build_kit(episode: Episode, model: BaseChatModel) -> Kit:
    tools = AgentTools(episode)
    lock = threading.Lock()

    def call(name: str, args: object) -> ToolResult:
        # Arguments are passed as the model sent them, so the episode can report a bad one.
        given = args if isinstance(args, Mapping) else {}
        item, recipe = given.get("item"), given.get("recipe")
        match name:
            case "look":
                return tools.look()
            case "inspect":
                return tools.inspect(item)
            case "gather":
                return tools.gather(item)
            case "craft":
                return tools.craft(item, recipe)
            case _:
                return episode.unknown(name)

    tool_node: ToolNode = _tool_node(episode, lock, call)

    def restart() -> bool:
        with lock:
            return episode.restart()

    return Kit(
        model=model,
        tools=copy.deepcopy(TOOL_SCHEMAS),
        tool_node=tool_node,
        base_prompt=BASE_PROMPT,
        start=json.dumps(tools.start.to_dict()),
        recursion_limit=RECURSION_LIMIT,
        add_scout=_no_scout,
        problem="workshop",
        restart=restart,
        max_attempts=episode.max_attempts,
    )
