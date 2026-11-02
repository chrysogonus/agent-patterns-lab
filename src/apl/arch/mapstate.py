"""A2 map state: an explicit map in graph state replaces the message history.

Each turn the model sees the base prompt with the map instructions, its previous reply with that
reply's tool results, and the map (specs/003 contracts/mapstate.md). Written by the agent at the
experimenter's request; the signal trace's probe log (specs/009) and the rune floor's walk log
(specs/010) too.
"""

import json
from typing import TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from apl.arch.dungeon_map import DungeonMap
from apl.arch.field_map import FieldMap
from apl.arch.probe_log import ProbeLog
from apl.arch.walk_log import WalkLog
from apl.kit import Kit

# Explains the map only; strategy advice would mix a prompt effect into the memory effect (R15).
MAP_INSTRUCTIONS = """\
You do not see the earlier conversation. Instead, every turn ends with your map. It is built \
from your own tool results so far: every room you have seen with its exits, where each exit \
leads once you have gone through it, the items in each room, your inventory, and the doors you \
opened. "unexplored" means you have not gone through that exit yet; "locked (color)" means it \
was locked when you last saw it. Your previous reply and its tool results come just before the \
map."""

# The same for the survey field (specs/005 R10): it explains the map, not where to go.
FIELD_MAP_INSTRUCTIONS = """\
You do not see the earlier conversation. Instead, every turn ends with your map. It is built \
from your own tool results so far: a picture of the field with every cell you have seen and \
whether it holds a deposit, the number of cells and deposits seen, the walls you have seen, and \
the unseen cells next to seen ones. Your previous reply and its tool results come just before the \
map."""

# The same for the signal trace (specs/009 contracts/architectures.md): the log, not a strategy.
PROBE_LOG_INSTRUCTIONS = """\
You do not see the earlier conversation. Instead, every turn ends with your probe log. It is built \
from your own tool results so far: the pipe's runs and every probe answer, in the order you got \
them. Your previous reply and its tool results come just before the log."""

# The same for the rune floor (specs/010 contracts/architectures.md): the walks, not the rule.
WALK_LOG_INSTRUCTIONS = """\
You do not see the earlier conversation. Instead, every turn ends with your walk log. It is built \
from your own tool results so far: the floor, the cell you are on, and every walk from the start, \
with the tiles you stepped on in order and how the walk ended. Your previous reply and its tool \
results come just before the log."""

# For the routes variant (mapstate_routes); it explains the list, it does not say which to take.
ROUTE_INSTRUCTIONS = """\
Under the map, each unexplored exit is listed with the moves that reach it from your room through \
doors you have already walked, nearest first."""


class MapState(TypedDict):
    # No reducers: each write replaces the value, so the history never builds up (R11).
    messages: list[BaseMessage]  # the latest turn only
    map: DungeonMap | FieldMap | ProbeLog | WalkLog


def play(kit: Kit) -> None:
    run(kit, routes=False)


def run(kit: Kit, *, routes: bool) -> None:
    model = kit.model.bind_tools(kit.tools)
    survey = kit.problem == "survey"  # the field map; written by the agent (specs/005 R10)
    signal = kit.problem == "signal"  # the probe log; written by the agent (specs/009 R11)
    rune = kit.problem == "rune"  # the walk log; written by the agent (specs/010 R12)
    if rune:
        instructions = WALK_LOG_INSTRUCTIONS
    elif signal:
        instructions = PROBE_LOG_INSTRUCTIONS
    elif survey:
        instructions = FIELD_MAP_INSTRUCTIONS
    else:
        instructions = MAP_INSTRUCTIONS + (" " + ROUTE_INSTRUCTIONS if routes else "")
    system = SystemMessage(kit.base_prompt + "\n\n" + instructions)
    start = HumanMessage(kit.start)

    def render(found: DungeonMap | FieldMap | ProbeLog | WalkLog) -> str:
        return found.render(routes) if isinstance(found, DungeonMap) else found.render()

    def agent(state: MapState) -> dict[str, list[BaseMessage]]:
        turn = state["messages"] or [start]
        reply = model.invoke([system, *turn, HumanMessage(render(state["map"]))])
        return {"messages": [reply]}

    def act(state: MapState) -> MapState:
        reply = state["messages"][-1]
        results = kit.tool_node(state)["messages"]
        assert isinstance(reply, AIMessage)
        calls = {c["id"]: c for c in [*reply.tool_calls, *reply.invalid_tool_calls]}
        for result in results:
            call = calls[result.tool_call_id]
            args = call["args"] if isinstance(call["args"], dict) else {}
            state["map"].apply(call["name"] or "", args, json.loads(str(result.content)))
        return {"messages": [reply, *results], "map": state["map"]}

    def route(state: MapState) -> str:
        last = state["messages"][-1]
        # Unparsable calls go to the tools too: they cost a step and get an error back.
        has_calls = isinstance(last, AIMessage) and (last.tool_calls or last.invalid_tool_calls)
        return "act" if has_calls else END

    graph = StateGraph(MapState)
    graph.add_node("agent", agent)
    graph.add_node("act", act)
    graph.add_edge(START, "agent")
    graph.add_conditional_edges("agent", route)
    graph.add_edge("act", "agent")
    found: DungeonMap | FieldMap | ProbeLog | WalkLog
    if rune:
        found = WalkLog.from_start(kit.start)
    elif signal:
        found = ProbeLog.from_start(kit.start)
    elif survey:
        found = FieldMap.from_start(kit.start)
    else:
        found = DungeonMap.from_start(kit.start)
    graph.compile().invoke(
        {"messages": [], "map": found},
        config={"recursion_limit": kit.recursion_limit},
    )
