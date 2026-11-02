"""A1 ReAct on the rune floor, unchanged (specs/010 FR-021)."""

from langchain_core.messages import BaseMessage, HumanMessage

from apl.rune import generate
from apl.runner import registry
from apl.runner.episode import EpisodeResult, play_episode
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from tests.rune.agents import reference_moves
from tests.runner.scripted import Strategy, play_calls, scripted_factory


def _play(strategy: Strategy, level: str = "R1") -> EpisodeResult:
    key = EpisodeKey("react", level, 1000, 1)
    return play_episode(
        key, "test", "dev", Settings(), registry.load("react"), scripted_factory(strategy),
        problem="rune",
    )  # fmt: skip


def test_react_crosses_on_the_reference_path() -> None:
    seen: list[list[BaseMessage]] = []
    moves = [("move", {"direction": d}) for d in reference_moves(generate("R1", 1000))]
    inner = play_calls(moves)

    def strategy(messages: list[BaseMessage]):  # type: ignore[no-untyped-def]
        seen.append(list(messages))
        return inner(messages)

    row = _play(strategy).row
    assert row.problem == "rune" and row.status == "completed" and row.success
    assert row.steps == row.optimal_steps and row.traps == 0
    first = seen[0][1]
    assert isinstance(first, HumanMessage) and '"floor"' in str(first.content)


def test_the_straight_row_traps_and_runs_out() -> None:
    floor = generate("R1", 1000)
    row = _play(play_calls([("move", {"direction": "east"})] * floor.budget)).row
    assert not row.success and row.budget_hit and row.traps is not None and row.traps >= 1
