"""The workshop's base prompt and tool schemas (specs/011 contracts/workshop-tools.md)."""

import hashlib
import json
from typing import Any

BASE_PROMPT = """\
You are in a workshop and must craft one goal item. Items are made from recipes: a recipe turns \
items you hold into a new item. Some items have two recipes. Raw materials are not crafted: you \
gather them from the stock, one unit per call, and the stock of each is limited.

You are given the goal, the stock and your inventory at the start. You do not know any recipe \
until you inspect the item. Crafting takes the recipe's inputs out of your inventory. If the goal \
can no longer be made from your inventory and the stock, the episode ends.

Use the tools look, inspect, gather and craft. Every tool call is one step, and failed calls cost \
a step too. You have a limited step budget, so avoid wasted calls. The episode ends when you craft \
the goal.

Tool results are JSON objects with "ok", "error" and "data". When "ok" is false, "error" has a \
"code" and a "message" that explain what went wrong."""

_COST = " Every call costs one step, including failed calls."
_ITEM = {"type": "string", "description": "The item's name, as the results write it."}
_RECIPE = {"type": "integer", "description": "The recipe's number: 1 or 2."}


def _schema(name: str, description: str, properties: dict[str, Any]) -> dict[str, Any]:
    parameters = {"type": "object", "properties": properties, "required": list(properties)}
    return {
        "type": "function",
        "function": {"name": name, "description": description + _COST, "parameters": parameters},
    }


TOOL_SCHEMAS: list[dict[str, Any]] = [
    _schema("look", "Describe the workshop again: the goal, the stock and your inventory.", {}),
    _schema(
        "inspect",
        "Show an item's recipes, or that it is a raw material. Error: unknown_item.",
        {"item": _ITEM},
    ),
    _schema(
        "gather",
        "Take one unit of a raw material from the stock. Errors: unknown_item, not_raw, "
        "out_of_stock.",
        {"item": _ITEM},
    ),
    _schema(
        "craft",
        "Make an item with one of its recipes (1 or 2), using the inputs from your inventory. "
        "Errors: unknown_item, no_such_recipe, missing_inputs.",
        {"item": _ITEM, "recipe": _RECIPE},
    ),
]


def prompt_fingerprint() -> str:
    """Identifies the base prompt and tool schemas; runs with different ones are not compared."""
    data = json.dumps({"prompt": BASE_PROMPT, "tools": TOOL_SCHEMAS}, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()[:12]
