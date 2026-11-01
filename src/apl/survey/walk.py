"""The reference walk that enters every cell (specs/005 research R8)."""

from collections import deque
from collections.abc import Callable

from apl.survey.model import DIRECTIONS, Cell

Neighbor = Callable[[Cell, str], Cell | None]


def snake(size: int) -> tuple[str, ...]:
    """Row 1 east, row 2 west, and so on: `size² − 1` moves, the shortest on an open field."""
    moves: list[str] = []
    for row in range(size):
        moves += ["east" if row % 2 == 0 else "west"] * (size - 1)
        if row < size - 1:
            moves.append("south")
    return tuple(moves)


def greedy(size: int, start: Cell, neighbor: Neighbor) -> tuple[str, ...]:
    """Always on to the nearest unseen cell by breadth-first search, ties north, east, south, west.

    Legal and short, though not always the shortest; used where walls make the snake impossible.
    """
    seen, here, moves = {start}, start, []
    while len(seen) < size * size:
        paths: dict[Cell, list[str]] = {here: []}
        queue, target = deque([here]), None
        while queue and target is None:
            cell = queue.popleft()
            for direction in DIRECTIONS:
                other = neighbor(cell, direction)
                if other is None or other in paths:
                    continue
                paths[other] = [*paths[cell], direction]
                if other not in seen:
                    target = other
                    break
                queue.append(other)
        if target is None:
            raise ValueError("the field has cells that cannot be reached")
        for direction in paths[target]:
            nxt = neighbor(here, direction)
            assert nxt is not None
            here = nxt
            seen.add(here)
        moves += paths[target]
    return tuple(moves)
