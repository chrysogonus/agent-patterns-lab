"""The floor map: the warehouse memory of A2 and the scouts (specs/012 contracts)."""

import json

from apl.arch.floor_map import FloorMap
from apl.warehouse import Episode, start_episode
from apl.warehouse.kit import build_kit
from apl.warehouse.model import cell_name
from apl.warehouse.plans import apply
from tests.warehouse.floors import p2_floor


def _start() -> tuple[FloorMap, Episode]:
    episode = start_episode(p2_floor())
    kit = build_kit(episode, model=None)  # type: ignore[arg-type]
    return FloorMap.from_start(kit.start), episode


def test_the_start() -> None:
    found, _ = _start()
    assert (found.columns, found.rows, found.total) == (9, 5, 3)
    assert found.current == "A2" and found.carrying is None and found.delivered == 0
    assert found.seen == ["west corridor"] and found.packages == {}
    assert found.aisles == ["aisle 1", "aisle 2", "aisle 3"]


def test_views_picks_and_deliveries() -> None:
    found, _ = _start()
    view = {
        "cell": "A1", "corridors": ["aisle 1", "west corridor"],
        "packages_seen": [{"package": "package 2", "cell": "E1"}], "carrying": None,
        "on_drop": False, "delivered": 0, "packages": 3, "columns": 9, "rows": 5,
    }  # fmt: skip
    found.apply("move", {"direction": "north"}, {"ok": True, "error": None, "data": view})
    assert found.current == "A1" and found.packages == {"package 2": "E1"}
    assert found.seen == ["west corridor", "aisle 1"]
    found.apply(
        "pick", {}, {"ok": True, "error": None, "data": {"picked": "package 2", "cell": "E1"}}
    )
    assert found.carrying == "package 2" and found.packages == {}
    dropped = {"delivered_package": "package 2", "delivered": 1, "packages": 3}
    found.apply("drop", {}, {"ok": True, "error": None, "data": dropped})
    assert found.carrying is None and found.delivered == 1
    found.apply("move", {}, {"ok": False, "error": {"code": "shelf", "message": "x"}, "data": None})
    assert found.current == "A1"


def test_a_view_forgets_packages_gone_from_its_corridors() -> None:
    found, _ = _start()
    found.packages = {"package 2": "E1", "package 1": "B5"}
    view = {
        "cell": "A1", "corridors": ["aisle 1", "west corridor"], "packages_seen": [],
        "carrying": None, "on_drop": False, "delivered": 1, "packages": 3, "columns": 9, "rows": 5,
    }  # fmt: skip
    found.apply("move", {"direction": "north"}, {"ok": True, "error": None, "data": view})
    assert found.packages == {"package 1": "B5"}


def test_the_rendering() -> None:
    found, _ = _start()
    found.packages = {"package 3": "D3"}
    found.seen = ["west corridor", "aisle 2"]
    lines = found.render({1: "C3"}).split("\n")
    assert lines[0] == "Your map (built from your tool results so far):"
    assert (
        lines[1]
        == "You are in: A2 (west corridor). You carry: nothing. Delivered: 0 of 3 packages."
    )
    assert lines[2] == "   A B C D E F G H I"
    assert lines[3] == "1  . ? ? ? ? ? ? ? ?"
    assert lines[4] == "2  @ # # # # # # # D"
    assert lines[5] == "3  . . 1 P . . . . ."
    assert (
        "Corridors seen: west corridor, aisle 2. Not seen yet: aisle 1, aisle 3, east corridor."
        in lines
    )
    assert "Packages seen: package 3 at D3." in lines
    orchestrator = found.render({0: "A2"}, here=False).split("\n")
    assert orchestrator[1] == "Delivered: 0 of 3 packages."


def test_the_map_follows_the_episode() -> None:
    found, episode = _start()
    floor = p2_floor()
    for action in floor.reference:
        apply(episode, action)
        done = episode.log[-1].result.to_dict()
        found.apply(action.tool, {}, json.loads(json.dumps(done)))
        waiting = {n: cell_name(c) for n, c in episode.waiting.items() if c in episode.seen}
        assert found.packages == waiting
        assert found.delivered == len(episode.delivered)
