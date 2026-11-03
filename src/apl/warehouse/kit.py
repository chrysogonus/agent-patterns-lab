"""What an architecture gets for one warehouse episode (specs/012 contracts/problems.md).

Runner side, modelled on the survey field's kit: a tool node per robot and `add_scout`.
"""

import copy
import json
import threading

from langchain_core.language_models import BaseChatModel

from apl.kit import RECURSION_LIMIT, Kit, Scout, ToolNode, _arg, _tool_node
from apl.warehouse.env import Episode
from apl.warehouse.prompt import BASE_PROMPT, TOOL_SCHEMAS
from apl.warehouse.results import ToolResult
from apl.warehouse.tools import AgentTools


def build_kit(episode: Episode, model: BaseChatModel) -> Kit:
    tools = AgentTools(episode)
    lock = threading.Lock()  # robots may call from parallel graph branches

    def tool_node_for(robot: int) -> ToolNode:
        def call(name: str, args: object) -> ToolResult:
            match name:
                case "look":
                    return tools.look(robot)
                case "move":
                    return tools.move(_arg(args, "direction"), robot)
                case "pick":
                    return tools.pick(robot)
                case "drop":
                    return tools.drop(robot)
                case _:
                    return episode.unknown(name, scout=robot)

        return _tool_node(episode, lock, call)

    def add_scout() -> Scout | None:
        with lock:
            number = episode.add_scout()
            if number is None:
                return None
            start = ToolResult.success(episode.start_view(number))
        return Scout(number, tool_node_for(number), json.dumps(start.to_dict()))

    return Kit(
        model=model,
        tools=copy.deepcopy(TOOL_SCHEMAS),
        tool_node=tool_node_for(0),
        base_prompt=BASE_PROMPT,
        start=json.dumps(tools.start.to_dict()),
        recursion_limit=RECURSION_LIMIT,
        add_scout=add_scout,
        problem="warehouse",
        max_attempts=episode.max_attempts,
    )
