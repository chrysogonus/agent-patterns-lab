"""The map that tool results have revealed, worked out from the layout (research R17).

Tests may read the layout; architectures may not. This is the independent check for A2's map.
"""

from collections.abc import Sequence

from apl.arch.dungeon_map import DungeonMap, RoomNote
from apl.dungeon.frames import Frame
from apl.dungeon.model import Direction, Dungeon, Edge, Pos, key_name


def _direction(a: Pos, b: Pos) -> str:
    return next(str(d) for d in Direction if (a[0] + d.delta[0], a[1] + d.delta[1]) == b)


def expected_map(dungeon: Dungeon, frames: Sequence[Frame], upto: int) -> DungeonMap:
    """What the results up to frame `upto` reveal: rooms as last seen, walked doors both ways."""
    layout = dungeon.layout
    shown = frames[: upto + 1]
    last_view: dict[Pos, int] = {}  # frame index of the last room view of each room
    walked: list[tuple[Pos, Pos]] = []
    opened_from: dict[Edge, Pos] = {}
    opened_order: list[Edge] = []
    for i, frame in enumerate(shown):
        tool = frame.action.tool if frame.action else None
        if i == 0 or (frame.ok and tool in ("move", "look")):
            last_view[frame.position] = i
        if i and frame.position != shown[i - 1].position:
            walked.append((shown[i - 1].position, frame.position))
        for new in sorted(frame.opened - (shown[i - 1].opened if i else frozenset())):
            opened_from[new] = frame.position
            opened_order.append(new)
    walked_edges = {Edge(a, b) for a, b in walked}
    final = shown[-1]
    rooms: dict[str, RoomNote] = {}
    for pos in sorted(
        last_view, key=lambda p: min(i for i, f in enumerate(shown) if f.position == p)
    ):
        seen = shown[last_view[pos]]
        exits: dict[str, str | None] = {}
        for direction in Direction:
            edge = layout.door(pos, direction)
            if edge is None:
                continue
            lock = layout.locks.get(edge)
            if edge in seen.opened or (
                edge in final.opened and (opened_from[edge] == pos or edge in walked_edges)
            ):
                lock = None
            exits[str(direction)] = lock
        items = [
            key_name(c)
            for c, p in seen.keys_in_rooms.items()
            if p == pos and c not in final.inventory
        ]
        rooms[layout.labels[pos]] = RoomNote(exits, {}, items)
    for a, b in walked:
        rooms[layout.labels[a]].leads_to[_direction(a, b)] = layout.labels[b]
        rooms[layout.labels[b]].leads_to[_direction(b, a)] = layout.labels[a]
    opened = [
        (
            layout.labels[opened_from[e]],
            _direction(opened_from[e], e.other(opened_from[e])),
            layout.locks[e],
        )
        for e in opened_order
    ]
    return DungeonMap(
        rooms=rooms,
        current=layout.labels[final.position],
        inventory=tuple(key_name(c) for c in final.inventory),
        opened=opened,
    )


def expected_shared(
    dungeon: Dungeon, frames: Sequence[Frame], upto: int, scouts: Sequence[int]
) -> tuple[set[str], dict[str, dict[str, str]], dict[int, str], dict[int, tuple[str, ...]]]:
    """For several scouts (specs/004): rooms seen, walked doors both ways, rooms and inventories.

    `scouts` are the scout numbers to report (those the architecture has created).
    """
    labels = dungeon.layout.labels
    shown = frames[: upto + 1]
    seen = {labels[dungeon.layout.start]}
    leads: dict[str, dict[str, str]] = {}
    for before, after in zip(shown, shown[1:], strict=False):
        for a, b in zip(before.scouts, after.scouts, strict=True):
            seen.add(labels[b.position])
            if a.position != b.position:
                here, there = labels[a.position], labels[b.position]
                leads.setdefault(here, {})[_direction(a.position, b.position)] = there
                leads.setdefault(there, {})[_direction(b.position, a.position)] = here
    last = shown[-1].scouts
    rooms = {n: labels[last[n].position] for n in scouts}
    held = {n: tuple(key_name(c) for c in last[n].inventory) for n in scouts}
    return seen, leads, rooms, held
