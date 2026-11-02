"""The floor's geometry, shortest paths, the reference and the scripted splits (specs/012 T005)."""

from apl.warehouse.model import Action, cell_name
from apl.warehouse.plans import blind_split, path, reference_calls, replanning_split
from tests.warehouse.floors import p2_floor


def test_the_floor_plan() -> None:
    floor = p2_floor()
    assert (floor.rows, floor.dock, floor.drop) == (5, (0, 1), (8, 1))
    assert cell_name(floor.dock) == "A2" and cell_name(floor.drop) == "I2"
    assert floor.aisle_names == ("aisle 1", "aisle 2", "aisle 3")
    assert all(floor.shelf((x, y)) for y in (1, 3) for x in range(1, 8))
    assert not floor.shelf((0, 1)) and not floor.shelf((8, 3)) and not floor.shelf((4, 2))
    assert floor.corridors((0, 0)) == ("aisle 1", "west corridor")
    assert floor.corridors((0, 1)) == ("west corridor",)
    assert floor.corridors((4, 2)) == ("aisle 2",)
    assert floor.corridors((8, 4)) == ("aisle 3", "east corridor")
    assert len(floor.corridor_cells("aisle 2")) == 9
    assert len(floor.corridor_cells("east corridor")) == 5
    assert floor.neighbor((0, 1), "east") is None  # a shelf
    assert floor.neighbor((0, 1), "west") is None  # the edge
    assert floor.neighbor((0, 1), "north") == (0, 0)


def test_shortest_paths_go_north_then_east_on_ties() -> None:
    floor = p2_floor()
    assert path(floor, floor.dock, (4, 0)) == ["north", "east", "east", "east", "east"]
    assert path(floor, (8, 1), (1, 4)) == ["south"] * 3 + ["west"] * 7
    assert path(floor, (3, 2), (3, 2)) == []


def test_the_reference_clears_the_aisles_north_to_south() -> None:
    floor = p2_floor()
    calls = reference_calls(floor)
    assert floor.reference == tuple(calls) and floor.reference_steps == len(calls) == 46
    tools = [c.tool for c in calls]
    assert tools.count("pick") == 3 and tools.count("drop") == 3 and calls[-1] == Action("drop")
    # Aisle 1's package first, then aisle 3's two, nearest first.
    assert calls[:6] == [
        Action("move", ("north",)),
        *[Action("move", ("east",))] * 4,
        Action("pick"),
    ]
    assert floor.budget == 3 * 46 and floor.reference_is_optimal is False


def test_a_blind_split_idles_a_robot_and_replanning_is_faster() -> None:
    floor = p2_floor()
    blind = blind_split(floor).outcome()
    replanned = replanning_split(floor).outcome()
    assert blind.success and replanned.success
    assert blind.idle_robot_turns > 0
    assert replanned.parallel_turns < blind.parallel_turns
    assert blind.scouts == replanned.scouts == 3
