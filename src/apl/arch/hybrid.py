"""A6 hybrid: code keeps the map, finds the routes and walks them; the model only picks a target.

The code nodes work only from the map, which is built from tool results (Constitution II), and
every call they make is a tool call that costs a step (Constitution III). On the signal trace
code keeps the suspects and lists the probes that split them best (specs/009). Written by the agent
at the experimenter's request.
"""

import itertools
import json
import re
from typing import NamedTuple, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from apl.arch.dungeon_map import DungeonMap
from apl.arch.probe_log import ProbeLog
from apl.kit import Kit

# Explains the setup and the answer format only; no advice on which option to pick.
HYBRID_INSTRUCTIONS = """\
In this setup you do not call the tools yourself. Every turn you see your map, built from your \
tool results so far, and a numbered list of options. Code carries out the option you choose: it \
walks the shortest route there through doors you have already walked, unlocks the door if the \
option says so, and then goes through the door or takes the item. Every call it makes costs a \
step, as shown next to each option. Answer with the number of one option and nothing else."""

# The signal trace's (specs/009 contracts/architectures.md): the setup and the format only.
SIGNAL_HYBRID_INSTRUCTIONS = """\
In this setup you do not call the tools yourself. Every turn you see your probe log and a numbered \
list of options. Code carries out the option you choose with one tool call. For each probe, the \
option says how many segments could still be the broken one after each answer. Answer with the \
number of one option and nothing else."""

# Probes listed per turn, and the suspects left from which submissions are offered (R11).
SIGNAL_PROBES = 8
SIGNAL_SUBMITS = 4

Call = tuple[str, dict[str, object]]

# Answers in a row that name no option before the agent gives up; re-asks cost no step.
MAX_MISSES = 3


class Option(NamedTuple):
    text: str  # what the model reads
    calls: list[Call]  # the tool calls code makes for it


class HybridState(TypedDict):
    map: DungeonMap | ProbeLog
    options: list[Option]
    note: str  # what happened since the model's last answer
    misses: int  # answers in a row that named no option


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


def signal_options(log: ProbeLog) -> list[Option]:
    """The probes that split the suspects most evenly, then submissions near the end."""
    left = log.suspects()
    if len(left) <= 1:
        return [Option(f"submit {k}", [("submit", {"segment": k})]) for k in sorted(left)]
    probes = []
    for k in range(1, log.segments + 1):
        dry = len(left & log.upstream(k))
        if 0 < dry < len(left):
            probes.append((max(dry, len(left) - dry), k, len(left) - dry, dry))
    probes.sort()
    found = [
        Option(f"probe {k}: leaves {wet} if wet, {dry} if dry", [("probe", {"segment": k})])
        for _, k, wet, dry in probes[:SIGNAL_PROBES]
    ]
    if len(left) <= SIGNAL_SUBMITS:
        found += [Option(f"submit {k}", [("submit", {"segment": k})]) for k in sorted(left)]
    return found


def play(kit: Kit) -> None:
    if kit.problem == "signal":  # specs/009: the same graph over a probe log
        system = SystemMessage(kit.base_prompt + "\n\n" + SIGNAL_HYBRID_INSTRUCTIONS)
        _graph(kit, system, ProbeLog.from_start(kit.start))
        return
    system = SystemMessage(kit.base_prompt + "\n\n" + HYBRID_INSTRUCTIONS)
    _graph(kit, system, DungeonMap.from_start(kit.start))


def _graph(kit: Kit, system: SystemMessage, start: DungeonMap | ProbeLog) -> None:
    ids = itertools.count(1)

    def plan(state: HybridState) -> dict[str, list[Option]]:
        found = state["map"]
        return {"options": signal_options(found) if isinstance(found, ProbeLog) else options(found)}

    def choose(state: HybridState) -> dict[str, object]:
        listed = "\n".join(f"{i}. {o.text}" for i, o in enumerate(state["options"], 1))
        prompt = f"{state['note']}\n\n{state['map'].render()}\n\nOptions:\n{listed}".lstrip()
        reply = kit.model.invoke([system, HumanMessage(prompt)])
        # The whole answer must be the number ("3", "3.", "Option 3"): a number picked out of
        # prose ("avoid 1", "-1", a label like "e9") would take a step the model did not choose.
        found = re.fullmatch(r"(?:option\s*)?(\d+)\.?", str(reply.text).strip(), re.IGNORECASE)
        if found and 1 <= (number := int(found.group(1))) <= len(state["options"]):
            return {"options": [state["options"][number - 1]], "note": "", "misses": 0}
        # The choice is asked again; only tool calls cost steps.
        answer = str(reply.text)[:200]
        note = f"Your answer {answer!r} named no option. Answer with one number."
        return {"note": note, "misses": state["misses"] + 1}

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
        if state["misses"] == 0:
            return "act"
        return END if state["misses"] >= MAX_MISSES else "choose"

    graph = StateGraph(HybridState)
    graph.add_node("plan", plan)
    graph.add_node("choose", choose)
    graph.add_node("act", act)
    graph.add_edge(START, "plan")
    graph.add_conditional_edges("plan", after_plan)
    graph.add_conditional_edges("choose", after_choose)
    graph.add_edge("act", "plan")
    graph.compile().invoke(
        {"map": start, "options": [], "note": "", "misses": 0},
        config={"recursion_limit": kit.recursion_limit},
    )
