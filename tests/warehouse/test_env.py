"""One warehouse episode: views, results, errors, robots and counts (specs/012 T008)."""

from apl.warehouse import start_episode
from apl.warehouse.env import MAX_SCOUTS, Episode
from apl.warehouse.plans import play
from tests.warehouse.floors import p2_floor


def _data(result: object) -> dict[str, object]:
    found = result.to_dict()  # type: ignore[attr-defined]
    assert isinstance(found, dict)
    return found


def _error(result: object) -> tuple[str, str]:
    error = _data(result)["error"]
    assert isinstance(error, dict)
    return error["code"], error["message"]


def test_the_start_view_and_look() -> None:
    episode = start_episode(p2_floor())
    start = episode.start_view().to_dict()
    assert start == {
        "cell": "A2", "corridors": ["west corridor"], "packages_seen": [], "carrying": None,
        "on_drop": False, "delivered": 0, "packages": 3, "columns": 9, "rows": 5,
        "floor": [".........", "S#######D", ".........", ".#######.", "........."],
        "aisles": ["aisle 1", "aisle 2", "aisle 3"],
    }  # fmt: skip
    looked = _data(episode.look())
    assert looked["ok"] is True and looked["data"] == episode.describe().to_dict()
    assert "floor" not in looked["data"]
    assert episode.steps == 1


def test_a_robot_sees_the_packages_of_its_corridors_only() -> None:
    episode = start_episode(p2_floor())
    view = _data(episode.move("south"))["data"]
    assert view == {
        "cell": "A3", "corridors": ["aisle 2", "west corridor"], "packages_seen": [],
        "carrying": None, "on_drop": False, "delivered": 0, "packages": 3, "columns": 9, "rows": 5,
    }  # fmt: skip
    episode.move("south")
    view = _data(episode.move("south"))["data"]
    assert view["packages_seen"] == [  # type: ignore[index]
        {"package": "package 1", "cell": "B5"},
        {"package": "package 3", "cell": "G5"},
    ]


def test_errors_cost_a_step_and_change_nothing() -> None:
    episode = start_episode(p2_floor())
    assert _error(episode.move("up")) == (
        "invalid_direction",
        "'up' is not a direction; use north, east, south or west.",
    )
    assert _error(episode.move("east")) == ("shelf", "There is a shelf to the east.")
    assert _error(episode.move("west")) == ("edge", "The floor ends to the west.")
    assert _error(episode.pick()) == ("no_package", "There is no package on A2.")
    assert _error(episode.drop()) == ("not_carrying", "You carry nothing.")
    assert _error(episode.unknown("push")) == (
        "unknown_tool",
        "There is no tool named 'push'. The tools are look, move, pick and drop.",
    )
    assert episode.steps == episode.invalid_actions == 6
    assert episode.robots == [(0, 1)]


def test_picking_and_delivering() -> None:
    episode = start_episode(p2_floor())
    for d in ["north", "east", "east", "east", "east"]:
        episode.move(d)
    assert _data(episode.pick())["data"] == {"picked": "package 2", "cell": "E1"}
    assert _error(episode.pick()) == ("already_carrying", "You already carry package 2.")
    assert _error(episode.drop()) == ("not_on_drop", "You can drop only on D.")
    for d in ["east"] * 4 + ["south"]:
        episode.move(d)
    assert episode.describe().on_drop and episode.describe().carrying == "package 2"
    assert _data(episode.drop())["data"] == {
        "delivered_package": "package 2",
        "delivered": 1,
        "packages": 3,
    }
    assert episode.end_reason is None


def test_the_last_delivery_ends_the_episode() -> None:
    floor = p2_floor()
    episode = start_episode(floor)
    play(episode, floor.reference)
    assert str(episode.end_reason) == "delivered" and episode.outcome().success
    after = _data(episode.look())
    assert after["error"] == {"code": "episode_over", "message": "The episode is over."}
    assert episode.log[-1].step is None


def test_the_budget_ends_the_episode_and_stop() -> None:
    floor = p2_floor()
    episode = start_episode(floor)
    for _ in range(floor.budget):
        episode.look()
    assert str(episode.end_reason) == "budget" and episode.outcome().budget_hit
    stopped = start_episode(floor)
    stopped.stop()
    assert str(stopped.end_reason) == "stopped"


def test_robots_are_added_on_the_dock_up_to_four() -> None:
    episode = start_episode(p2_floor())
    turn = [7]
    episode.turn_source = lambda: turn[0]
    assert [episode.add_scout() for _ in range(4)] == [1, 2, 3, None]
    assert MAX_SCOUTS == 4 and episode.robots == [(0, 1)] * 4
    assert episode.added_turn == [0, 7, 7, 7]
    assert episode.restart() is False


def test_two_robots_on_one_cell_pick_in_order() -> None:
    episode = start_episode(p2_floor())
    episode.add_scout()
    for robot in (0, 1):
        for d in ["north", "east", "east", "east", "east"]:
            episode.move(d, scout=robot)
    assert _data(episode.pick(scout=0))["ok"] is True
    assert _error(episode.pick(scout=1))[0] == "no_package"


def _rebuilt(episode: Episode) -> tuple[int, int, int]:
    """Delivered, parallel turns and idle robot-turns from the saved outcome alone (SC-006)."""
    saved = episode.outcome().to_dict()
    log = saved["log"]
    assert isinstance(log, list)
    counted = [e for e in log if e["step"] is not None]
    delivered = sum(1 for e in counted if e["action"]["tool"] == "drop" and e["result"]["ok"])
    turns = sorted({e.get("turn", e["step"]) for e in counted})
    added = saved["added_turns"]
    assert isinstance(added, list)
    idle = 0
    for t in turns:
        acting = {e.get("scout", 0) for e in counted if e.get("turn", e["step"]) == t}
        idle += sum(1 for a in added if a <= t) - len(acting)
    return delivered, len(turns), idle


def test_the_counts_are_rebuilt_from_the_saved_log() -> None:
    from apl.warehouse.plans import blind_split

    episode = blind_split(p2_floor())
    outcome = episode.outcome()
    saved = outcome.to_dict()
    for key in ("delivered", "packages", "parallel_turns", "idle_robot_turns"):
        assert key in saved
    assert saved["reference_is_optimal"] is False and saved["scouts"] == 3
    assert _rebuilt(episode) == (
        outcome.delivered,
        outcome.parallel_turns,
        outcome.idle_robot_turns,
    )
