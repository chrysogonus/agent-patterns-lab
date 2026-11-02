"""A6 on the workshop: code offers the actions it can take now, the model picks one (specs/011)."""

import re
from collections.abc import Mapping

from langchain_core.messages import AIMessage, BaseMessage

from apl.arch.hybrid import MAX_MISSES, WORKSHOP_HYBRID_INSTRUCTIONS
from apl.workshop import generate
from apl.workshop.plans import reference_calls
from apl.workshop.prompt import BASE_PROMPT
from tests.arch.orchestrated import recording, text
from tests.arch.workshop_play import play

OPTION = re.compile(r"^(\d+)\. (.*)$", re.MULTILINE)


def _options(messages: list[BaseMessage]) -> list[str]:
    return [m[2] for m in OPTION.finditer(text(messages).split("Options:\n", 1)[1])]


def _wanted(call: tuple[str, Mapping[str, object]]) -> str:
    name, args = call
    if name == "craft":
        return f"craft {args['item']} with recipe {args['recipe']} ("
    if name == "gather":
        return f"gather {args['item']} ("
    return f"inspect {args['item']}"


def test_the_first_options() -> None:
    seen: list[list[BaseMessage]] = []
    w = generate("W2", 1000)
    play("hybrid", "W2", 1000, recording(lambda m: AIMessage("1"), seen))
    assert str(seen[0][0].content) == BASE_PROMPT + "\n\n" + WORKSHOP_HYBRID_INSTRUCTIONS
    assert _options(seen[0]) == [
        f"inspect {w.goal}",
        *(f"gather {raw} ({n} left)" for raw, n in w.stock.items()),
    ]
    assert f"Goal: {w.goal}." in text(seen[0])
    after = _options(seen[1])  # the goal inspected: its craftable inputs are offered next
    craftable_inputs = [i for i in w.recipes[w.goal][0] if w.craftable(i)]
    assert after[: len(craftable_inputs)] == [f"inspect {i}" for i in craftable_inputs]


def test_following_the_reference_crafts_the_goal() -> None:
    w = generate("W2", 1000)
    calls = iter(reference_calls(w))
    seen: list[list[BaseMessage]] = []

    def strategy(messages: list[BaseMessage]) -> AIMessage:
        wanted = _wanted(next(calls))
        options = _options(messages)
        return AIMessage(str(next(i for i, o in enumerate(options, 1) if o.startswith(wanted))))

    result = play("hybrid", "W2", 1000, recording(strategy, seen))
    assert result.row.success and result.row.steps == w.reference
    crafts = [o for m in seen for o in _options(m) if o.startswith("craft ")]
    assert crafts and all(" with recipe " in o and "(uses " in o for o in crafts)


def test_answers_that_name_no_option_are_asked_again_then_end() -> None:
    seen: list[list[BaseMessage]] = []
    result = play("hybrid", "W1", 1000, recording(lambda m: AIMessage("the coal one"), seen))
    assert len(seen) == MAX_MISSES and result.row.steps == 0
    assert result.row.end_reason == "stopped"
