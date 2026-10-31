"""The environment against contracts/tools.md and contracts/outcome.md."""

import pytest

from apl.dungeon.env import Episode, start_episode
from apl.dungeon.model import Action, Dungeon, Layout
from apl.dungeon.results import EndReason, ErrorCode, RoomView, ToolResult
from tests.dungeon.reference import chained_keys, locked_shortcut_wins, two_open_routes


def _episode(layout: Layout) -> Episode:
    return start_episode(Dungeon.from_layout(layout))


def _code(result: ToolResult) -> ErrorCode | None:
    return result.error.code if result.error else None


def _assert_error(episode: Episode, result: ToolResult, code: ErrorCode, steps: int) -> None:
    assert not result.ok and _code(result) == code and result.data is None
    assert episode.steps == steps


def test_start_description_is_free() -> None:
    episode = _episode(locked_shortcut_wins())
    start = episode.describe()
    assert episode.steps == 0
    assert episode.look().data == start
    assert episode.steps == 1
    assert start.label == "a2" and not start.is_exit
    assert [str(e.direction) for e in start.exits] == ["east", "south"]


def test_invalid_direction() -> None:
    episode = _episode(two_open_routes())
    _assert_error(episode, episode.move("up"), ErrorCode.INVALID_DIRECTION, 1)
    assert episode.position == (0, 0)


def test_no_door() -> None:
    episode = _episode(two_open_routes())
    _assert_error(episode, episode.move("north"), ErrorCode.NO_DOOR, 1)
    _assert_error(episode, episode.use("red key", "west"), ErrorCode.NO_DOOR, 2)


def test_locked() -> None:
    episode = _episode(locked_shortcut_wins())
    episode.move("east")
    result = episode.move("east")
    _assert_error(episode, result, ErrorCode.LOCKED, 2)
    assert result.error is not None and "red" in result.error.message
    assert episode.position == (1, 0)


def test_no_such_item() -> None:
    episode = _episode(locked_shortcut_wins())
    _assert_error(episode, episode.take("red key"), ErrorCode.NO_SUCH_ITEM, 1)


def test_not_in_inventory() -> None:
    episode = _episode(locked_shortcut_wins())
    episode.move("east")
    _assert_error(episode, episode.use("red key", "east"), ErrorCode.NOT_IN_INVENTORY, 2)


def test_wrong_key() -> None:
    episode = _episode(chained_keys())
    for call in ["south", "take", "north", "east", "use", "east", "south"]:
        if call == "take":
            episode.take("red key")
        elif call == "use":
            episode.use("red key", "east")
        else:
            episode.move(call)
    assert episode.position == (2, 1)
    _assert_error(episode, episode.use("red key", "south"), ErrorCode.WRONG_KEY, 8)
    assert episode.describe().exits[-1].lock == "blue"


def test_not_locked() -> None:
    episode = _episode(locked_shortcut_wins())
    episode.move("east")
    episode.take("red key")
    _assert_error(episode, episode.use("red key", "west"), ErrorCode.NOT_LOCKED, 3)
    episode.use("red key", "east")
    _assert_error(episode, episode.use("red key", "east"), ErrorCode.NOT_LOCKED, 5)


def test_episode_over_counts_nothing() -> None:
    episode = _episode(two_open_routes())
    episode.move("east")
    episode.move("east")
    assert episode.end_reason == EndReason.EXIT
    before = (episode.position, episode.steps, list(episode.inventory))
    for result in [episode.look(), episode.move("west"), episode.take("x"), episode.use("x", "y")]:
        assert _code(result) == ErrorCode.EPISODE_OVER
    assert (episode.position, episode.steps, list(episode.inventory)) == before
    assert episode.invalid_actions == 0


def test_error_precedence() -> None:
    episode = _episode(locked_shortcut_wins())
    assert _code(episode.use("red key", "up")) == ErrorCode.INVALID_DIRECTION


