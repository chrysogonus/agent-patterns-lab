"""A2 and A3 on the signal trace (specs/009 contracts/architectures.md, FR-022, FR-023)."""

from langchain_core.messages import AIMessage, BaseMessage

from apl.arch.mapstate import PROBE_LOG_INSTRUCTIONS
from apl.arch.plan_execute import PLANNER_INSTRUCTIONS, REPLANNER_INSTRUCTIONS
from apl.signal_trace import generate
from apl.signal_trace.prompt import BASE_PROMPT
from apl.signal_trace.strategy import reference_run
from tests.arch.orchestrated import recording, roles, text
from tests.arch.signal_play import play, reference
from tests.runner.scripted import by_system, json_answer


def _said(answers: list[tuple[int, bool]]) -> str:
    if not answers:
        return "Probes so far: none."
    listed = ", ".join(f"{k} {'wet' if w else 'dry'}" for k, w in answers)
    return f"Probes so far ({len(answers)}, in order): {listed}."


def test_mapstate_reads_its_probe_log_every_turn() -> None:
    seen: list[list[BaseMessage]] = []
    result = play("mapstate", "T2", 1000, recording(reference("T2", 1000), seen))
    assert result.row.success and result.row.problem == "signal"
    assert str(seen[0][0].content) == BASE_PROMPT + "\n\n" + PROBE_LOG_INSTRUCTIONS
    probes, _ = reference_run(generate("T2", 1000))
    for turn, messages in enumerate(seen):
        last = str(messages[-1].content)
        assert last.startswith("Pipe: 64 segments.\nRuns: S → 1–64\n")
        assert last.endswith(_said(probes[:turn]))


def test_plan_execute_plans_and_its_executor_reads_the_log() -> None:
    seen: list[list[BaseMessage]] = []
    strategy = by_system(
        {
            PLANNER_INSTRUCTIONS: json_answer({"plan": ["find the broken segment"]}),
            REPLANNER_INSTRUCTIONS: json_answer({"done": True}),
        },
        reference("T1", 1000),
    )
    result = play("plan_execute", "T1", 1000, recording(strategy, seen))
    assert result.row.success
    assert roles(result)[:2] == ["planner", "executor (subgoal 1)"]
    executor = [m for m in seen if PROBE_LOG_INSTRUCTIONS in str(m[0].content)]
    assert executor and all("Pipe: 16 segments." in text(m) for m in executor)
    planner = seen[0]
    assert "Pipe: 16 segments." in text(planner) and '"runs"' in text(planner)


def test_mapstate_stops_when_the_model_stops() -> None:
    result = play("mapstate", "T1", 1000, lambda messages: AIMessage("I give up."))
    assert not result.row.success and result.row.end_reason == "stopped"
