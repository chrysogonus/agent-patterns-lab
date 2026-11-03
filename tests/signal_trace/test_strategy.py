"""The probe rule and the reference strategy (specs/009 research R5, R6; SC-003, SC-004)."""

import math
import statistics

import pytest

from apl.signal_trace import DEV_SEEDS, LEVELS, TEST_SEEDS, generate
from apl.signal_trace.strategy import (
    choose,
    informative,
    reference_run,
    runs_of,
    suspects,
    worst_case,
)

LINE8 = tuple(range(8))  # S → 1 → … → 8
# S → 1 → 2 → 3, then 3 feeds 4 → 5 → 6 and 7 → 8 → 9 → 10
TREE10 = (0, 1, 2, 3, 4, 5, 3, 7, 8, 9)
SEEDS = [*DEV_SEEDS, *TEST_SEEDS]


def test_runs_of_a_line_and_a_tree() -> None:
    assert [(r.feeder, r.first, r.last) for r in runs_of(LINE8)] == [(0, 1, 8)]
    assert [(r.feeder, r.first, r.last) for r in runs_of(TREE10)] == [
        (0, 1, 3), (3, 4, 6), (3, 7, 10),
    ]  # fmt: skip


def test_suspects_on_a_line() -> None:
    assert suspects(LINE8, []) == frozenset(range(1, 9))
    assert suspects(LINE8, [(4, True)]) == frozenset({5, 6, 7, 8})  # 1–4 are clear
    assert suspects(LINE8, [(4, False)]) == frozenset({1, 2, 3, 4})
    assert suspects(LINE8, [(4, True), (6, False)]) == frozenset({5, 6})


def test_suspects_on_a_tree() -> None:
    # Wet at 6 clears its path S → 1 → 2 → 3 → 4 → 5 → 6 only.
    assert suspects(TREE10, [(6, True)]) == frozenset({7, 8, 9, 10})
    # Dry at 6 keeps only its path.
    assert suspects(TREE10, [(6, False)]) == frozenset({1, 2, 3, 4, 5, 6})
    # Dry at 9 and wet at 6: the break is on 7–9.
    assert suspects(TREE10, [(9, False), (6, True)]) == frozenset({7, 8, 9})


def test_informative() -> None:
    every = suspects(LINE8, [])
    assert informative(LINE8, every, 4)
    assert not informative(LINE8, every, 8)  # dry for every suspect
    after = suspects(LINE8, [(4, True)])
    assert not informative(LINE8, after, 2)  # already known wet
    assert not informative(LINE8, after, 4)  # a repeat


def test_choose_splits_evenly_and_takes_the_lowest_on_a_tie() -> None:
    assert choose(LINE8, suspects(LINE8, [])) == 4
    assert choose(LINE8, frozenset({5, 6, 7})) == 5  # 5 leaves 1 or 2; 6 leaves 2 or 1


@pytest.mark.parametrize("n", [1, 2, 3, 5, 8, 16, 17, 64])
def test_bisection_is_optimal_on_a_single_run(n: int) -> None:
    assert worst_case(tuple(range(n))) == math.ceil(math.log2(n))


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_the_reference_finds_the_break_within_its_probes(level: str) -> None:
    for seed in SEEDS:
        pipe = generate(level, seed)
        probes, submitted = reference_run(pipe)
        assert submitted == pipe.broken
        assert len(probes) <= pipe.reference_probes
        assert all(water == pipe.wet(k) for k, water in probes)


def _scan(feeder: tuple[int, ...], broken: int) -> int:
    """Probe the lowest informative suspect until one suspect is left."""
    up = {k: _upstream(feeder, k) for k in range(1, len(feeder) + 1)}
    answers: list[tuple[int, bool]] = []
    while len(left := suspects(feeder, answers)) > 1:
        k = min(k for k in left if informative(feeder, left, k))
        answers.append((k, broken not in up[k]))
    return len(answers)


def _upstream(feeder: tuple[int, ...], k: int) -> set[int]:
    path = set()
    while k:
        path.add(k)
        k = feeder[k - 1]
    return path


def test_a_probe_by_probe_scan_needs_far_more_probes_on_t2() -> None:
    pipes = [generate("T2", seed) for seed in SEEDS]
    scans = [_scan(p.feeder, p.broken) for p in pipes]
    assert statistics.mean(scans) >= 3 * pipes[0].reference_probes
