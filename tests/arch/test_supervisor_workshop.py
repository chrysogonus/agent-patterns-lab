"""A5 on the workshop: a researcher and a crafter (specs/011 contracts/architectures.md)."""

import itertools
from collections.abc import Mapping, Sequence

from langchain_core.messages import AIMessage, BaseMessage

from apl.arch.mapstate import WORKSHOP_LOG_INSTRUCTIONS
from apl.arch.supervisor import (
    CRAFTER_INSTRUCTIONS,
    RESEARCHER_INSTRUCTIONS,
    WORKSHOP_SUPERVISOR_INSTRUCTIONS,
)
from apl.workshop import generate
from apl.workshop.plans import reference_calls
from apl.workshop.prompt import BASE_PROMPT
from tests.arch.orchestrated import recording, roles
from tests.arch.workshop_play import play
from tests.runner.scripted import by_system, json_answer, tool_calls


def _turns(calls: Sequence[tuple[str, Mapping[str, object]]]):  # type: ignore[no-untyped-def]
    """One call per turn, then a report without a call."""
    turn = itertools.count()

    def strategy(messages: list[BaseMessage]) -> AIMessage:
        n = next(turn)
        return tool_calls(calls[n]) if n < len(calls) else AIMessage("Done.")

    return strategy


def test_the_researcher_inspects_and_the_crafter_makes_the_goal() -> None:
    w = generate("W2", 1000)
    right = reference_calls(w)
    first_raw = next(iter(w.stock))
    research = [("gather", {"item": first_raw})] + [c for c in right if c[0] == "inspect"]
    making = [("inspect", {"item": w.goal})] + [c for c in right if c[0] != "inspect"]
    handoffs = iter([
        {"to": "researcher", "task": "inspect every recipe"},
        {"to": "crafter", "task": "make the goal"},
        {"done": True},
    ])  # fmt: skip
    seen: list[list[BaseMessage]] = []
    strategy = by_system(
        {
            WORKSHOP_SUPERVISOR_INSTRUCTIONS: lambda m: json_answer(next(handoffs))(m),
            RESEARCHER_INSTRUCTIONS: _turns(research),
            CRAFTER_INSTRUCTIONS: _turns(making),
        },
        lambda m: AIMessage("?"),
    )
    result = play("supervisor", "W2", 1000, recording(strategy, seen))
    assert result.row.success and result.row.problem == "workshop"
    assert result.row.steps == len(right)  # the refused calls cost nothing
    assert roles(result)[:2] == ["supervisor", "researcher (task 1)"]
    assert str(seen[0][0].content) == BASE_PROMPT + "\n\n" + WORKSHOP_SUPERVISOR_INSTRUCTIONS
    researcher = next(m for m in seen if RESEARCHER_INSTRUCTIONS in str(m[0].content))
    assert str(researcher[0].content) == (
        BASE_PROMPT + "\n\n" + WORKSHOP_LOG_INSTRUCTIONS + " " + RESEARCHER_INSTRUCTIONS
    )
    refused = [
        str(m.content) for messages in seen for m in messages if "Not made:" in str(m.content)
    ]
    assert any("gather is the crafter's tool" in r for r in refused)
    assert any("inspect is the researcher's tool" in r for r in refused)


def test_the_supervisor_offers_only_the_workshops_helpers() -> None:
    assert '"researcher"' in WORKSHOP_SUPERVISOR_INSTRUCTIONS
    assert '"crafter"' in WORKSHOP_SUPERVISOR_INSTRUCTIONS
    assert "navigator" not in WORKSHOP_SUPERVISOR_INSTRUCTIONS
    assert "look and inspect" in RESEARCHER_INSTRUCTIONS
    assert "gather and craft" in CRAFTER_INSTRUCTIONS
