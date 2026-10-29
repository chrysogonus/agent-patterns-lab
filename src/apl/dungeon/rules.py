"""Level rules FR-001 to FR-008, shared by the generator and the tests."""

from collections import deque
from collections.abc import Iterable

from apl.dungeon.model import Direction, Edge, Layout, Level, Pos, neighbor


def distances(layout: Layout, source: Pos, doors: Iterable[Edge]) -> dict[Pos, int]:
    """Moves from source to every reachable room through the given doors, locks ignored."""
    open_doors = set(doors)
    dist = {source: 0}
    queue = deque([source])
    while queue:
        room = queue.popleft()
        for direction in Direction:
            other = neighbor(room, direction)
            if other not in dist and layout.in_grid(other) and Edge(room, other) in open_doors:
                dist[other] = dist[room] + 1
                queue.append(other)
    return dist


def ordered_locks(layout: Layout) -> list[Edge]:
    """Locked doors by distance of their nearer side from the start (door A first)."""
    dist = distances(layout, layout.start, layout.doors)
    return sorted(layout.locks, key=lambda e: (min(dist.get(e.a, 999), dist.get(e.b, 999)), e))


def check_level_rules(layout: Layout, level: Level) -> list[str]:
    """Return one message per broken rule; an empty list means the layout meets the level."""
    try:
        layout.validate()
    except ValueError as error:
        return [f"structure: {error}"]
    n = layout.size
    problems: list[str] = []
    if n != level.size:
        problems.append(f"FR-010 size: {n}, expected {level.size}")
    full = distances(layout, layout.start, layout.doors)
    if len(full) != n * n:
        problems.append("FR-002 connected: some rooms are unreachable with locks ignored")
    extra = len(layout.doors) - (n * n - 1)
    if extra != level.extra_doors:
        problems.append(f"FR-002 extra doors: {extra}, expected {level.extra_doors}")
    if full.get(layout.exit, -1) < 2 * (n - 1):
        problems.append(f"FR-003 distance: start and exit are closer than {2 * (n - 1)} moves")
    if len(layout.locks) != level.locks:
        problems.append(f"FR-004 locks: {len(layout.locks)}, expected {level.locks}")

    locks = ordered_locks(layout)
    for edge in locks:
        color = layout.locks[edge]
        without = distances(layout, layout.start, layout.doors - {edge})
        if layout.exit in without:
            problems.append(f"FR-005 necessary: the {color} door can be bypassed")
        key = layout.keys[color]
        if key not in without:
            problems.append(f"FR-006 reachable: the {color} key lies behind its own door")
        if key == layout.start:
            problems.append(f"FR-006 start room: the {color} key is in the start room")
        near = edge.a if full.get(edge.a, 999) <= full.get(edge.b, 999) else edge.b
        from_key = distances(layout, key, layout.doors)
        if near in full and full.get(key, 999) + from_key.get(near, 999) == full[near]:
            problems.append(f"FR-006 detour: the {color} key lies on a shortest route to its door")
    for first, second in zip(locks, locks[1:], strict=False):
        before_first = distances(layout, layout.start, layout.doors - {first})
        if layout.keys[layout.locks[second]] in before_first:
            problems.append("FR-007 chained: the second key is not behind the first door")

    degree = {room: 0 for room in layout.rooms()}
    for edge in layout.doors:
        degree[edge.a] += 1
        degree[edge.b] += 1
    keyed = set(layout.keys.values())
    dead_ends = [
        r for r, d in degree.items() if d == 1 and r not in (layout.start, layout.exit, *keyed)
    ]
    if len(dead_ends) < level.min_dead_ends:
        problems.append(f"FR-008 dead ends: {len(dead_ends)}, expected {level.min_dead_ends}")
    return problems
