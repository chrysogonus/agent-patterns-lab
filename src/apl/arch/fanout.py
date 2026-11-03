"""A7 fan-out once: the orchestrator splits the work once; scouts explore on their own maps.

The orchestrator is called once with the start room. Each scout sees only its own map and never
hears from the others (specs/004 contracts/orchestrators.md). On the survey field the
orchestrator is called once more with the scouts' reports and submits the total (specs/005 R14).
In the warehouse the scouts are robots and there is no collect step: the last delivery ends the
episode (specs/012).
Written by the agent at the experimenter's request.
"""

from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from apl.arch.hybrid import MAX_MISSES
from apl.arch.scouts import (
    ScoutGraph,
    ScoutState,
    ScoutTurn,
    SharedMap,
    act,
    dispatch,
    first_scout,
    new_scout,
    read_answer,
    read_tasks,
    read_total,
    scout_node,
    submit,
)
from apl.kit import Kit

# Explains the setup and the answer format only; no advice on how to split the dungeon.
FANOUT_INSTRUCTIONS = """\
In this setup you do not call the tools yourself. You send between 1 and 4 scouts into the \
dungeon. Each starts in the start room, calls the tools itself, carries out the task you give \
it within the number of steps you give it, and never hears from the other scouts. Keys stay \
with the scout that took them. Every tool call of every scout costs a step from the one shared \
budget. You decide once, now. Answer with one JSON object and nothing else:
{"scouts": [{"task": "<what this scout should do>", "steps": <its step limit>}, ...]}"""

# The same for the survey field, plus the collect step (specs/005 contracts/architectures.md).
FIELD_FANOUT_INSTRUCTIONS = """\
In this setup you do not call the tools yourself. You send between 1 and 4 scouts onto the \
field. Each starts in A1, calls the tools itself, carries out the task you give it within the \
number of steps you give it, reports back by answering without a tool call, and never hears \
from the other scouts. Every tool call of every scout costs a step from the one shared budget. \
When all scouts are done, you get their reports and submit the total. You decide the scouts \
once, now. Answer with one JSON object and nothing else:
{"scouts": [{"task": "<what this scout should do>", "steps": <its step limit>}, ...]}"""

# The same for the warehouse (specs/012 contracts/architectures.md): no advice on the split.
WAREHOUSE_FANOUT_INSTRUCTIONS = """\
In this setup you do not call the tools yourself. You send between 1 and 4 robots into the \
warehouse. Each starts on the dock, calls the tools itself, carries out the task you give it \
within the number of steps you give it, and never hears from the other robots. Every tool call of \
every robot costs a step from the one shared budget. You decide once, now. Answer with one JSON \
object and nothing else:
{"scouts": [{"task": "<what this robot should do>", "steps": <its step limit>}, ...]}"""

COLLECT = """\
The scouts are done. Their reports:
{reports}

Answer with one JSON object and nothing else:
{{"total": <the number of deposits in the whole field>}}"""


class FanoutState(ScoutGraph):
    note: str  # why the last answer was not used
    misses: int


def play(kit: Kit) -> None:
    survey = kit.problem == "survey"
    warehouse = kit.problem == "warehouse"  # specs/012
    instructions = FIELD_FANOUT_INSTRUCTIONS if survey else FANOUT_INSTRUCTIONS
    if warehouse:
        instructions = WAREHOUSE_FANOUT_INSTRUCTIONS
    system = SystemMessage(kit.base_prompt + "\n\n" + instructions)
    after_scouts = "collect" if survey else END

    def own_map(number: int, start: str) -> SharedMap[Any]:
        return SharedMap.from_start(start, number)

    def orchestrate(state: FanoutState) -> dict[str, Any]:
        start = "The start cell" if survey else "The start view" if warehouse else "The start room"
        prompt = f"{state['note']}\n\n{start}:\n{kit.start}".lstrip()
        config: Any = {"metadata": {"role": "orchestrator"}}
        reply = kit.model.invoke([system, HumanMessage(prompt)], config=config)
        assert isinstance(reply, AIMessage)
        answer = read_answer(str(reply.text))
        plan = (
            read_tasks(answer, "scouts", with_scout=False) if isinstance(answer, dict) else answer
        )
        if isinstance(plan, str):
            note = f"Your answer was not used: {plan}. Answer with one JSON object as described."
            return {"note": note, "misses": state["misses"] + 1}
        scouts: list[ScoutState] = []
        for i, (_, task, steps) in enumerate(plan):
            scout = first_scout(kit, own_map) if i == 0 else new_scout(kit, own_map)
            if scout is None:  # the shared setup's limit; cannot happen with at most 4 entries
                break
            scout.task, scout.steps_left = task, steps
            scouts.append(scout)
        return {"scouts": scouts, "note": "", "misses": 0}

    def after_orchestrate(state: FanoutState) -> Any:
        if state["scouts"]:
            return dispatch(kit, after_scouts)(state)
        return END if state["misses"] >= MAX_MISSES else "orchestrate"

    def collect(state: FanoutState) -> dict[str, Any]:
        """Survey only: the orchestrator turns the scouts' reports into one total and submits it."""
        reports = "\n".join(
            f"scout {s.number}: " + (s.report or "used up its steps") for s in state["scouts"]
        )
        prompt = f"{state['note']}\n\n{COLLECT.format(reports=reports)}".lstrip()
        config: Any = {"metadata": {"role": "orchestrator"}}
        reply = kit.model.invoke([system, HumanMessage(prompt)], config=config)
        assert isinstance(reply, AIMessage)
        answer = read_answer(str(reply.text))
        total = read_total(answer) if isinstance(answer, dict) else answer
        if isinstance(total, str):
            note = f"Your answer was not used: {total}. Answer with one JSON object as described."
            return {"note": note, "misses": state["misses"] + 1}
        submit(kit, total)  # ends the episode
        return {"note": "", "misses": 0}

    def after_collect(state: FanoutState) -> str:
        return END if state["misses"] >= MAX_MISSES else "collect"

    graph = StateGraph(FanoutState)
    graph.add_node("orchestrate", orchestrate)
    graph.add_node("scout", scout_node(kit), input_schema=ScoutTurn)
    graph.add_node("act", act)
    graph.add_edge(START, "orchestrate")
    graph.add_conditional_edges("orchestrate", after_orchestrate, ["orchestrate", "scout", END])
    graph.add_edge("scout", "act")
    graph.add_conditional_edges("act", dispatch(kit, after_scouts), ["scout", after_scouts])
    if survey:
        graph.add_node("collect", collect)
        graph.add_conditional_edges("collect", after_collect, ["collect", END])
    graph.compile().invoke(
        {"scouts": [], "replies": [], "board": None, "steps": 0, "note": "", "misses": 0},
        config={"recursion_limit": kit.recursion_limit},
    )
