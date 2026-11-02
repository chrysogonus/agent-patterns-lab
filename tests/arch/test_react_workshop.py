"""A1 ReAct on the workshop, unchanged (specs/011 FR-021)."""

from langchain_core.messages import BaseMessage, HumanMessage

from tests.arch.orchestrated import recording
from tests.arch.workshop_play import greedy, play, reference


def test_react_crafts_the_goal_with_the_reference_plan() -> None:
    seen: list[list[BaseMessage]] = []
    row = play("react", "W2", 1000, recording(reference("W2", 1000), seen)).row
    assert row.problem == "workshop" and row.status == "completed" and row.success
    assert row.steps == row.optimal_steps and row.wasted == 0 and row.stuck is False
    first = seen[0][1]
    assert isinstance(first, HumanMessage) and '"goal"' in str(first.content)


def test_the_greedy_plan_gets_stuck() -> None:
    row = play("react", "W2", 1000, greedy("W2", 1000)).row
    assert not row.success and row.end_reason == "stuck" and row.stuck is True
    assert row.wasted is not None and row.wasted >= 1
