"""Generated warehouses for every level and seed (specs/012 T006, SC-002)."""

from collections import Counter

import pytest

from apl.warehouse import DEV_SEEDS, LEVELS, TEST_SEEDS, generate

SEEDS = [*DEV_SEEDS, *TEST_SEEDS]
SHAPES = {"P1": (9, 5), "P2": (9, 5), "P3": (11, 9)}
SPREADS: dict[str, list[tuple[int, ...]]] = {
    "P1": [(1, 1, 1)],
    "P2": [(0, 1, 2)],
    "P3": [(0, 1, 1, 1, 3), (0, 0, 1, 2, 3)],
}


@pytest.mark.parametrize("level", sorted(LEVELS))
@pytest.mark.parametrize("seed", SEEDS)
def test_every_warehouse_follows_its_level(level: str, seed: int) -> None:
    floor = generate(level, seed)
    assert generate(level, seed) == floor
    assert (floor.columns, floor.rows) == SHAPES[level]
    middle = 2 * (floor.aisles // 2)
    assert floor.dock == (0, middle - 1) and floor.drop == (floor.columns - 1, middle - 1)
    cells = [c for _, c in floor.packages]
    assert len(set(cells)) == len(cells)
    assert all(y % 2 == 0 and 1 <= x <= floor.columns - 2 for x, y in cells)
    per_aisle = Counter(y // 2 for _, y in cells)
    assert tuple(sorted(per_aisle.get(a, 0) for a in range(floor.aisles))) in SPREADS[level]
    assert sorted(n for n, _ in floor.packages) == sorted(
        f"package {i}" for i in range(1, len(cells) + 1)
    )
    assert floor.budget == 3 * floor.reference_steps
    assert floor.reference_is_optimal is False


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_package_numbers_are_shuffled(level: str) -> None:
    def reading_order(seed: int) -> bool:
        floor = generate(level, seed)
        ordered = sorted(floor.packages, key=lambda p: (p[1][1], p[1][0]))
        return [n for n, _ in ordered] == [f"package {i}" for i in range(1, len(ordered) + 1)]

    assert not all(reading_order(seed) for seed in DEV_SEEDS)


def test_unknown_levels_are_refused() -> None:
    with pytest.raises(ValueError, match="P1, P2, P3"):
        generate("P9", 1000)
