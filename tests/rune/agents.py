"""Scripted rune-floor agents for the tests (specs/010 research R7). Each knows exactly what its
name says, and plays through an `Episode` like an architecture would."""

from collections import deque

from apl.rune.env import Episode
from apl.rune.model import DIRECTIONS, STEP, Cell, Floor
from apl.rune.rules import reference_path


def moves_of(path: list[Cell]) -> list[str]:
    """The directions that walk a path of neighbouring cells."""
    out = []
    for (x0, y0), (x1, y1) in zip(path, path[1:], strict=False):
        out.append(next(d for d in DIRECTIONS if STEP[d] == (x1 - x0, y1 - y0)))
    return out


def reference_moves(floor: Floor) -> list[str]:
    path = reference_path(floor)
    assert path is not None
    return moves_of(path)


def walk_reference(episode: Episode) -> None:
    for direction in reference_moves(episode.floor):
        episode.move(direction)


def learner(episode: Episode) -> None:
    """East along the straight row until the first trap; then it knows the rule."""
    while episode.end_reason is None:
        before = len(episode.traps)
        episode.move("east")
        if len(episode.traps) > before:
            break
    if episode.end_reason is None:
        walk_reference(episode)


def repeater(episode: Episode) -> None:
    """East along the straight row, again and again."""
    while episode.end_reason is None:
        episode.move("east")


def memory_only(episode: Episode) -> None:
    """Knows no rule; remembers (cell, walk length) for every trap and avoids those."""
    floor = episode.floor
    bad: set[tuple[Cell, int]] = set()
    while episode.end_reason is None:
        route = _route(floor, bad, limit=floor.budget)
        if route is None:
            episode.stop()
            return
        for i, direction in enumerate(route):
            before = len(episode.traps)
            cell = floor.neighbor(episode.position, direction)
            episode.move(direction)
            if episode.end_reason is not None:
                return
            if len(episode.traps) > before and cell is not None:
                bad.add((cell, i))
                break


def _route(floor: Floor, bad: set[tuple[Cell, int]], limit: int) -> list[str] | None:
    start = (floor.start, 0)
    prev: dict[tuple[Cell, int], tuple[tuple[Cell, int], str] | None] = {start: None}
    queue = deque([start])
    while queue:
        cell, i = queue.popleft()
        for direction in DIRECTIONS:
            other = floor.neighbor(cell, direction)
            if other is None or other == floor.start:
                continue
            if other == floor.goal:
                route = [direction]
                node = (cell, i)
                while (link := prev[node]) is not None:
                    node, step = link
                    route.append(step)
                return route[::-1]
            key = (other, i + 1)
            if (other, i) in bad or key in prev or i + 1 > limit:
                continue
            prev[key] = ((cell, i), direction)
            queue.append(key)
    return None
