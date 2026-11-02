"""Pipes from a level and a seed (specs/009 research R3, R4)."""

import random

from apl.signal_trace.model import LEVELS, Pipe, SignalLevel
from apl.signal_trace.strategy import runs_of, worst_case

MAX_TRIES = 1000


def _tree(level: SignalLevel, rng: random.Random) -> tuple[int, ...] | None:
    """A tree grown segment by segment, renumbered in preorder; None if a run is too short.

    Each new segment extends a pipe end, except at `ends − 1` seeded moments, when it starts a
    branch from a segment that feeds only one: so no segment feeds more than two.
    """
    n = level.segments
    parent: dict[int, int] = {1: 0}  # growth order; 0 is S
    children: dict[int, list[int]] = {1: []}
    pipe_ends, pending = [1], 0
    moments = set(rng.sample(range(3, n // 2), level.ends - 1))
    for new in range(2, n + 1):
        pending += new in moments
        single = [k for k in sorted(children) if len(children[k]) == 1]
        if pending and single:
            pending -= 1
            source = rng.choice(single)
        else:
            source = rng.choice(pipe_ends)
            pipe_ends.remove(source)
        parent[new], children[new] = source, []
        children[source].append(new)
        pipe_ends.append(new)
    order, stack = [], [1]
    while stack:
        here = stack.pop()
        order.append(here)
        stack.extend(reversed(children[here]))
    number = {old: k for k, old in enumerate(order, 1)}
    feeder = tuple(number.get(parent[old], 0) for old in order)
    runs = runs_of(feeder)
    if len(pipe_ends) != level.ends or min(r.last - r.first + 1 for r in runs) < level.min_run:
        return None
    return feeder


def generate(level: str, seed: int) -> Pipe:
    if level not in LEVELS:
        raise ValueError(f"unknown level {level!r} (levels: {', '.join(sorted(LEVELS))})")
    spec = LEVELS[level]
    rng = random.Random(f"signal:{level}:{seed}")
    if spec.ends == 1:
        feeder: tuple[int, ...] | None = tuple(range(spec.segments))
    else:
        for _ in range(MAX_TRIES):
            if (feeder := _tree(spec, rng)) is not None:
                break
        else:
            raise RuntimeError(f"no pipe for level {level} after {MAX_TRIES} tries")
    assert feeder is not None
    runs = runs_of(feeder)
    return Pipe(
        level=spec,
        seed=seed,
        feeder=feeder,
        runs=runs,
        broken=rng.randint(1, spec.segments),
        reference_probes=worst_case(feeder),
        reference_is_optimal=len(runs) == 1,
    )
