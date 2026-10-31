"""A9 shared blackboard with scripted answers (specs/004 contracts/orchestrators.md, US2)."""

import pytest
from langchain_core.messages import AIMessage, BaseMessage

from apl.dungeon import generate
from tests.arch.orchestrated import play, recording, roles, text
from tests.runner.scripted import Strategy, walk_solution


def _strategy(level: str, seed: int) -> Strategy:
    walk = walk_solution(generate(level, seed))

    def strategy(messages: list[BaseMessage]) -> AIMessage:
        if "You are scout 0." in text(messages):
            return walk(messages)
        return AIMessage("I will look elsewhere.\nclaim: z9 north")

    return strategy


@pytest.mark.parametrize(("level", "seed"), [("L1", 1000), ("L2", 1001), ("L3", 1002)])
def test_one_scout_walking_the_solution_escapes(level: str, seed: int) -> None:  # 2.1
    result = play("blackboard", level, seed, _strategy(level, seed))
    row = result.row
    assert row.success and row.efficiency == 1.0 and row.orchestrator_calls == 0
    assert {r for r in roles(result)} == {"scout 0", "scout 1", "scout 2", "scout 3"}


def test_scouts_see_every_scout_and_the_claims() -> None:  # 2.5
    seen: list[list[BaseMessage]] = []
    play("blackboard", "L2", 1001, recording(_strategy("L2", 1001), seen))
    walker = [text(m) for m in seen if "You are scout 0." in text(m)]
    assert all(t.count(" is in ") >= 3 for t in walker)  # the other three scouts
    assert "Claims: scout 1 → z9 north; scout 2 → z9 north; scout 3 → z9 north." in walker[-1]


def test_the_same_answers_give_the_same_episode() -> None:
    first, second = (play("blackboard", "L3", 1002, _strategy("L3", 1002)) for _ in range(2))
    assert first.outcome is not None and second.outcome is not None
    assert first.outcome.to_dict() == second.outcome.to_dict()


def test_one_scout_acts_at_a_time_in_turn() -> None:
    seen: list[list[BaseMessage]] = []
    result = play("blackboard", "L2", 1001, recording(_strategy("L2", 1001), seen))
    assert roles(result)[:5] == ["scout 0", "scout 1", "scout 2", "scout 3", "scout 0"]
    # Scout 1 already sees scout 0's first move: the board is updated between turns.
    assert "Other scouts: scout 0 is in " in text(seen[1])
    start = text(seen[0]).split("You are in: ")[1].split(".")[0]
    assert f"scout 0 is in {start} " not in text(seen[1])
