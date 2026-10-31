"""Frames replay routes through the real environment (research R7, SC-012)."""

import pytest

from apl.dungeon import DEV_SEEDS, LEVELS, generate, start_episode
from apl.dungeon.env import Episode
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


def _scripted_scouts(dungeon: Dungeon, scouts: int, turns: int) -> Episode:
    """Scouts take turns walking the solution, each from its own start; a fixed script."""
    episode = start_episode(dungeon)
    for _ in range(scouts - 1):
        episode.add_scout()
    actions = dungeon.solution.actions
    for i in range(turns):
        scout, action = i % scouts, actions[(i // scouts) % len(actions)]
        getattr(episode, action.tool)(*action.args, scout=scout)
        if episode.end_reason is not None:
            break
    if episode.end_reason is None:
        episode.stop()
    return episode


@pytest.mark.parametrize(
    ("level", "seed", "scouts"),
    [("L1", 1000, 2), ("L1", 1003, 3), ("L2", 1001, 2), ("L2", 1004, 4), ("L3", 1002, 3)],
)
def test_several_scouts_replay_exactly(level: str, seed: int, scouts: int) -> None:  # SC-002
    dungeon = generate(level, seed)
    episode = _scripted_scouts(dungeon, scouts, turns=40)
    route = parse_route_file(episode.outcome().to_dict())
    frames = route.frames(dungeon)  # raises if any replayed result differs from the log
    live = start_episode(dungeon)
    for _ in range(scouts - 1):
        live.add_scout()
    for frame, entry in zip(frames[1:], episode.log, strict=True):
        getattr(live, entry.action.tool)(*entry.action.args, scout=entry.scout)
        views = [(s.position, tuple(s.inventory)) for s in live.scouts]
        assert [(v.position, v.inventory) for v in frame.scouts] == views
        assert frame.opened == frozenset(live.opened)
        assert frame.to_dict()["scouts"] == [
            {"position": list(p), "inventory": list(i)} for p, i in views
        ]


def test_single_scout_frames_have_no_scouts_field() -> None:
    dungeon = Dungeon.from_layout(locked_shortcut_wins())
    frames = build_frames(dungeon, dungeon.solution.actions)
    assert all("scouts" not in f.to_dict() for f in frames)
    assert parse_route_file({"actions": [{"tool": "look"}]}).scouts == [0]
