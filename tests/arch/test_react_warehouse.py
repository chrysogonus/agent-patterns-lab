"""A1 ReAct on the warehouse, unchanged (specs/012 FR-021)."""

from langchain_core.messages import BaseMessage, HumanMessage

from tests.arch.orchestrated import recording
from tests.arch.warehouse_play import play, reference


def test_react_delivers_every_package_with_the_reference() -> None:
    seen: list[list[BaseMessage]] = []
    row = play("react", "P2", 1000, recording(reference("P2", 1000), seen)).row
    assert row.problem == "warehouse" and row.status == "completed" and row.success
    assert row.steps == row.optimal_steps and row.delivered == row.packages == 3
    assert row.end_reason == "delivered" and row.idle_robot_turns == 0
    first = seen[0][1]
    assert isinstance(first, HumanMessage) and '"floor"' in str(first.content)
