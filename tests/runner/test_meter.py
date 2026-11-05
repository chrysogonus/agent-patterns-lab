"""Counting calls and tokens, the token cap and the end-of-episode guard (research R3)."""

import threading

import pytest
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from apl.dungeon.env import Episode, start_episode
from apl.dungeon.model import Dungeon
from apl.dungeon.results import EndReason
from apl.kit import EpisodeEnded
from apl.runner.meter import Meter
from tests.dungeon.reference import two_open_routes
from tests.runner.scripted import ScriptedChatModel, Usage, text_answer, usage_per_call


def _setup(usage: Usage, cap: int = 1000) -> tuple[Meter, ScriptedChatModel, Episode]:
    episode = start_episode(Dungeon.from_layout(two_open_routes()))
    meter = Meter(episode, token_cap=cap)
    return meter, ScriptedChatModel(strategy=text_answer(), usage=usage, callbacks=[meter]), episode


PROMPT = [SystemMessage("rules"), HumanMessage("start")]


def test_counts_calls_and_tokens() -> None:
    meter, model, _ = _setup(usage_per_call(100, 7))
    model.invoke(PROMPT)
    model.invoke(PROMPT)
    assert (meter.llm_calls, meter.input_tokens, meter.output_tokens) == (2, 200, 14)
    assert not meter.usage_missing and not meter.token_cap_hit


def test_missing_usage_is_flagged() -> None:
    meter, model, _ = _setup(lambda messages: None)
    model.invoke(PROMPT)
    assert meter.usage_missing and meter.llm_calls == 1


def test_token_cap_stops_the_episode() -> None:
    meter, model, episode = _setup(usage_per_call(400, 100), cap=900)
    model.invoke(PROMPT)
    assert not meter.token_cap_hit  # 500 tokens
    model.invoke(PROMPT)
    assert meter.token_cap_hit and episode.end_reason == EndReason.STOPPED  # 1000 > 900
    with pytest.raises(EpisodeEnded):
        model.invoke(PROMPT)
    assert meter.llm_calls == 2


def test_no_call_after_the_end() -> None:
    meter, model, episode = _setup(usage_per_call(1))
    episode.stop()
    with pytest.raises(EpisodeEnded):
        model.invoke(PROMPT)
    assert meter.llm_calls == 0


def test_meter_survives_bind_tools_and_with_config() -> None:
    meter, model, _ = _setup(usage_per_call(1))
    model.bind_tools([]).invoke(PROMPT)
    model.with_config(callbacks=[]).invoke(PROMPT)
    assert meter.llm_calls == 2


def test_transcript_stores_each_message_once() -> None:
    meter, model, _ = _setup(usage_per_call(3, 2))
    reply = model.invoke(PROMPT)
    model.invoke([*PROMPT, reply, HumanMessage("again")])
    data = meter.transcript.to_dict()
    assert [m["type"] for m in data["messages"]] == ["system", "human", "ai", "human", "ai"]
    first, second = data["calls"]
    assert first["input"] == [0, 1] and first["output"] == 2
    assert second["input"] == [0, 1, 2, 3] and second["output"] == 4
    assert first["usage"]["input_tokens"] == 3 and first["latency_s"] >= 0
    assert data["messages"][0]["content"] == "rules"


@pytest.mark.parametrize(
    "metadata",
    [{"done_reason": "length"}, {"finish_reason": "length"}, {"stop_reason": "max_tokens"}],
)
def test_counts_calls_cut_off_by_the_output_limit(metadata: dict[str, str]) -> None:
    episode = start_episode(Dungeon.from_layout(two_open_routes()))
    meter = Meter(episode, token_cap=1000)
    cut = AIMessage("", response_metadata=metadata)
    model = ScriptedChatModel(strategy=lambda messages: cut, callbacks=[meter])
    model.invoke(PROMPT)
    model.invoke(PROMPT)
    assert meter.output_limit_hits == 2


def test_normal_answers_are_not_counted_as_cut_off() -> None:
    meter, model, _ = _setup(usage_per_call(1))
    model.invoke(PROMPT)
    assert meter.output_limit_hits == 0


def test_counts_orchestrator_calls_and_records_roles() -> None:  # specs/004 research R5
    meter, model, _ = _setup(usage_per_call(1))
    model.invoke(PROMPT, config={"metadata": {"role": "orchestrator"}})
    model.bind_tools([]).invoke(PROMPT, config={"metadata": {"role": "scout 2"}})
    model.invoke(PROMPT)
    assert (meter.llm_calls, meter.orchestrator_calls) == (3, 1)
    roles = [call.get("role") for call in meter.transcript.calls]
    assert roles == ["orchestrator", "scout 2", None]
    assert "role" not in meter.transcript.calls[2]  # calls without a role are as before


def test_planning_calls_count_as_orchestrator_calls() -> None:  # specs/006 research R7
    meter, model, _ = _setup(usage_per_call(1))
    for role in ("planner", "executor (subgoal 1)", "replanner", "scout 0"):
        model.invoke(PROMPT, config={"metadata": {"role": role}})
    assert (meter.llm_calls, meter.orchestrator_calls) == (4, 2)
    roles = [call.get("role") for call in meter.transcript.calls]
    assert roles == ["planner", "executor (subgoal 1)", "replanner", "scout 0"]


def test_parallel_calls_are_counted_exactly() -> None:
    meter, model, _ = _setup(usage_per_call(3, 2), cap=10**9)
    prompts = [[SystemMessage("rules"), HumanMessage(f"start {i % 7}")] for i in range(25)]

    def work() -> None:
        for prompt in prompts:
            model.invoke(prompt)

    threads = [threading.Thread(target=work) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert (meter.llm_calls, meter.input_tokens, meter.output_tokens) == (100, 300, 200)
    assert len(meter.transcript.calls) == 100
    keys = [str(m) for m in meter.transcript.messages]
    assert len(keys) == len(set(keys))
