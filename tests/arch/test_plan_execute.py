"""A3 plan-and-execute with scripted answers (specs/006 contracts/plan-execute.md, US2)."""

import itertools

import pytest
from langchain_core.messages import AIMessage, BaseMessage

from apl.arch.mapstate import FIELD_MAP_INSTRUCTIONS, MAP_INSTRUCTIONS
from apl.arch.plan_execute import (
    EXECUTOR_INSTRUCTIONS,
    MAX_IDLE,
    MAX_TURNS,
    PLANNER_INSTRUCTIONS,
    REPLANNER_INSTRUCTIONS,
)
from apl.dungeon import generate
from apl.kit import BASE_PROMPT
from apl.runner import registry
from apl.runner.episode import EpisodeResult, play_episode
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from apl.survey import generate as generate_field
from apl.survey.prompt import BASE_PROMPT as FIELD_BASE_PROMPT
from tests.arch.orchestrated import recording, roles, text
from tests.runner.scripted import (
    Strategy,
    bump_wall,
    by_system,
    json_answer,
    scripted_factory,
    walk_field,
    walk_solution,
)
from tests.runner.test_run import _wall

ONE_GOAL = {"plan": ["reach the exit"]}


def _play(arch: str, level: str, seed: int, strategy: Strategy) -> EpisodeResult:
    problem = "survey" if level.startswith("S") else "dungeon"
    key = EpisodeKey(arch, level, seed, 1)
    return play_episode(
        key, "test", "dev", Settings(), registry.load(arch), scripted_factory(strategy),
        problem=problem,
    )  # fmt: skip


def _a3(executor: Strategy, planner: Strategy, replanner: Strategy | None = None) -> Strategy:
    # The full texts as markers: the two planning texts share their first sentence.
    routes = {PLANNER_INSTRUCTIONS: planner, REPLANNER_INSTRUCTIONS: replanner or planner}
    return by_system(routes, executor)


def _answers(*answers: object) -> Strategy:
    """The answers in order, then the last one again."""
    queue = itertools.chain(answers, itertools.repeat(answers[-1]))
    return lambda messages: json_answer(next(queue))(messages)


def _system(messages: list[BaseMessage]) -> str:
    return str(messages[0].content)


@pytest.mark.parametrize(("level", "seed"), [("L1", 1000), ("L2", 1001), ("L3", 1002)])
def test_a_one_subgoal_plan_escapes_like_mapstate(level: str, seed: int) -> None:  # SC-002, 2.1
    walk = walk_solution(generate(level, seed))
    result = _play("plan_execute", level, seed, _a3(walk, json_answer(ONE_GOAL)))
    reference = _play("mapstate", level, seed, walk).row
    row = result.row
    assert row.success and row.efficiency == 1.0 and row.arch_error is None
    assert row.steps == reference.steps and row.budget == reference.budget
    assert roles(result)[:2] == ["planner", "executor (subgoal 1)"]
    assert row.orchestrator_calls == 1  # the planner; the episode ended inside subgoal 1
    assert roles(result)[-1] == "executor (subgoal 1)"  # no planning call after the end


@pytest.mark.parametrize("level", ["S1", "S2", "S3"])
def test_the_executor_walks_the_field_and_submits(level: str) -> None:  # SC-002, acceptance 2.2
    field = generate_field(level, 1000)
    walk = walk_field(field.walk, total=field.true_total)
    plan = json_answer({"plan": ["walk every cell and submit the total"]})
    row = _play("plan_execute", level, 1000, _a3(walk, plan)).row
    reference = _play("mapstate", level, 1000, walk).row
    assert row.success and row.submitted_total == field.true_total
    assert row.steps == reference.steps and row.budget == reference.budget


@pytest.mark.parametrize(
    ("level", "seed", "base", "instructions"),
    [
        ("L3", 1002, BASE_PROMPT, MAP_INSTRUCTIONS),
        ("S2", 1000, FIELD_BASE_PROMPT, FIELD_MAP_INSTRUCTIONS),
    ],
)
def test_every_job_gets_the_base_prompt_and_the_executor_a2s_map(
    level: str, seed: int, base: str, instructions: str
) -> None:  # SC-003
    seen: list[list[BaseMessage]] = []
    executor = lambda m: AIMessage("Nothing to do.")  # noqa: E731
    replanner = json_answer({"done": True})
    _play(
        "plan_execute",
        level,
        seed,
        recording(_a3(executor, json_answer(ONE_GOAL), replanner), seen),
    )
    systems = [_system(m) for m in seen]
    assert systems == [
        base + "\n\n" + PLANNER_INSTRUCTIONS,
        base + "\n\n" + instructions + " " + EXECUTOR_INSTRUCTIONS,
        base + "\n\n" + REPLANNER_INSTRUCTIONS,
    ]
    assert "Your map (built from your tool results so far):" in text(seen[0])  # the planner's map
    assert "Your subgoal: reach the exit" in text(seen[1])


def test_steps_are_the_executors_tool_calls_and_planning_is_counted_apart() -> None:  # SC-004
    wall = _wall("L1", 1000)
    turns = iter([True, True, False, True, True, False])  # two bumps, then a report, twice
    executor = lambda m: bump_wall(wall)(m) if next(turns) else AIMessage("Bumped.")  # noqa: E731
    plan = json_answer({"plan": ["bump", "bump again"]})
    replanner = _answers({"plan": ["bump again"]}, {"done": True})
    result = _play("plan_execute", "L1", 1000, _a3(executor, plan, replanner))
    row = result.row
    assert row.steps == 4 and row.invalid_actions == 4
    planning = roles(result).count("planner") + roles(result).count("replanner")
    assert row.orchestrator_calls == planning == 3
    assert row.end_reason == "stopped"


