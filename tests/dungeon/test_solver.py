"""The solver against hand-worked answers (SC-008)."""

import pytest

from apl.dungeon import solve
from apl.dungeon.model import Layout
from tests.dungeon.reference import REFERENCE, locked_shortcut_wins, open_route_wins


@pytest.mark.parametrize(("name", "layout", "optimum"), REFERENCE, ids=[r[0] for r in REFERENCE])
def test_reference_answers(name: str, layout: Layout, optimum: int | None) -> None:
    solution = solve(layout)
    if optimum is None:
        assert solution is None
    else:
        assert solution is not None and solution.length == optimum


def test_locked_route_wins_when_it_is_shorter() -> None:
    solution = solve(locked_shortcut_wins())
    assert solution is not None and any(a.tool == "use" for a in solution.actions)


def test_open_route_wins_when_the_key_is_far() -> None:
    solution = solve(open_route_wins())
    assert solution is not None and all(a.tool == "move" for a in solution.actions)


def test_solutions_are_reproducible() -> None:
    for _, layout, _ in REFERENCE:
        assert solve(layout) == solve(layout)
