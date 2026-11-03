"""Generated rune floors (specs/010 research R4, R5; SC-002)."""

import pytest

from apl.rune import DEV_SEEDS, LEVELS, TEST_SEEDS, generate
from apl.rune.model import COLORS
from apl.rune.rules import reference_path

SEEDS = [*DEV_SEEDS, *TEST_SEEDS]
SIZES = {"R0": (7, 5), "R1": (7, 5), "R2": (9, 7), "R3": (9, 7)}
BOUND = {"R0": 12, "R1": 12, "R2": 16, "R3": 16}


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_every_floor_is_valid(level: str) -> None:
    for seed in SEEDS:
        floor = generate(level, seed)
        assert floor == generate(level, seed)
        assert (floor.columns, floor.rows) == SIZES[level]
        assert floor.start == (0, floor.rows // 2)
        assert floor.goal == (floor.columns - 1, floor.rows // 2)
        cells = {(x, y) for x in range(floor.columns) for y in range(floor.rows)}
        assert set(floor.colors) == cells - {floor.start, floor.goal}
        assert set(floor.colors.values()) <= set(COLORS)
        path = reference_path(floor)
        assert path is not None and len(path) - 1 == floor.reference
        assert floor.columns - 1 < floor.reference <= BOUND[level]  # the straight row traps
        assert floor.budget == 4 * floor.reference
        assert floor.reference_steps == floor.reference and floor.reference_is_optimal


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_each_level_has_its_rule(level: str) -> None:
    for seed in SEEDS:
        rule = generate(level, seed).rule
        if level == "R0":
            assert rule.kind == "none" and rule.colors == () and rule.traps
        elif level == "R1":
            assert rule.kind == "cycle" and len(rule.colors) == 3 == len(set(rule.colors))
            assert not rule.traps
        elif level == "R2":
            a, b, c, d = rule.colors
            assert rule.kind == "cycle" and a == b and len({a, c, d}) == 3
        else:
            assert rule.kind == "rows" and len(rule.colors) == 2 == len(set(rule.colors))


def test_seeds_give_different_floors() -> None:
    assert len({tuple(sorted(generate("R1", s).colors.items())) for s in SEEDS}) == len(SEEDS)


def test_an_unknown_level_is_refused() -> None:
    with pytest.raises(ValueError, match="R0, R1, R2, R3"):
        generate("R9", 1000)
