"""Shortest paths, the reference and the scripted splits (specs/012 research R6, R7).

Runner and test side only: these read the whole floor, which no architecture may.
"""

from collections import deque
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import replace

from apl.warehouse.env import MAX_SCOUTS, Episode
from apl.warehouse.model import DIRECTIONS, Action, Cell, Floor


def path(floor: Floor, start: Cell, goal: Cell) -> list[str]:
    """The moves of a shortest path; breadth first, trying north, east, south, west in turn."""
    parent: dict[Cell, tuple[Cell, str] | None] = {start: None}
    queue = deque([start])
    while queue:
        cell = queue.popleft()
        if cell == goal:
            break
        for direction in DIRECTIONS:
            other = floor.neighbor(cell, direction)
            if other is not None and other not in parent:
                parent[other] = (cell, direction)
                queue.append(other)
    moves: list[str] = []
    step = parent.get(goal)
    if goal != start and step is None:
        raise ValueError(f"no path from {start} to {goal}")
    while step is not None:
        cell, direction = step
        moves.append(direction)
        step = parent[cell]
    return moves[::-1]


def _walk(floor: Floor, start: Cell, moves: Iterable[str]) -> Cell:
    cell = start
    for direction in moves:
        found = floor.neighbor(cell, direction)
        assert found is not None
        cell = found
    return cell


def _nearest(floor: Floor, start: Cell, cells: Iterable[Cell]) -> Cell:
    """The cell with the shortest path; ties to the north, then the west."""
    return min(cells, key=lambda c: (len(path(floor, start, c)), c[1], c[0]))


def _go(floor: Floor, start: Cell, goal: Cell, calls: list[Action]) -> Cell:
    calls.extend(Action("move", (d,)) for d in path(floor, start, goal))
    return goal


def reference_calls(floor: Floor) -> list[Action]:
    """A single robot that knows nothing: aisle by aisle, north to south, it enters the aisle and
    carries each package there to D, nearest first, before going on (research R6). It knows the
    package count, so it stops at the last delivery."""
    calls: list[Action] = []
    here = floor.dock
    for aisle in floor.aisle_names:
        if calls.count(Action("drop")) == len(floor.packages):
            break
        cells = floor.corridor_cells(aisle)
        here = _go(floor, here, _nearest(floor, here, cells), calls)
        waiting = [c for _, c in floor.packages if c in cells]
        while waiting:
            target = _nearest(floor, here, waiting)
            waiting.remove(target)
            here = _go(floor, here, target, calls)
            calls.append(Action("pick"))
            here = _go(floor, here, floor.drop, calls)
            calls.append(Action("drop"))
    return calls


def with_reference(floor: Floor) -> Floor:
    return replace(floor, reference=tuple(reference_calls(floor)))


def apply(episode: Episode, action: Action, robot: int = 0) -> None:
    match action.tool:
        case "move":
            episode.move(action.args[0], scout=robot)
        case "pick":
            episode.pick(scout=robot)
        case "drop":
            episode.drop(scout=robot)
        case _:
            episode.look(scout=robot)


def play(episode: Episode, actions: Iterable[Action], robot: int = 0) -> None:
    for action in actions:
        apply(episode, action, robot)


def as_calls(actions: Sequence[Action]) -> list[tuple[str, Mapping[str, object]]]:
    """The actions as a scripted model's tool calls."""
    return [(a.tool, {"direction": a.args[0]} if a.tool == "move" else {}) for a in actions]


def blind_split(floor: Floor) -> Episode:
    return _split(floor, replan=False)


def replanning_split(floor: Floor) -> Episode:
    return _split(floor, replan=True)


def _split(floor: Floor, replan: bool) -> Episode:
    """Robots in lockstep rounds, aisles dealt out before anyone has looked (research R7).

    Each robot clears its own aisles; with `replan`, a robot without work takes the nearest
    package someone has seen that no robot is heading for.
    """
    episode = Episode(floor)
    rounds = [0]
    episode.turn_source = lambda: rounds[0]
    robots = min(floor.aisles, MAX_SCOUTS)
    for _ in range(robots - 1):
        episode.add_scout()
    own = {r: floor.aisle_names[r::robots] for r in range(robots)}
    targets: dict[int, Cell] = {}
    legs: dict[int, list[Action]] = {r: [] for r in range(robots)}

    def known() -> dict[Cell, str]:
        return {c: n for n, c in episode.waiting.items() if c in episode.seen}

    def next_leg(r: int) -> list[Action]:
        here, calls = episode.robots[r], list[Action]()
        if episode.carrying[r] is not None:
            _go(floor, here, floor.drop, calls)
            return [*calls, Action("drop")]
        free = {c for c in known() if c not in targets.values()}
        mine = {c for c in free for a in own[r] if c in floor.corridor_cells(a)}
        unseen = [a for a in own[r] if not set(floor.corridor_cells(a)) <= episode.seen]
        choice = mine or (free if replan and not unseen else set())
        if choice:
            targets[r] = _nearest(floor, here, choice)
            _go(floor, here, targets[r], calls)
            return [*calls, Action("pick")]
        if unseen:
            _go(floor, here, _nearest(floor, here, floor.corridor_cells(unseen[0])), calls)
            return calls
        return []

    while episode.end_reason is None:
        rounds[0] += 1
        acted = False
        for r in range(robots):
            if not legs[r]:
                if episode.carrying[r] is None:
                    targets.pop(r, None)  # delivered, or arrived without a target
                legs[r] = next_leg(r)
            if legs[r] and episode.end_reason is None:
                apply(episode, legs[r].pop(0), r)
                acted = True
        if not acted:
            episode.stop()
    return episode
