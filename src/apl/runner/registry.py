"""Architecture names and their modules (research R6). The experimenter writes the modules."""

import importlib
import importlib.util
from collections.abc import Callable
from typing import cast

from apl.kit import Kit

ARCHITECTURES: dict[str, str] = {"react": "apl.arch.react", "mapstate": "apl.arch.mapstate"}

Play = Callable[[Kit], None]


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
