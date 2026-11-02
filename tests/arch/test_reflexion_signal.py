"""A4 on the signal trace: a wrong segment, one restart, one budget (specs/009 contracts)."""

import re

from langchain_core.messages import AIMessage, BaseMessage

from apl.arch.reflexion import MAX_STALE, REFLECTOR_INSTRUCTIONS
from apl.runner import registry
from apl.runner.episode import play_episode
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from apl.signal_trace import Episode, generate
from tests.arch.orchestrated import recording, text
from tests.arch.signal_play import reference_calls
from tests.runner.scripted import by_system, scripted_factory, tool_calls

NOTE = "The segment I named was wrong; probe before submitting."


def test_a_wrong_segment_uses_one_attempt_and_one_restart() -> None:
    pipe = generate("T1", 1000)
    wrong = pipe.broken % 16 + 1
    right = reference_calls("T1", 1000)

    def actor(messages: list[BaseMessage]) -> AIMessage:
        if "Attempt 1 of 3." in text(messages):
            return tool_calls(("submit", {"segment": wrong}))
        # A4 keeps only the latest turn; the probe log says how many probes this attempt made.
        found = re.search(r"Probes so far \((\d+), in order\)", text(messages))
        return tool_calls(right[int(found[1]) if found else 0])

    restarts: list[int] = []

    def watch(episode: Episode) -> None:
        def on_restart() -> None:
            restarts.append(episode.attempt)

        episode.on_restart = on_restart

    seen: list[list[BaseMessage]] = []
    strategy = by_system({REFLECTOR_INSTRUCTIONS: lambda m: AIMessage(NOTE)}, actor)
    key = EpisodeKey("reflexion", "T1", 1000, 1)
    result = play_episode(
        key, "test", "dev", Settings(), registry.load("reflexion"),
        scripted_factory(recording(strategy, seen)), on_episode=watch, problem="signal",
    )  # fmt: skip
    row, outcome = result.row, result.outcome
    assert row.success and row.attempts == 2 and outcome is not None
    assert restarts == [2]
    assert row.steps == 1 + len(right)  # both attempts in one budget
    reflection = next(text(m) for m in seen if REFLECTOR_INSTRUCTIONS in str(m[0].content))
    assert "The attempt ended: wrong segment." in reflection
    second = [m for m in seen if "Attempt 2 of 3." in text(m)]
    assert second and f"1. {NOTE}" in text(second[0])


def test_repeating_known_probes_goes_stale() -> None:
    def actor(messages: list[BaseMessage]) -> AIMessage:
        return tool_calls(("probe", {"segment": 3}))

    strategy = by_system({REFLECTOR_INSTRUCTIONS: lambda m: AIMessage(NOTE)}, actor)
    key = EpisodeKey("reflexion", "T2", 1000, 1)
    result = play_episode(
        key, "test", "dev", Settings(), registry.load("reflexion"), scripted_factory(strategy),
        problem="signal",
    )  # fmt: skip
    # Each attempt: one new probe, then MAX_STALE turns that add nothing.
    assert result.row.attempts == 3 and not result.row.success
    assert result.row.steps == 3 * (1 + MAX_STALE)
