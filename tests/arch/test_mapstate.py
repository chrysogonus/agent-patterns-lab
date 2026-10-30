"""A2 map state with the scripted model (US3, SC-006, SC-007, FR-023, FR-024)."""

import json
import re
from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage

from apl.arch.mapstate import MAP_INSTRUCTIONS
from apl.dungeon import DEV_SEEDS, LEVELS, generate
from apl.dungeon.frames import build_frames
from apl.dungeon.model import Direction
from apl.kit import BASE_PROMPT
from apl.runner import registry
from apl.runner.episode import EpisodeResult, play_episode
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from apl.viewer.app import Viewer
from tests.arch.oracle import expected_map
from tests.runner.scripted import (
    Strategy,
    bump_wall,
    replay_solution,
    scripted_factory,
    text_answer,
    tool_calls,
)


def _play(level: str, seed: int, strategy: Strategy) -> EpisodeResult:
    key = EpisodeKey("mapstate", level, seed, 1)
    return play_episode(
        key, "test", "dev", Settings(), registry.load("mapstate"), scripted_factory(strategy)
    )


def _recording(
    inner: Strategy, seen: list[list[BaseMessage]], replies: list[AIMessage] | None = None
) -> Strategy:
    def strategy(messages: list[BaseMessage]) -> AIMessage:
        seen.append(list(messages))
        reply = inner(messages)
        if replies is not None:
            replies.append(reply)
        return reply

    return strategy


@pytest.mark.parametrize("level", sorted(LEVELS))
@pytest.mark.parametrize("per_turn", [1, 2])
def test_replays_the_shortest_solution(level: str, per_turn: int) -> None:  # SC-006
    for seed in DEV_SEEDS:
        row = _play(level, seed, replay_solution(generate(level, seed), per_turn)).row
        assert row.success and row.efficiency == 1.0 and row.arch_error is None, seed


@pytest.mark.parametrize(("level", "seed"), [("L2", 1000), ("L3", 1002)])
def test_the_model_sees_the_true_map_each_turn(level: str, seed: int) -> None:  # SC-007
    dungeon = generate(level, seed)
    seen: list[list[BaseMessage]] = []
    _play(level, seed, _recording(replay_solution(dungeon, per_turn=2), seen))
    actions = dungeon.solution.actions
    frames = build_frames(dungeon, actions)
    for call, messages in enumerate(seen):
        done = min(2 * call, len(actions))
        assert messages[-1].content == expected_map(dungeon, frames, done).render(), call


def test_model_input_layout() -> None:  # US3/AC5
    dungeon = generate("L2", 1001)
    seen: list[list[BaseMessage]] = []
    _play("L2", 1001, _recording(replay_solution(dungeon), seen))
    first = seen[0]
    assert [type(m) for m in first] == [SystemMessage, HumanMessage, HumanMessage]
    assert first[0].content == BASE_PROMPT + "\n\n" + MAP_INSTRUCTIONS
    assert '"label"' in str(first[1].content) and str(first[2].content).startswith("Your map")
    for messages in seen[1:]:
        assert [type(m) for m in messages] == [SystemMessage, AIMessage, ToolMessage, HumanMessage]
        assert str(messages[-1].content).startswith("Your map")


def _wander(level: str, seed: int) -> Strategy:
    """Look and bump a wall in turn, forever: a long episode that ends at the budget."""
    layout = generate(level, seed).layout
    wall = next(str(d) for d in Direction if layout.door(layout.start, d) is None)
    count = iter(range(10_000))
    return lambda messages: (
        tool_calls(("look", {})) if next(count) % 2 else bump_wall(wall)(messages)
    )


def test_no_older_turn_is_ever_sent() -> None:  # US3/AC6, FR-023
    seen: list[list[BaseMessage]] = []
    replies: list[AIMessage] = []
    row = _play("L3", 1000, _recording(_wander("L3", 1000), seen, replies)).row
    assert row.budget_hit and len(seen) >= 30
    for call in range(1, len(seen)):
        sent = [m for m in seen[call] if isinstance(m, AIMessage | ToolMessage)]
        # Exactly the previous reply and its result: nothing from any earlier turn.
        assert len(sent) == 2
        assert sent[0].tool_calls == replies[call - 1].tool_calls  # type: ignore[union-attr]
        assert isinstance(sent[1], ToolMessage)
        assert sent[1].tool_call_id == replies[call - 1].tool_calls[0]["id"]


def test_text_answer_ends_the_episode() -> None:  # FR-024
    row = _play("L1", 1000, text_answer()).row
    assert row.end_reason == "stopped" and row.steps == 0 and row.arch_error is None


def test_running_into_the_budget() -> None:  # FR-024
    layout = generate("L1", 1000).layout
    wall = next(str(d) for d in Direction if layout.door(layout.start, d) is None)
    row = _play("L1", 1000, bump_wall(wall)).row
    assert row.budget_hit and row.arch_error is None


def test_a_batch_that_reaches_the_exit_ends_cleanly() -> None:  # FR-024
    dungeon = generate("L1", 1002)
    everything = len(dungeon.solution.actions)
    row = _play("L1", 1002, replay_solution(dungeon, per_turn=everything)).row
    assert row.success and row.llm_calls == 1


def test_instructions_explain_the_map_without_numbers() -> None:  # R15
    assert not re.search(r"\d", MAP_INSTRUCTIONS)
    assert "map" in MAP_INSTRUCTIONS and "unexplored" in MAP_INSTRUCTIONS


def test_the_viewer_shows_the_map_every_turn(tmp_path: Path) -> None:  # US3/AC8
    dungeon = generate("L2", 1003)
    viewer = Viewer(
        Settings(model="ollama:qwen3:8b"),
        results_dir=tmp_path,
        model_factory=scripted_factory(replay_solution(dungeon)),
        architectures={"mapstate": registry.load("mapstate")},
    )
    status, _, body = viewer.start_episode({"arch": "mapstate", "level": "L2", "seed": 1003})
    assert status == 201
    session = viewer.session(json.loads(body)["id"])
    assert session is not None
    list(session.stream())
    thinking = [e["data"] for e in session.events if e["type"] == "thinking"]
    assert len(thinking) > 2
    for event in thinking[1:]:
        assert event["new_input"][-1]["content"].startswith("Your map")
