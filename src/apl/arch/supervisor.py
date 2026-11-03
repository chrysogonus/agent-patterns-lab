"""A5 supervisor: a supervisor hands one task at a time to a navigator or an inventory helper.

Each helper is A2's map-state agent offered only its own tools (the navigator look and move, the
inventory helper take and use) and runs as a subgraph. Both act as one body and share one map;
the supervisor sees the same map and makes no tool calls, so A5 differs from A2 in the split into
specialists and the handoffs between them (specs/008 contracts/supervisor.md). On the workshop
the helpers are a researcher (look, inspect) and a crafter (gather, craft) on the workshop log
(specs/011 contracts/architectures.md). Written by the agent at the experimenter's request.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import Command

from apl.arch.dungeon_map import DungeonMap
from apl.arch.hybrid import MAX_MISSES
from apl.arch.mapstate import MAP_INSTRUCTIONS, WORKSHOP_LOG_INSTRUCTIONS
from apl.arch.plan_execute import MAX_IDLE, MAX_TURNS
from apl.arch.scouts import read_answer
from apl.arch.workshop_log import WorkshopLog
from apl.kit import Kit

Helper = str  # a helper's name in its problem's team
Goto = str  # "supervisor", a helper, or "__end__"
STOP: Literal["__end__"] = "__end__"  # LangGraph's END, typed for Command

TOOLS: dict[Helper, tuple[str, str]] = {"navigator": ("look", "move"), "inventory": ("take", "use")}
CALLED = {"navigator": "the navigator", "inventory": "the inventory helper"}

# The texts explain the setup and the answer format only; no advice on whom to send where (R6).
SUPERVISOR_INSTRUCTIONS = """\
In this setup you do not call the tools yourself. You direct two helpers who act as one body in \
the dungeon and see the same map as you (the map's "you" is that body). The navigator can call \
look and move. The inventory helper can call take and use. Hand one task at a time to one \
helper; it reports back when the task is done or cannot be done. Every tool call of a helper \
costs a step from the budget. Answer with one JSON object and nothing else:
{"to": "navigator", "task": "<task>"}, {"to": "inventory", "task": "<task>"}, or {"done": true} \
to stop."""

_HELPER_INSTRUCTIONS = """\
In this setup you can call only {own}; {other} calls {others}. The line starting with \
"Your task:" says what to do now. When the task is done or cannot be done, answer without a \
tool call and say briefly what you did and found."""

NAVIGATOR_INSTRUCTIONS = _HELPER_INSTRUCTIONS.format(
    own="look and move", other="the inventory helper", others="take and use"
)
INVENTORY_INSTRUCTIONS = _HELPER_INSTRUCTIONS.format(
    own="take and use", other="the navigator", others="look and move"
)
INSTRUCTIONS: dict[Helper, str] = {
    "navigator": NAVIGATOR_INSTRUCTIONS,
    "inventory": INVENTORY_INSTRUCTIONS,
}

# The workshop's team (specs/011 contracts/architectures.md): the same texts with its names.
WORKSHOP_SUPERVISOR_INSTRUCTIONS = """\
In this setup you do not call the tools yourself. You direct two helpers who share one inventory \
and see the same workshop log as you. The researcher can call look and inspect. The crafter can \
call gather and craft. Hand one task at a time to one helper; it reports back when the task is \
done or cannot be done. Every tool call of a helper costs a step from the budget. Answer with one \
JSON object and nothing else:
{"to": "researcher", "task": "<task>"}, {"to": "crafter", "task": "<task>"}, or {"done": true} \
to stop."""
RESEARCHER_INSTRUCTIONS = _HELPER_INSTRUCTIONS.format(
    own="look and inspect", other="the crafter", others="gather and craft"
)
CRAFTER_INSTRUCTIONS = _HELPER_INSTRUCTIONS.format(
    own="gather and craft", other="the researcher", others="look and inspect"
)

Memory = DungeonMap | WorkshopLog


@dataclass(frozen=True, slots=True)
class Team:
    """A problem's supervisor text, helpers, their tools and texts, and the shared memory."""

    supervisor: str
    tools: dict[Helper, tuple[str, ...]]
    called: dict[Helper, str]
    instructions: dict[Helper, str]
    memory_instructions: str
    memory: Callable[[str], Memory]  # built from the start view

    @property
    def owner(self) -> dict[str, Helper]:
        return {tool: helper for helper, tools in self.tools.items() for tool in tools}


TEAMS: dict[str, Team] = {
    "dungeon": Team(
        SUPERVISOR_INSTRUCTIONS,
        dict(TOOLS),
        dict(CALLED),
        dict(INSTRUCTIONS),
        MAP_INSTRUCTIONS,
        DungeonMap.from_start,
    ),
    "workshop": Team(
        WORKSHOP_SUPERVISOR_INSTRUCTIONS,
        {"researcher": ("look", "inspect"), "crafter": ("gather", "craft")},
        {"researcher": "the researcher", "crafter": "the crafter"},
        {"researcher": RESEARCHER_INSTRUCTIONS, "crafter": CRAFTER_INSTRUCTIONS},
        WORKSHOP_LOG_INSTRUCTIONS,
        WorkshopLog.from_start,
    ),
}


@dataclass(frozen=True, slots=True)
class Report:
    helper: Helper
    task: str
    status: Literal["done", "unfinished"]
    report: str  # the helper's last reply text

    def render(self, number: int) -> str:
        how = "done" if self.status == "done" else f"unfinished after {MAX_TURNS} turns"
        return f"{number}. {self.helper}: {self.task}: {how}: {self.report}"


class SupervisorState(TypedDict):
    # No reducers: each write replaces the value, as in A2 (data-model.md). The helpers'
    # subgraphs use this schema too, so they read and write the parent's keys directly.
    messages: list[BaseMessage]  # the current helper's latest turn only
    map: Memory
    helper: str  # the helper of the current handoff
    task: str
    finished: list[Report]
    handoffs: int  # handoffs so far, for the helper's role
    turns: int  # helper turns on the current handoff
    acted: bool  # whether a call of the current handoff reached the dungeon
    idle: int  # finished handoffs in a row without such a call
    misses: int  # unusable supervisor answers in a row
    note: str  # why the last supervisor answer was not used
    steps: int  # calls that reached the dungeon so far
    started: bool  # whether a helper has seen the start result


def read_handoff(
    answer: dict[str, Any] | str, team: Team = TEAMS["dungeon"]
) -> tuple[Helper, str] | str:
    """The helper and task of an answer, or why there are none."""
    if isinstance(answer, str):
        return answer
    helper, task = answer.get("to"), answer.get("task")
    if not isinstance(helper, str) or helper not in team.tools:
        first, second = team.tools
        return f'"to" must be "{first}" or "{second}"'
    if not isinstance(task, str) or not task.strip():
        return '"task" must be a non-empty text'
    return helper, task.strip()


def refusal(tool: str, team: Team = TEAMS["dungeon"]) -> str:
    return f"Not made: {tool} is {team.called[team.owner[tool]]}'s tool. It cost no step."


def _has_calls(message: BaseMessage) -> bool:
    # Unparsable calls go to the tools too: they cost a step and get an error back.
    return isinstance(message, AIMessage) and bool(message.tool_calls or message.invalid_tool_calls)


def _role(name: str) -> Any:
    return {"metadata": {"role": name}}


def _finish(
    state: SupervisorState, status: Literal["done", "unfinished"], report: str, acted: bool
) -> dict[str, Any]:
    done = Report(state["helper"], state["task"], status, report)
    return {"finished": [*state["finished"], done], "idle": 0 if acted else state["idle"] + 1}


def play(kit: Kit) -> None:
    team = TEAMS[kit.problem]
    supervisor_system = SystemMessage(kit.base_prompt + "\n\n" + team.supervisor)

    def supervisor(state: SupervisorState) -> Command[Goto]:
        handoffs = "\n".join(r.render(i) for i, r in enumerate(state["finished"], 1)) or "none"
        parts = [
            state["note"],
            kit.start,
            f"Handoffs so far:\n{handoffs}",
            f"Steps used so far: {state['steps']}",
            state["map"].render(),
        ]
        prompt = HumanMessage("\n\n".join(part for part in parts if part))
        reply = kit.model.invoke([supervisor_system, prompt], config=_role("supervisor"))
        assert isinstance(reply, AIMessage)
        answer = read_answer(str(reply.text))
        if isinstance(answer, dict) and answer.get("done") is True:
            return Command(goto=STOP)
        handoff = read_handoff(answer, team)
        if isinstance(handoff, str):
            note = f"Your answer was not used: {handoff}. Answer with one JSON object as described."
            misses = state["misses"] + 1
            again: Goto = STOP if misses >= MAX_MISSES else "supervisor"
            return Command(goto=again, update={"misses": misses, "note": note})
        helper, task = handoff
        update = {
            "helper": helper,
            "task": task,
            "handoffs": state["handoffs"] + 1,
            "turns": 0,
            "acted": False,
            "messages": [],
            "misses": 0,
            "note": "",
        }
        return Command(goto=helper, update=update)

    def subgraph(name: Helper) -> CompiledStateGraph[Any, Any, Any, Any]:
        own = team.tools[name]
        model = kit.model.bind_tools([t for t in kit.tools if t["function"]["name"] in own])
        system = SystemMessage(
            kit.base_prompt + "\n\n" + team.memory_instructions + " " + team.instructions[name]
        )

        def helper(state: SupervisorState) -> dict[str, Any]:
            line = f"Your task: {state['task']}"
            if not state["started"]:
                line += "\n\n" + kit.start
            messages = [
                system,
                HumanMessage(line),
                *state["messages"],
                HumanMessage(state["map"].render()),
            ]
            reply = model.invoke(messages, config=_role(f"{name} (task {state['handoffs']})"))
            if _has_calls(reply):
                return {"messages": [reply], "turns": state["turns"] + 1, "started": True}
            report = _finish(state, "done", str(reply.text), state["acted"])
            return {"messages": [reply], "started": True, **report}

        def act(state: SupervisorState) -> dict[str, Any]:
            reply = state["messages"][-1]
            assert isinstance(reply, AIMessage)
            calls = [*reply.tool_calls, *reply.invalid_tool_calls]
            # The other helper's tools never reach the dungeon (research R2); the rest do, in order.
            refused = {c["id"] for c in calls if team.owner.get(c["name"] or "", name) != name}
            sent = reply.model_copy(
                update={
                    "tool_calls": [c for c in reply.tool_calls if c["id"] not in refused],
                    "invalid_tool_calls": [
                        c for c in reply.invalid_tool_calls if c["id"] not in refused
                    ],
                }
            )
            results = kit.tool_node({"messages": [sent]})["messages"]
            answers: dict[str | None, ToolMessage] = {r.tool_call_id: r for r in results}
            for call in calls:
                if call["id"] in refused:
                    text = refusal(call["name"] or "", team)
                    answers[call["id"]] = ToolMessage(
                        text, tool_call_id=call["id"] or "", name=call["name"], status="error"
                    )
                else:
                    args = call["args"] if isinstance(call["args"], dict) else {}
                    result = json.loads(str(answers[call["id"]].content))
                    state["map"].apply(call["name"] or "", args, result)
            acted = state["acted"] or bool(results)
            update: dict[str, Any] = {
                "messages": [reply, *(answers[c["id"]] for c in calls)],
                "map": state["map"],
                "acted": acted,
                "steps": state["steps"] + len(results),
            }
            if state["turns"] >= MAX_TURNS:
                update |= _finish(state, "unfinished", str(reply.text) or "no report", acted)
            return update

        def after_helper(state: SupervisorState) -> str:
            return "act" if _has_calls(state["messages"][-1]) else END

        def after_act(state: SupervisorState) -> str:
            return END if state["turns"] >= MAX_TURNS else "helper"

        graph = StateGraph(SupervisorState)
        graph.add_node("helper", helper)
        graph.add_node("act", act)
        graph.add_edge(START, "helper")
        graph.add_conditional_edges("helper", after_helper, ["act", END])
        graph.add_conditional_edges("act", after_act, ["helper", END])
        return graph.compile()

    def after_handoff(state: SupervisorState) -> str:
        return END if state["idle"] >= MAX_IDLE else "supervisor"

    graph = StateGraph(SupervisorState)
    graph.add_node("supervisor", supervisor)
    for name in team.tools:
        graph.add_node(name, subgraph(name))
        graph.add_conditional_edges(name, after_handoff, ["supervisor", END])
    graph.add_edge(START, "supervisor")
    graph.compile().invoke(
        {
            "messages": [],
            "map": team.memory(kit.start),
            "helper": "",
            "task": "",
            "finished": [],
            "handoffs": 0,
            "turns": 0,
            "acted": False,
            "idle": 0,
            "misses": 0,
            "note": "",
            "steps": 0,
            "started": False,
        },
        config={"recursion_limit": kit.recursion_limit},
    )
