import dataclasses

import pytest

from apl.dungeon.model import LEVELS, Action, Direction, Dungeon, Edge, Layout
from apl.dungeon.solver import solve
from tests.dungeon.reference import (
    SHORTCUT,
    grid_labels,
    key_behind_own_door,
    locked_shortcut_wins,
    two_open_routes,
)


def test_levels_match_fr_010() -> None:
    table = {n: (lv.size, lv.locks, lv.extra_doors, lv.min_dead_ends) for n, lv in LEVELS.items()}
    assert table == {"L1": (3, 0, 1, 0), "L2": (4, 1, 2, 0), "L3": (5, 2, 3, 2)}


def test_edge_is_unordered_and_needs_neighbors() -> None:
    assert Edge((1, 0), (0, 0)) == Edge((0, 0), (1, 0))
    assert Edge((1, 0), (0, 0)).a == (0, 0)
    with pytest.raises(ValueError):
        Edge((0, 0), (1, 1))
    with pytest.raises(ValueError):
        Edge((0, 0), (2, 0))


def test_direction_order_and_opposites() -> None:
    assert list(Direction) == ["north", "east", "south", "west"]
    assert all(d.opposite.opposite == d for d in Direction)


def _broken(**changes: object) -> Layout:
    return dataclasses.replace(locked_shortcut_wins(), **changes)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "layout",
    [
        _broken(size=1),
        _broken(doors=frozenset({Edge((2, 0), (3, 0))})),
        _broken(locks={Edge((0, 0), (1, 0)): "red", SHORTCUT: "blue"}),
        _broken(locks={SHORTCUT: "red", Edge((0, 0), (1, 0)): "red"}),
        _broken(keys={}),
        _broken(keys={"red": (5, 5)}),
        _broken(start=(3, 3)),
        _broken(exit=(0, 0)),
        _broken(labels={(0, 0): "a2"}),
        _broken(labels=dict.fromkeys(grid_labels(3), "a2")),
    ],
)
def test_validate_rejects_each_rule(layout: Layout) -> None:
    with pytest.raises(ValueError):
        layout.validate()


def test_reference_layouts_are_valid() -> None:
    two_open_routes().validate()
    locked_shortcut_wins().validate()


def test_action_arity() -> None:
    assert str(Action("use", ("red key", "north"))) == "use red key north"
    with pytest.raises(ValueError):
        Action("move")
    with pytest.raises(ValueError):
        Action.parse({"tool": "jump", "args": []})


def test_budget_and_from_layout() -> None:
    dungeon = Dungeon.from_layout(two_open_routes())
    assert dungeon.level is None and dungeon.seed is None
    assert dungeon.solution.length == 2
    assert dungeon.budget == 12
    with pytest.raises(ValueError, match="unsolvable"):
        Dungeon.from_layout(key_behind_own_door())


def test_solver_smoke() -> None:
    solution = solve(two_open_routes())
    assert solution is not None and solution.length == 2
