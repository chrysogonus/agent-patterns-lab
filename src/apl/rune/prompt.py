"""The rune floor's base prompt and tool schemas (specs/010 contracts/rune-tools.md)."""

import hashlib
import json
from typing import Any

BASE_PROMPT = """\
You are crossing a rune floor: a grid of colored tiles. You start on the tile marked start and \
your goal is to reach the tile marked goal. Cells are named by column letter and row number: A1 \
is the north-west corner, columns go east (A, B, C, ...), rows go south (1, 2, 3, ...).

You are given the whole floor at the start: every tile's color, and where the start and the goal \
are. A hidden rule decides which tiles are safe to step on. A step the rule forbids is a trap: it \
sends you back to the start. The rule never changes during the episode.

Use the tools look and move. Every tool call is one step, and failed calls cost a step too. You \
have a limited step budget, so avoid wasted calls. The episode ends when you reach the goal.

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
        "Describe the floor again: its size, every tile's color, the start, the goal and the cell "
        "you are on.",
        {},
    ),
    _schema(
        "move",
        "Step onto the neighboring tile in a direction. Errors: invalid_direction, edge.",
        {"direction": _DIRECTION},
    ),
]


def prompt_fingerprint() -> str:
    """Identifies the base prompt and tool schemas; runs with different ones are not compared."""
    data = json.dumps({"prompt": BASE_PROMPT, "tools": TOOL_SCHEMAS}, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()[:12]
