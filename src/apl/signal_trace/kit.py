"""What an architecture gets for one signal-trace episode (specs/009 contracts/problems.md).

Runner side.
"""

import copy
import json
import threading
from collections.abc import Mapping

from langchain_core.language_models import BaseChatModel

from apl.kit import RECURSION_LIMIT, Kit, Scout, ToolNode, _tool_node
from apl.signal_trace.env import Episode
from apl.signal_trace.prompt import BASE_PROMPT, TOOL_SCHEMAS
from apl.signal_trace.results import ToolResult
from apl.signal_trace.tools import AgentTools


def _no_scout() -> Scout | None:
    return None  # one agent on the signal trace (research R9)


def build_kit(episode: Episode, model: BaseChatModel) -> Kit:
    tools = AgentTools(episode)
    lock = threading.Lock()

    def call(name: str, args: object) -> ToolResult:
        # Segments are passed as the model sent them, so the episode can tell 12 from "about 12".
        segment = args.get("segment") if isinstance(args, Mapping) else None
        match name:
            case "look":
                return tools.look()
            case "probe":
                return tools.probe(segment)
            case "submit":
                return tools.submit(segment)
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
        problem="signal",
        restart=restart,
        max_attempts=episode.max_attempts,
    )
