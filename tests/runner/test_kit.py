"""The architecture interface (contracts/kit.md, research R4–R6)."""

import json
import threading
from dataclasses import fields
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage, ToolMessage

import apl.kit
from apl.dungeon import generate
from apl.dungeon.env import Episode, start_episode
from apl.dungeon.model import Dungeon
from apl.dungeon.results import ErrorCode
from apl.dungeon.tools import AgentTools
from apl.kit import BASE_PROMPT, TOOL_SCHEMAS, EpisodeEnded, Kit, build_kit, prompt_fingerprint
from tests.dungeon.reference import locked_shortcut_wins
from tests.runner.scripted import ScriptedChatModel, text_answer, tool_calls


def _kit() -> tuple[Kit, Episode]:
    episode = start_episode(Dungeon.from_layout(locked_shortcut_wins()))
    return build_kit(episode, ScriptedChatModel(strategy=text_answer())), episode


def _run(kit: Kit, *calls: tuple[str, dict[str, object]]) -> list[ToolMessage]:
    return kit.tool_node({"messages": [tool_calls(*calls)]})["messages"]


def _code(message: ToolMessage) -> str | None:
    error = json.loads(str(message.content))["error"]
    return error["code"] if error else None


def test_tool_schemas() -> None:
    functions = {t["function"]["name"]: t["function"] for t in TOOL_SCHEMAS}
    assert set(functions) == {"look", "move", "take", "use"}
    params = {name: set(f["parameters"]["properties"]) for name, f in functions.items()}
    assert params == {
        "look": set(),
        "move": {"direction"},
        "take": {"item"},
        "use": {"item", "direction"},
    }
    direction = functions["move"]["parameters"]["properties"]["direction"]
    assert direction["enum"] == ["north", "east", "south", "west"]
    assert all("step" in f["description"] for f in functions.values())


def test_base_prompt_reveals_no_numbers() -> None:
    assert not any(c.isdigit() for c in BASE_PROMPT)
    for word in ("exit", "step", "key", "JSON"):
        assert word in BASE_PROMPT


def test_prompt_fingerprint(monkeypatch: pytest.MonkeyPatch) -> None:
    fingerprint = prompt_fingerprint()
    assert len(fingerprint) == 12 and int(fingerprint, 16) >= 0
    assert prompt_fingerprint() == fingerprint
    changed = json.loads(json.dumps(TOOL_SCHEMAS))
    changed[0]["function"]["description"] += " Changed."
    monkeypatch.setattr(apl.kit, "TOOL_SCHEMAS", changed)
    assert prompt_fingerprint() != fingerprint


def test_calls_run_in_order() -> None:
    kit, episode = _kit()
    move, take = _run(kit, ("move", {"direction": "east"}), ("take", {"item": "red key"}))
    assert move.status == "success" and take.status == "success"
    assert json.loads(str(take.content))["data"] == {"inventory": ["red key"]}
    assert episode.steps == 2
    assert move.name == "move" and move.tool_call_id != take.tool_call_id


def test_failed_result_is_an_error_message() -> None:
    kit, _ = _kit()
    (message,) = _run(kit, ("move", {"direction": "north"}))
    assert message.status == "error" and _code(message) == ErrorCode.NO_DOOR


@pytest.mark.parametrize(
    ("call", "code"),
    [
        (("move", {}), ErrorCode.INVALID_DIRECTION),
        (("move", {"direction": 3}), ErrorCode.INVALID_DIRECTION),
        (("take", {}), ErrorCode.NO_SUCH_ITEM),
        (("use", {"item": "red key"}), ErrorCode.INVALID_DIRECTION),
        (("open", {"door": "north"}), ErrorCode.UNKNOWN_TOOL),
    ],
)
def test_invalid_calls_cost_a_step(call: tuple[str, dict[str, object]], code: ErrorCode) -> None:
    kit, episode = _kit()
    (message,) = _run(kit, call)
    assert _code(message) == code
    assert episode.steps == 1 and episode.invalid_actions == 1


def test_non_string_and_extra_arguments() -> None:
    kit, episode = _kit()
    _run(kit, ("move", {"direction": 3}), ("look", {"verbose": True}))
    assert episode.log[0].action.args == ("3",)
    assert episode.log[1].result.ok


def test_unparsable_tool_calls_are_answered() -> None:
    kit, episode = _kit()
    message = AIMessage(
        content="",
        invalid_tool_calls=[{"name": "move", "args": "{bad", "id": "call_x", "error": "json"}],
    )
    (reply,) = kit.tool_node({"messages": [message]})["messages"]
    assert reply.tool_call_id == "call_x" and _code(reply) == ErrorCode.INVALID_DIRECTION
    assert episode.steps == 1


def test_episode_end_stops_the_turn() -> None:
    kit, episode = _kit()
    _run(kit, ("move", {"direction": "east"}), ("take", {"item": "red key"}))
    with pytest.raises(EpisodeEnded):
        _run(
            kit,
            ("use", {"item": "red key", "direction": "east"}),
            ("move", {"direction": "east"}),
            ("look", {}),
        )
    assert episode.end_reason == "exit"
    assert len(episode.log) == 4  # the look after the exit was not carried out


def test_already_ended_episode_runs_nothing() -> None:
    kit, episode = _kit()
    episode.stop()
    with pytest.raises(EpisodeEnded):
        _run(kit, ("look", {}))
    assert episode.log == []


def test_object_state_is_accepted() -> None:
    kit, episode = _kit()
    kit.tool_node(SimpleNamespace(messages=[tool_calls(("look", {}))]))
    assert episode.steps == 1


def test_kit_contents() -> None:
    kit, episode = _kit()
    assert kit.start == json.dumps(AgentTools(episode).start.to_dict())
    assert kit.recursion_limit == 1000
    assert kit.base_prompt == BASE_PROMPT and kit.tools == TOOL_SCHEMAS
    kit.tools[0]["function"]["description"] = "tampered"
    assert TOOL_SCHEMAS[0]["function"]["description"] != "tampered"
    for field in fields(kit):
        assert not isinstance(getattr(kit, field.name), Episode | AgentTools)


def test_add_scout() -> None:  # specs/004 contracts/scouts.md
    kit, episode = _kit()
    scouts = [kit.add_scout() for _ in range(4)]
    assert [s.number if s else None for s in scouts] == [1, 2, 3, None]
    assert episode.steps == 0 and episode.log == []
    scout = scouts[0]
    assert scout is not None
    assert json.loads(scout.start) == AgentTools(episode).start.to_dict()
    scout.tool_node({"messages": [tool_calls(("move", {"direction": "east"}))]})
    assert episode.describe(scout=1).label == "a3" and episode.position == (0, 0)
    assert episode.log[-1].scout == 1


def test_parallel_tool_calls_are_applied_one_at_a_time() -> None:
    episode = start_episode(generate("L3", 1000))  # budget 108, above the 100 calls
    kit = build_kit(episode, ScriptedChatModel(strategy=text_answer()))
    scout = kit.add_scout()
    assert scout is not None and episode.dungeon.budget > 100

    def work(node: apl.kit.ToolNode) -> None:
        for _ in range(50):
            node({"messages": [tool_calls(("look", {}))]})

    threads = [threading.Thread(target=work, args=(n,)) for n in (kit.tool_node, scout.tool_node)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert episode.steps == 100 and [e.step for e in episode.log] == list(range(1, 101))
    assert sorted(e.scout for e in episode.log) == [0] * 50 + [1] * 50
