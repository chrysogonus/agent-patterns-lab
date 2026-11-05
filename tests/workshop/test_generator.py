"""Generated workshops (specs/011 research R3, R4, R6; SC-002)."""

import pytest

from apl.workshop import DEV_SEEDS, LEVELS, TEST_SEEDS, generate
from apl.workshop.model import CRAFTABLE_NAMES, RAW_NAMES, Workshop
from apl.workshop.plans import reference_calls

SEEDS = [*DEV_SEEDS, *TEST_SEEDS]
SHAPE = {
    "W1": (3, 2, 1, 0),
    "W2": (5, 3, 1, 1),
    "W3": (8, 4, 2, 2),
    "W4": (12, 5, 3, 3),  # specs/013 FR-004
}  # craftables, depth, alts, scarce
BOUND = {"W1": 12, "W2": 20, "W3": 32, "W4": 48}


def _tree(w: Workshop) -> tuple[list[str], int]:
    """The craftables under the goal through the reference's recipes, and the tree's depth."""
    seen: list[str] = []

    def walk(item: str, depth: int) -> int:
        assert item not in seen, f"{item} used twice"
        seen.append(item)
        choice = w.reference_choice.get(item, 1)
        deepest = depth
        for name in w.recipes[item][choice - 1]:
            if w.craftable(name):
                deepest = max(deepest, walk(name, depth + 1))
        return deepest

    return seen, walk(w.goal, 1)


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_every_workshop_is_valid(level: str) -> None:
    craftables, depth, alternatives, scarce = SHAPE[level]
    for seed in SEEDS:
        w = generate(level, seed)
        assert w == generate(level, seed)
        for recipes in w.recipes.values():
            for recipe in recipes:
                assert all(w.craftable(i) or w.raw(i) for i in recipe)
        tree, deepest = _tree(w)
        assert len(tree) == craftables and deepest == depth
        assert len([i for i, r in w.recipes.items() if len(r) == 2]) == alternatives
        assert len(w.scarce) == scarce and all(w.stock[s] == 1 for s in w.scarce)
        assert set(w.recipes) <= set(CRAFTABLE_NAMES) and set(w.stock) <= set(RAW_NAMES)
        assert list(w.stock) == sorted(w.stock)
        assert w.budget == 3 * w.reference and w.reference_is_optimal
        assert w.reference == len(reference_calls(w)) <= BOUND[level]


def test_w1s_second_recipe_is_harmless() -> None:
    for seed in SEEDS:
        w = generate("W1", seed)
        (item,) = [i for i, r in w.recipes.items() if len(r) == 2]
        assert all(w.raw(i) and i not in w.scarce for i in w.recipes[item][1])


def test_seeds_give_different_workshops() -> None:
    assert len({tuple(sorted(generate("W2", s).recipes)) for s in SEEDS}) > len(SEEDS) // 2


def test_an_unknown_level_is_refused() -> None:
    with pytest.raises(ValueError, match="W1, W2, W3, W4"):
        generate("W9", 1000)
