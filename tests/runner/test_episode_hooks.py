"""Observation hooks and context overflow (research R3, R10)."""

from typing import Any
from uuid import UUID

import pytest
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage

from apl.dungeon import generate, start_episode
from apl.dungeon.env import Episode, LogEntry
from apl.dungeon.frames import build_frames, call, snapshot
from apl.runner.episode import PermanentProviderError, play_episode
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from tests.runner import loop_arch
from tests.runner.scripted import (
    FakeProviderError,
    raise_error,
    replay_solution,
    scripted_factory,
    then,
)

KEY = EpisodeKey("loop", "L1", 1000, 1)
OVERFLOW = "This model's maximum context length is 8192 tokens. However, you requested 9000 tokens."


def test_on_step_sees_every_logged_call() -> None:
    dungeon = generate("L1", 1000)
    episode = start_episode(dungeon)
    seen: list[LogEntry] = []
    episode.on_step = seen.append
    for action in dungeon.solution.actions:
        call(episode, action)
    episode.look()  # after the exit: an uncounted episode_over call
    assert seen == episode.log
    assert seen[-1].step is None


def test_snapshot_matches_build_frames() -> None:
    dungeon = generate("L2", 1000)
    episode = start_episode(dungeon)
    frames = [snapshot(episode, 0, None, None)]
    for i, action in enumerate(dungeon.solution.actions, 1):
        frames.append(snapshot(episode, i, action, call(episode, action)))
    assert frames == build_frames(dungeon, dungeon.solution.actions)


class Recorder(BaseCallbackHandler):
    def __init__(self) -> None:
        self.starts = 0

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        **kwargs: Any,
    ) -> None:
        self.starts += 1


def test_play_episode_hooks() -> None:
    episodes: list[Episode] = []
    recorder = Recorder()
    result = play_episode(
        KEY,
        "test",
        "dev",
        Settings(),
        loop_arch.play,
        scripted_factory(replay_solution(generate("L1", 1000))),
        callbacks=[recorder],
        on_episode=episodes.append,
    )
    assert result.row.success
    assert len(episodes) == 1 and episodes[0].end_reason is not None
    assert recorder.starts == result.row.llm_calls  # the extra handler sees every call


@pytest.mark.parametrize(
    "error",
    [
        FakeProviderError(400, OVERFLOW),
        FakeProviderError(400, "too long", "context_length_exceeded"),
    ],
)
def test_context_overflow_is_the_architectures_failure(error: Exception) -> None:
    strategy = then(replay_solution(generate("L1", 1000)), 1, raise_error(error))
    result = play_episode(
        KEY, "test", "dev", Settings(), loop_arch.play, scripted_factory(strategy)
    )
    row = result.row
    assert row.status == "completed" and row.end_reason == "stopped" and row.success is False
    assert row.arch_error is not None and row.arch_error.startswith("context window exceeded")


def test_other_bad_requests_stay_permanent() -> None:
    strategy = raise_error(FakeProviderError(400, "unknown model"))
    with pytest.raises(PermanentProviderError):
        play_episode(KEY, "test", "dev", Settings(), loop_arch.play, scripted_factory(strategy))
