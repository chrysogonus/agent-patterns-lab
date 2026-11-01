"""The survey field's base prompt and tool schemas (specs/005 contracts/survey-tools.md)."""

import hashlib
import json
from typing import Any

BASE_PROMPT = """\
You are surveying a field: a grid of square cells. Some cells hold an ore deposit. Your goal is \
to find out how many deposits the field holds and submit that number.

You only see the cell you are in. Cells are named by column letter and row number: A1 is the \
north-west corner, columns go east (A, B, C, ...), rows go south (1, 2, 3, ...). Every result \
tells you the field's number of columns and rows. Some neighboring cells are separated by walls.

Use the tools look, move and submit. Every tool call is one step, and failed calls cost a step \
too. You have a limited step budget, so avoid wasted calls. The episode ends when you submit a \
total; you can submit only once.

Tool results are JSON objects with "ok", "error" and "data". When "ok" is false, "error" has a \
"code" and a "message" that explain what went wrong."""

_COST = " Every call costs one step, including failed calls."
_DIRECTION = {
    "type": "string",
    "enum": ["north", "east", "south", "west"],
    "description": "The direction to move in.",
}
_TOTAL = {"type": "integer", "description": "The number of deposits in the whole field."}


def _schema(name: str, description: str, properties: dict[str, Any]) -> dict[str, Any]:
    parameters = {"type": "object", "properties": properties, "required": list(properties)}
    return {
        "type": "function",
        "function": {"name": name, "description": description + _COST, "parameters": parameters},
    }


TOOL_SCHEMAS: list[dict[str, Any]] = [
    _schema(
        "look",
        "Describe the current cell: its name, whether it holds a deposit, the directions you can "
        "move, and the field's size.",
        {},
    ),
    _schema(
        "move",
        "Move to the neighboring cell in a direction and describe it. Errors: "
        "invalid_direction, wall.",
        {"direction": _DIRECTION},
    ),
    _schema(
        "submit",
        "Submit the number of deposits in the whole field. This ends the episode. Error: "
        "invalid_total.",
        {"total": _TOTAL},
    ),
]


def prompt_fingerprint() -> str:
    """Identifies the base prompt and tool schemas; runs with different ones are not compared."""
    data = json.dumps({"prompt": BASE_PROMPT, "tools": TOOL_SCHEMAS}, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()[:12]
