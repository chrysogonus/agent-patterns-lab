"""A4r retry: A4's attempts and restarts without the reflector, the notes-only baseline."""

from langchain_core.messages import AIMessage, BaseMessage

from apl.arch.reflexion import ATTEMPT_INSTRUCTIONS, NOTES_INSTRUCTIONS
from apl.dungeon import generate
from apl.runner import registry
from tests.arch.orchestrated import recording, roles, text
from tests.arch.rune_play import play as play_rune
from tests.arch.rune_play import reference_calls
from tests.arch.test_plan_execute import _play
from tests.arch.test_reflexion_rune import _straight_row_trap
from tests.runner.scripted import tool_calls, walk_solution


def test_it_plays_where_reflexion_plays_and_retries() -> None:
    assert registry.SUPPORTS["retry"] == registry.SUPPORTS["reflexion"]
    assert "retry" in registry.RETRYING


def test_a_second_attempt_escapes_without_a_reflection() -> None:
    seen: list[list[BaseMessage]] = []
    walk = walk_solution(generate("L2", 1001))

    def actor(messages: list[BaseMessage]) -> AIMessage:
        return AIMessage("I give up.") if "Attempt 1 of 3." in text(messages) else walk(messages)

    result = _play("retry", "L2", 1001, recording(actor, seen))
    row = result.row
    assert row.success and row.attempts == 2 and row.orchestrator_calls == 0
    assert roles(result)[:2] == ["actor (attempt 1)", "actor (attempt 2)"]
    system = str(seen[0][0].content)
    assert ATTEMPT_INSTRUCTIONS.format(max_attempts=3) in system
    assert NOTES_INSTRUCTIONS not in system
    assert all("Notes from earlier attempts" not in text(m) for m in seen)


def test_a_trap_restarts_the_floor_and_keeps_the_walk_log() -> None:
    trap_after = _straight_row_trap("R1", 1000)
    right = reference_calls("R1", 1000)
    seen: list[list[BaseMessage]] = []

    def actor(messages: list[BaseMessage]) -> AIMessage:
        if "Attempt 1 of 3." in text(messages):
            return tool_calls(*[("move", {"direction": "east"})] * trap_after)
        return tool_calls(*right)

    result = play_rune("retry", "R1", 1000, recording(actor, seen))
    assert result.row.success and result.row.attempts == 2 and result.row.traps == 1
    assert set(roles(result)) == {"actor (attempt 1)", "actor (attempt 2)"}
    second = next(m for m in seen if "Attempt 2 of 3." in text(m))
    assert "→ trap at" in str(second[-1].content)
