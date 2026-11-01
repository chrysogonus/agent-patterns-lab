"""A2 and the scout architectures A7–A9 on the survey field (specs/005 US1, R10, R14)."""

import itertools
from typing import Any

import pytest
from langchain_core.messages import AIMessage, BaseMessage

from apl.arch.blackboard import FIELD_TASK
from apl.arch.fanout import FIELD_FANOUT_INSTRUCTIONS
from apl.arch.mapstate import FIELD_MAP_INSTRUCTIONS
from apl.arch.rounds import FIELD_ROUNDS_INSTRUCTIONS
from apl.arch.scouts import SharedMap
from apl.runner import registry
from apl.runner.episode import EpisodeResult, play_episode
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from apl.survey import generate
from apl.survey.prompt import BASE_PROMPT
from tests.arch.oracle import expected_field_map
from tests.arch.orchestrated import recording, roles, text
from tests.runner.scripted import Strategy, by_system, json_answer, scripted_factory, walk_field

FIELD = generate("S1", 1000)
WALK = FIELD.walk


def _play(arch: str, strategy: Strategy, level: str = "S1") -> EpisodeResult:
    key = EpisodeKey(arch, level, 1000, 1)
    return play_episode(
        key, "test", "dev", Settings(), registry.load(arch), scripted_factory(strategy),
        problem="survey",
    )  # fmt: skip


def test_mapstate_walks_its_field_map_and_submits() -> None:
    seen: list[list[BaseMessage]] = []
    result = _play("mapstate", recording(walk_field(WALK, total=6), seen))
    row = result.row
    assert row.success and row.steps == 36 and row.parallel_turns == 36
    assert str(seen[0][0].content) == BASE_PROMPT + "\n\n" + FIELD_MAP_INSTRUCTIONS
    assert all("Your map (built from your tool results so far):" in text(m) for m in seen)
    assert "Cells seen: 36 of 36. Deposits seen: 6." in str(seen[-1][-1].content)


def test_mapstate_map_matches_the_oracle_after_every_call(monkeypatch: pytest.MonkeyPatch) -> None:
    from apl.arch import field_map

    snapshots: list[dict[str, Any]] = []
    apply = field_map.FieldMap.apply

    def spy(self: field_map.FieldMap, name: str, args: Any, result: Any) -> None:
        apply(self, name, args, result)
        snapshots.append({k: (v.deposit, v.exits) for k, v in self.cells.items()})

    monkeypatch.setattr(field_map.FieldMap, "apply", spy)
    result = _play("mapstate", walk_field(WALK, total=6))
    assert result.outcome is not None
    log = result.outcome.log
    for i, snapshot in enumerate(snapshots, 1):
        cells, _ = expected_field_map(FIELD, log, i)
        assert snapshot == cells and list(snapshot) == list(cells), i


def _fanout(plan: dict[str, Any], total: Any) -> Strategy:
    def orchestrator(messages: list[BaseMessage]) -> AIMessage:
        if "The scouts are done." in str(messages[-1].content):
            return json_answer(total)(messages)
        return json_answer(plan)(messages)

    return by_system({FIELD_FANOUT_INSTRUCTIONS[:60]: orchestrator}, walk_field(WALK))


def test_fanout_collects_the_reports_and_submits_through_scout_0() -> None:
    plan = {"scouts": [{"task": "walk", "steps": 40}, {"task": "walk", "steps": 40}]}
    seen: list[list[BaseMessage]] = []
    result = _play("fanout", recording(_fanout(plan, {"total": 6}), seen))
    row, outcome = result.row, result.outcome
    assert outcome is not None and row.success and row.orchestrator_calls == 2
    last = outcome.log[-1]
    assert last.action.tool == "submit" and last.scout == 0 and last.action.args == ("6",)
    assert row.steps == 71 and row.parallel_turns == 36  # the two scouts walk side by side
    collect = next(m for m in seen if "The scouts are done." in text(m))
    assert "scout 0: I walked my part of the field." in text(collect)
    assert "scout 1: I walked my part of the field." in text(collect)


def test_fanout_asks_again_for_a_bad_total_then_gives_up() -> None:
    plan = {"scouts": [{"task": "walk", "steps": 3}]}
    row = _play("fanout", _fanout(plan, {"total": "six"})).row
    assert row.end_reason == "stopped" and row.submitted_total is None
    assert row.orchestrator_calls == 1 + 3 and row.steps == 3


def _rounds(answers: list[Any]) -> Strategy:
    queue = iter(answers)
    orchestrator = lambda messages: json_answer(next(queue))(messages)  # noqa: E731
    return by_system({FIELD_ROUNDS_INSTRUCTIONS[:60]: orchestrator}, walk_field(WALK))


def test_rounds_submits_the_total_answer() -> None:
    tasks = {"tasks": [{"scout": 0, "task": "walk", "steps": 35}]}
    row = _play("rounds", _rounds([tasks, {"total": 6}])).row
    assert row.success and row.steps == 36 and row.orchestrator_calls == 2


def test_rounds_refuses_done_on_the_survey() -> None:
    seen: list[list[BaseMessage]] = []
    strategy = recording(_rounds([{"done": True}, {"total": 5}]), seen)
    row = _play("rounds", strategy).row
    assert not row.success and row.submitted_total == 5 and row.steps == 1
    assert "Your answer was not used" in text(seen[1])


