"""A2's map: built only from tool results (US3, SC-007, SC-008; research R13, R14)."""

import json
from typing import Any

import pytest

from apl.arch.dungeon_map import DungeonMap, RoomNote
from apl.dungeon import DEV_SEEDS, generate, start_episode
from apl.dungeon.frames import build_frames, call
from apl.dungeon.model import Action, Direction, Dungeon, key_name
from apl.dungeon.tools import AgentTools
from tests.arch.oracle import expected_map
from tests.dungeon.reference import REFERENCE


def _args(action: Action) -> dict[str, str]:
    names = {"look": [], "move": ["direction"], "take": ["item"], "use": ["item", "direction"]}
    return dict(zip(names[action.tool], action.args, strict=True))


def _play(dungeon: Dungeon, actions: list[Action]) -> list[DungeonMap]:
    """The map after each step, applied from the result JSON exactly as A2 receives it."""
    episode = start_episode(dungeon)
    current = DungeonMap.from_start(json.dumps(AgentTools(episode).start.to_dict()))
    maps = [_copy(current)]
    for action in actions:
        if episode.end_reason is not None:
            break
        result = json.loads(json.dumps(call(episode, action).to_dict()))
        current.apply(action.tool, _args(action), result)
        maps.append(_copy(current))
    return maps


def _copy(m: DungeonMap) -> DungeonMap:
    rooms = {
        k: RoomNote(dict(v.exits), dict(v.leads_to), list(v.items)) for k, v in m.rooms.items()
    }
    return DungeonMap(rooms, m.current, m.inventory, list(m.opened))


def _wall(dungeon: Dungeon) -> str:
    layout = dungeon.layout
    return next(str(d) for d in Direction if layout.door(layout.start, d) is None)


def _route(dungeon: Dungeon) -> list[Action]:
    """The solution with detours: a look, a failed move, locked moves, and back-and-forth moves."""
    route = [Action("look"), Action("move", (_wall(dungeon),))]
    revisits = 2
    for action in dungeon.solution.actions:
        if action.tool == "use":
            route.append(Action("move", (action.args[1],)))  # still locked: fails
        route.append(action)
        if action.tool == "move" and revisits:
            back = str(Direction(action.args[0]).opposite)
            route += [Action("move", (back,)), Action("move", action.args)]
            revisits -= 1
    return route


def _dungeons() -> list[tuple[str, Dungeon]]:
    found = [(name, Dungeon.from_layout(layout)) for name, layout, opt in REFERENCE if opt]
    for level in ("L1", "L2", "L3"):
        found += [(f"{level}-{seed}", generate(level, seed)) for seed in DEV_SEEDS[:3]]
    return found


@pytest.mark.parametrize(
    ("name", "dungeon"), _dungeons(), ids=lambda x: x if isinstance(x, str) else ""
)
def test_map_matches_what_the_results_revealed(name: str, dungeon: Dungeon) -> None:  # SC-007
    route = _route(dungeon)
    maps = _play(dungeon, route)
    frames = build_frames(dungeon, route[: len(maps) - 1])
    ended = frames[-1].end_reason is not None
    for i, actual in enumerate(maps[:-1] if ended else maps):  # the ending batch is not applied
        assert actual == expected_map(dungeon, frames, i), (
            f"step {i}: {route[i - 1] if i else 'start'}"
        )


def _room(
    label: str,
    exits: dict[str, str | None],
    items: tuple[str, ...] = (),
    held: tuple[str, ...] = (),
) -> dict[str, Any]:
    """A successful room-view result, as the tools return it."""
    data = {
        "label": label,
        "exits": [{"direction": d, "lock": lock} for d, lock in exits.items()],
        "items": list(items),
        "inventory": list(held),
        "is_exit": False,
    }
    return {"ok": True, "error": None, "data": data}


def _two_rooms() -> DungeonMap:
    """Start in c3 (north open, east locked red, a red key); e9 lies north."""
    return DungeonMap.from_start(
        json.dumps(_room("c3", {"north": None, "east": "red"}, ("red key",)))
    )


NORTH = _room("e9", {"south": None, "west": None})
FAILED = {"ok": False, "error": {"code": "no_door", "message": "x"}, "data": None}


def test_a_move_records_the_connection_both_ways() -> None:  # US3/AC3
    m = _two_rooms()
    m.apply("move", {"direction": "north"}, NORTH)
    assert m.current == "e9"
    assert m.rooms["c3"].leads_to == {"north": "e9"} and m.rooms["e9"].leads_to == {"south": "c3"}
    assert m.unexplored("c3") == ["east"] and m.unexplored("e9") == ["west"]