def test_take_and_use_open_the_door_both_ways() -> None:
    episode = _episode(locked_shortcut_wins())
    episode.move("east")
    taken = episode.take("red key")
    assert taken.to_dict() == {"ok": True, "error": None, "data": {"inventory": ["red key"]}}
    opened = episode.use("red key", "east")
    assert opened.to_dict()["data"] == {"direction": "east", "color": "red"}
    room = episode.describe()
    assert isinstance(room, RoomView) and room.items == () and room.inventory == ("red key",)
    assert [e.lock for e in room.exits] == [None, None]
    episode.move("east")
    assert episode.end_reason == EndReason.EXIT
    assert episode.outcome().success and episode.steps == 4


def test_opened_door_is_open_from_the_other_side() -> None:
    episode = _episode(chained_keys())
    episode.move("south")
    episode.take("red key")
    episode.move("north")
    episode.move("east")
    episode.use("red key", "east")
    episode.move("east")
    assert episode.move("west").ok and episode.move("east").ok
    assert episode.inventory == ["red"]


def test_exit_on_the_last_step_is_a_success() -> None:
    episode = _episode(two_open_routes())  # optimal 2, budget 12
    for _ in range(10):
        episode.move("north")
    episode.move("east")
    episode.move("east")
    outcome = episode.outcome()
    assert outcome.steps == 12 and outcome.success and not outcome.budget_hit


def test_budget_runs_out() -> None:
    episode = _episode(two_open_routes())
    for _ in range(12):
        episode.look()
    outcome = episode.outcome()
    assert outcome.end_reason == EndReason.BUDGET and outcome.budget_hit and not outcome.success
    assert outcome.invalid_actions == 0


def test_stop_costs_nothing_and_is_idempotent() -> None:
    episode = _episode(two_open_routes())
    episode.move("east")
    episode.stop()
    episode.stop()
    assert episode.end_reason == EndReason.STOPPED and episode.steps == 1


def test_outcome_before_the_end_raises() -> None:
    with pytest.raises(RuntimeError):
        _episode(two_open_routes()).outcome()


def test_outcome_shape_and_log() -> None:
    episode = _episode(two_open_routes())
    episode.move("up")
    episode.move("east")
    episode.move("east")
    episode.look()
    data = episode.outcome().to_dict()
    assert list(data) == [
        "level",
        "seed",
        "success",
        "end_reason",
        "steps",
        "optimal_steps",
        "budget",
        "invalid_actions",
        "budget_hit",
        "log",
    ]
    assert data["level"] is None and data["seed"] is None
    assert (data["steps"], data["optimal_steps"], data["budget"]) == (3, 2, 12)
    assert (data["invalid_actions"], data["end_reason"], data["success"]) == (1, "exit", True)
    log = data["log"]
    assert isinstance(log, list)
    assert [e["step"] for e in log] == [1, 2, 3, None]
    assert log[0]["action"] == {"tool": "move", "args": ["up"]}
    assert log[3]["result"]["error"]["code"] == "episode_over"


def test_revisit_shows_the_same_label() -> None:
    episode = _episode(two_open_routes())
    first = episode.describe().label
    episode.move("south")
    episode.move("south")
    episode.move("north")
    episode.move("north")
    assert episode.describe().label == first


def test_unknown_tool_costs_a_step() -> None:
    episode = _episode(two_open_routes())
    result = episode.unknown("open")
    _assert_error(episode, result, ErrorCode.UNKNOWN_TOOL, 1)
    assert result.error is not None and "'open'" in result.error.message
    assert all(t in result.error.message for t in ("look", "move", "take", "use"))
    assert episode.invalid_actions == 1
    assert episode.log[-1].to_dict()["action"] == {"tool": "unknown", "args": ["open"]}
    episode.stop()
    _assert_error(episode, episode.unknown("open"), ErrorCode.EPISODE_OVER, 1)


def test_unknown_is_a_one_argument_pseudo_tool() -> None:
    assert Action.parse({"tool": "unknown", "args": ["open"]}) == Action("unknown", ("open",))
    with pytest.raises(ValueError):
        Action("unknown", ())
