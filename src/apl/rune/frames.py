"""The viewer's rune-floor frames (specs/010 data-model.md "Frames", contracts/viewer.md).

The page draws the current walk from `walk`, the earlier ones from `walks`, a cross per trap from
`traps`, and the agent at `position`.
"""

from typing import Any

from apl.rune.env import Episode, start_episode
from apl.rune.model import DIRECTIONS, STEP, Action, Floor, cell_name
from apl.rune.results import ToolResult
from apl.rune.rules import reference_path


def snapshot(
    episode: Episode, step: int, action: Action | None, result: ToolResult | None
) -> dict[str, Any]:
    return {
        "step": step,
        "action": action.to_dict() if action else None,
        "ok": result is None or result.ok,
        "error": str(result.error.code) if result and result.error else None,
        "end_reason": str(episode.end_reason) if episode.end_reason else None,
        "position": cell_name(episode.position),
        "walk": [cell_name(c) for c in episode.walk],
        "walks": [
            {
                "cells": [cell_name(c) for c in w.cells],
                "ending": w.ending,
                "at": cell_name(w.at) if w.at else None,
            }
            for w in episode.finished
        ],
        "traps": [
            {"cell": cell_name(t.cell), "step": t.step, "repeated": t.repeated}
            for t in episode.traps
        ],
        "traps_count": len(episode.traps),
        "repeated": episode.repeated_traps,
        "walk_number": episode.walks,
        **({"attempt": episode.attempt} if episode.attempt > 1 else {}),  # specs/007
    }


def reference_frames(floor: Floor) -> list[dict[str, Any]]:
    """The reference path walked from S, frame by frame, for the page's reference toggle."""
    episode = start_episode(floor)
    frames = [snapshot(episode, 0, None, None)]
    path = reference_path(floor) or []
    for i, (a, b) in enumerate(zip(path, path[1:], strict=False), 1):
        direction = next(d for d in DIRECTIONS if STEP[d] == (b[0] - a[0], b[1] - a[1]))
        result = episode.move(direction)
        frames.append(snapshot(episode, i, Action("move", (direction,)), result))
    return frames
