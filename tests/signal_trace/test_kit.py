"""The signal trace's kit (specs/009 contracts/problems.md, contracts/signal-tools.md)."""

import json

import pytest
from langchain_core.messages import AIMessage

from apl.kit import EpisodeEnded
from apl.kit import prompt_fingerprint as dungeon_fingerprint
from apl.signal_trace import generate, start_episode
from apl.signal_trace.kit import build_kit
from apl.signal_trace.prompt import BASE_PROMPT, TOOL_SCHEMAS, prompt_fingerprint
from apl.survey.prompt import prompt_fingerprint as survey_fingerprint

COST = " Every call costs one step, including failed calls."


def _calls(*calls: tuple[str, object]) -> AIMessage:
    return AIMessage(
        content="",
        tool_calls=[{"name": n, "args": a, "id": f"c{i}"} for i, (n, a) in enumerate(calls)],
    )


def test_the_kit_carries_the_signal_prompt_tools_and_layout() -> None:
    episode = start_episode(generate("T2", 1000))
    kit = build_kit(episode, None)  # type: ignore[arg-type]
    assert kit.problem == "signal" and kit.base_prompt == BASE_PROMPT
    assert [t["function"]["name"] for t in kit.tools] == ["look", "probe", "submit"]
    assert all(t["function"]["description"].endswith(COST) for t in kit.tools)
    assert kit.tools == TOOL_SCHEMAS and kit.tools is not TOOL_SCHEMAS
    start = json.loads(kit.start)
    assert start == {
        "ok": True, "error": None,
        "data": {"segments": 64, "runs": [{"from": "S", "first": 1, "last": 64}]},
    }  # fmt: skip
    assert episode.steps == 0
    assert kit.add_scout() is None
    assert kit.max_attempts == 1 and not kit.restart()


def test_the_prompt_and_schemas_match_the_contract() -> None:
    assert BASE_PROMPT.startswith("You are tracing a fault in a pipe. Water flows from a source S")
    assert "you can submit only once." in BASE_PROMPT
    assert "segment between S and that segment.\n\nUse the tools look, probe and submit." in (
        BASE_PROMPT
    )
    for name in ("probe", "submit"):
        tool = next(t for t in TOOL_SCHEMAS if t["function"]["name"] == name)
        parameters = tool["function"]["parameters"]
        assert parameters["properties"]["segment"]["type"] == "integer"
        assert parameters["required"] == ["segment"]
    look = next(t for t in TOOL_SCHEMAS if t["function"]["name"] == "look")
    assert look["function"]["description"] == (
        "Describe the pipe's layout again: the number of segments and the runs." + COST
    )


def test_the_tool_node_answers_every_call() -> None:
    pipe = generate("T2", 1000)
    episode = start_episode(pipe)
    kit = build_kit(episode, None)  # type: ignore[arg-type]
    reply = _calls(("look", {}), ("probe", {"segment": 32}), ("scan", {}), ("probe", {}))
    results = kit.tool_node({"messages": [reply]})["messages"]
    data = [json.loads(str(r.content)) for r in results]
    assert [d["ok"] for d in data] == [True, True, False, False]
    assert data[1]["data"] == {"segment": 32, "water": pipe.wet(32)}
    assert data[2]["error"]["code"] == "unknown_tool"
    assert data[3]["error"]["code"] == "no_such_segment"
    assert episode.steps == 4


def test_submit_through_the_tool_node_ends_the_episode() -> None:
    pipe = generate("T1", 1000)
    episode = start_episode(pipe)
    kit = build_kit(episode, None)  # type: ignore[arg-type]
    with pytest.raises(EpisodeEnded):
        kit.tool_node({"messages": [_calls(("submit", {"segment": str(pipe.broken)}))]})
    assert episode.outcome().success


def test_the_fingerprint_is_its_own_and_stable() -> None:
    assert prompt_fingerprint() == prompt_fingerprint()
    assert prompt_fingerprint() not in {dungeon_fingerprint(), survey_fingerprint()}
    assert dungeon_fingerprint() == "ff9afb3b9f66"
