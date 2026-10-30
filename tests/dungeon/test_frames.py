"""Frames replay routes through the real environment (research R7, SC-012)."""

import pytest

from apl.dungeon import DEV_SEEDS, LEVELS, generate, start_episode
from apl.dungeon.frames import build_frames, parse_route_file
from apl.dungeon.model import Action, Dungeon
from apl.dungeon.results import EndReason
from tests.dungeon.reference import locked_shortcut_wins


@pytest.mark.parametrize("level", sorted(LEVELS))
def test_frames_match_the_environment_after_every_step(level: str) -> None:
    for seed in DEV_SEEDS:
        dungeon = generate(level, seed)
        actions = dungeon.solution.actions
        frames = build_frames(dungeon, actions)
        assert len(frames) == len(actions) + 1
        episode = start_episode(dungeon)
        assert (frames[0].step, frames[0].action, frames[0].position) == (0, None, episode.position)
        for frame, action in zip(frames[1:], actions, strict=True):
            getattr(episode, action.tool)(*action.args)
            assert frame.action == action and frame.ok
            assert frame.position == episode.position
            assert frame.inventory == tuple(episode.inventory)
            assert dict(frame.keys_in_rooms) == episode.keys_in_rooms
            assert frame.opened == frozenset(episode.opened)
        assert frames[-1].end_reason == "exit"


def test_failed_actions_do_not_move() -> None:
    dungeon = Dungeon.from_layout(locked_shortcut_wins())
    frames = build_frames(dungeon, [Action("move", ("north",)), Action("move", ("up",))])
    assert [f.ok for f in frames[1:]] == [False, False]
    assert [f.error_code for f in frames[1:]] == ["no_door", "invalid_direction"]
    assert {f.position for f in frames} == {(0, 0)}


def test_log_replay_must_match() -> None:
    dungeon = Dungeon.from_layout(locked_shortcut_wins())
    episode = start_episode(dungeon)
    episode.move("east")
    episode.take("red key")
    episode.stop()
    route = parse_route_file(episode.outcome().to_dict())
    frames = route.frames(dungeon)
    assert len(frames) == 3 and frames[-1].end_reason == "stopped"
    assert route.results is not None
    route.results[1] = {
        "ok": False,
        "error": {"code": "no_such_item", "message": "x"},
        "data": None,
    }
    with pytest.raises(ValueError, match="step 2"):
        route.frames(dungeon)


def test_stopped_log_with_calls_after_the_stop_replays() -> None:
    dungeon = Dungeon.from_layout(locked_shortcut_wins())
    episode = start_episode(dungeon)
    episode.look()
    episode.stop()
    episode.look()
    episode.move("east")
    frames = parse_route_file(episode.outcome().to_dict()).frames(dungeon)
    assert [f.end_reason for f in frames] == [None, None, "stopped", "stopped"]
    assert [f.error_code for f in frames[2:]] == ["episode_over", "episode_over"]
    assert {f.position for f in frames} == {(0, 0)}


def test_log_end_reason_must_match() -> None:
    dungeon = Dungeon.from_layout(locked_shortcut_wins())
    with pytest.raises(ValueError, match="ended with exit"):
        build_frames(dungeon, [Action("look")], end_reason=EndReason.EXIT)


@pytest.mark.parametrize(
    "data",
    [
        [],
        {"actions": "east"},
        {"actions": [{"tool": "fly", "args": []}]},
        {"log": [{}]},
        {"log": [], "end_reason": []},
        {"log": [], "end_reason": "won"},
        3,
    ],
)
def test_bad_route_files_are_rejected(data: object) -> None:
    with pytest.raises(ValueError):
        parse_route_file(data)


def test_log_with_an_unknown_tool_replays() -> None:
    dungeon = Dungeon.from_layout(locked_shortcut_wins())
    episode = start_episode(dungeon)
    episode.move("east")
    episode.unknown("open")
    episode.stop()
    record = episode.outcome().to_dict()
    frames = parse_route_file(record).frames(dungeon)
    assert [f.action for f in frames[1:]] == [
        Action("move", ("east",)),
        Action("unknown", ("open",)),
    ]
    assert frames[-1].error_code == "unknown_tool" and frames[-1].end_reason == EndReason.STOPPED
