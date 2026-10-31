"""Several scouts in one episode (specs/004 contracts/scouts.md, US1)."""

import pytest

from apl.dungeon.env import MAX_SCOUTS, Episode, start_episode
from apl.dungeon.model import Dungeon
from apl.dungeon.results import EndReason, ErrorCode, RoomView
from tests.dungeon.reference import locked_shortcut_wins, two_open_routes

# locked_shortcut_wins: a2 (start) east a3 (red key), east through red to a4 (exit);
# a2 south is the ring.


def _episode() -> Episode:
    return start_episode(Dungeon.from_layout(locked_shortcut_wins()))


def _label(episode: Episode, scout: int) -> str:
    return episode.describe(scout=scout).label


def test_scouts_have_their_own_positions_and_share_the_steps() -> None:  # 1.1
    episode = _episode()
    assert episode.add_scout() == 1
    assert episode.move("east").ok and episode.move("south", scout=1).ok
    assert (_label(episode, 0), _label(episode, 1)) == ("a3", "a5")
    assert episode.steps == 2


def test_a_key_held_by_another_scout_does_not_open_the_door() -> None:  # 1.2
    episode = _episode()
    episode.add_scout()
    episode.move("east")
    episode.take("red key")
    episode.move("east", scout=1)
    result = episode.use("red key", "east", scout=1)
    assert result.error is not None and result.error.code == ErrorCode.NOT_IN_INVENTORY
    assert episode.steps == 4 and not episode.opened
    assert episode.describe(scout=1).inventory == () and episode.inventory == ["red"]


def test_a_door_opened_by_one_scout_is_open_for_all() -> None:  # 1.3
    episode = _episode()
    episode.add_scout()
    episode.move("east")
    episode.take("red key")
    assert episode.use("red key", "east").ok
    episode.move("east", scout=1)
    assert episode.move("east", scout=1).ok  # through scout 0's door, into the exit


def test_any_scout_in_the_exit_ends_the_episode() -> None:  # 1.4
    episode = _episode()
    episode.add_scout()
    episode.move("south")
    episode.move("east", scout=1)
    episode.take("red key", scout=1)
    episode.use("red key", "east", scout=1)
    episode.move("east", scout=1)
    assert episode.end_reason == EndReason.EXIT and episode.steps == 5
    late = episode.move("north")
    assert late.error is not None and late.error.code == ErrorCode.EPISODE_OVER
    assert episode.outcome().steps == 5


def test_the_budget_is_shared() -> None:  # 1.5
    episode = _episode()
    episode.add_scout()
    for i in range(episode.dungeon.budget):
        episode.look(scout=i % 2)
    assert episode.end_reason == EndReason.BUDGET
    late = episode.look(scout=1)
    assert late.error is not None and late.error.code == ErrorCode.EPISODE_OVER
    assert episode.steps == episode.dungeon.budget


def test_at_most_four_scouts() -> None:  # 1.6
    episode = _episode()
    assert [episode.add_scout() for _ in range(4)] == [1, 2, 3, None]
    assert MAX_SCOUTS == 4 and len(episode.scouts) == 4
    assert episode.steps == 0 and episode.log == []


def test_an_unknown_scout_is_an_error() -> None:
    episode = _episode()
    with pytest.raises(ValueError, match="scout 1"):
        episode.look(scout=1)


def test_a_new_scout_starts_in_the_start_room_with_nothing() -> None:
    episode = _episode()
    episode.move("east")
    episode.take("red key")
    number = episode.add_scout()
    assert number is not None
    room = episode.describe(scout=number)
    assert isinstance(room, RoomView) and room.label == "a2" and room.inventory == ()


def test_keys_held_by_any_scout_are_gone_from_the_rooms() -> None:
    episode = _episode()
    episode.add_scout()
    episode.move("east", scout=1)
    episode.take("red key", scout=1)
    assert episode.keys_in_rooms == {}
    assert episode.take("red key").error is not None


def test_logs_name_scouts_only_when_there_are_several() -> None:
    single = start_episode(Dungeon.from_layout(two_open_routes()))
    single.move("east")
    single.move("east")
    data = single.outcome().to_dict()
    entries = data["log"]
    assert isinstance(entries, list) and "scouts" not in data
    assert all("scout" not in e for e in entries)

    episode = _episode()
    episode.add_scout()
    episode.move("south")
    episode.move("east", scout=1)
    episode.stop()
    data = episode.outcome().to_dict()
    assert data["scouts"] == 2
    log = data["log"]
    assert isinstance(log, list) and "scout" not in log[0] and log[1]["scout"] == 1
