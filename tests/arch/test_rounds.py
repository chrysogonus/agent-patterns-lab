"""A8 supervisor in rounds with scripted answers (specs/004 contracts/orchestrators.md, US2)."""

import re

import pytest
from langchain_core.messages import AIMessage, BaseMessage

from apl.arch.rounds import ROUNDS_INSTRUCTIONS
from apl.dungeon import LEVELS, generate
from tests.arch.orchestrated import play, recording, roles, text
from tests.runner.scripted import (
    Strategy,
    bump_wall,
    by_system,
    by_task,
    json_answer,
    walk_solution,
)
from tests.runner.test_run import _wall

ROUND = {
    "tasks": [{"scout": 0, "task": "walk", "steps": 3}, {"scout": 1, "task": "rest", "steps": 2}]
}
MARKER = ROUNDS_INSTRUCTIONS[:60]


def _strategy(level: str, seed: int, orchestrator: Strategy | None = None) -> Strategy:
    scouts = by_task({"walk": walk_solution(generate(level, seed))}, lambda m: AIMessage("Idle."))
    return by_system({MARKER: orchestrator or json_answer(ROUND)}, scouts)


@pytest.mark.parametrize(("level", "seed"), [("L1", 1000), ("L2", 1001), ("L3", 1002)])
def test_rounds_of_three_steps_escape(level: str, seed: int) -> None:  # acceptance 2.1
    seen: list[list[BaseMessage]] = []
    result = play("rounds", level, seed, recording(_strategy(level, seed), seen))
    row = result.row
    assert row.success and row.efficiency == 1.0 and row.arch_error is None
    plans = [m for m in seen if MARKER in str(m[0].content)]
    assert row.orchestrator_calls == len(plans) == roles(result).count("orchestrator") >= 2
    used = [int(re.search(r"Steps used so far: (\d+)", text(m))[1]) for m in plans]  # type: ignore[index]
    assert used == [3 * i for i in range(len(plans))]  # acceptance 2.4
    assert all("Scouts: scout 0 is in " in text(m) for m in plans)


def test_scouts_see_the_merged_map_of_their_round() -> None:
    seen: list[list[BaseMessage]] = []
    play("rounds", "L2", 1001, recording(_strategy("L2", 1001), seen))
    resting = [text(m) for m in seen if "You are scout 1" in text(m)]
    start = re.search(r"Other scouts: scout 0 is in (\S+)", resting[0])
    later = re.search(r"Other scouts: scout 0 is in (\S+)", resting[1])
    assert start and later and start[1] != later[1]  # scout 0 walked in round 1


def test_done_ends_the_episode() -> None:
    row = play("rounds", "L1", 1000, _strategy("L1", 1000, json_answer({"done": True}))).row
    assert row.end_reason == "stopped" and row.steps == 0 and row.orchestrator_calls == 1


def test_unknown_scout_numbers_are_asked_again() -> None:
    seen: list[list[BaseMessage]] = []
    answers = iter([{"tasks": [{"scout": 4, "task": "walk", "steps": 3}]}, {"done": True}])
    orchestrator = recording(lambda m: json_answer(next(answers))(m), seen)
    row = play("rounds", "L1", 1000, _strategy("L1", 1000, orchestrator)).row
    assert row.orchestrator_calls == 2 and row.steps == 0
    assert "scout 4" in text(seen[1])


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_three_invalid_answers_give_up(level: str) -> None:
    row = play("rounds", level, 1000, _strategy(level, 1000, lambda m: AIMessage("?"))).row
    assert row.end_reason == "stopped" and row.orchestrator_calls == 3


def test_the_round_report_names_a_failed_call() -> None:  # contracts/orchestrators.md A8
    seen: list[list[BaseMessage]] = []
    answers = iter([{"tasks": [{"scout": 0, "task": "bump", "steps": 1}]}, {"done": True}])
    orchestrator = recording(lambda m: json_answer(next(answers))(m), seen)
    wall = _wall("L1", 1000)
    scouts = by_task({"bump": bump_wall(wall)}, lambda m: AIMessage("Idle."))
    play("rounds", "L1", 1000, by_system({MARKER: orchestrator}, scouts))
    assert f'scout 0: last failed call: move {{"direction": "{wall}"}}: There is no door' in text(
        seen[1]
    )
