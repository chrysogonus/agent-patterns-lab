"""A2 and A3 on the workshop (specs/011 contracts/architectures.md, FR-022, FR-023)."""

import json

from langchain_core.messages import AIMessage, BaseMessage

from apl.arch.mapstate import WORKSHOP_LOG_INSTRUCTIONS
from apl.arch.plan_execute import PLANNER_INSTRUCTIONS, REPLANNER_INSTRUCTIONS
from apl.arch.workshop_log import WorkshopLog
from apl.workshop import AgentTools, generate, start_episode
from apl.workshop.prompt import BASE_PROMPT
from tests.arch.orchestrated import recording, roles, text
from tests.arch.workshop_play import play, reference
from tests.runner.scripted import by_system, json_answer


def test_mapstate_reads_its_workshop_log_every_turn() -> None:
    seen: list[list[BaseMessage]] = []
    result = play("mapstate", "W2", 1000, recording(reference("W2", 1000), seen))
    assert result.row.success and result.row.problem == "workshop" and result.outcome is not None
    assert str(seen[0][0].content) == BASE_PROMPT + "\n\n" + WORKSHOP_LOG_INSTRUCTIONS
    w = generate("W2", 1000)
    log = WorkshopLog.from_start(json.dumps(AgentTools(start_episode(w)).start.to_dict()))
    for turn, messages in enumerate(seen):
        assert str(messages[-1].content) == log.render(), turn
        if turn < len(result.outcome.log):
            entry = result.outcome.log[turn]
            args: dict[str, object] = {"item": entry.action.args[0]}
            if entry.action.tool == "craft":
                args["recipe"] = int(entry.action.args[1])
            log.apply(entry.action.tool, args, entry.result.to_dict())


def test_plan_execute_plans_and_its_executor_reads_the_log() -> None:
    seen: list[list[BaseMessage]] = []
    strategy = by_system(
        {
            PLANNER_INSTRUCTIONS: json_answer({"plan": ["craft the goal"]}),
            REPLANNER_INSTRUCTIONS: json_answer({"done": True}),
        },
        reference("W2", 1000),
    )
    result = play("plan_execute", "W2", 1000, recording(strategy, seen))
    assert result.row.success
    assert roles(result)[:2] == ["planner", "executor (subgoal 1)"]
    executor = [m for m in seen if WORKSHOP_LOG_INSTRUCTIONS in str(m[0].content)]
    assert executor and all("Goal: gear." in text(m) for m in executor)
    assert '"stock"' in text(seen[0])


def test_mapstate_stops_when_the_model_stops() -> None:
    result = play("mapstate", "W1", 1000, lambda messages: AIMessage("I give up."))
    assert not result.row.success and result.row.end_reason == "stopped"
