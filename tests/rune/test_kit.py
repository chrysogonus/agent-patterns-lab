"""The rune floor's kit (specs/010 contracts/problems.md, contracts/rune-tools.md)."""

import json

import pytest
from langchain_core.messages import AIMessage

from apl.kit import EpisodeEnded
from apl.kit import prompt_fingerprint as dungeon_fingerprint
from apl.rune import generate, start_episode
from apl.rune.kit import build_kit
from apl.rune.prompt import BASE_PROMPT, TOOL_SCHEMAS, prompt_fingerprint
from apl.signal_trace.prompt import prompt_fingerprint as signal_fingerprint
from apl.survey.prompt import prompt_fingerprint as survey_fingerprint
from tests.rune.agents import reference_moves

COST = " Every call costs one step, including failed calls."


def _calls(*calls: tuple[str, object]) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": n, "args": a, "id": f"c{i}"} for i, (n, a) in enumerate(calls)],
    )


def test_the_kit_carries_the_rune_prompt_tools_and_floor() -> None:
    episode = start_episode(generate("R1", 1000))
    kit = build_kit(episode, None)  # type: ignore[arg-type]
    assert kit.problem == "rune" and kit.base_prompt == BASE_PROMPT
    assert [t["function"]["name"] for t in kit.tools] == ["look", "move"]
    assert all(t["function"]["description"].endswith(COST) for t in kit.tools)
    assert kit.tools == TOOL_SCHEMAS and kit.tools is not TOOL_SCHEMAS
    start = json.loads(kit.start)
    assert start["ok"] and start["data"]["start"] == "A3" and start["data"]["goal"] == "G3"
    assert len(start["data"]["floor"]) == 5 and len(start["data"]["floor"][0]) == 7
    assert episode.steps == 0
    assert kit.add_scout() is None
    assert kit.max_attempts == 1 and not kit.restart()


def test_the_prompt_and_schemas_match_the_contract() -> None:
    assert BASE_PROMPT.startswith("You are crossing a rune floor: a grid of colored tiles.")
    assert "A hidden rule decides which tiles are safe to step on." in BASE_PROMPT
    assert "The rule never changes during the episode.\n\nUse the tools look and move." in (
        BASE_PROMPT
    )
    move = next(t for t in TOOL_SCHEMAS if t["function"]["name"] == "move")
    parameters = move["function"]["parameters"]
    assert parameters["properties"]["direction"]["enum"] == ["north", "east", "south", "west"]
    assert parameters["required"] == ["direction"]
    assert move["function"]["description"] == (
        "Step onto the neighboring tile in a direction. Errors: invalid_direction, edge." + COST
    )
    look = next(t for t in TOOL_SCHEMAS if t["function"]["name"] == "look")
    assert look["function"]["description"] == (
        "Describe the floor again: its size, every tile's color, the start, the goal and the cell "
        "you are on." + COST
    )


def test_the_tool_node_answers_every_call() -> None:
    episode = start_episode(generate("R1", 1000))
    kit = build_kit(episode, None)  # type: ignore[arg-type]
    reply = _calls(("look", {}), ("move", {"direction": "west"}), ("jump", {}), ("move", {}))
    results = kit.tool_node({"messages": [reply]})["messages"]
    data = [json.loads(str(r.content)) for r in results]
    assert [d["ok"] for d in data] == [True, False, False, False]
    assert data[1]["error"]["code"] == "edge"
    assert data[2]["error"]["code"] == "unknown_tool"
    assert data[3]["error"]["code"] == "invalid_direction"
    assert episode.steps == 4


def test_reaching_the_goal_through_the_tool_node_ends_the_episode() -> None:
    floor = generate("R1", 1000)
    episode = start_episode(floor)
    kit = build_kit(episode, None)  # type: ignore[arg-type]
    moves = [("move", {"direction": d}) for d in reference_moves(floor)]
    with pytest.raises(EpisodeEnded):
        kit.tool_node({"messages": [_calls(*moves)]})
    assert episode.outcome().success


def test_the_fingerprint_is_its_own_and_stable() -> None:
    assert prompt_fingerprint() == prompt_fingerprint()
    assert prompt_fingerprint() not in {
        dungeon_fingerprint(), survey_fingerprint(), signal_fingerprint(),
    }  # fmt: skip
