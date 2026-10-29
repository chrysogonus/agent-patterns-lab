"""Each broken rule is reported by check_level_rules (FR-001 to FR-008)."""

import dataclasses

from apl.dungeon import DEV_SEEDS, LEVELS, check_level_rules, generate
from apl.dungeon.model import Direction, Dungeon, Edge, Layout, neighbor
from apl.dungeon.rules import distances, ordered_locks


def _with(dungeon: Dungeon, **changes: object) -> list[str]:
    layout = dataclasses.replace(dungeon.layout, **changes)  # type: ignore[arg-type]
    assert dungeon.level is not None
    return check_level_rules(layout, dungeon.level)


def _tags(problems: list[str]) -> set[str]:
    return {p.split(":")[0] for p in problems}


def _near_side(layout: Layout, edge: Edge) -> tuple[int, int]:
    dist = distances(layout, layout.start, layout.doors)
    return edge.a if dist[edge.a] <= dist[edge.b] else edge.b


def test_generated_dungeons_have_no_problems() -> None:
    assert check_level_rules(generate("L3", 1000).layout, LEVELS["L3"]) == []


def test_wrong_size() -> None:
    assert "FR-010 size" in _tags(check_level_rules(generate("L1", 1000).layout, LEVELS["L2"]))


def test_disconnected_room() -> None:
    d = generate("L1", 1000)
    cut_off = {e for e in d.layout.doors if d.layout.exit in (e.a, e.b)}
    assert "FR-002 connected" in _tags(_with(d, doors=d.layout.doors - cut_off))


def test_wrong_extra_door_count() -> None:
    d = generate("L1", 1000)
    missing = next(
        Edge(room, neighbor(room, dr))
        for room in d.layout.rooms()
        for dr in Direction
        if d.layout.in_grid(neighbor(room, dr)) and d.layout.door(room, dr) is None
    )
    assert "FR-002 extra doors" in _tags(_with(d, doors=d.layout.doors | {missing}))


def test_start_and_exit_too_close() -> None:
    d = generate("L1", 1000)
    near_exit = next(
        e.other(d.layout.start) for e in sorted(d.layout.doors) if d.layout.start in (e.a, e.b)
    )
    assert "FR-003 distance" in _tags(_with(d, exit=near_exit))


def test_wrong_lock_count() -> None:
    assert "FR-004 locks" in _tags(check_level_rules(generate("L2", 1000).layout, LEVELS["L1"]))


def test_duplicate_colors_are_a_structure_problem() -> None:
    d = generate("L3", 1000)
    color, room = sorted(d.layout.keys.items())[0]
    same = dict.fromkeys(d.layout.locks, color)
    assert "structure" in _tags(_with(d, locks=same, keys={color: room}))


def test_bypassable_lock() -> None:
    d = generate("L2", 1000)
    ((edge, color),) = d.layout.locks.items()
    off_path = [
        e
        for e in sorted(d.layout.doors)
        if e != edge and d.layout.exit in distances(d.layout, d.layout.start, d.layout.doors - {e})
    ]
    assert "FR-005 necessary" in _tags(_with(d, locks={off_path[0]: color}))


def test_key_in_start_room() -> None:
    d = generate("L2", 1000)
    (color,) = d.layout.keys
    assert "FR-006 start room" in _tags(_with(d, keys={color: d.layout.start}))


def test_key_on_the_shortest_route() -> None:
    for seed in DEV_SEEDS:
        d = generate("L2", seed)
        ((edge, color),) = d.layout.locks.items()
        near = _near_side(d.layout, edge)
        if near != d.layout.start:
            assert "FR-006 detour" in _tags(_with(d, keys={color: near}))
            return
    raise AssertionError("no dev seed with a door away from the start room")


def test_key_behind_its_own_door() -> None:
    d = generate("L2", 1000)
    ((edge, color),) = d.layout.locks.items()
    far = edge.other(_near_side(d.layout, edge))
    assert "FR-006 reachable" in _tags(_with(d, keys={color: far}))


def test_second_key_in_front_of_first_door() -> None:
    d = generate("L3", 1000)
    first, second = ordered_locks(d.layout)
    before_first = distances(d.layout, d.layout.start, d.layout.doors - {first})
    room = next(r for r in sorted(before_first) if r != d.layout.start)
    keys = {**d.layout.keys, d.layout.locks[second]: room}
    assert "FR-007 chained" in _tags(_with(d, keys=keys))


def test_too_few_dead_ends() -> None:
    d = generate("L3", 1000)
    strict = dataclasses.replace(LEVELS["L3"], min_dead_ends=99)
    assert "FR-008 dead ends" in _tags(check_level_rules(d.layout, strict))
