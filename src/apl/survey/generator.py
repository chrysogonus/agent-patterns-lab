"""Survey fields from a level and a seed, reachable by construction (specs/005 research R9)."""

import random
from collections import deque

from apl.survey.model import LEVELS, Cell, Field, SurveyLevel, Wall, wall
from apl.survey.walk import greedy, snake

MAX_TRIES = 1000


def _reachable(size: int, walls: set[Wall]) -> bool:
    seen, queue = {(0, 0)}, deque([(0, 0)])
    while queue:
        x, y = queue.popleft()
        for other in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            inside = 0 <= other[0] < size and 0 <= other[1] < size
            if inside and other not in seen and wall((x, y), other) not in walls:
                seen.add(other)
                queue.append(other)
    return len(seen) == size * size


def _exits(size: int, walls: set[Wall], cell: Cell) -> int:
    x, y = cell
    others = ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1))
    return sum(0 <= o[0] < size and 0 <= o[1] < size and wall(cell, o) not in walls for o in others)


def _walls(level: SurveyLevel, rng: random.Random) -> set[Wall]:
    n = level.size
    segments = sorted(
        [wall((x, y), (x + 1, y)) for y in range(n) for x in range(n - 1)]
        + [wall((x, y), (x, y + 1)) for y in range(n - 1) for x in range(n)],
        key=sorted,
    )
    cells = [(x, y) for y in range(n) for x in range(n)]
    for _ in range(MAX_TRIES):
        walls: set[Wall] = set()
        for segment in rng.sample(segments, len(segments)):
            if len(walls) == level.walls:
                break
            walls.add(segment)
            if not _reachable(n, walls):
                walls.discard(segment)
        dead_ends = sum(_exits(n, walls, c) == 1 for c in cells)
        if len(walls) == level.walls and dead_ends >= level.min_dead_ends:
            return walls
    raise RuntimeError(f"no field for level {level.name} after {MAX_TRIES} tries")


def generate(level: str, seed: int) -> Field:
    if level not in LEVELS:
        raise ValueError(f"unknown level {level!r} (levels: {', '.join(sorted(LEVELS))})")
    spec = LEVELS[level]
    rng = random.Random(f"survey:{level}:{seed}")
    walls = _walls(spec, rng) if spec.walls else set()
    cells = [(x, y) for y in range(spec.size) for x in range(spec.size)]
    deposits = frozenset(rng.sample(cells[1:], spec.deposits))  # never the start, A1
    if walls:
        draft = Field(spec, seed, spec.size, frozenset(walls), deposits, (), False)
        walk = greedy(spec.size, draft.start, draft.neighbor)
        return Field(spec, seed, spec.size, frozenset(walls), deposits, walk, False)
    return Field(spec, seed, spec.size, frozenset(), deposits, snake(spec.size), True)
