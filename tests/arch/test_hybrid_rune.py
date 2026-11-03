"""A6 on the rune floor: code offers the moves with their records; the model picks (specs/010)."""

import re

from langchain_core.messages import AIMessage, BaseMessage

from apl.arch.hybrid import MAX_MISSES, RUNE_HYBRID_INSTRUCTIONS
from apl.rune import generate
from apl.rune.prompt import BASE_PROMPT
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
    assert "move west to the start" in _options(seen[5])  # on B3
    on_d3 = _options(seen[7])
    assert on_d3[1] == "move east to E3 (yellow), walk step 4: trap at walk step 4 (once)"


def test_walking_the_reference_reaches_the_goal() -> None:
    floor = generate("R1", 1000)
    moves = iter(reference_moves(floor))
    seen: list[list[BaseMessage]] = []

    def strategy(messages: list[BaseMessage]) -> AIMessage:
        return _choose(next(moves), messages)

    result = play("hybrid", "R1", 1000, recording(strategy, seen))
    assert result.row.success and result.row.steps == floor.reference
    assert any(o == "move east to the goal" for o in _options(seen[-1]))


def test_answers_that_name_no_option_are_asked_again_then_end() -> None:
    seen: list[list[BaseMessage]] = []
    result = play("hybrid", "R1", 1000, recording(lambda m: AIMessage("the safe one"), seen))
    assert len(seen) == MAX_MISSES and result.row.steps == 0
    assert result.row.end_reason == "stopped"
