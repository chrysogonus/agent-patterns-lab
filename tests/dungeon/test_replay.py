"""The solver and the environment agree (SC-002)."""

import pytest

from apl.dungeon import DEV_SEEDS, LEVELS, TEST_SEEDS, generate, start_episode
from apl.dungeon.results import EndReason


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_solution_replays_to_the_exit(level: str) -> None:
    for seed in [*DEV_SEEDS, *TEST_SEEDS]:
        dungeon = generate(level, seed)
        episode = start_episode(dungeon)
        for action in dungeon.solution.actions:
            assert getattr(episode, action.tool)(*action.args).ok, (level, seed, action)
        assert episode.end_reason == EndReason.EXIT, (level, seed)
        assert episode.steps == dungeon.solution.length
