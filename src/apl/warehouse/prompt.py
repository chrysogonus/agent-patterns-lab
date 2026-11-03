"""The warehouse's base prompt and tool schemas (specs/012 contracts/warehouse-tools.md)."""

import hashlib
import json
from typing import Any

BASE_PROMPT = """\
You are a robot in a warehouse: a grid of square cells with rows of shelves. Your goal is to \
deliver every package to the drop zone D. The episode ends by itself when every package is \
delivered.

The floor plan is given at the start: "#" is a shelf, "." an open cell, "S" the dock where robots \
start and "D" the drop zone. The open rows between the shelf rows are the aisles, numbered from \
north to south; the open columns at the two ends are the west corridor and the east corridor. \
Cells are named by column letter and row number: A1 is the north-west corner, columns go east \
(A, B, C, ...), rows go south (1, 2, 3, ...).

Packages stand in the aisles. You see the packages in the corridors you stand in (your aisle, \
and the west or east corridor at its ends), and nowhere else. The start tells you how many \
packages there are. You carry at most one package: pick up the package on your cell, carry it \
to D and drop it there to deliver it.

Use the tools look, move, pick and drop. Every tool call is one step, and failed calls cost a \
step too. You have a limited step budget, so avoid wasted calls.

Tool results are JSON objects with "ok", "error" and "data". When "ok" is false, "error" has a \
"code" and a "message" that explain what went wrong."""

_COST = " Every call costs one step, including failed calls."
_DIRECTION = {
    "type": "string",
    "enum": ["north", "east", "south", "west"],
    "description": "The direction to move in.",
}


def _schema(name: str, description: str, properties: dict[str, Any]) -> dict[str, Any]:
    parameters = {"type": "object", "properties": properties, "required": list(properties)}
    return {
        "type": "function",
        "function": {"name": name, "description": description + _COST, "parameters": parameters},
    }


TOOL_SCHEMAS: list[dict[str, Any]] = [
    _schema(
        "look",
        "Describe your cell, the corridors you stand in, the packages you see there, what you "
        "carry, whether you are on D, and the packages delivered.",
        {},
    ),
    _schema(
        "move",
        "Move one cell in a direction and describe it. Errors: invalid_direction, shelf, edge.",
        {"direction": _DIRECTION},
    ),
    _schema(
        "pick",
        "Pick up the package on your cell. Errors: no_package, already_carrying.",
        {},
    ),
    _schema(
        "drop",
        "Drop the package you carry on D, which delivers it. Errors: not_on_drop, not_carrying.",
        {},
    ),
]


def prompt_fingerprint() -> str:
    """Identifies the base prompt and tool schemas; runs with different ones are not compared."""
    data = json.dumps({"prompt": BASE_PROMPT, "tools": TOOL_SCHEMAS}, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()[:12]
