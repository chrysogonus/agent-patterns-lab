"""A9 shared blackboard: no planner; scouts take turns on one live map and claim frontiers.

One scout acts at a time, round robin, so each sees the board after the previous scout's move and
claim, with every scout's room. Deciding at the same moment from the same board, the scouts moved
as one pack in a first live run (specs/004 contracts/orchestrators.md). Written by the agent at
the experimenter's request.
"""

from collections.abc import Sequence

from langgraph.graph import END, START, StateGraph
from langgraph.types import Send

from apl.arch.scouts import (
    ScoutGraph,
    ScoutTurn,
    SharedMap,
    act,
    first_scout,
    new_scout,
    scout_messages,
    scout_node,
)
from apl.kit import Kit

# The same task for every scout; it explains the board and the claim line, not where to go.
TASK = (
    "Find the exit. Other scouts explore the same dungeon; the board shows what all of you have "
    "seen and which exit each of you has claimed. To claim an unexplored exit, add a line "
    '"claim: <room> <direction>" to your reply.'
)


def play(kit: Kit) -> None:
    board = SharedMap.from_start(kit.start, 0)
    scouts = [first_scout(kit, lambda number, start: board)]
    while (scout := new_scout(kit, lambda number, start: board)) is not None:
        board.add(scout.number)
        scouts.append(scout)
    for scout in scouts:
        scout.task = TASK

    def next_scout(state: ScoutGraph) -> Sequence[Send] | str:
        """The active scout with the fewest turns: one scout per turn, in number order."""
        active = [s for s in state["scouts"] if not s.done]
        if not active:
            return END
        scout = min(active, key=lambda s: (s.turns, s.number))
        return [Send("scout", ScoutTurn(number=scout.number, messages=scout_messages(kit, scout)))]

    graph = StateGraph(ScoutGraph)
    graph.add_node("scout", scout_node(kit), input_schema=ScoutTurn)
    graph.add_node("act", act)
    graph.add_conditional_edges(START, next_scout, ["scout", END])
    graph.add_edge("scout", "act")
    graph.add_conditional_edges("act", next_scout, ["scout", END])
    graph.compile().invoke(
        {"scouts": scouts, "replies": [], "board": board, "steps": 0},
        config={"recursion_limit": kit.recursion_limit},
    )
