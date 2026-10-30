"""A1 ReAct with the scripted model (User Story 4, SC-008). Skips until react.py exists."""

import pytest
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from apl.dungeon import generate
from apl.dungeon.model import Direction
from apl.kit import BASE_PROMPT
from apl.runner import registry
from apl.runner.episode import EpisodeResult, play_episode
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from tests.runner.scripted import (
    Strategy,
    bump_wall,
    replay_solution,
    scripted_factory,
    text_answer,
)

pytestmark = pytest.mark.skipif(
    not registry.is_written("react"), reason="src/apl/arch/react.py is not written yet"
)


def _play(level: str, strategy: Strategy) -> EpisodeResult:
    play = registry.load("react")
    key = EpisodeKey("react", level, 1000, 1)
    return play_episode(key, "test", "dev", Settings(), play, scripted_factory(strategy))


@pytest.mark.parametrize("level", ["L1", "L2", "L3"])
def test_replays_the_shortest_solution(level: str) -> None:
    row = _play(level, replay_solution(generate(level, 1000))).row
    assert row.success and row.efficiency == 1.0 and row.arch_error is None


def test_text_answer_ends_the_episode() -> None:
    row = _play("L1", text_answer()).row
    assert row.end_reason == "stopped" and row.steps == 0 and row.arch_error is None


def test_runs_until_the_budget() -> None:
    layout = generate("L1", 1000).layout
    wall = next(str(d) for d in Direction if layout.door(layout.start, d) is None)
    row = _play("L1", bump_wall(wall)).row
    # More steps than LangGraph's default recursion limit allows: kit.recursion_limit is used.
    assert row.budget_hit and row.arch_error is None


def test_starts_from_the_base_prompt_and_the_start_room() -> None:
    seen: list[list[BaseMessage]] = []

    def strategy(messages: list[BaseMessage]) -> object:
        seen.append(messages)
        return text_answer()(messages)

    _play("L1", strategy)  # type: ignore[arg-type]
    first = seen[0]
    assert isinstance(first[0], SystemMessage) and first[0].content == BASE_PROMPT
    human = next(m for m in first if isinstance(m, HumanMessage))
    assert '"ok": true' in str(human.content) and '"label"' in str(human.content)
