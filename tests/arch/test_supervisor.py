"""A5 supervisor with scripted answers (specs/008 contracts/supervisor.md, US1)."""

import itertools
from collections.abc import Sequence
from typing import Any

import pytest
from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import AIMessage, BaseMessage, ToolMessage
from langchain_core.runnables import Runnable
from pydantic import Field

from apl.arch.hybrid import MAX_MISSES
from apl.arch.mapstate import MAP_INSTRUCTIONS
from apl.arch.plan_execute import MAX_IDLE, MAX_TURNS
from apl.arch.supervisor import (
    INVENTORY_INSTRUCTIONS,
    NAVIGATOR_INSTRUCTIONS,
    SUPERVISOR_INSTRUCTIONS,
)
from apl.dungeon import generate
from apl.kit import BASE_PROMPT, TOOL_SCHEMAS
from apl.runner import registry
from apl.runner.episode import EpisodeResult, play_episode
from apl.runner.settings import Settings
from apl.runner.spec import EpisodeKey
from tests.arch.orchestrated import play, recording, roles, text
from tests.runner.scripted import (
    ScriptedChatModel,
    Strategy,
    bump_wall,
    by_system,
    json_answer,
    next_action,
    tool_calls,
    unknown_tool,
    walk_solution,
)
from tests.runner.test_run import _wall

ITEM_TOOLS = {"take", "use"}
DONE = json_answer({"done": True})
UNUSED: Strategy = lambda m: AIMessage("This helper is never handed a task.")  # noqa: E731


def _a5(supervisor: Strategy, navigator: Strategy, inventory: Strategy | None = None) -> Strategy:
    routes = {
        SUPERVISOR_INSTRUCTIONS: supervisor,
        NAVIGATOR_INSTRUCTIONS: navigator,
        INVENTORY_INSTRUCTIONS: inventory or navigator,
    }
    return by_system(routes, lambda m: AIMessage("unrouted"))


def _answers(*answers: object) -> Strategy:
    """The answers in order, then the last one again."""
    queue = itertools.chain(answers, itertools.repeat(answers[-1]))
    return lambda messages: json_answer(next(queue))(messages)


def _replies(*replies: AIMessage) -> Strategy:
    queue = itertools.chain(replies, itertools.repeat(replies[-1]))
    return lambda messages: next(queue)


def split_walk(level: str, seed: int) -> Strategy:
    """The solution split by tool: the supervisor hands to whoever owns the next action."""
    dungeon = generate(level, seed)
    find, walk = next_action(dungeon), walk_solution(dungeon)

    def supervisor(messages: list[BaseMessage]) -> AIMessage:
        action = find(messages)
        if action is None:
            return json_answer({"done": True})(messages)
        helper = "inventory" if action.tool in ITEM_TOOLS else "navigator"
        return json_answer({"to": helper, "task": f"do the next {action.tool}"})(messages)

    def helper(own: set[str]) -> Strategy:
        def strategy(messages: list[BaseMessage]) -> AIMessage:
            action = find(messages)
            return walk(messages) if action and action.tool in own else AIMessage("Done.")

        return strategy

    return _a5(supervisor, helper({"look", "move"}), helper(ITEM_TOOLS))


def _system(messages: list[BaseMessage]) -> str:
    return str(messages[0].content)


@pytest.mark.parametrize(("level", "seed"), [("L1", 1000), ("L2", 1001), ("L3", 1002)])
def test_the_split_walk_escapes_like_mapstate(level: str, seed: int) -> None:  # SC-001, US1 1
    result = play("supervisor", level, seed, split_walk(level, seed))
    reference = play("mapstate", level, seed, walk_solution(generate(level, seed))).row
    row = result.row
    assert row.success and row.efficiency == 1.0 and row.arch_error is None
    assert row.steps == reference.steps and row.budget == reference.budget  # SC-002, SC-003
    assert roles(result)[:2] == ["supervisor", "navigator (task 1)"]
    assert row.orchestrator_calls == roles(result).count("supervisor")  # FR-013
    assert not roles(result)[-1] == "supervisor"  # no supervisor call after the end


def test_the_inventory_helper_opens_the_door_on_l3() -> None:  # US1 2
    result = play("supervisor", "L3", 1002, split_walk("L3", 1002))
    assert result.row.success
    helpers = [r for r in roles(result) if r and r != "supervisor"]
    assert any(r.startswith("inventory (task ") for r in helpers)
    tasks = [int(r.split("task ")[1].rstrip(")")) for r in helpers]
    assert tasks == sorted(tasks) and tasks[0] == 1  # n counts handoffs


