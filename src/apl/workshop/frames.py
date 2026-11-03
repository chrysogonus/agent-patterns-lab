"""The viewer's workshop frames (specs/011 data-model.md "Frames", contracts/viewer.md).

The page opens the tree from `inspected`, updates the stock and the held-count badges, and fills
its stats from `crafted` and `wasted`.
"""

from typing import Any

from apl.workshop.env import Episode, start_episode
from apl.workshop.model import Action, Workshop
from apl.workshop.plans import reference_calls
from apl.workshop.results import ToolResult


def snapshot(
    episode: Episode, step: int, action: Action | None, result: ToolResult | None
) -> dict[str, Any]:
    return {
        "step": step,
        "action": action.to_dict() if action else None,
        "ok": result is None or result.ok,
        "error": str(result.error.code) if result and result.error else None,
        "end_reason": str(episode.end_reason) if episode.end_reason else None,
        "stock": dict(episode.stock),
        "inventory": dict(episode.describe().inventory),
        "inspected": list(dict.fromkeys(episode.inspected)),  # in order, each once
        "crafted": episode.crafted,
        "wasted": episode.wasted,
        **({"attempt": episode.attempt} if episode.attempt > 1 else {}),  # specs/007
    }


def reference_frames(workshop: Workshop) -> list[dict[str, Any]]:
    """The reference plan played from the start, frame by frame, for the page's reference view."""
    episode = start_episode(workshop)
    frames = [snapshot(episode, 0, None, None)]
    for i, (name, args) in enumerate(reference_calls(workshop), 1):
        if name == "inspect":
            result = episode.inspect(args["item"])
        elif name == "gather":
            result = episode.gather(args["item"])
        else:
            result = episode.craft(args["item"], args["recipe"])
        frames.append(snapshot(episode, i, episode.log[-1].action, result))
    return frames
