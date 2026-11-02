"""A3 plan-and-execute: a planner writes subgoals, an executor works through them in order, and a
replanner is asked again only when a subgoal cannot be done or finished, or the plan is used up.

A3 commits to its plan: a done subgoal hands straight over to the next, which is what sets it apart
from A5's supervisor, who decides after every task.

The executor is A2's map-state agent with a subgoal line; the planner and replanner see the same
map and make no tool calls, so A3 differs from A2 in planning alone (specs/006
contracts/plan-execute.md). Written by the agent at the experimenter's request, as is its
signal-trace version on the probe log (specs/009) and its rune-floor version on the walk log
(specs/010) and its workshop version on the
workshop log (specs/011).
"""

import json
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from apl.arch.dungeon_map import DungeonMap
from apl.arch.field_map import FieldMap
from apl.arch.hybrid import MAX_MISSES
from apl.arch.mapstate import (
    FIELD_MAP_INSTRUCTIONS,
    MAP_INSTRUCTIONS,
    PROBE_LOG_INSTRUCTIONS,
    WALK_LOG_INSTRUCTIONS,
    WORKSHOP_LOG_INSTRUCTIONS,
)
from apl.arch.probe_log import ProbeLog
from apl.arch.scouts import read_answer
from apl.arch.walk_log import WalkLog
from apl.arch.workshop_log import WorkshopLog
from apl.kit import Kit

# Constants, not derived from the step budget: the budget would reveal the optimum (research R5).
MAX_SUBGOALS = 8  # a longer plan is not used
MAX_TURNS = 20  # executor turns on one subgoal; then it goes back to the replanner as unfinished
MAX_IDLE = 3  # subgoals in a row without a tool call; then A3 stops

# The planning texts explain the setup and the answer format only; no advice on what to plan.
PLANNER_INSTRUCTIONS = """\
In this setup you do not call the tools yourself. You write a plan: a short ordered list of \
subgoals. An executor carries them out in order with the tools and sees the same map as you (the \
map's "you" is the executor). You are asked again only when a subgoal cannot be done or finished, \
or the plan is used up. Every tool call of the executor costs a step from the budget. Answer with \
one JSON object and nothing else:
{"plan": ["<subgoal>", ...]} with 1 to 8 subgoals."""

REPLANNER_INSTRUCTIONS = """\
In this setup you do not call the tools yourself. You keep a plan up to date: a short ordered \
list of subgoals. An executor carries them out in order with the tools and sees the same map as \
you (the map's "you" is the executor). You are asked again only when a subgoal cannot be done or \
finished, or the plan is used up; then you see the reports so far, the map and the plan still to \
do. Every tool call of the executor costs a step from the budget. Answer with one JSON object and \
nothing else:
{"plan": ["<subgoal>", ...]} with the 1 to 8 subgoals still to do, or {"done": true} to stop."""

# Explains the subgoal line, as the scouts' text explains their task line (research R2).
EXECUTOR_INSTRUCTIONS = """\
The line starting with "Your subgoal:" says what to do now; it is one step of a longer plan. \
When the subgoal is done or cannot be done, answer without a tool call and say briefly what you \
did and found. If it cannot be done, start that answer with "Cannot:"."""

CANNOT = "cannot:"  # the start of a report on a subgoal that cannot be done, in any case


@dataclass(frozen=True, slots=True)
class Outcome:
    subgoal: str
    status: Literal["done", "cannot", "unfinished"]
    report: str  # the executor's last reply text

    def render(self, number: int) -> str:
        how = {"done": "done", "cannot": "could not be done"}.get(
            self.status, f"unfinished after {MAX_TURNS} turns"
        )
        return f"{number}. {self.subgoal}: {how}: {self.report}"


class PlanState(TypedDict):
    # No reducers: each write replaces the value, as in A2 (data-model.md).
    messages: list[BaseMessage]  # the executor's latest turn only
    map: DungeonMap | FieldMap | ProbeLog | WalkLog | WorkshopLog
    plan: list[str]  # subgoals still to do; plan[0] is the current one
    finished: list[Outcome]
    subgoal: int  # subgoals started so far, for the executor's role
    turns: int  # executor turns on the current subgoal
    acted: bool  # whether the current subgoal made a tool call
    idle: int  # subgoals in a row that ended without a tool call
    misses: int  # unusable planning answers in a row
    note: str  # why the last planning answer was not used
    steps: int  # tool calls applied so far
    started: bool  # whether the executor has seen the start result
    stop: bool  # the replanner answered {"done": true}


