"""What an architecture gets for one survey episode (specs/005 research R3). Runner side."""

import copy
import json
import threading
from collections.abc import Mapping

from langchain_core.language_models import BaseChatModel

from apl.kit import RECURSION_LIMIT, Kit, Scout, ToolNode, _arg, _tool_node
from apl.survey.env import Episode
from apl.survey.prompt import BASE_PROMPT, TOOL_SCHEMAS
from apl.survey.results import ToolResult
from apl.survey.tools import AgentTools


def build_kit(episode: Episode, model: BaseChatModel) -> Kit:
    tools = AgentTools(episode)
    lock = threading.Lock()  # scouts may call from parallel graph branches

    def tool_node_for(scout: int) -> ToolNode:
        def call(name: str, args: object) -> ToolResult:
            match name:
                case "look":
                    return tools.look(scout)
                case "move":
                    return tools.move(_arg(args, "direction"), scout)
                case "submit":
                    # Passed as the model sent it, so the episode can tell 12 from "about 12".
                    total = args.get("total") if isinstance(args, Mapping) else None
                    return tools.submit(total, scout)
                case _:
                    return episode.unknown(name, scout=scout)

        return _tool_node(episode, lock, call)

    def add_scout() -> Scout | None:
        with lock:
            number = episode.add_scout()
            if number is None:
                return None
            start = ToolResult.success(episode.describe(number))
        return Scout(number, tool_node_for(number), json.dumps(start.to_dict()))

    def restart() -> bool:
        with lock:
            return episode.restart()

    return Kit(
        model=model,
        tools=copy.deepcopy(TOOL_SCHEMAS),
        tool_node=tool_node_for(0),
        base_prompt=BASE_PROMPT,
        start=json.dumps(tools.start.to_dict()),
        recursion_limit=RECURSION_LIMIT,
        add_scout=add_scout,
        problem="survey",
        restart=restart,
        max_attempts=episode.max_attempts,
    )
