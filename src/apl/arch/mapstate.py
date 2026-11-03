"""A2 map state: an explicit map in graph state replaces the message history.

Each turn the model sees the base prompt with the map instructions, its previous reply with that
reply's tool results, and the map (specs/003 contracts/mapstate.md). Written by the agent at the
experimenter's request; the signal trace's probe log (specs/009) and the rune floor's walk log
(specs/010), the workshop's log
(specs/011) and the warehouse's floor map (specs/012) too.
"""

import json
from collections.abc import Callable
from typing import TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from apl.arch.dungeon_map import DungeonMap
from apl.arch.field_map import FieldMap
from apl.arch.floor_map import FloorMap
from apl.arch.probe_log import ProbeLog
from apl.arch.walk_log import WalkLog
from apl.arch.workshop_log import WorkshopLog
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

# The same for the workshop (specs/011 contracts/architectures.md): what was seen, not a plan.
WORKSHOP_LOG_INSTRUCTIONS = """\
You do not see the earlier conversation. Instead, every turn ends with your workshop log. It is \
built from your own tool results so far: the goal, the stock, your inventory and every recipe you \
have inspected. Your previous reply and its tool results come just before the log."""

# The same for the warehouse (specs/012 contracts/architectures.md): what was seen, not a split.
FLOOR_MAP_INSTRUCTIONS = """\
You do not see the earlier conversation. Instead, every turn ends with your floor map. It is built \
from your own tool results so far: the floor plan, the corridors you have seen, the packages you \
have seen and where, what you carry, and how many packages are delivered. Your previous reply and \
its tool results come just before the map."""

# For the routes variant (mapstate_routes); it explains the list, it does not say which to take.
ROUTE_INSTRUCTIONS = """\
Under the map, each unexplored exit is listed with the moves that reach it from your room through \
doors you have already walked, nearest first."""


Memory = DungeonMap | FieldMap | ProbeLog | WalkLog | WorkshopLog | FloorMap

# Each problem's explicit memory, built from the start view, and the text that explains it. A2,
# A3 and A4 use the same memory on a problem; an unknown problem gets the dungeon's, as before.
MEMORIES: dict[str, tuple[str, Callable[[str], Memory]]] = {
    "dungeon": (MAP_INSTRUCTIONS, DungeonMap.from_start),
    "survey": (FIELD_MAP_INSTRUCTIONS, FieldMap.from_start),  # specs/005 R10
    "signal": (PROBE_LOG_INSTRUCTIONS, ProbeLog.from_start),  # specs/009 R11
    "rune": (WALK_LOG_INSTRUCTIONS, WalkLog.from_start),  # specs/010 R12
    "workshop": (WORKSHOP_LOG_INSTRUCTIONS, WorkshopLog.from_start),  # specs/011 R12
    "warehouse": (FLOOR_MAP_INSTRUCTIONS, FloorMap.from_start),  # specs/012 R12
}


def memory(problem: str) -> tuple[str, Callable[[str], Memory]]:
    """The memory's instructions and builder for a problem."""
    return MEMORIES.get(problem, MEMORIES["dungeon"])


class MapState(TypedDict):
    # No reducers: each write replaces the value, so the history never builds up (R11).
    messages: list[BaseMessage]  # the latest turn only
    map: Memory


def play(kit: Kit) -> None:
    run(kit, routes=False)


def run(kit: Kit, *, routes: bool) -> None:
    model = kit.model.bind_tools(kit.tools)
    instructions, build = memory(kit.problem)
    if routes and instructions == MAP_INSTRUCTIONS:  # the routes explain a dungeon map's list
        instructions += " " + ROUTE_INSTRUCTIONS
    system = SystemMessage(kit.base_prompt + "\n\n" + instructions)
    start = HumanMessage(kit.start)

    def render(found: Memory) -> str:
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
    graph.compile().invoke(
        {"messages": [], "map": build(kit.start)},
        config={"recursion_limit": kit.recursion_limit},
    )