def read_plan(answer: dict[str, Any] | str) -> list[str] | str:
    """The subgoals of an answer, or why there are none."""
    if isinstance(answer, str):
        return answer
    plan = answer.get("plan")
    if not isinstance(plan, list) or not 1 <= len(plan) <= MAX_SUBGOALS:
        return f'"plan" must be a list of 1 to {MAX_SUBGOALS} subgoals'
    if not all(isinstance(subgoal, str) and subgoal.strip() for subgoal in plan):
        return "every subgoal must be a non-empty text"
    return [subgoal.strip() for subgoal in plan]


def _has_calls(message: BaseMessage) -> bool:
    # Unparsable calls go to the tools too: they cost a step and get an error back.
    return isinstance(message, AIMessage) and bool(message.tool_calls or message.invalid_tool_calls)


def _role(name: str) -> Any:
    return {"metadata": {"role": name}}


def _miss(state: PlanState, why: str) -> dict[str, Any]:
    note = f"Your answer was not used: {why}. Answer with one JSON object as described."
    return {"misses": state["misses"] + 1, "note": note}


def _finish(
    state: PlanState, status: Literal["done", "cannot", "unfinished"], report: str
) -> dict[str, Any]:
    outcome = Outcome(state["plan"][0], status, report)
    return {"finished": [*state["finished"], outcome], "plan": state["plan"][1:]}


