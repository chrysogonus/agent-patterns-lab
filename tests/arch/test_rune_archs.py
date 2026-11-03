"""A2 and A3 on the rune floor (specs/010 contracts/architectures.md, FR-022, FR-023)."""

import json

from langchain_core.messages import AIMessage, BaseMessage

from apl.arch.mapstate import WALK_LOG_INSTRUCTIONS
from apl.arch.plan_execute import PLANNER_INSTRUCTIONS, REPLANNER_INSTRUCTIONS
from apl.arch.walk_log import WalkLog
from apl.rune import AgentTools, generate, start_episode
from apl.rune.prompt import BASE_PROMPT
from tests.arch.orchestrated import recording, roles, text
from tests.arch.rune_play import play, reference
from tests.runner.scripted import by_system, json_answer


def test_mapstate_reads_its_walk_log_every_turn() -> None:
    seen: list[list[BaseMessage]] = []
    result = play("mapstate", "R1", 1000, recording(reference("R1", 1000), seen))
    assert result.row.success and result.row.problem == "rune" and result.outcome is not None
    assert str(seen[0][0].content) == BASE_PROMPT + "\n\n" + WALK_LOG_INSTRUCTIONS
    # Every turn ends with the log built from the results so far.
    floor = generate("R1", 1000)
    log = WalkLog.from_start(json.dumps(AgentTools(start_episode(floor)).start.to_dict()))
    for turn, messages in enumerate(seen):
        assert str(messages[-1].content) == log.render(), turn
        if turn < len(result.outcome.log):
            entry = result.outcome.log[turn]
            args = {"direction": entry.action.args[0]}
            log.apply("move", args, entry.result.to_dict())
    assert str(seen[0][-1].content).startswith("Floor: 7 columns × 5 rows. Start A3, goal G3.")


def test_plan_execute_plans_and_its_executor_reads_the_log() -> None:
    seen: list[list[BaseMessage]] = []
    strategy = by_system(
        {
            PLANNER_INSTRUCTIONS: json_answer({"plan": ["reach the goal"]}),
            REPLANNER_INSTRUCTIONS: json_answer({"done": True}),
        },
        reference("R1", 1000),
    )
    result = play("plan_execute", "R1", 1000, recording(strategy, seen))
    assert result.row.success
    assert roles(result)[:2] == ["planner", "executor (subgoal 1)"]
    executor = [m for m in seen if WALK_LOG_INSTRUCTIONS in str(m[0].content)]
    assert executor and all("Floor: 7 columns × 5 rows." in text(m) for m in executor)
    planner = seen[0]
    assert "Floor: 7 columns × 5 rows." in text(planner) and '"floor"' in text(planner)


def test_mapstate_stops_when_the_model_stops() -> None:
    result = play("mapstate", "R1", 1000, lambda messages: AIMessage("I give up."))
    assert not result.row.success and result.row.end_reason == "stopped"
