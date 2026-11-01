"""Architecture names and their modules (research R6). The experimenter writes the modules."""

import importlib
import importlib.util
from collections.abc import Callable, Collection, Mapping
from typing import cast

from apl.kit import Kit

ARCHITECTURES: dict[str, str] = {
    "react": "apl.arch.react",
    "mapstate": "apl.arch.mapstate",
    "mapstate_routes": "apl.arch.mapstate_routes",
    "hybrid": "apl.arch.hybrid",
    "fanout": "apl.arch.fanout",
    "rounds": "apl.arch.rounds",
    "blackboard": "apl.arch.blackboard",
    "plan_execute": "apl.arch.plan_execute",
    "reflexion": "apl.arch.reflexion",
    "supervisor": "apl.arch.supervisor",
}

# Which problems each architecture plays (specs/005 research R15).
_BOTH = frozenset({"dungeon", "survey"})
SUPPORTS: dict[str, frozenset[str]] = {
    "react": _BOTH,
    "mapstate": _BOTH,
    "mapstate_routes": frozenset({"dungeon"}),
    "hybrid": frozenset({"dungeon"}),
    "fanout": _BOTH,
    "rounds": _BOTH,
    "blackboard": _BOTH,
    "plan_execute": _BOTH,
    "reflexion": _BOTH,
    "supervisor": frozenset({"dungeon"}),  # its inventory helper needs items (specs/008)
}

# Architectures that may restart the world, up to 3 attempts (constitution 2.1.0, specs/007 R2).
RETRYING: frozenset[str] = frozenset({"reflexion"})

Play = Callable[[Kit], None]


def plays(name: str, problem: str, supports: Mapping[str, Collection[str]] = SUPPORTS) -> bool:
    """Names outside the table (test doubles) play only the dungeon, as before specs/005."""
    return problem in supports.get(name, ("dungeon",))


def refusal(name: str, problem: str, supports: Mapping[str, Collection[str]] = SUPPORTS) -> str:
    plays = ", ".join(sorted(supports.get(name, ()))) or "nothing yet"
    return f"{name} does not play the {problem} problem (it plays: {plays})"


def _module(name: str) -> str:
    if name not in ARCHITECTURES:
        raise ValueError(f"unknown architecture {name!r} (registered: {', '.join(ARCHITECTURES)})")
    return ARCHITECTURES[name]


def is_written(name: str) -> bool:
    return importlib.util.find_spec(_module(name)) is not None


def load(name: str) -> Play:
    module = _module(name)
    if not is_written(name):
        path = "src/" + module.replace(".", "/") + ".py"
        raise ValueError(f"architecture {name} is not written yet ({path})")
    return cast(Play, importlib.import_module(module).play)
