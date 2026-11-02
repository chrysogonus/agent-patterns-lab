"""What an architecture gets for one rune-floor episode (specs/010 contracts/problems.md).

Runner side.
"""

import copy
import json
import threading
from collections.abc import Mapping

from langchain_core.language_models import BaseChatModel

from apl.kit import RECURSION_LIMIT, Kit, Scout, ToolNode, _tool_node
from apl.rune.env import Episode
from apl.rune.prompt import BASE_PROMPT, TOOL_SCHEMAS
from apl.rune.results import ToolResult
from apl.rune.tools import AgentTools


def _no_scout() -> Scout | None:
    return None  # one agent on the rune floor (research R10)


def build_kit(episode: Episode, model: BaseChatModel) -> Kit:
    tools = AgentTools(episode)
    lock = threading.Lock()

    def call(name: str, args: object) -> ToolResult:
        # The direction is passed as the model sent it, so the episode can report a bad one.
        direction = args.get("direction") if isinstance(args, Mapping) else None
        match name:
            case "look":
                return tools.look()
            case "move":
                return tools.move(direction)
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
        problem="rune",
        restart=restart,
        max_attempts=episode.max_attempts,
    )
