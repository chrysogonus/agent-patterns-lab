"""A7 fan-out once with scripted answers (specs/004 contracts/orchestrators.md, US2)."""

import pytest
from langchain_core.messages import AIMessage, BaseMessage

from apl.arch.fanout import FANOUT_INSTRUCTIONS
from apl.dungeon import DEV_SEEDS, LEVELS, generate
from tests.arch.orchestrated import play, recording, roles, text
from tests.runner.scripted import Strategy, by_system, by_task, json_answer, walk_solution

PLAN = {"scouts": [{"task": "walk", "steps": 500}] + [{"task": "rest", "steps": 5}] * 2}
MARKER = FANOUT_INSTRUCTIONS[:60]


def _strategy(level: str, seed: int, orchestrator: Strategy | None = None) -> Strategy:
    scouts = by_task({"walk": walk_solution(generate(level, seed))}, lambda m: AIMessage("Idle."))
    return by_system({MARKER: orchestrator or json_answer(PLAN)}, scouts)


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_one_scout_walking_the_solution_escapes(level: str) -> None:  # acceptance 2.1
    for seed in DEV_SEEDS:
        result = play("fanout", level, seed, _strategy(level, seed))
        row = result.row
        assert row.success and row.efficiency == 1.0 and row.arch_error is None, seed
        assert row.orchestrator_calls == 1 and roles(result).count("orchestrator") == 1


def test_scouts_see_only_their_own_map() -> None:  # acceptance 2.3
    seen: list[list[BaseMessage]] = []
    play("fanout", "L2", 1001, recording(_strategy("L2", 1001), seen))
    scouts = [m for m in seen if MARKER not in str(m[0].content)]
    assert len({text(m).split("You are scout ")[1][0] for m in scouts}) == 3
    assert all("Other scouts" not in text(m) for m in scouts)


def test_invalid_plans_are_asked_again_then_give_up() -> None:
    answers = iter(["no plan", '{"scouts": []}', '{"scouts": [{"task": "walk", "steps": 0}]}'])
    result = play("fanout", "L1", 1000, _strategy("L1", 1000, lambda m: AIMessage(next(answers))))
    row = result.row
    assert row.end_reason == "stopped" and row.steps == 0 and row.orchestrator_calls == 3


def test_five_scouts_is_invalid_and_a_retry_costs_no_step() -> None:
    seen: list[list[BaseMessage]] = []
    answers = iter([{"scouts": [{"task": "walk", "steps": 5}] * 5}, PLAN])
    orchestrator = recording(lambda m: json_answer(next(answers))(m), seen)
    row = play("fanout", "L1", 1000, _strategy("L1", 1000, orchestrator)).row
    assert row.success and row.efficiency == 1.0 and row.orchestrator_calls == 2
    assert "at most 4" in text(seen[1])


def test_the_same_answers_give_the_same_episode() -> None:
    first, second = (play("fanout", "L3", 1002, _strategy("L3", 1002)) for _ in range(2))
    assert first.outcome is not None and second.outcome is not None
    assert first.outcome.to_dict() == second.outcome.to_dict()
