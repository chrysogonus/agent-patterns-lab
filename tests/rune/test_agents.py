"""The scripted agents behind the generator's guarantees (specs/010 research R7; SC-003, SC-004)."""

import pytest

from apl.rune import DEV_SEEDS, LEVELS, TEST_SEEDS, generate, start_episode
from apl.rune.generator import memory_only_steps
from tests.rune.agents import learner, memory_only, repeater, walk_reference

SEEDS = [*DEV_SEEDS, *TEST_SEEDS]


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_the_reference_path_reaches_the_goal_in_the_reference(level: str) -> None:
    for seed in SEEDS:
        episode = start_episode(generate(level, seed))
        walk_reference(episode)
        outcome = episode.outcome()
        assert outcome.success and outcome.steps == outcome.optimal_steps and outcome.traps == 0


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_a_learner_fits_the_budget_and_a_repeater_does_not(level: str) -> None:
    for seed in SEEDS:
        floor = generate(level, seed)
        episode = start_episode(floor)
        learner(episode)
        outcome = episode.outcome()
        assert outcome.success and outcome.traps == 1
        assert outcome.steps < 2 * floor.reference <= floor.budget
        episode = start_episode(floor)
        repeater(episode)
        outcome = episode.outcome()
        assert not outcome.success and outcome.budget_hit and outcome.traps >= 2


def test_memory_alone_is_enough_on_r0() -> None:
    for seed in SEEDS:
        floor = generate("R0", seed)
        episode = start_episode(floor)
        memory_only(episode)
        outcome = episode.outcome()
        assert outcome.success and outcome.steps <= floor.budget
        assert memory_only_steps(floor) == outcome.steps  # the generator's copy agrees


def test_memory_alone_falls_short_on_some_rule_floors() -> None:
    """Reported, not required (research R7): the gap the board is built to show."""
    for level in ("R1", "R2", "R3"):
        finished = 0
        for seed in SEEDS:
            episode = start_episode(generate(level, seed))
            memory_only(episode)
            finished += episode.outcome().success
        assert finished < len(SEEDS), level
