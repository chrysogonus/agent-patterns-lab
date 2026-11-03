"""The signal trace's base prompt and tool schemas (specs/009 contracts/signal-tools.md)."""

import hashlib
import json
from typing import Any

BASE_PROMPT = """\
You are tracing a fault in a pipe. Water flows from a source S through numbered pipe segments. \
Exactly one segment is broken: water does not get past it, so the broken segment and every \
segment downstream of it are dry, and every other segment is wet. Your goal is to find the broken \
segment and submit its number.

You are given the pipe's layout at the start, as runs. A run {"from": F, "first": a, "last": b} \
means that F feeds segment a, a feeds a+1, and so on up to b. F is "S" or a segment number. Where \
a segment feeds two runs, the pipe branches. Water reaches a segment only if it gets past every \
segment between S and that segment.

Use the tools look, probe and submit. Every tool call is one step, and failed calls cost a step \
too. You have a limited step budget, so avoid wasted calls. The episode ends when you submit a \
segment; you can submit only once.

Tool results are JSON objects with "ok", "error" and "data". When "ok" is false, "error" has a \
"code" and a "message" that explain what went wrong."""

_COST = " Every call costs one step, including failed calls."
_SEGMENT = {"type": "integer", "description": "The number of a segment."}


def _schema(name: str, description: str, properties: dict[str, Any]) -> dict[str, Any]:
    parameters = {"type": "object", "properties": properties, "required": list(properties)}
    return {
        "type": "function",
        "function": {"name": name, "description": description + _COST, "parameters": parameters},
    }


TOOL_SCHEMAS: list[dict[str, Any]] = [
    _schema("look", "Describe the pipe's layout again: the number of segments and the runs.", {}),
    _schema(
        "probe",
        "Check whether water reaches a segment. Error: no_such_segment.",
        {"segment": _SEGMENT},
    ),
    _schema(
        "submit",
        "Submit the number of the broken segment. This ends the episode. Error: no_such_segment.",
        {"segment": _SEGMENT},
    ),
]


def prompt_fingerprint() -> str:
    """Identifies the base prompt and tool schemas; runs with different ones are not compared."""
    data = json.dumps({"prompt": BASE_PROMPT, "tools": TOOL_SCHEMAS}, sort_keys=True)
    return hashlib.sha256(data.encode()).hexdigest()[:12]