def test_three_unusable_plans_give_up() -> None:  # data-model.md, SC-005
    seen: list[list[BaseMessage]] = []
    executor = lambda m: AIMessage("Nothing to do.")  # noqa: E731
    row = _play(
        "plan_execute", "L1", 1000, recording(_a3(executor, lambda m: AIMessage("?")), seen)
    ).row
    assert row.end_reason == "stopped" and row.orchestrator_calls == 3 and row.steps == 0
    assert "Your answer was not used:" in str(seen[1][1].content)


@pytest.mark.parametrize(
    "answer",
    [
        {"plan": [f"subgoal {i}" for i in range(9)]},
        {"plan": []},
        {"plan": ["  "]},
        {"plan": "reach the exit"},
        {"done": True},  # valid for the replanner only
    ],
)
def test_unusable_plans(answer: object) -> None:  # data-model.md validation rules
    seen: list[list[BaseMessage]] = []
    executor = lambda m: AIMessage("Nothing to do.")  # noqa: E731
    _play(
        "plan_execute",
        "L1",
        1000,
        recording(_a3(executor, _answers(answer, ONE_GOAL), json_answer({"done": True})), seen),
    )
    assert "Your answer was not used:" in text(seen[1])
    assert _system(seen[2]).endswith(EXECUTOR_INSTRUCTIONS)


def test_idle_subgoals_stop_a3() -> None:  # edge case: no tool call, subgoal after subgoal
    seen: list[list[BaseMessage]] = []
    executor = lambda m: AIMessage("Nothing to do.")  # noqa: E731
    result = _play(
        "plan_execute", "L1", 1000, recording(_a3(executor, json_answer(ONE_GOAL)), seen)
    )
    assert result.row.end_reason == "stopped" and result.row.steps == 0
    assert roles(result) == [
        "planner",
        "executor (subgoal 1)",
        "replanner",
        "executor (subgoal 2)",
        "replanner",
        "executor (subgoal 3)",
    ]
    assert MAX_IDLE == 3


def test_an_unfinished_subgoal_goes_back_to_the_replanner() -> None:  # MAX_TURNS, edge case
    seen: list[list[BaseMessage]] = []
    executor = bump_wall(_wall("L3", 1002))
    result = _play(
        "plan_execute",
        "L3",
        1002,
        recording(_a3(executor, json_answer(ONE_GOAL), json_answer({"done": True})), seen),
    )
    assert result.row.steps == MAX_TURNS == 20
    assert roles(result).count("executor (subgoal 1)") == MAX_TURNS
    replanning = text(seen[-1])
    assert f"1. reach the exit: unfinished after {MAX_TURNS} turns:" in replanning
    assert f"Steps used so far: {MAX_TURNS}" in replanning


def test_done_ends_the_episode_as_stopped() -> None:  # acceptance 2.4
    executor = lambda m: AIMessage("Looked around.")  # noqa: E731
    row = _play(
        "plan_execute",
        "L1",
        1000,
        _a3(executor, json_answer(ONE_GOAL), json_answer({"done": True})),
    ).row
    assert row.end_reason == "stopped" and row.orchestrator_calls == 2 and row.steps == 0


def test_the_replanner_sees_reports_and_the_plan_still_to_do() -> None:
    seen: list[list[BaseMessage]] = []
    reports = iter(["Found a red key.", "Saw the exit."])
    executor = lambda m: AIMessage(next(reports))  # noqa: E731
    plan = json_answer({"plan": ["look for keys", "look for the exit", "leave"]})
    replanner = _answers({"plan": ["look for the exit", "leave"]}, {"done": True})
    _play("plan_execute", "L1", 1000, recording(_a3(executor, plan, replanner), seen))
    first, second = (text(m) for m in seen if _system(m).endswith(REPLANNER_INSTRUCTIONS))
    assert "1. look for keys: done: Found a red key." in first
    assert "Still planned:\n1. look for the exit\n2. leave" in first
    assert "2. look for the exit: done: Saw the exit." in second
    assert "Still planned:\n1. leave" in second
    assert "Steps used so far: 0" in first
    assert '"ok": true' in first and '"ok": true' in second  # the start result (FR-004)


def test_a_new_subgoal_starts_without_the_previous_turn() -> None:
    seen: list[list[BaseMessage]] = []
    wall = _wall("L1", 1000)
    moves = iter([True, False, True, False])
    executor = lambda m: bump_wall(wall)(m) if next(moves) else AIMessage("Done.")  # noqa: E731
    plan = json_answer({"plan": ["bump", "bump again"]})
    replanner = _answers({"plan": ["bump again"]}, {"done": True})
    result = _play("plan_execute", "L1", 1000, recording(_a3(executor, plan, replanner), seen))
    executing = [m for m in seen if _system(m).endswith(EXECUTOR_INSTRUCTIONS)]
    assert [len(m) for m in executing] == [3, 5, 3, 5]  # system, subgoal, [reply, result,] map
    assert "Your subgoal: bump again" in text(executing[2])
    assert '"ok"' in str(executing[0][1].content)  # the start result, on the first turn only
    assert '"ok"' not in str(executing[2][1].content)
    assert "executor (subgoal 2)" in roles(result)
