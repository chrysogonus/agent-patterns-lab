"""Generated survey fields (specs/005 SC-002, research R5, R9)."""

from collections import deque

import pytest

from apl.survey import DEV_SEEDS, LEVELS, TEST_SEEDS, generate
from apl.survey.model import Cell, Field

SEEDS = [*DEV_SEEDS, *TEST_SEEDS]


def _reachable(field: Field) -> set[Cell]:
    seen, queue = {field.start}, deque([field.start])
    while queue:
        cell = queue.popleft()
        for direction in field.exits(cell):
            other = field.neighbor(cell, direction)
            assert other is not None
            if other not in seen:
                seen.add(other)
                queue.append(other)
    return seen


def test_levels() -> None:
    assert sorted(LEVELS) == ["S1", "S2", "S3"]
    sizes = {
        name: (lv.size, lv.deposits, lv.walls, lv.min_dead_ends) for name, lv in LEVELS.items()
    }
    assert sizes == {"S1": (6, 6, 0, 0), "S2": (10, 15, 0, 0), "S3": (10, 15, 18, 3)}


@pytest.mark.parametrize("level", ["S1", "S2", "S3"])
def test_every_field_follows_its_level(level: str) -> None:
    spec = LEVELS[level]
    for seed in SEEDS:
        field = generate(level, seed)
        assert field == generate(level, seed)  # deterministic
        assert field.size == spec.size and field.cells == spec.size**2
        assert len(field.deposits) == spec.deposits == field.true_total
        assert field.start == (0, 0) and field.start not in field.deposits
        assert len(field.walls) == spec.walls
        assert _reachable(field) == set(field.all_cells())
        dead_ends = [c for c in field.all_cells() if len(field.exits(c)) == 1]
        assert len(dead_ends) >= spec.min_dead_ends


def test_seeds_give_different_fields() -> None:
    assert len({generate("S2", seed).deposits for seed in DEV_SEEDS}) == len(DEV_SEEDS)


def test_an_unknown_level_is_refused() -> None:
    with pytest.raises(ValueError, match=r"unknown level 'L1' \(levels: S1, S2, S3\)"):
        generate("L1", 1000)
