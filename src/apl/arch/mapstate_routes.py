"""A2 with routes: A2's map plus the shortest known route to each unexplored exit.

The routes come from the map alone, so from tool results (Constitution II). They take the route
finding off the model, so this tests memory plus a planning aid, not memory alone. Written by the
agent at the experimenter's request.
"""

from apl.arch.mapstate import run
from apl.kit import Kit


def play(kit: Kit) -> None:
    run(kit, routes=True)