def test_an_off_role_call_is_refused_and_costs_no_step() -> None:  # US1 3, FR-003
    seen: list[list[BaseMessage]] = []
    wall = _wall("L1", 1000)
    navigator = _replies(
        tool_calls(("take", {"item": "red key"}), ("move", {"direction": wall})),
        AIMessage("Done."),
    )
    supervisor = _answers({"to": "navigator", "task": "go"}, {"done": True})
    row = play("supervisor", "L1", 1000, recording(_a5(supervisor, navigator), seen)).row
    assert row.steps == 1 and row.invalid_actions == 1  # the move only
    second = seen[2]  # the navigator's second turn: its reply and both answers
    answers = [m for m in second if isinstance(m, ToolMessage)]
    assert [a.status for a in answers] == ["error", "error"]
    assert answers[0].content == "Not made: take is the inventory helper's tool. It cost no step."
    assert '"no_door"' in str(answers[1].content)  # the move reached the dungeon


def test_an_unknown_tool_reaches_the_dungeon_like_everyone_elses() -> None:  # edge cases
    seen: list[list[BaseMessage]] = []
    navigator = _replies(unknown_tool()([]), AIMessage("Done."))
    supervisor = _answers({"to": "navigator", "task": "open the door"}, {"done": True})
    row = play("supervisor", "L1", 1000, recording(_a5(supervisor, navigator), seen)).row
    assert row.steps == 1 and row.invalid_actions == 1
    answers = [m for m in seen[2] if isinstance(m, ToolMessage)]
    assert len(answers) == 1 and '"unknown_tool"' in str(answers[0].content)


def test_a_navigator_that_only_calls_take_ends() -> None:  # SC-004
    navigator = lambda m: tool_calls(("take", {"item": "red key"}))  # noqa: E731
    supervisor = json_answer({"to": "navigator", "task": "take the key"})
    result = play("supervisor", "L1", 1000, _a5(supervisor, navigator))
    assert result.row.end_reason == "stopped" and result.row.steps == 0
    assert roles(result).count("supervisor") == MAX_IDLE
    assert len(roles(result)) == MAX_IDLE * (1 + MAX_TURNS)


def test_done_first_stops_without_a_step() -> None:  # US1 4
    result = play("supervisor", "L1", 1000, _a5(DONE, UNUSED))
    assert result.row.end_reason == "stopped" and result.row.steps == 0
    assert roles(result) == ["supervisor"]


@pytest.mark.parametrize(
    "answer",
    [
        "no json here",
        {"to": "cook", "task": "make soup"},
        {"to": "navigator", "task": "  "},
        {"to": "navigator"},
        {"plan": ["go"]},
    ],
)
def test_unusable_answers_stop_a5(answer: object) -> None:  # R4, edge cases
    seen: list[list[BaseMessage]] = []
    reply = (lambda m: AIMessage(answer)) if isinstance(answer, str) else json_answer(answer)
    result = play("supervisor", "L1", 1000, recording(_a5(reply, UNUSED), seen))
    assert result.row.end_reason == "stopped" and result.row.steps == 0
    assert roles(result) == ["supervisor"] * MAX_MISSES
    assert "Your answer was not used:" in text(seen[1])
    assert "Your answer was not used:" not in text(seen[0])


def test_a_usable_answer_after_a_miss_clears_the_note() -> None:
    seen: list[list[BaseMessage]] = []
    supervisor = _answers("bad", {"to": "navigator", "task": "look"}, {"done": True})
    navigator = lambda m: AIMessage("Nothing to do.")  # noqa: E731
    play("supervisor", "L1", 1000, recording(_a5(supervisor, navigator), seen))
    assert "Your answer was not used:" in text(seen[1])
    assert "Your answer was not used:" not in text(seen[3])


def test_idle_handoffs_stop_a5() -> None:  # MAX_IDLE, edge cases
    navigator = lambda m: AIMessage("Nothing to do.")  # noqa: E731
    supervisor = json_answer({"to": "navigator", "task": "look around"})
    result = play("supervisor", "L1", 1000, _a5(supervisor, navigator))
    assert result.row.end_reason == "stopped" and result.row.steps == 0
    assert roles(result) == [
        "supervisor",
        "navigator (task 1)",
        "supervisor",
        "navigator (task 2)",
        "supervisor",
        "navigator (task 3)",
    ]


