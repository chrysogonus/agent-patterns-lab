"""The probe rule, suspects and the reference strategy (specs/009 research R5, R6).

Plain functions over a feeder tuple (`feeder[k - 1]` feeds segment k, 0 is S), so the generator
can use them before a `Pipe` exists. Suspect sets are kept as bit masks: bit k is segment k.
"""

from collections.abc import Iterable
from functools import cache

from apl.signal_trace.model import Pipe, Run

Answer = tuple[int, bool]  # (segment, water)
Feeder = tuple[int, ...]


def runs_of(feeder: Feeder) -> tuple[Run, ...]:
    """The straight pieces, in order of `first`; numbering in preorder makes each contiguous."""
    fed: dict[int, list[int]] = {}
    for k, f in enumerate(feeder, 1):
        fed.setdefault(f, []).append(k)
    starts = sorted(k for k, f in enumerate(feeder, 1) if f == 0 or len(fed[f]) == 2)
    runs = []
    for first in starts:
        last = first
        while len(fed.get(last, ())) == 1:
            last = fed[last][0]
        runs.append(Run(feeder[first - 1], first, last))
    return tuple(runs)


@cache
def _upstream_masks(feeder: Feeder) -> tuple[int, ...]:
    """Index k: the mask of segment k and its feeders up to S; index 0 is unused."""
    masks = [0]
    for k, f in enumerate(feeder, 1):
        masks.append(masks[f] | (1 << k))  # a feeder is always below k, so it is already known
    return tuple(masks)


def _all(feeder: Feeder) -> int:
    return ((1 << len(feeder)) - 1) << 1


def _mask(segments: Iterable[int]) -> int:
    return sum(1 << k for k in set(segments))


def _segments(mask: int) -> frozenset[int]:
    return frozenset(k for k in range(mask.bit_length()) if mask >> k & 1)


def _suspect_mask(feeder: Feeder, answers: Iterable[Answer]) -> int:
    up = _upstream_masks(feeder)
    left = _all(feeder)
    for k, water in answers:
        # Wet: nothing on k's path is broken. Dry: the break is on k's path.
        left = left & ~up[k] if water else left & up[k]
    return left


def suspects(feeder: Feeder, answers: Iterable[Answer]) -> frozenset[int]:
    """Every segment that could still be the broken one after these answers."""
    return _segments(_suspect_mask(feeder, answers))


def informative(feeder: Feeder, left: frozenset[int], segment: int) -> bool:
    """Some suspect would make `segment` dry and some would leave it wet."""
    dry = _mask(left) & _upstream_masks(feeder)[segment]
    return 0 < dry.bit_count() < len(left)


def _choose(feeder: Feeder, left: int) -> int:
    up, total = _upstream_masks(feeder), left.bit_count()
    best, choice = total, 0
    for k in range(1, len(feeder) + 1):
        dry = (left & up[k]).bit_count()
        if 0 < dry < total and max(dry, total - dry) < best:  # strict: the lowest k on a tie
            best, choice = max(dry, total - dry), k
    return choice


def choose(feeder: Feeder, left: frozenset[int]) -> int:
    """The probe whose larger outcome leaves the fewest suspects; the lowest one on a tie."""
    return _choose(feeder, _mask(left))


def worst_case(feeder: Feeder) -> int:
    """The most probes the strategy needs, over every possible broken segment."""
    up = _upstream_masks(feeder)

    @cache
    def worst(left: int) -> int:
        if left.bit_count() <= 1:
            return 0
        k = _choose(feeder, left)
        return 1 + max(worst(left & up[k]), worst(left & ~up[k]))

    return worst(_all(feeder))


def reference_run(pipe: Pipe) -> tuple[list[Answer], int]:
    """The strategy on this pipe's break: the probes with their answers, and the submission."""
    up = _upstream_masks(pipe.feeder)
    left, probes = _all(pipe.feeder), []
    while left.bit_count() > 1:
        k = _choose(pipe.feeder, left)
        water = pipe.wet(k)
        probes.append((k, water))
        left = left & ~up[k] if water else left & up[k]
    (submitted,) = _segments(left)
    return probes, submitted
