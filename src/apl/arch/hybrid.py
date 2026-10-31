"""A6 hybrid: code keeps the map, finds the routes and walks them; the model only picks a target.

The code nodes work only from the map, which is built from tool results (Constitution II), and
every call they make is a tool call that costs a step (Constitution III). Written by the agent at
the experimenter's request.
"""

import itertools
import json
import re
from typing import NamedTuple, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from apl.arch.dungeon_map import DungeonMap
from apl.kit import Kit

# Explains the setup and the answer format only; no advice on which option to pick.
HYBRID_INSTRUCTIONS = """\
In this setup you do not call the tools yourself. Every turn you see your map, built from your \
tool results so far, and a numbered list of options. Code carries out the option you choose: it \
walks the shortest route there through doors you have already walked, unlocks the door if the \
option says so, and then goes through the door or takes the item. Every call it makes costs a \
step, as shown next to each option. Answer with the number of one option and nothing else."""

Call = tuple[str, dict[str, str]]


class Option(NamedTuple):
    text: str  # what the model reads
    calls: list[Call]  # the tool calls code makes for it


class HybridState(TypedDict):
    map: DungeonMap
    options: list[Option]
    note: str  # what happened since the model's last answer


def options(m: DungeonMap) -> list[Option]:
    """Every target the map shows a way to, fewest steps first."""
    paths = m.paths()
    found = []
    for room, direction, moves in m.routes():
        walk: list[Call] = [("move", {"direction": d}) for d in moves[:-1]]
        through: Call = ("move", {"direction": direction})
        lock = m.rooms[room].exits[direction]
        key = f"{lock} key"  # the key naming the tool results use
        if lock is None:
            found.append((f"explore {room} {direction}", [*walk, through]))
        elif key in m.inventory:
            unlock: Call = ("use", {"item": key, "direction": direction})
            found.append(
                (f"unlock {room} {direction} with the {key}, go through", [*walk, unlock, through])
            )
    for room, note in m.rooms.items():
        walk = [("move", {"direction": d}) for d in paths[room]]
        for item in note.items:
            found.append((f"take the {item} in {room}", [*walk, ("take", {"item": item})]))
    found.sort(key=lambda option: len(option[1]))
    return [
        Option(f"{text} ({len(calls)} step{'s' if len(calls) > 1 else ''})", calls)
        for text, calls in found
    ]


def play(kit: Kit) -> None:
    system = SystemMessage(kit.base_prompt + "\n\n" + HYBRID_INSTRUCTIONS)
    ids = itertools.count(1)

    def plan(state: HybridState) -> dict[str, list[Option]]:
        return {"options": options(state["map"])}

    def choose(state: HybridState) -> dict[str, object]:
        listed = "\n".join(f"{i}. {o.text}" for i, o in enumerate(state["options"], 1))
        prompt = f"{state['note']}\n\n{state['map'].render()}\n\nOptions:\n{listed}".lstrip()
        reply = kit.model.invoke([system, HumanMessage(prompt)])
        number = re.search(r"\d+", str(reply.text))
        if number and 1 <= int(number.group()) <= len(state["options"]):
            return {"options": [state["options"][int(number.group()) - 1]], "note": ""}
        # The choice is asked again; only tool calls cost steps.
        answer = str(reply.text)[:200]
        return {"note": f"Your answer {answer!r} named no option. Answer with one number."}

    def act(state: HybridState) -> dict[str, object]:
        (chosen,) = state["options"]
        for name, args in chosen.calls:
            call = {"name": name, "args": args, "id": f"a6_{next(ids)}", "type": "tool_call"}
            (result,) = kit.tool_node({"messages": [AIMessage("", tool_calls=[call])]})["messages"]
            data = json.loads(str(result.content))
            state["map"].apply(name, args, data)
            if not data["ok"]:
                note = f"Last choice: {chosen.text}. It stopped: {data['error']['message']}"
                return {"map": state["map"], "note": note}
        return {"map": state["map"], "note": f"Last choice: {chosen.text}. Done."}

    def after_plan(state: HybridState) -> str:
        return "choose" if state["options"] else END  # nothing left the map shows a way to

    def after_choose(state: HybridState) -> str:
        return "choose" if state["note"] else "act"

    graph = StateGraph(HybridState)
    graph.add_node("plan", plan)
    graph.add_node("choose", choose)
    graph.add_node("act", act)
    graph.add_edge(START, "plan")
    graph.add_conditional_edges("plan", after_plan)
    graph.add_conditional_edges("choose", after_choose)
    graph.add_edge("act", "plan")
    graph.compile().invoke(
        {"map": DungeonMap.from_start(kit.start), "options": [], "note": ""},
        config={"recursion_limit": kit.recursion_limit},
    )
