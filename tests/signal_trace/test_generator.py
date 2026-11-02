"""Pipes from a level and a seed (specs/009 SC-002, research R3, R4)."""

import pytest

from apl.signal_trace import DEV_SEEDS, LEVELS, TEST_SEEDS, generate
from apl.signal_trace.model import Pipe, Run

SEEDS = [*DEV_SEEDS, *TEST_SEEDS]


def _pipes(level: str) -> list[Pipe]:
    return [generate(level, seed) for seed in SEEDS]


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_a_pipe_is_the_same_every_time(level: str) -> None:
    for seed in SEEDS:
        assert generate(level, seed) == generate(level, seed)


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_every_pipe_has_the_level_shape(level: str) -> None:
    spec = LEVELS[level]
    for pipe in _pipes(level):
        n = pipe.segments
        assert n == spec.segments == len(pipe.feeder)
        assert all(0 <= f < k for k, f in enumerate(pipe.feeder, 1))  # feeders always < k
        fed = [pipe.feeder.count(k) for k in range(n + 1)]
        assert max(fed[1:]) <= 2 and fed[0] == 1  # S feeds one segment; no segment feeds three
        ends = sum(fed[k] == 0 for k in range(1, n + 1))
        assert ends == spec.ends
        assert 1 <= pipe.broken <= n


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_runs_are_contiguous_ranges_in_order(level: str) -> None:
    spec = LEVELS[level]
    for pipe in _pipes(level):
        runs = pipe.runs
        assert [r.first for r in runs] == sorted(r.first for r in runs)
        covered = [k for r in runs for k in range(r.first, r.last + 1)]
        assert covered == list(range(1, pipe.segments + 1))
        for run in runs:
            assert pipe.feeder[run.first - 1] == run.feeder
            assert all(pipe.feeder[k - 1] == k - 1 for k in range(run.first + 1, run.last + 1))
            assert run.last - run.first + 1 >= spec.min_run


def test_straight_levels_are_one_run_and_optimal() -> None:
    for level, n in (("T1", 16), ("T2", 64)):
        for pipe in _pipes(level):
            assert pipe.runs == (Run(0, 1, n),)
            assert pipe.reference_is_optimal


def test_t3_is_a_bounded_tree_marked_as_a_reference() -> None:
    for pipe in _pipes("T3"):
        assert not pipe.reference_is_optimal
        assert pipe.reference_probes <= 8


@pytest.mark.parametrize(("level", "budget"), [("T1", 16), ("T2", 64), ("T3", 64)])
def test_the_budget(level: str, budget: int) -> None:
    for pipe in _pipes(level):
        assert pipe.reference_steps == pipe.reference_probes + 1
        assert pipe.budget == max(3 * pipe.reference_steps, pipe.segments) == budget


def test_the_broken_segment_varies_with_the_seed() -> None:
    assert len({generate("T2", seed).broken for seed in SEEDS}) > 10


def test_an_unknown_level_is_refused() -> None:
    with pytest.raises(ValueError, match="T1, T2, T3"):
        generate("T9", 1000)