def play(kit: Kit) -> None:
    model = kit.model.bind_tools(kit.tools)
    survey = kit.problem == "survey"
    signal = kit.problem == "signal"  # the probe log (specs/009 R11)
    rune = kit.problem == "rune"  # the walk log (specs/010 R12)
    workshop = kit.problem == "workshop"  # the workshop log (specs/011 R12)
    if workshop:
        map_instructions = WORKSHOP_LOG_INSTRUCTIONS
    elif rune:
        map_instructions = WALK_LOG_INSTRUCTIONS
    elif signal:
        map_instructions = PROBE_LOG_INSTRUCTIONS
    else:
        map_instructions = FIELD_MAP_INSTRUCTIONS if survey else MAP_INSTRUCTIONS
    planner_system = SystemMessage(kit.base_prompt + "\n\n" + PLANNER_INSTRUCTIONS)
    replanner_system = SystemMessage(kit.base_prompt + "\n\n" + REPLANNER_INSTRUCTIONS)
    executor_system = SystemMessage(
        kit.base_prompt + "\n\n" + map_instructions + " " + EXECUTOR_INSTRUCTIONS
    )

    def render(found: DungeonMap | FieldMap | ProbeLog | WalkLog | WorkshopLog) -> str:
        return found.render(False) if isinstance(found, DungeonMap) else found.render()

    def ask(system: SystemMessage, parts: list[str], role: str) -> dict[str, Any] | str:
        prompt = HumanMessage("\n\n".join(part for part in parts if part))
        reply = kit.model.invoke([system, prompt], config=_role(role))
        assert isinstance(reply, AIMessage)
        return read_answer(str(reply.text))

    def planner(state: PlanState) -> dict[str, Any]:
        answer = ask(planner_system, [state["note"], kit.start, render(state["map"])], "planner")
        plan = read_plan(answer)
        if isinstance(plan, str):
            return _miss(state, plan)
        return {"plan": plan, "subgoal": 1, "misses": 0, "note": ""}

    def executor(state: PlanState) -> dict[str, Any]:
        line = f"Your subgoal: {state['plan'][0]}"
        if not state["started"]:
            line += "\n\n" + kit.start
        messages = [
            executor_system,
            HumanMessage(line),
            *state["messages"],
            HumanMessage(render(state["map"])),
        ]
        reply = model.invoke(messages, config=_role(f"executor (subgoal {state['subgoal']})"))
        if _has_calls(reply):
            return {"messages": [reply], "turns": state["turns"] + 1, "started": True}
        idle = 0 if state["acted"] else state["idle"] + 1
        said = str(reply.text).strip()
        if said.lower().startswith(CANNOT):
            report = _finish(state, "cannot", said[len(CANNOT) :].strip())
        else:
            report = _finish(state, "done", said)
        update = {"messages": [reply], "started": True, "idle": idle, **report}
        if report["finished"][-1].status == "done" and report["plan"]:
            # The next subgoal starts without its predecessor's turn and without replanning.
            update |= {"messages": [], "turns": 0, "acted": False, "subgoal": state["subgoal"] + 1}
        return update

    def act(state: PlanState) -> dict[str, Any]:
        reply = state["messages"][-1]
        results = kit.tool_node(state)["messages"]
        assert isinstance(reply, AIMessage)
        calls = {c["id"]: c for c in [*reply.tool_calls, *reply.invalid_tool_calls]}
        for result in results:
            call = calls[result.tool_call_id]
            args = call["args"] if isinstance(call["args"], dict) else {}
            state["map"].apply(call["name"] or "", args, json.loads(str(result.content)))
        update: dict[str, Any] = {
            "messages": [reply, *results],
            "map": state["map"],
            "acted": True,
            "steps": state["steps"] + len(results),
        }
        if state["turns"] >= MAX_TURNS:
            update |= _finish(state, "unfinished", str(reply.text) or "no report")
            update["idle"] = 0
        return update

    def replanner(state: PlanState) -> dict[str, Any]:
        worked = "\n".join(o.render(i) for i, o in enumerate(state["finished"], 1))
        left = "\n".join(f"{i}. {s}" for i, s in enumerate(state["plan"], 1)) or "nothing"
        parts = [
            state["note"],
            kit.start,
            f"Subgoals worked on:\n{worked}",
            f"Still planned:\n{left}",
            f"Steps used so far: {state['steps']}",
            render(state["map"]),
        ]
        answer = ask(replanner_system, parts, "replanner")
        if isinstance(answer, dict) and answer.get("done") is True:
            return {"stop": True}
        plan = read_plan(answer)
        if isinstance(plan, str):
            return _miss(state, plan)
        return {
            "plan": plan,
            "subgoal": state["subgoal"] + 1,
            "turns": 0,
            "acted": False,
            "messages": [],
            "misses": 0,
            "note": "",
        }

    def after_planning(again: str) -> Any:
        def edge(state: PlanState) -> str:
            if state["stop"] or state["misses"] >= MAX_MISSES:
                return END
            return again if state["note"] else "executor"

        return edge

    def after_executor(state: PlanState) -> str:
        if state["messages"] and _has_calls(state["messages"][-1]):
            return "act"
        if state["idle"] >= MAX_IDLE:
            return END
        ahead = state["finished"][-1].status == "done" and state["plan"]
        return "executor" if ahead else "replanner"

    def after_act(state: PlanState) -> str:
        return "replanner" if state["turns"] >= MAX_TURNS else "executor"

    graph = StateGraph(PlanState)
    graph.add_node("planner", planner)
    graph.add_node("executor", executor)
    graph.add_node("act", act)
    graph.add_node("replanner", replanner)
    graph.add_edge(START, "planner")
    graph.add_conditional_edges("planner", after_planning("planner"), ["planner", "executor", END])
    graph.add_conditional_edges("executor", after_executor, ["act", "executor", "replanner", END])
    graph.add_conditional_edges("act", after_act, ["executor", "replanner"])
    graph.add_conditional_edges(
        "replanner", after_planning("replanner"), ["replanner", "executor", END]
    )
    found: DungeonMap | FieldMap | ProbeLog | WalkLog | WorkshopLog
    if workshop:
        found = WorkshopLog.from_start(kit.start)
    elif rune:
        found = WalkLog.from_start(kit.start)
    elif signal:
        found = ProbeLog.from_start(kit.start)
    elif survey:
        found = FieldMap.from_start(kit.start)
    else:
        found = DungeonMap.from_start(kit.start)
    graph.compile().invoke(
        {
            "messages": [],
            "map": found,
            "plan": [],
            "finished": [],
            "subgoal": 0,
            "turns": 0,
            "acted": False,
            "idle": 0,
            "misses": 0,
            "note": "",
            "steps": 0,
            "started": False,
            "stop": False,
        },
        config={"recursion_limit": kit.recursion_limit},
    )
