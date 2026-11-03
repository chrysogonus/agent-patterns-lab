"""The scripted plans behind the guarantees (specs/011 research R7; SC-003, SC-004)."""

import pytest

from apl.workshop import DEV_SEEDS, LEVELS, TEST_SEEDS, generate, start_episode
from apl.workshop.plans import greedy_calls, planner_calls, reference_calls
from tests.workshop.lantern import play

SEEDS = [*DEV_SEEDS, *TEST_SEEDS]


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_the_reference_plan_crafts_the_goal_in_the_reference(level: str) -> None:
    for seed in SEEDS:
        w = generate(level, seed)
        episode = start_episode(w)
        play(episode, reference_calls(w))
        outcome = episode.outcome()
        assert outcome.success and outcome.steps == outcome.optimal_steps and outcome.wasted == 0


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_greedy_gets_stuck_where_there_is_a_conflict(level: str) -> None:
    for seed in SEEDS:
        w = generate(level, seed)
        episode = start_episode(w)
        play(episode, greedy_calls(w))
        outcome = episode.outcome() if episode.end_reason else None
        if level == "W1":
            assert outcome is not None and outcome.success
        else:
            assert outcome is not None and outcome.stuck and outcome.wasted >= 1, seed


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_the_planner_fits_the_budget(level: str) -> None:
    for seed in SEEDS:
        w = generate(level, seed)
        episode = start_episode(w)
        play(episode, planner_calls(w))
        outcome = episode.outcome()
        assert outcome.success and outcome.steps <= w.budget
