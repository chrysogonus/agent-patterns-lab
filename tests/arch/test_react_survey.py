"""A1 ReAct on the survey field, unchanged (specs/005 FR-026)."""

import itertools

from langchain_core.messages import AIMessage, BaseMessage

from apl.runner import registry
from apl.runner.episode import EpisodeResult, play_episode
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from apl.survey import generate
from tests.runner.scripted import Strategy, scripted_factory, tool_calls


def walk_and_submit(total: int) -> Strategy:
    walk = generate("S1", 1000).walk
    turn = itertools.count()

    def strategy(messages: list[BaseMessage]) -> AIMessage:
        n = next(turn)
        if n < len(walk):
            return tool_calls(("move", {"direction": walk[n]}))
        return tool_calls(("submit", {"total": total}))

    return strategy


def _play(strategy: Strategy) -> EpisodeResult:
    key = EpisodeKey("react", "S1", 1000, 1)
    return play_episode(
        key, "test", "dev", Settings(), registry.load("react"), scripted_factory(strategy),
        problem="survey",
    )  # fmt: skip


def test_react_walks_the_field_and_submits_the_right_total() -> None:
    row = _play(walk_and_submit(6)).row
    assert row.problem == "survey" and row.status == "completed" and row.success
    assert row.steps == 36 and row.optimal_steps == 36 and row.efficiency == 1.0
    assert row.parallel_turns == 36 and row.cells_seen == row.cells == 36
    assert row.submitted_total == row.true_total == 6 and row.reference_is_optimal


def test_a_wrong_total_fails() -> None:
    row = _play(walk_and_submit(5)).row
    assert not row.success and row.end_reason == "submitted" and row.submitted_total == 5
