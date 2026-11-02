"""A4 on the rune floor: a trap ends an attempt, one restart, one budget (specs/010 contracts)."""

from langchain_core.messages import AIMessage, BaseMessage

from apl.arch.reflexion import MAX_STALE, REFLECTOR_INSTRUCTIONS
from apl.rune import Episode, generate
from apl.rune.rules import next_state, outcome_of
from tests.arch.orchestrated import recording, roles, text
from tests.arch.rune_play import play, reference_calls
from tests.runner.scripted import by_system, tool_calls

NOTE = "The yellow tile after red and blue sent me back; try another color order."


def _straight_row_trap(level: str, seed: int) -> int:
    """How many moves east along the straight row until the trap."""
    floor = generate(level, seed)
    cell, state = floor.start, 0
    for moves in range(1, floor.columns):
        cell = (cell[0] + 1, cell[1])
        if outcome_of(floor, state, cell) == "trap":
            return moves
        state = next_state(floor.rule, state)
    raise AssertionError("the straight row is safe")


def _watch(restarts: list[int]):  # type: ignore[no-untyped-def]
    def watch(episode: Episode) -> None:
        def on_restart() -> None:
            restarts.append(episode.attempt)

        episode.on_restart = on_restart

    return watch


def test_a_trap_uses_one_attempt_and_one_restart() -> None:
    right = reference_calls("R1", 1000)
    trap_after = _straight_row_trap("R1", 1000)

    def actor(messages: list[BaseMessage]) -> AIMessage:
        if "Attempt 1 of 3." in text(messages):
            return tool_calls(("move", {"direction": "east"}))
        return tool_calls(*right)  # the whole reference path in one reply

    restarts: list[int] = []
    seen: list[list[BaseMessage]] = []
    strategy = by_system({REFLECTOR_INSTRUCTIONS: lambda m: AIMessage(NOTE)}, actor)
    result = play("reflexion", "R1", 1000, recording(strategy, seen), _watch(restarts))
    row = result.row
    assert row.success and row.attempts == 2 and restarts == [2]
    assert row.steps == trap_after + len(right) and row.traps == 1  # one budget
    assert roles(result).count("reflector") == 1
    reflection = next(text(m) for m in seen if REFLECTOR_INSTRUCTIONS in str(m[0].content))
    assert "The attempt ended: trap." in reflection
    second = [m for m in seen if "Attempt 2 of 3." in text(m)]
    assert second and f"1. {NOTE}" in text(second[0])


def test_moves_after_a_trap_in_the_same_reply_do_not_run() -> None:
    right = reference_calls("R1", 1000)
    trap_after = _straight_row_trap("R1", 1000)
    replies: list[AIMessage] = []

    def actor(messages: list[BaseMessage]) -> AIMessage:
        if "Attempt 1 of 3." in text(messages):
            if trap_after > 1 and len(replies) == 0:
                reply = tool_calls(*[("move", {"direction": "east"})] * (trap_after - 1))
            else:
                reply = tool_calls(*[("move", {"direction": "east"})] * 3)  # the first traps
            replies.append(reply)
            return reply
        return tool_calls(*right)

    restarts: list[int] = []
    seen: list[list[BaseMessage]] = []
    strategy = by_system({REFLECTOR_INSTRUCTIONS: lambda m: AIMessage(NOTE)}, actor)
    result = play("reflexion", "R1", 1000, recording(strategy, seen), _watch(restarts))
    assert result.row.success and result.row.attempts == 2 and restarts == [2]
    # Only the trapping move of the last batch ran: one step, then the reflector.
    assert result.row.steps == trap_after + len(right)
    assert result.row.traps == 1
    after_batch = roles(result)[len(replies)]
    assert after_batch == "reflector"


def test_with_no_attempt_left_a_trap_does_not_end_the_attempt() -> None:
    trap_after = _straight_row_trap("R1", 1000)

    def actor(messages: list[BaseMessage]) -> AIMessage:
        if "Attempt 3 of 3." in text(messages):
            return tool_calls(*[("move", {"direction": "east"})] * (trap_after + 1))
        return tool_calls(*[("move", {"direction": "east"})] * trap_after)

    strategy = by_system({REFLECTOR_INSTRUCTIONS: lambda m: AIMessage(NOTE)}, actor)
    result = play("reflexion", "R1", 1000, strategy)
    outcome = result.outcome
    assert outcome is not None and result.row.attempts == 3
    # In the last attempt the whole batch runs: a trap, then one more move from the start.
    last = [e for e in outcome.log if e.attempt == 3]
    assert len([e for e in last if e.step is not None]) >= trap_after + 1


def test_walking_into_the_edge_goes_stale() -> None:
    def actor(messages: list[BaseMessage]) -> AIMessage:
        return tool_calls(("move", {"direction": "west"}))  # S is on the west edge

    strategy = by_system({REFLECTOR_INSTRUCTIONS: lambda m: AIMessage(NOTE)}, actor)
    result = play("reflexion", "R1", 1000, strategy)
    assert result.row.attempts == 3 and not result.row.success
    assert result.row.steps == 3 * MAX_STALE


def test_the_walk_log_is_kept_after_a_trap() -> None:
    trap_after = _straight_row_trap("R1", 1000)

    def actor(messages: list[BaseMessage]) -> AIMessage:
        if "Attempt 1 of 3." in text(messages):
            return tool_calls(*[("move", {"direction": "east"})] * trap_after)
        return AIMessage("Done.")

    seen: list[list[BaseMessage]] = []
    strategy = by_system({REFLECTOR_INSTRUCTIONS: lambda m: AIMessage(NOTE)}, actor)
    play("reflexion", "R1", 1000, recording(strategy, seen))
    second = next(m for m in seen if "Attempt 2 of 3." in text(m))
    assert "1. B3" in str(second[-1].content) and "→ trap at" in str(second[-1].content)


def test_cells_count_as_new_once_per_attempt() -> None:
    trap_after = _straight_row_trap("R1", 1000)
    assert trap_after > 1  # B3 is safe, so attempts 2 and 3 can step on it again

    def actor(messages: list[BaseMessage]) -> AIMessage:
        if "Attempt 1 of 3." in text(messages):
            return tool_calls(*[("move", {"direction": "east"})] * trap_after)
        on_start = "You are on A3." in str(messages[-1].content)
        return tool_calls(("move", {"direction": "east" if on_start else "west"}))

    strategy = by_system({REFLECTOR_INSTRUCTIONS: lambda m: AIMessage(NOTE)}, actor)
    result = play("reflexion", "R1", 1000, strategy)
    # Attempts 2 and 3: B3 is new to the attempt once, then MAX_STALE turns add nothing.
    assert result.row.attempts == 3 and not result.row.success
    assert result.row.steps == trap_after + 2 * (1 + MAX_STALE)
