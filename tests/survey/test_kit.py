"""The survey field's kit (specs/005 contracts/problems.md, contracts/survey-tools.md)."""

import json

from langchain_core.messages import AIMessage

from apl.kit import prompt_fingerprint as dungeon_fingerprint
from apl.survey import generate, start_episode
from apl.survey.kit import build_kit
from apl.survey.prompt import BASE_PROMPT, TOOL_SCHEMAS, prompt_fingerprint

COST = " Every call costs one step, including failed calls."


def _calls(*calls: tuple[str, object]) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": n, "args": a, "id": f"c{i}"} for i, (n, a) in enumerate(calls)],
    )


def test_the_kit_carries_the_survey_prompt_and_tools() -> None:
    episode = start_episode(generate("S1", 1000))
    kit = build_kit(episode, None)  # type: ignore[arg-type]
    assert kit.problem == "survey" and kit.base_prompt == BASE_PROMPT
    assert [t["function"]["name"] for t in kit.tools] == ["look", "move", "submit"]
    assert all(t["function"]["description"].endswith(COST) for t in kit.tools)
    assert kit.tools == TOOL_SCHEMAS and kit.tools is not TOOL_SCHEMAS
    start = json.loads(kit.start)
    assert start["ok"] and start["data"]["cell"] == "A1" and episode.steps == 0


def test_the_base_prompt_matches_the_contract() -> None:
    assert BASE_PROMPT.startswith("You are surveying a field: a grid of square cells.")
    assert "you can submit only once." in BASE_PROMPT
    assert "A1 is the\nnorth-west corner" not in BASE_PROMPT  # one paragraph per line group
    submit = next(t for t in TOOL_SCHEMAS if t["function"]["name"] == "submit")
    assert submit["function"]["parameters"]["properties"]["total"]["type"] == "integer"


def test_the_tool_node_answers_every_call() -> None:
    episode = start_episode(generate("S1", 1000))
    kit = build_kit(episode, None)  # type: ignore[arg-type]
    reply = _calls(("look", {}), ("move", {"direction": "east"}), ("scan", {}), ("move", {}))
    results = kit.tool_node({"messages": [reply]})["messages"]
    data = [json.loads(str(r.content)) for r in results]
    assert [d["ok"] for d in data] == [True, True, False, False]
    assert data[1]["data"]["cell"] == "B1"
    assert (
        data[2]["error"]["code"] == "unknown_tool"
        and data[3]["error"]["code"] == "invalid_direction"
    )
    assert episode.steps == 4


def test_submit_through_the_tool_node_ends_the_episode() -> None:
    from apl.kit import EpisodeEnded

    episode = start_episode(generate("S1", 1000))
    kit = build_kit(episode, None)  # type: ignore[arg-type]
    try:
        kit.tool_node({"messages": [_calls(("submit", {"total": 6}))]})
    except EpisodeEnded:
        pass
    assert episode.outcome().success


def test_the_fingerprint_is_the_surveys_own() -> None:
    assert prompt_fingerprint() == prompt_fingerprint() != dungeon_fingerprint()
    assert len(prompt_fingerprint()) == 12
