"""The workshop's kit (specs/011 contracts/problems.md, contracts/workshop-tools.md)."""

import json

import pytest
from langchain_core.messages import AIMessage

from apl.kit import EpisodeEnded
from apl.kit import prompt_fingerprint as dungeon_fingerprint
from apl.rune.prompt import prompt_fingerprint as rune_fingerprint
from apl.signal_trace.prompt import prompt_fingerprint as signal_fingerprint
from apl.survey.prompt import prompt_fingerprint as survey_fingerprint
from apl.workshop import generate, start_episode
from apl.workshop.kit import build_kit
from apl.workshop.plans import reference_calls
from apl.workshop.prompt import BASE_PROMPT, TOOL_SCHEMAS, prompt_fingerprint

COST = " Every call costs one step, including failed calls."


def _calls(*calls: tuple[str, object]) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": n, "args": a, "id": f"c{i}"} for i, (n, a) in enumerate(calls)],
    )


def test_the_kit_carries_the_workshop_prompt_tools_and_start() -> None:
    w = generate("W2", 1000)
    episode = start_episode(w)
    kit = build_kit(episode, None)  # type: ignore[arg-type]
    assert kit.problem == "workshop" and kit.base_prompt == BASE_PROMPT
    assert [t["function"]["name"] for t in kit.tools] == ["look", "inspect", "gather", "craft"]
    assert all(t["function"]["description"].endswith(COST) for t in kit.tools)
    assert kit.tools == TOOL_SCHEMAS and kit.tools is not TOOL_SCHEMAS
    start = json.loads(kit.start)
    assert start["data"] == {"goal": w.goal, "stock": dict(w.stock), "inventory": {}}
    assert episode.steps == 0 and kit.add_scout() is None
    assert kit.max_attempts == 1 and not kit.restart()


def test_the_prompt_and_schemas_match_the_contract() -> None:
    assert BASE_PROMPT.startswith("You are in a workshop and must craft one goal item.")
    assert "You do not know any recipe until you inspect the item." in BASE_PROMPT
    assert "Use the tools look, inspect, gather and craft." in BASE_PROMPT
    craft = next(t for t in TOOL_SCHEMAS if t["function"]["name"] == "craft")
    parameters = craft["function"]["parameters"]
    assert parameters["properties"]["item"]["type"] == "string"
    assert parameters["properties"]["recipe"]["type"] == "integer"
    assert parameters["required"] == ["item", "recipe"]
    gather = next(t for t in TOOL_SCHEMAS if t["function"]["name"] == "gather")
    assert gather["function"]["description"] == (
        "Take one unit of a raw material from the stock. Errors: unknown_item, not_raw, "
        "out_of_stock." + COST
    )


def test_the_tool_node_answers_every_call() -> None:
    w = generate("W1", 1000)
    episode = start_episode(w)
    kit = build_kit(episode, None)  # type: ignore[arg-type]
    reply = _calls(
        ("look", {}), ("inspect", {"item": w.goal}), ("gather", {"item": w.goal}), ("build", {}),
        ("craft", {}),
    )  # fmt: skip
    results = kit.tool_node({"messages": [reply]})["messages"]
    data = [json.loads(str(r.content)) for r in results]
    assert [d["ok"] for d in data] == [True, True, False, False, False]
    assert data[2]["error"]["code"] == "not_raw"
    assert data[3]["error"]["code"] == "unknown_tool"
    assert data[4]["error"]["code"] == "unknown_item"
    assert episode.steps == 5


def test_crafting_the_goal_through_the_tool_node_ends_the_episode() -> None:
    w = generate("W2", 1000)
    episode = start_episode(w)
    kit = build_kit(episode, None)  # type: ignore[arg-type]
    with pytest.raises(EpisodeEnded):
        kit.tool_node({"messages": [_calls(*reference_calls(w))]})
    assert episode.outcome().success


def test_the_fingerprint_is_its_own_and_stable() -> None:
    assert prompt_fingerprint() == prompt_fingerprint()
    others = {dungeon_fingerprint(), survey_fingerprint(), signal_fingerprint(), rune_fingerprint()}
    assert prompt_fingerprint() not in others
