"""A4 on the workshop: getting stuck ends an attempt, one restart, one budget (specs/011)."""

from collections.abc import Mapping

from langchain_core.messages import AIMessage, BaseMessage

from apl.arch.reflexion import MAX_STALE, REFLECTOR_INSTRUCTIONS, WORKSHOP_ATTEMPT
from apl.workshop import Episode, generate, start_episode
from apl.workshop.plans import greedy_calls, planner_calls, reference_calls
from tests.arch.orchestrated import recording, roles, text
from tests.arch.workshop_play import play
from tests.runner.scripted import by_system, tool_calls
from tests.workshop.lantern import play as play_calls_on

NOTE = "The first recipe used the scarce material another part needs; inspect first."


def _until_stuck(level: str, seed: int) -> list[tuple[str, Mapping[str, object]]]:
    """The greedy calls up to and including the craft that gets stuck."""
    w = generate(level, seed)
    episode = start_episode(w)
    play_calls_on(episode, greedy_calls(w))
    assert episode.outcome().stuck
    return list(greedy_calls(w)[: episode.steps])


def _watch(restarts: list[int]):  # type: ignore[no-untyped-def]
    def watch(episode: Episode) -> None:
        def on_restart() -> None:
            restarts.append(episode.attempt)

        episode.on_restart = on_restart

    return watch


def test_getting_stuck_uses_one_attempt_and_one_restart() -> None:
    greedy = _until_stuck("W2", 1000)
    right = reference_calls(generate("W2", 1000))
    turn = iter(greedy)

    def actor(messages: list[BaseMessage]) -> AIMessage:
        if "Attempt 1 of 3." in text(messages):
            return tool_calls(next(turn))
        return tool_calls(*right)

    restarts: list[int] = []
    seen: list[list[BaseMessage]] = []
    strategy = by_system({REFLECTOR_INSTRUCTIONS: lambda m: AIMessage(NOTE)}, actor)
    result = play("reflexion", "W2", 1000, recording(strategy, seen), _watch(restarts))
    row = result.row
    assert row.success and row.attempts == 2 and restarts == [2]
    assert row.steps == len(greedy) + len(right) and row.wasted == 1
    assert roles(result).count("reflector") == 1
    reflection = next(text(m) for m in seen if REFLECTOR_INSTRUCTIONS in str(m[0].content))
    assert "The attempt ended: stuck." in reflection
    actor_system = next(str(m[0].content) for m in seen if "Attempt 1 of 3." in text(m))
    assert actor_system.endswith(WORKSHOP_ATTEMPT)


def test_calls_after_the_stuck_craft_in_the_same_reply_do_not_run() -> None:
    w = generate("W2", 1000)
    greedy = _until_stuck("W2", 1000)
    right = reference_calls(w)

    def actor(messages: list[BaseMessage]) -> AIMessage:
        if "Attempt 1 of 3." in text(messages):
            return tool_calls(*greedy_calls(w))  # the whole greedy plan in one reply
        return tool_calls(*right)

    restarts: list[int] = []
    strategy = by_system({REFLECTOR_INSTRUCTIONS: lambda m: AIMessage(NOTE)}, actor)
    result = play("reflexion", "W2", 1000, strategy, _watch(restarts))
    assert result.row.success and result.row.attempts == 2 and restarts == [2]
    assert result.row.steps == len(greedy) + len(right)
    assert roles(result)[1] == "reflector"


def test_gathering_and_crafting_count_as_progress() -> None:
    """A long production phase after inspecting everything is not a stale attempt."""
    w = generate("W3", 1000)
    calls = planner_calls(w)
    production = sum(1 for name, _ in calls if name != "inspect")
    assert production > MAX_STALE  # without the fix this attempt would go stale
    turn = iter(calls)
    result = play("reflexion", "W3", 1000, lambda m: tool_calls(next(turn)))
    assert result.row.success and result.row.attempts == 1 and result.row.steps == len(calls)
