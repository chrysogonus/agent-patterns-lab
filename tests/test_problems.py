"""The problem registry (specs/005 contracts/problems.md)."""

import pytest

from apl import problems
from apl.dungeon import DEV_SEEDS, LEVELS, TEST_SEEDS, generate, start_episode
from apl.kit import build_kit, prompt_fingerprint


def test_the_dungeon_is_the_default() -> None:
    assert problems.DEFAULT == "dungeon"
    assert problems.get(None) is problems.get("dungeon")
    dungeon = problems.get("dungeon")
    assert dungeon.name == "dungeon" and sorted(dungeon.levels) == ["L1", "L2", "L3"]
    assert dungeon.levels is LEVELS
    assert dungeon.dev_seeds == DEV_SEEDS and dungeon.test_seeds == TEST_SEEDS
    assert dungeon.seed_sets == {"dev": range(1000, 1010), "test": range(2000, 2020)}


def test_the_dungeon_entry_uses_the_existing_functions() -> None:
    dungeon = problems.get("dungeon")
    world = dungeon.generate("L2", 1003)
    assert world == generate("L2", 1003)
    assert dungeon.reference_steps(world) == world.solution.length
    assert dungeon.start_episode(world).dungeon is world
    assert dungeon.prompt_fingerprint() == prompt_fingerprint()
    assert dungeon.build_kit.__name__ == build_kit.__name__
    episode = start_episode(world)
    assert dungeon.build_kit(episode, None).problem == "dungeon"


def test_an_unknown_problem_is_refused() -> None:
    with pytest.raises(ValueError, match=r"unknown problem 'chess' \(problems: dungeon"):
        problems.get("chess")
