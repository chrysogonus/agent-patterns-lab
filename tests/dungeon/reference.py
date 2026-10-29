"""Hand-built reference dungeons with hand-worked answers (SC-008).

All are 3×3. Coordinates are (x, y) with (0, 0) north-west and south = y + 1. They need only
pass Layout.validate(), not any level's rules.
"""

from apl.dungeon.model import Edge, Layout, Pos

START: Pos = (0, 0)
EXIT: Pos = (2, 0)

# The ring: the long way round from (0,0) to (2,0) is south, south, east, east, north, north
# (6 moves). (0,0)-(1,0) is open too, so (1,0) is a side room.
RING = frozenset(
    {
        Edge((0, 0), (0, 1)),
        Edge((0, 1), (0, 2)),
        Edge((0, 2), (1, 2)),
        Edge((1, 2), (2, 2)),
        Edge((2, 2), (2, 1)),
        Edge((2, 1), (2, 0)),
        Edge((0, 0), (1, 0)),
    }
)
SHORTCUT = Edge((1, 0), (2, 0))


def grid_labels(size: int) -> dict[Pos, str]:
    """Labels a2, a3, … in grid order. Fine for tests; generated dungeons draw them at random."""
    names = [f"{c}{d}" for c in "abcdefghjk" for d in "23456789"]
    rooms = [(x, y) for y in range(size) for x in range(size)]
    return dict(zip(rooms, names, strict=False))


def _layout(
    doors: frozenset[Edge],
    locks: dict[Edge, str] | None = None,
    keys: dict[str, Pos] | None = None,
    exit: Pos = EXIT,
) -> Layout:
    return Layout(3, doors, locks or {}, keys or {}, START, exit, grid_labels(3))


def two_open_routes() -> Layout:
    """
    S . E     The ring plus an open shortcut (1,0)-(2,0).
    . . .     Optimal 2: move east, move east. The ring (6) loses.
    . . .
    """
    return _layout(RING | {SHORTCUT})


def locked_shortcut_wins() -> Layout:
    """
    S r R E   The shortcut is locked red; the red key lies at (1,0), right on the way.
    . . .     Optimal 4: move east (1), take red key (2), use red key east (3), move east (4).
    . . .     The open ring costs 6.
    """
    return _layout(RING | {SHORTCUT}, {SHORTCUT: "red"}, {"red": (1, 0)})


def open_route_wins() -> Layout:
    """
    S . R E   The shortcut is locked red, but the red key lies at (0,2), down the ring.
    . . .     Via the lock: south, south (2), take (3), north, north, east (6), use (7),
    r . .     east (8) = 8. Continuing the ring after the key is 2 + 1 + 4 = 7.
              Optimal 6: the open ring, with no take and no use.
    """
    return _layout(RING | {SHORTCUT}, {SHORTCUT: "red"}, {"red": (0, 2)})


def chained_keys() -> Layout:
    """
    S . R .   Doors: (0,0)-(1,0), (0,0)-(0,1), (2,0)-(2,1) open; (1,0)-(2,0) locked red;
    r     b   (2,1)-(2,2) locked blue. Red key at (0,1), blue key at (2,1). Exit at (2,2).
          B   Optimal 10: south, take red, north, east, use red east, east, south,
          E   take blue, use blue south, south. Every one of those actions is required.
    """
    red, blue = Edge((1, 0), (2, 0)), Edge((2, 1), (2, 2))
    doors = frozenset({Edge((0, 0), (1, 0)), Edge((0, 0), (0, 1)), Edge((2, 0), (2, 1)), red, blue})
    return _layout(doors, {red: "red", blue: "blue"}, {"red": (0, 1), "blue": (2, 1)}, (2, 2))


def key_behind_own_door() -> Layout:
    """
    S R r . E   (0,0)-(1,0) locked red, with the red key at (1,0) behind it; (1,0)-(2,0) open.
                Unsolvable: the only way to the key is through its own door.
    """
    door = Edge((0, 0), (1, 0))
    return _layout(frozenset({door, SHORTCUT}), {door: "red"}, {"red": (1, 0)})


REFERENCE: list[tuple[str, Layout, int | None]] = [
    ("two_open_routes", two_open_routes(), 2),
    ("locked_shortcut_wins", locked_shortcut_wins(), 4),
    ("open_route_wins", open_route_wins(), 6),
    ("chained_keys", chained_keys(), 10),
    ("key_behind_own_door", key_behind_own_door(), None),
]
