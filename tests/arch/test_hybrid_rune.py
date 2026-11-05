"""A6 on the rune floor: code offers the moves with their records; the model picks (specs/010)."""

import re
from collections.abc import Callable

import pytest
from langchain_core.messages import AIMessage, BaseMessage

from apl.arch.hybrid import MAX_MISSES, RUNE_HYBRID_INSTRUCTIONS, rune_options
from apl.arch.walk_log import WalkLog, WalkNote
from apl.rune import generate
from apl.rune.prompt import BASE_PROMPT
from apl.rune.seeds import DEV_SEEDS
from tests.arch.orchestrated import recording, text
from tests.arch.rune_play import play
from tests.rune.agents import reference_moves

OPTION = re.compile(r"^(\d+)\. (.*)$", re.MULTILINE)


def _options(messages: list[BaseMessage]) -> list[str]:
    return [m[2] for m in OPTION.finditer(text(messages).split("Options:\n", 1)[1])]


def _choose(direction: str, messages: list[BaseMessage]) -> AIMessage:
    options = _options(messages)
    return AIMessage(
        str(next(i for i, o in enumerate(options, 1) if o.startswith(f"move {direction} ")))
    )


def test_the_first_options_are_the_moves_from_the_start() -> None:
    seen: list[list[BaseMessage]] = []
    floor = generate("R1", 1000)
    play("hybrid", "R1", 1000, recording(lambda m: AIMessage("2"), seen))
    assert str(seen[0][0].content) == BASE_PROMPT + "\n\n" + RUNE_HYBRID_INSTRUCTIONS
    first = _options(seen[0])
    a2, b3, a4 = floor.colors[(0, 1)], floor.colors[(1, 2)], floor.colors[(0, 3)]
    assert first == [
        f"move north to A2 ({a2}), walk step 1: never stepped on",
        f"move east to B3 ({b3}), walk step 1: never stepped on",
        f"move south to A4 ({a4}), walk step 1: never stepped on",
    ]
    assert "Floor: 7 columns × 5 rows." in text(seen[0])


def test_records_and_the_start_and_goal_wordings() -> None:
    seen: list[list[BaseMessage]] = []
    # R1 seed 1000, row 3: S r b y y y G under red, blue, yellow: east ×3 is safe, the 4th traps.
    play("hybrid", "R1", 1000, recording(lambda m: _choose("east", m), seen))
    after_trap = _options(seen[4])  # back on S after the trap at E3
    assert after_trap[1] == "move east to B3 (red), walk step 1: safe at walk step 1 (once)"
    on_d3 = _options(seen[7])
    assert on_d3[1] == "move east to E3 (yellow), walk step 4: trap at walk step 4 (once)"


def _scripted(moves: list[str]) -> Callable[[list[BaseMessage]], AIMessage]:
    """Takes the moves in order, then answers nothing valid, which ends the episode."""
    left = iter(moves)

    def strategy(messages: list[BaseMessage]) -> AIMessage:
        move = next(left, None)
        return _choose(move, messages) if move else AIMessage("no choice")

    return strategy


def _directions(messages: list[BaseMessage]) -> list[str]:
    return [o.split()[1] for o in _options(messages)]


def test_tiles_already_stepped_on_in_this_walk_are_not_offered() -> None:
    # R3 seed 1000: S B4 C4 C5 B5 is safe and turns back beside B4: the square Haiku circled.
    seen: list[list[BaseMessage]] = []
    play("hybrid", "R3", 1000, recording(_scripted(["east", "east", "south", "west"]), seen))
    assert _directions(seen[1]) == ["north", "east", "south"]  # on B4, not back to the start
    assert _directions(seen[2]) == ["north", "east", "south"]  # on C4, not back to B4
    assert _directions(seen[3]) == ["east", "south", "west"]  # on C5, not back to C4
    assert _directions(seen[4]) == ["south", "west"]  # on B5, not to C5 or B4


def test_after_a_trap_every_move_is_offered_again() -> None:
    # R3 seed 1000: C3 north of C4 is a trap, which puts the agent back on the start at A4.
    seen: list[list[BaseMessage]] = []
    play("hybrid", "R3", 1000, recording(_scripted(["east", "east", "north"]), seen))
    assert _directions(seen[3]) == ["north", "east", "south"]


def test_every_move_is_offered_when_all_neighbors_were_stepped_on() -> None:
    # On A1 after S, B2, B1, A1: its only neighbors are B1 and the start at A2.
    log = WalkLog(
        3,
        3,
        start=(0, 1),
        goal=(2, 1),
        floor=[["red"] * 3, ["start", "red", "goal"], ["red"] * 3],
        position=(0, 0),
        walks=[WalkNote(steps=[((1, 1), "red"), ((1, 0), "red"), ((0, 0), "red")])],
    )
    assert [o.text for o in rune_options(log)] == [
        "move east to B1 (red), walk step 4: safe at walk step 2 (once)",
        "move south to the start",
    ]


@pytest.mark.parametrize("level", ["R0", "R1", "R2", "R3"])
@pytest.mark.parametrize("seed", DEV_SEEDS)
def test_walking_the_reference_reaches_the_goal(level: str, seed: int) -> None:
    floor = generate(level, seed)
    moves = iter(reference_moves(floor))
    seen: list[list[BaseMessage]] = []

    def strategy(messages: list[BaseMessage]) -> AIMessage:
        return _choose(next(moves), messages)

    result = play("hybrid", level, seed, recording(strategy, seen))
    assert result.row.success and result.row.steps == floor.reference
    assert any(o.endswith(" to the goal") for o in _options(seen[-1]))


def test_answers_that_name_no_option_are_asked_again_then_end() -> None:
    seen: list[list[BaseMessage]] = []
    result = play("hybrid", "R1", 1000, recording(lambda m: AIMessage("the safe one"), seen))
    assert len(seen) == MAX_MISSES and result.row.steps == 0
    assert result.row.end_reason == "stopped"
