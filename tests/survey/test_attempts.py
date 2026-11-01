"""Attempts on the survey field: restart and the wrong total (specs/007 data-model.md)."""

import json

from apl.survey import generate, start_episode
from apl.survey.env import MAX_ATTEMPTS, Episode
from apl.survey.frames import snapshot

FIELD = generate("S1", 1000)  # 6 deposits


def _walked(max_attempts: int = MAX_ATTEMPTS, moves: int = 7) -> Episode:
    episode = start_episode(FIELD)
    episode.max_attempts = max_attempts
    for direction in FIELD.walk[:moves]:
        episode.move(direction)
    return episode


def test_a_restart_puts_the_field_back_and_keeps_the_steps() -> None:  # SC-002
    assert MAX_ATTEMPTS == 3
    episode = _walked()
    seen = set(episode.seen)
    steps = episode.steps
    assert episode.restart() is True
    fresh = start_episode(FIELD)
    assert episode.scouts == fresh.scouts and episode.seen == fresh.seen
    assert episode.describe() == fresh.describe()
    assert (episode.steps, episode.attempt) == (steps, 2)
    episode.move(FIELD.walk[0])
    episode.stop()
    assert episode.seen_ever >= seen and episode.outcome().cells_seen == len(episode.seen_ever)
    assert episode.outcome().to_dict()["attempts"] == 2


def test_restarts_are_refused_at_the_cap_and_by_default() -> None:  # SC-003
    episode = _walked()
    assert episode.restart() and episode.restart() and not episode.restart()
    one = _walked(max_attempts=1)
    assert one.restart() is False and one.attempt == 1
    one.stop()
    assert "attempts" not in one.outcome().to_dict()


def test_a_wrong_total_ends_the_attempt_and_says_nothing_more() -> None:  # FR-004, SC-004
    episode = _walked()
    restarts: list[int] = []
    episode.on_restart = lambda: restarts.append(episode.attempt)
    result = episode.submit(4).to_dict()
    assert result["ok"] and result["data"] == {
        "submitted": 4, "correct": False, "attempts_left": 2,
    }  # fmt: skip
    text = json.dumps(result)
    assert "6" not in text and "2" not in text.replace('"attempts_left": 2', "")  # no total, no gap
    assert episode.end_reason is None and episode.attempt == 2 and restarts == [2]
    assert episode.scouts == [FIELD.start] and episode.seen == {FIELD.start}
    entries = [e.to_dict() for e in episode.log]
    assert "attempt" not in entries[-1]  # the submission belongs to attempt 1
    assert snapshot(episode, len(entries), None, None)["attempt"] == 2


def test_a_right_total_or_the_last_wrong_one_ends_the_episode() -> None:
    right = _walked()
    right.submit(4)
    right.submit(6)
    assert right.outcome().success and right.outcome().attempts == 2
    last = _walked()
    last.submit(1)
    last.submit(2)
    result = last.submit(3).to_dict()
    assert result["data"] == {"submitted": 3}
    outcome = last.outcome()
    assert str(outcome.end_reason) == "submitted" and outcome.submitted_total == 3
    assert not outcome.success and outcome.attempts == 3


def test_without_attempts_a_wrong_total_ends_the_episode_as_before() -> None:
    episode = _walked(max_attempts=1)
    assert episode.submit(4).to_dict()["data"] == {"submitted": 4}
    assert str(episode.end_reason) == "submitted"
    assert "attempt" not in snapshot(episode, 1, None, None)