def test_rounds_board_matches_the_oracle() -> None:
    tasks = {"tasks": [{"scout": n, "task": "walk", "steps": 5} for n in range(3)]}
    seen: list[list[BaseMessage]] = []
    result = _play("rounds", recording(_rounds([tasks, {"total": 6}]), seen))
    assert result.outcome is not None
    cells, positions = expected_field_map(FIELD, result.outcome.log, len(result.outcome.log) - 1)
    board = text(seen[-1])
    assert f"Cells seen: {len(cells)} of 36." in board
    for n, cell in positions.items():
        assert f"scout {n} is in {cell}" in board


def test_blackboard_scouts_submit_and_take_turns(monkeypatch: pytest.MonkeyPatch) -> None:
    claims = itertools.count()

    def scout(messages: list[BaseMessage]) -> AIMessage:
        if "You are scout 0." not in text(messages):
            return AIMessage("The others have it covered.")  # scouts 1-3 stop at once
        reply = walk_field(WALK, total=6)(messages)
        if next(claims) == 0:
            reply = reply.model_copy(update={"content": "claim: A1 east"})
        return reply

    boards: list[SharedMap[Any]] = []
    apply = SharedMap.apply

    def spy(self: SharedMap[Any], number: int, name: str, args: Any, result: Any) -> None:
        apply(self, number, name, args, result)
        boards.append(self)

    monkeypatch.setattr(SharedMap, "apply", spy)
    seen: list[list[BaseMessage]] = []
    result = _play("blackboard", recording(scout, seen))
    row, outcome = result.row, result.outcome
    assert outcome is not None and row.success and row.parallel_turns == row.steps
    assert outcome.log[-1].action.tool == "submit"
    assert any(FIELD_TASK in text(m) for m in seen)
    assert any("Claims: scout 0 → A1 east." in text(m) for m in seen)
    board = boards[-1]
    cells, positions = expected_field_map(FIELD, outcome.log, len(outcome.log) - 1)
    assert {k: (v.deposit, v.exits) for k, v in board.map.cells.items()} == cells
    # Scouts without a call are still in A1, where they appeared.
    assert board.positions == {n: positions.get(n, "A1") for n in range(4)}


def test_a_claim_without_a_tool_call_keeps_a_blackboard_scout_going() -> None:
    first = itertools.count()

    def scout(messages: list[BaseMessage]) -> AIMessage:
        if "You are scout 0." not in text(messages):
            return AIMessage("claim: A1 south")  # never moves: done after 3 in a row
        if next(first) < 2:
            return AIMessage("claim: A1 eastclaim: A1 east")  # two text parts run together
        return walk_field(WALK, total=6)(messages)

    seen: list[list[BaseMessage]] = []
    result = _play("blackboard", recording(scout, seen))
    assert result.row.success and result.row.steps == len(WALK) + 1
    calls = roles(result)
    assert [calls.count(f"scout {n}") for n in (1, 2, 3)] == [3, 3, 3]
    assert any("Claims: scout 0 → A1 east; scout 1 → A1 south" in text(m) for m in seen)


def test_claims_between_steps_do_not_end_the_graph_before_the_budget() -> None:
    turn = itertools.count()

    def scout(messages: list[BaseMessage]) -> AIMessage:
        if "You are scout 0." not in text(messages):
            return AIMessage("Nothing to add.")
        if (n := next(turn)) % 3 < 2:  # the most claims in a row that keep a scout going
            return AIMessage("claim: A1 east")
        call = {"name": "look", "args": {}, "id": f"look-{n}"}
        return AIMessage("", tool_calls=[call])

    row = _play("blackboard", scout, level="S2").row
    assert row.arch_error is None
    assert row.end_reason == "budget" and row.steps == row.budget == 300


FIELD2 = generate("S2", 1000)


def _quarter(first: int, last: int) -> list[str]:
    """From A1 down column A to row `first`, then the snake over rows `first`..`last`."""
    moves = ["south"] * first
    for i, _ in enumerate(range(first, last + 1)):
        moves += ["east" if i % 2 == 0 else "west"] * 9
        if first + i < last:
            moves.append("south")
    return moves


QUARTERS = {"q0": (0, 2), "q1": (3, 4), "q2": (5, 7), "q3": (8, 9)}


def four_scouts(total: int) -> Strategy:
    from tests.runner.scripted import by_task

    tasks = {
        "tasks": [
            {"scout": n, "task": name, "steps": 40} for n, name in enumerate(QUARTERS)
        ]
    }  # fmt: skip
    walkers = {name: walk_field(_quarter(*rows)) for name, rows in QUARTERS.items()}
    answers = iter([tasks, {"total": total}])
    orchestrator = lambda messages: json_answer(next(answers))(messages)  # noqa: E731
    scouts = by_task(walkers, lambda m: AIMessage("Nothing to do."))
    return by_system({FIELD_ROUNDS_INSTRUCTIONS[:60]: orchestrator}, scouts)


def test_four_scouts_on_an_open_field_take_about_a_quarter_of_the_turns() -> None:  # SC-007
    row = _play("rounds", four_scouts(FIELD2.true_total), level="S2").row
    assert row.success and row.cells_seen == 100 and row.scouts == 4
    assert row.optimal_steps == 100 and row.steps is not None and row.steps > 100
    # The longest quarter is 5 moves down plus 29 along rows 6–8; then the submission.
    assert row.parallel_turns == 35 and row.parallel_turns <= row.optimal_steps / 2.5
