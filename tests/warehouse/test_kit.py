"""The warehouse's kit: prompt, tool schemas, robots (specs/012 T010)."""

import json

from langchain_core.messages import AIMessage
from langchain_core.messages.tool import ToolCall, invalid_tool_call

from apl.kit import Kit
from apl.warehouse import start_episode
from apl.warehouse.kit import build_kit
from apl.warehouse.prompt import BASE_PROMPT, TOOL_SCHEMAS, prompt_fingerprint
from tests.warehouse.floors import p2_floor


def _kit() -> Kit:
    return build_kit(start_episode(p2_floor()), model=None)  # type: ignore[arg-type]


def _call(kit: Kit, name: str, args: dict[str, object]) -> dict[str, object]:
    call = ToolCall(name=name, args=args, id="c1")
    (reply,) = kit.tool_node({"messages": [AIMessage("", tool_calls=[call])]})["messages"]
    found = json.loads(str(reply.content))
    assert isinstance(found, dict)
    return found


def test_the_kit() -> None:
    kit = _kit()
    assert kit.problem == "warehouse" and kit.base_prompt == BASE_PROMPT
    assert kit.tools == TOOL_SCHEMAS and kit.tools is not TOOL_SCHEMAS
    names = [t["function"]["name"] for t in kit.tools]
    assert names == ["look", "move", "pick", "drop"]
    params = {t["function"]["name"]: t["function"]["parameters"]["properties"] for t in kit.tools}
    assert params["look"] == params["pick"] == params["drop"] == {}
    assert params["move"]["direction"]["enum"] == ["north", "east", "south", "west"]
    assert json.loads(kit.start)["data"]["floor"][1] == "S#######D"
    assert kit.restart() is False and kit.max_attempts == 1


def test_the_tool_node_answers_every_tool() -> None:
    kit = _kit()
    assert _call(kit, "look", {})["ok"] is True
    assert _call(kit, "move", {"direction": "north"})["data"]["cell"] == "A1"  # type: ignore[index]
    assert _call(kit, "pick", {})["error"]["code"] == "no_package"  # type: ignore[index]
    assert _call(kit, "drop", {})["error"]["code"] == "not_carrying"  # type: ignore[index]
    assert _call(kit, "push", {})["error"]["code"] == "unknown_tool"  # type: ignore[index]
    bad = invalid_tool_call(name="move", args="{", id="c2", error="bad json")
    (reply,) = kit.tool_node({"messages": [AIMessage("", invalid_tool_calls=[bad])]})["messages"]
    assert json.loads(str(reply.content))["ok"] is False


def test_robots_can_be_added_up_to_four() -> None:
    kit = _kit()
    scouts = [kit.add_scout() for _ in range(4)]
    assert [s.number if s else None for s in scouts] == [1, 2, 3, None]
    first = scouts[0]
    assert first is not None and json.loads(first.start)["data"]["cell"] == "A2"
    call = ToolCall(name="move", args={"direction": "north"}, id="s1")
    (reply,) = first.tool_node({"messages": [AIMessage("", tool_calls=[call])]})["messages"]
    assert json.loads(str(reply.content))["data"]["cell"] == "A1"


def test_the_fingerprint_is_stable_and_its_own() -> None:
    from apl.problems import PROBLEMS

    others = {p.prompt_fingerprint() for name, p in PROBLEMS.items() if name != "warehouse"}
    assert len(others) == 5
    assert prompt_fingerprint() == prompt_fingerprint() and prompt_fingerprint() not in others
