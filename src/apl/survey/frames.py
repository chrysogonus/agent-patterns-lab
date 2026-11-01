"""The viewer's survey snapshots, in the dungeon frames' shape (specs/005 R13, contracts/viewer.md).

The page draws positions, trails and fog from the same keys as for the dungeon; `deposits_seen`
and `submitted` feed its tally panel.
"""

from typing import Any

from apl.survey.env import Episode, start_episode
from apl.survey.model import Action, Field
from apl.survey.results import ToolResult


def snapshot(
    episode: Episode, step: int, action: Action | None, result: ToolResult | None
) -> dict[str, Any]:
    scouts = [{"position": list(p), "inventory": []} for p in episode.scouts]
    return {
        "step": step,
        "action": action.to_dict() if action else None,
        "ok": result is None or result.ok,
        "error": str(result.error.code) if result and result.error else None,
        "position": list(episode.scouts[0]),
        "inventory": [],
        "keys": {},
        "opened": [],
        "end_reason": str(episode.end_reason) if episode.end_reason else None,
        **({"scouts": scouts} if len(scouts) > 1 else {}),
        "deposits_seen": len(episode.seen & episode.field.deposits),
        "submitted": episode.submitted,
    }


def reference_frames(field: Field) -> list[dict[str, Any]]:
    """The reference walk, frame by frame, for the page's route line."""
    episode = start_episode(field)
    frames = [snapshot(episode, 0, None, None)]
    for i, direction in enumerate(field.walk, 1):
        result = episode.move(direction)
        frames.append(snapshot(episode, i, Action("move", (direction,)), result))
    return frames