def test_an_unfinished_task_goes_back_to_the_supervisor() -> None:  # MAX_TURNS
    seen: list[list[BaseMessage]] = []
    supervisor = _answers({"to": "navigator", "task": "bump"}, {"done": True})
    navigator = bump_wall(_wall("L3", 1002))
    result = play("supervisor", "L3", 1002, recording(_a5(supervisor, navigator), seen))
    assert result.row.steps == MAX_TURNS == 20
    assert roles(result).count("navigator (task 1)") == MAX_TURNS
    last = text(seen[-1])
    assert f"1. navigator: bump: unfinished after {MAX_TURNS} turns:" in last
    assert f"Steps used so far: {MAX_TURNS}" in last


def test_a_finished_handoff_is_reported() -> None:
    seen: list[list[BaseMessage]] = []
    supervisor = _answers({"to": "inventory", "task": "check"}, {"done": True})
    inventory = lambda m: AIMessage("Nothing to take here.")  # noqa: E731
    play("supervisor", "L1", 1000, recording(_a5(supervisor, UNUSED, inventory), seen))
    assert "Handoffs so far:\nnone" in text(seen[0])
    assert "1. inventory: check: done: Nothing to take here." in text(seen[2])


def test_the_budget_can_run_out_inside_a_task() -> None:  # edge case
    supervisor = json_answer({"to": "navigator", "task": "bump"})
    result = play("supervisor", "L1", 1000, _a5(supervisor, bump_wall(_wall("L1", 1000))))
    assert result.row.budget_hit and result.row.steps == result.row.budget
    assert roles(result)[-1] != "supervisor"


def test_every_job_gets_the_base_prompt_and_the_helpers_a2s_map() -> None:  # SC-002, FR-004
    seen: list[list[BaseMessage]] = []
    play("supervisor", "L3", 1002, recording(split_walk("L3", 1002), seen))
    systems = {_system(m) for m in seen}
    assert systems == {
        BASE_PROMPT + "\n\n" + SUPERVISOR_INSTRUCTIONS,
        BASE_PROMPT + "\n\n" + MAP_INSTRUCTIONS + " " + NAVIGATOR_INSTRUCTIONS,
        BASE_PROMPT + "\n\n" + MAP_INSTRUCTIONS + " " + INVENTORY_INSTRUCTIONS,
    }
    assert _system(seen[0]).endswith(SUPERVISOR_INSTRUCTIONS)
    last = str(seen[0][-1].content)
    assert last.startswith("Your map (built") or "\n\nYour map (built" in last
    assert last.rstrip().splitlines()[-1].startswith("Unexplored exits:")  # the map comes last
    head = str(seen[1][1].content)
    assert head.startswith("Your task: ") and head.count('"ok": true') == 1  # the start result
    later = [m for m in seen[2:] if not _system(m).endswith(SUPERVISOR_INSTRUCTIONS)]
    assert all('"ok": true' not in str(m[1].content) for m in later)  # only the first turn


class _Offered(ScriptedChatModel):
    offered: list[list[dict[str, Any]]] = Field(default_factory=list)

    def bind_tools(self, tools: Sequence[Any], **kwargs: Any) -> Runnable[Any, AIMessage]:
        self.offered.append(list(tools))
        return super().bind_tools(tools, **kwargs)


def test_each_helper_is_offered_only_its_tools() -> None:  # FR-003, SC-002
    model = _Offered(strategy=_a5(DONE, UNUSED))

    def factory(settings: Settings, callbacks: list[BaseCallbackHandler]) -> _Offered:
        model.callbacks = callbacks
        return model

    key = EpisodeKey("supervisor", "L1", 1000, 1)
    result: EpisodeResult = play_episode(
        key, "test", "dev", Settings(), registry.load("supervisor"), factory
    )
    assert result.row.arch_error is None
    schemas = {s["function"]["name"]: s for s in TOOL_SCHEMAS}
    names = sorted([s["function"]["name"] for s in tools] for tools in model.offered)
    assert names == [["look", "move"], ["take", "use"]]
    assert all(s == schemas[s["function"]["name"]] for tools in model.offered for s in tools)


def test_supervisor_plays_the_dungeon_only() -> None:  # US3 2
    assert registry.plays("supervisor", "dungeon")
    assert not registry.plays("supervisor", "survey")
