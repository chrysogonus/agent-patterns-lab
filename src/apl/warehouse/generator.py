"""Warehouses from a level and a seed (specs/012 research R2, R5–R7). Runner side only."""

import random

from apl.warehouse.model import LEVELS, Cell, Floor, WarehouseLevel
from apl.warehouse.plans import blind_split, replanning_split, with_reference

MAX_TRIES = 1000


def generate(level: str, seed: int) -> Floor:
    if level not in LEVELS:
        raise ValueError(f"unknown level {level!r} (levels: {', '.join(LEVELS)})")
    spec = LEVELS[level]
    rng = random.Random(f"warehouse:{level}:{seed}")
    for _ in range(MAX_TRIES):
        found = _draw(spec, seed, rng)
        if found is not None:
            return found
    raise RuntimeError(f"no {level} warehouse for seed {seed} in {MAX_TRIES} tries")


def _draw(spec: WarehouseLevel, seed: int, rng: random.Random) -> Floor | None:
    counts = list(rng.choice(spec.spreads))
    rng.shuffle(counts)
    cells: list[Cell] = []
    for aisle, count in enumerate(counts):
        columns = rng.sample(range(1, spec.columns - 1), count)
        cells += [(x, 2 * aisle) for x in sorted(columns)]
    numbers = list(range(1, len(cells) + 1))
    rng.shuffle(numbers)
    packages = tuple((f"package {n}", cell) for n, cell in zip(numbers, cells, strict=True))
    floor = with_reference(Floor(spec, seed, spec.columns, spec.aisles, packages))
    if len(set(spec.spreads[0])) > 1:  # an uneven level: the gap must exist by construction
        blind, replanned = blind_split(floor).outcome(), replanning_split(floor).outcome()
        if blind.idle_robot_turns == 0 or replanned.parallel_turns >= blind.parallel_turns:
            return None
    return floor
