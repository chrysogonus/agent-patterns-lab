"""A4r retry: A4's attempts, restarts and stall rule with no reflector and no notes.

The notes-only baseline: what A4 adds over it is the reflector's notes alone. Written by the
agent at the experimenter's request.
"""

from apl.arch.reflexion import run
from apl.kit import Kit


def play(kit: Kit) -> None:
    run(kit, reflect=False)
