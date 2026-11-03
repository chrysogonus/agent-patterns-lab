"""The scripted agents on every warehouse (specs/012 T007, SC-003, SC-004)."""

import pytest

from apl.warehouse import DEV_SEEDS, LEVELS, TEST_SEEDS, generate, start_episode
from apl.warehouse.plans import blind_split, play, replanning_split

SEEDS = [*DEV_SEEDS, *TEST_SEEDS]


@pytest.mark.parametrize("level", sorted(LEVELS))
@pytest.mark.parametrize("seed", SEEDS)
def test_the_reference_delivers_everything_in_its_steps(level: str, seed: int) -> None:
    floor = generate(level, seed)
    episode = start_episode(floor)
    play(episode, floor.reference)
    outcome = episode.outcome()
    assert outcome.success and outcome.steps == floor.reference_steps
    assert outcome.delivered == outcome.packages == len(floor.packages)


@pytest.mark.parametrize("level", ["P2", "P3"])
@pytest.mark.parametrize("seed", SEEDS)
def test_a_blind_split_idles_a_robot_and_a_replanning_split_is_faster(
    level: str, seed: int
) -> None:
    floor = generate(level, seed)
    blind, replanned = blind_split(floor).outcome(), replanning_split(floor).outcome()
    assert blind.success and replanned.success
    assert blind.idle_robot_turns > 0
    assert replanned.parallel_turns < blind.parallel_turns
