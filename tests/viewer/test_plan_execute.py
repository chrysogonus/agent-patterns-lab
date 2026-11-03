"""A3 in the viewer: offered on both problems, its roles in the side panel (specs/006 US1)."""

from pathlib import Path

import pytest
from langchain_core.messages import AIMessage, BaseMessage

from apl.dungeon import generate
from apl.survey import generate as generate_field
from tests.arch.orchestrated import text
from tests.arch.test_plan_execute import _a3, _answers
from tests.runner.scripted import Strategy, json_answer, scripted_factory, walk_field, walk_solution
from tests.viewer.test_app import OLLAMA, _body, _events, _start, _viewer

PLAN = {"plan": ["look around", "finish the task"]}


def test_plan_execute_is_offered_on_both_problems(tmp_path: Path) -> None:  # acceptance 1.1
    data = _body(_viewer(tmp_path, architectures=None).options())
    assert "plan_execute" in data["problems"]["dungeon"]["architectures"]
    assert "plan_execute" in data["problems"]["survey"]["architectures"]


def _looks_first(then: Strategy) -> Strategy:
    """Subgoal "look around" is reported at once; the next one is played by `then`."""

    def strategy(messages: list[BaseMessage]) -> AIMessage:
        return (
            AIMessage("Looked.")
            if "Your subgoal: look around" in text(messages)
            else then(messages)
        )

    return strategy


@pytest.mark.parametrize("level", ["L1", "L2", "L3", "S1", "S2", "S3"])  # SC-001
def test_the_side_panel_shows_each_job_and_replays_it(tmp_path: Path, level: str) -> None:
    survey = level.startswith("S")
    if not survey:
        play = walk_solution(generate(level, 1000))
    else:
        field = generate_field(level, 1000)
        play = walk_field(field.walk, total=field.true_total)
    strategy = _a3(_looks_first(play), json_answer(PLAN), _answers({"plan": ["finish the task"]}))
    viewer = _viewer(tmp_path, OLLAMA, model_factory=scripted_factory(strategy), architectures=None)
    problem = {"problem": "survey"} if survey else {}
    episode_id = _start(viewer, "plan_execute", level, 1000, **problem)
    events = _events(viewer, episode_id)
    turns = [e["data"] for e in events if e["type"] == "turn"]
    roles = [t["role"] for t in turns]
    # A done subgoal hands straight over to the next one (acceptance 1.2, 1.3).
    assert roles[:3] == ["planner", "executor (subgoal 1)", "executor (subgoal 2)"]
    # A walk longer than MAX_TURNS brings the replanner back in between.
    assert {r for r in roles[2:] if not r.startswith("executor (subgoal ")} <= {"replanner"}
    assert turns[0]["text"] == '{"plan": ["look around", "finish the task"]}'
    assert events[-1]["data"]["row"]["success"]
    replayed = _viewer(tmp_path, OLLAMA).session(episode_id)  # acceptance 1.4
    assert replayed is not None and replayed.done
    assert [event for _, event in (x for x in replayed.stream() if x)] == events
