"""A4 Reflexion with scripted answers (specs/007 contracts/reflexion.md, US1)."""

import pytest
from langchain_core.messages import AIMessage, BaseMessage

from apl.arch.mapstate import FIELD_MAP_INSTRUCTIONS, MAP_INSTRUCTIONS
from apl.arch.reflexion import ACTOR_INSTRUCTIONS, MAX_STALE, REFLECTOR_INSTRUCTIONS
from apl.dungeon import generate
from apl.kit import BASE_PROMPT
from apl.survey import generate as generate_field
from apl.survey.prompt import BASE_PROMPT as FIELD_BASE_PROMPT
from tests.arch.orchestrated import recording, roles, text
from tests.arch.test_plan_execute import _play
from tests.runner.scripted import Strategy, bump_wall, by_system, walk_field, walk_solution
from tests.runner.test_run import _wall

NOTE = "Try harder."


def _a4(actor: Strategy, reflector: Strategy | None = None) -> Strategy:
    return by_system({REFLECTOR_INSTRUCTIONS: reflector or (lambda m: AIMessage(NOTE))}, actor)


def _gives_up_first(then: Strategy) -> Strategy:
    """Gives up at once in attempt 1, then plays `then`."""

    def strategy(messages: list[BaseMessage]) -> AIMessage:
        return AIMessage("I give up.") if "Attempt 1 of 3." in text(messages) else then(messages)

    return strategy


def _actors(seen: list[list[BaseMessage]]) -> list[list[BaseMessage]]:
    return [m for m in seen if ACTOR_INSTRUCTIONS.format(max_attempts=3) in str(m[0].content)]


def _reflections(seen: list[list[BaseMessage]]) -> list[str]:
    return [text(m) for m in seen if REFLECTOR_INSTRUCTIONS in str(m[0].content)]


@pytest.mark.parametrize(("level", "seed"), [("L1", 1000), ("L2", 1001), ("L3", 1002)])
def test_a_second_attempt_escapes(level: str, seed: int) -> None:  # SC-001, acceptance 1.1
    seen: list[list[BaseMessage]] = []
    walk = walk_solution(generate(level, seed))
    result = _play("reflexion", level, seed, recording(_a4(_gives_up_first(walk)), seen))
    row = result.row
    assert row.success and row.attempts == 2 and row.arch_error is None
    assert row.steps == _play("mapstate", level, seed, walk).row.steps
    assert roles(result)[:3] == ["actor (attempt 1)", "reflector", "actor (attempt 2)"]
    assert row.orchestrator_calls == 1  # the reflector
    second = text(_actors(seen)[1])
    assert "Attempt 2 of 3." in second and f"Notes from earlier attempts:\n1. {NOTE}" in second
    assert "Notes from" not in str(_actors(seen)[0][1].content)  # the head, not the system text


@pytest.mark.parametrize("level", ["S1", "S2", "S3"])
def test_a_second_attempt_surveys_the_field(level: str) -> None:  # SC-001
    field = generate_field(level, 1000)
    walk = walk_field(field.walk, total=field.true_total)
    row = _play("reflexion", level, 1000, _a4(_gives_up_first(walk))).row
    assert row.success and row.attempts == 2
    assert row.steps == _play("mapstate", level, 1000, walk).row.steps


def test_a_wrong_total_is_reflected_on_and_tried_again() -> None:  # acceptance 1.2
    seen: list[list[BaseMessage]] = []
    field = generate_field("S1", 1000)
    wrong, right = walk_field(field.walk, total=5), walk_field(field.walk, total=6)

    def actor(messages: list[BaseMessage]) -> AIMessage:
        return (wrong if "Attempt 1 of 3." in text(messages) else right)(messages)

    row = _play("reflexion", "S1", 1000, recording(_a4(actor), seen)).row
    assert row.success and row.attempts == 2 and row.submitted_total == 6
    (reflection,) = _reflections(seen)
    assert "The attempt ended: wrong total." in reflection
    assert "Cells seen: 36 of 36." in reflection  # the map at the end of attempt 1
    first_map = str(_actors(seen)[len(field.walk) + 1][-1].content)  # attempt 2's first turn
    assert "Cells seen: 1 of 36." in first_map


def test_three_give_ups_end_the_episode() -> None:  # acceptance 1.4, SC-003
    result = _play("reflexion", "L1", 1000, _a4(lambda m: AIMessage("I give up.")))
    row = result.row
    assert row.end_reason == "stopped" and row.attempts == 3 and row.steps == 0
    assert roles(result).count("reflector") == 2


def test_three_wrong_totals_end_with_the_last_one() -> None:
    field = generate_field("S1", 1000)
    row = _play("reflexion", "S1", 1000, _a4(walk_field(field.walk, total=5))).row
    assert row.end_reason == "submitted" and not row.success and row.attempts == 3
    assert row.submitted_total == 5


def test_nothing_new_ends_an_attempt_and_the_budget_ends_the_episode() -> None:  # 1.5
    seen: list[list[BaseMessage]] = []
    result = _play("reflexion", "L1", 1000, recording(_a4(bump_wall(_wall("L1", 1000))), seen))
    row = result.row
    assert MAX_STALE == 12
    (reflection,) = _reflections(seen)
    assert f"The attempt ended: nothing new for {MAX_STALE} turns." in reflection
    assert row.budget_hit and row.attempts == 2 and row.steps == row.budget == 2 * MAX_STALE


def test_an_empty_note_is_not_kept() -> None:
    seen: list[list[BaseMessage]] = []
    walk = walk_solution(generate("L1", 1000))
    _play(
        "reflexion",
        "L1",
        1000,
        recording(_a4(_gives_up_first(walk), lambda m: AIMessage(" ")), seen),
    )
    assert "Notes from" not in str(_actors(seen)[1][1].content)


@pytest.mark.parametrize(
    ("level", "base", "instructions"),
    [("L3", BASE_PROMPT, MAP_INSTRUCTIONS), ("S2", FIELD_BASE_PROMPT, FIELD_MAP_INSTRUCTIONS)],
)
def test_every_job_gets_the_base_prompt_and_the_actor_a2s_map(
    level: str, base: str, instructions: str
) -> None:  # SC-006
    seen: list[list[BaseMessage]] = []
    row = _play(
        "reflexion", level, 1000, recording(_a4(lambda m: AIMessage("I give up.")), seen)
    ).row
    systems = {str(m[0].content) for m in seen}
    assert systems == {
        base + "\n\n" + instructions + " " + ACTOR_INSTRUCTIONS.format(max_attempts=3),
        base + "\n\n" + REFLECTOR_INSTRUCTIONS,
    }
    assert row.budget == _play("mapstate", level, 1000, lambda m: AIMessage("Done.")).row.budget


def test_calls_after_a_submission_in_the_same_reply_are_not_run() -> None:
    from tests.runner.scripted import tool_calls

    seen: list[list[BaseMessage]] = []
    field = generate_field("S1", 1000)
    right = walk_field(field.walk, total=6)

    def actor(messages: list[BaseMessage]) -> AIMessage:
        if "Attempt 1 of 3." in text(messages):
            return tool_calls(("submit", {"total": 5}), ("move", {"direction": "south"}))
        return right(messages)

    result = _play("reflexion", "S1", 1000, recording(_a4(actor), seen))
    assert result.row.success and result.row.attempts == 2
    log = result.outcome.log
    assert [e.action.tool for e in log if e.attempt == 1] == ["submit"]  # the move never ran
    moves = [e.action.args[0] for e in log if e.attempt == 2 and e.action.tool == "move"]
    assert moves == list(field.walk)  # attempt 2 walks from the start its map shows
