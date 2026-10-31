"""A7 fan-out once: the orchestrator splits the work once; scouts explore on their own maps.

The orchestrator is called once with the start room. Each scout sees only its own map and never
hears from the others (specs/004 contracts/orchestrators.md). Written by the agent at the
experimenter's request.
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
    scout_node,
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


class FanoutState(ScoutGraph):
    note: str  # why the last answer was not used
    misses: int


def play(kit: Kit) -> None:
    system = SystemMessage(kit.base_prompt + "\n\n" + FANOUT_INSTRUCTIONS)

    def own_map(number: int, start: str) -> SharedMap:
        return SharedMap.from_start(start, number)

    def orchestrate(state: FanoutState) -> dict[str, Any]:
        prompt = f"{state['note']}\n\nThe start room:\n{kit.start}".lstrip()
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
            return dispatch(kit, END)(state)
        return END if state["misses"] >= MAX_MISSES else "orchestrate"

    graph = StateGraph(FanoutState)
    graph.add_node("orchestrate", orchestrate)
    graph.add_node("scout", scout_node(kit), input_schema=ScoutTurn)
    graph.add_node("act", act)
    graph.add_edge(START, "orchestrate")
    graph.add_conditional_edges("orchestrate", after_orchestrate, ["orchestrate", "scout", END])
    graph.add_edge("scout", "act")
    graph.add_conditional_edges("act", dispatch(kit, END), ["scout", END])
    graph.compile().invoke(
        {"scouts": [], "replies": [], "board": None, "steps": 0, "note": "", "misses": 0},
        config={"recursion_limit": kit.recursion_limit},
    )
