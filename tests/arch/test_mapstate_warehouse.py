"""A2 map state on the warehouse (specs/012 FR-022)."""

from langchain_core.messages import BaseMessage

from apl.arch.mapstate import FLOOR_MAP_INSTRUCTIONS
from apl.warehouse.prompt import BASE_PROMPT
from tests.arch.orchestrated import recording
from tests.arch.warehouse_play import play, reference


def test_mapstate_delivers_with_the_floor_map() -> None:
    seen: list[list[BaseMessage]] = []
    row = play("mapstate", "P2", 1000, recording(reference("P2", 1000), seen)).row
    assert row.success and row.steps == row.optimal_steps and row.delivered == 3
    for messages in seen:
        assert str(messages[0].content) == f"{BASE_PROMPT}\n\n{FLOOR_MAP_INSTRUCTIONS}"
        assert str(messages[-1].content).startswith("Your map (built from your tool results")
    assert len(seen[3]) == 4  # system, its last reply, that reply's result, the map