def test_failed_results_change_nothing() -> None:
    m = _two_rooms()
    before = _copy(m)
    for name in ("move", "take", "use", "look", "open"):
        m.apply(name, {"direction": "east", "item": "red key"}, FAILED)
    assert m == before


def test_opened_door_keeps_its_color_turns_later() -> None:  # US3/AC4
    m = _two_rooms()
    m.apply(
        "take", {"item": "red key"}, {"ok": True, "error": None, "data": {"inventory": ["red key"]}}
    )
    assert m.inventory == ("red key",) and m.rooms["c3"].items == []
    opened = {"ok": True, "error": None, "data": {"direction": "east", "color": "red"}}
    m.apply("use", {"item": "red key", "direction": "east"}, opened)
    north = _room("e9", {"south": None, "west": None}, held=("red key",))
    m.apply("move", {"direction": "north"}, north)
    m.apply("look", {}, north)
    assert m.opened == [("c3", "east", "red")] and m.rooms["c3"].exits["east"] is None
    text = m.render()
    assert "Doors you opened: c3 east (red)." in text and "Inventory: red key." in text


def test_render_format() -> None:
    m = _two_rooms()
    assert m.render() == (
        "Your map (built from your tool results so far):\n"
        "You are in: c3. Inventory: nothing.\n"
        "Rooms seen:\n"
        "- c3 (you are here): north: unexplored; east: unexplored, locked (red); items: red key\n"
        "Unexplored exits: c3 north; c3 east (locked, red)."
    )
    m.apply("move", {"direction": "north"}, NORTH)
    assert m.render() == (
        "Your map (built from your tool results so far):\n"
        "You are in: e9. Inventory: nothing.\n"
        "Rooms seen:\n"
        "- c3: north -> e9; east: unexplored, locked (red); items: red key\n"
        "- e9 (you are here): south -> c3; west: unexplored\n"
        "Unexplored exits: c3 east (locked, red); e9 west."
    )


def test_invariants_hold_on_every_step() -> None:
    dungeon = generate("L3", 1001)
    for m in _play(dungeon, _route(dungeon)):
        assert m.current in m.rooms
        for label, room in m.rooms.items():
            for direction, target in room.leads_to.items():
                assert target in m.rooms
                assert m.rooms[target].leads_to[str(Direction(direction).opposite)] == label
        for label, direction, _color in m.opened:
            assert m.rooms[label].exits[direction] is None


@pytest.mark.parametrize("seed", DEV_SEEDS)
def test_a_fully_explored_map_fits_a_quarter_of_the_context(seed: int) -> None:  # SC-008
    layout = generate("L3", seed).layout
    rooms = {}
    for pos in layout.rooms():
        exits, leads = {}, {}
        for d in Direction:
            if (edge := layout.door(pos, d)) is not None:
                exits[str(d)] = layout.locks.get(edge)
                leads[str(d)] = layout.labels[edge.other(pos)]
        items = [key_name(c) for c, p in layout.keys.items() if p == pos]
        rooms[layout.labels[pos]] = RoomNote(exits, leads, items)
    full = DungeonMap(rooms, layout.labels[layout.start], (), [])
    # Every room seen but no door walked: the longest text, since each exit is "unexplored".
    unwalked = DungeonMap(
        {k: RoomNote(v.exits, {}, v.items) for k, v in rooms.items()}, full.current, (), []
    )
    # ASCII text: every token covers at least one character, so this bounds the tokens.
    assert len(full.render()) <= 8192 // 4 and len(unwalked.render()) <= 8192 // 4


def test_render_with_routes() -> None:
    m = _two_rooms()
    m.apply("move", {"direction": "north"}, NORTH)
    assert m.render(routes=True).splitlines()[-3:] == [
        "Routes to unexplored exits (through doors you have walked):",
        "- e9 west (1 move): west",
        "- c3 east, locked (red) (2 moves): south, east",
    ]
    assert m.render(routes=True).splitlines()[:-3] == m.render().splitlines()[:-1]


@pytest.mark.parametrize(
    ("name", "dungeon"), _dungeons()[-6:], ids=lambda x: x if isinstance(x, str) else ""
)
def test_every_route_walks_known_doors_to_its_exit(name: str, dungeon: Dungeon) -> None:
    for m in _play(dungeon, _route(dungeon)):
        routes = m.routes()
        assert {(r, d) for r, d, _ in routes} == {(r, d) for r in m.rooms for d in m.unexplored(r)}
        assert [len(moves) for _, _, moves in routes] == sorted(
            len(moves) for _, _, moves in routes
        )
        for room, direction, moves in routes:
            at = m.current
            for move in moves[:-1]:
                at = m.rooms[at].leads_to[move]
            assert at == room and moves[-1] == direction
