"""Attempts on the dungeon: restart, logs, outcomes and replay (specs/007 contracts/attempts.md)."""

import json

from apl.dungeon import generate, start_episode
from apl.dungeon.env import MAX_ATTEMPTS, Episode
from apl.dungeon.frames import call, parse_route_file

DUNGEON = generate("L3", 1002)  # keys and locked doors
ALMOST = DUNGEON.solution.actions[:-1]  # every take and use, but not the exit


def _state(episode: Episode) -> tuple[object, ...]:
    scouts = [(s.position, tuple(s.inventory)) for s in episode.scouts]
    return episode.describe(), dict(episode.keys_in_rooms), set(episode.opened), scouts


def _played(max_attempts: int = MAX_ATTEMPTS) -> Episode:
    episode = start_episode(DUNGEON)
    episode.max_attempts = max_attempts
    for action in ALMOST:
        call(episode, action)
    return episode


def test_a_restart_puts_the_world_back_and_keeps_the_steps() -> None:  # SC-002
    assert MAX_ATTEMPTS == 3
    assert any(a.tool == "use" for a in ALMOST) and any(a.tool == "take" for a in ALMOST)
    episode = _played()
    episode.unknown("dance")  # a failed call: counted as a step and as invalid
    steps, invalid = episode.steps, episode.invalid_actions
    restarts: list[int] = []
    episode.on_restart = lambda: restarts.append(episode.attempt)
    assert episode.restart() is True
    assert _state(episode) == _state(start_episode(DUNGEON))
    assert (episode.steps, episode.invalid_actions, episode.attempt) == (steps, invalid, 2)
    assert restarts == [2] and len(episode.log) == steps


def test_restarts_are_refused_at_the_cap_after_the_end_and_by_default() -> None:  # SC-003
    episode = _played()
    assert episode.restart() and episode.restart()
    assert episode.attempt == 3 and episode.restart() is False and episode.attempt == 3
    one = _played(max_attempts=1)
    before = _state(one)
    assert one.restart() is False and _state(one) == before and one.attempt == 1
    ended = _played()
    call(ended, DUNGEON.solution.actions[-1])
    assert ended.end_reason is not None and ended.restart() is False


def test_logs_and_outcomes_name_the_attempt_only_after_a_restart() -> None:
    episode = _played()
    first = len(episode.log)
    episode.restart()
    episode.look()
    episode.stop()
    entries = [e.to_dict() for e in episode.log]
    assert all("attempt" not in e for e in entries[:first])
    assert entries[first]["attempt"] == 2
    assert episode.outcome().to_dict()["attempts"] == 2
    single = _played(max_attempts=1)
    single.stop()
    data = single.outcome().to_dict()
    assert "attempts" not in data
    assert all("attempt" not in e.to_dict() for e in single.log)


def test_a_logged_episode_with_restarts_replays_exactly() -> None:  # SC-005
    episode = _played()
    episode.restart()
    for action in DUNGEON.solution.actions[:3]:
        call(episode, action)
    episode.restart()  # a restart with no later action, then the architecture stops
    episode.stop()
    record = json.loads(json.dumps(episode.outcome().to_dict()))
    frames = parse_route_file(record).frames(DUNGEON)
    assert len(frames) == len(record["log"]) + 2  # the trailing restart adds a frame
    positions = [f.position for f in frames[1:-1]]
    replayed = start_episode(DUNGEON)
    replayed.max_attempts = MAX_ATTEMPTS
    expected = []
    for action in ALMOST:
        call(replayed, action)
        expected.append(replayed.position)
    replayed.restart()
    for action in DUNGEON.solution.actions[:3]:
        call(replayed, action)
        expected.append(replayed.position)
    assert positions == expected
    assert frames[len(ALMOST)].attempt == 1 and frames[len(ALMOST) + 1].attempt == 2
    assert frames[len(ALMOST) + 1].to_dict()["attempt"] == 2
    assert "attempt" not in frames[1].to_dict()
    assert frames[-1].attempt == 3 and frames[-1].position == DUNGEON.layout.start
    assert str(frames[-1].end_reason) == "stopped"
