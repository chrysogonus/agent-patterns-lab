"""The viewer's warehouse snapshots, in the survey frames' shape (specs/012 contracts/viewer.md).

The page draws positions, trails and robots from the same keys as for the survey field; `seen`
replaces the visited cells as its fog, and `packages` places every package.
"""

from typing import Any

from apl.warehouse.env import Episode, start_episode
from apl.warehouse.model import Action, Floor
from apl.warehouse.plans import apply
from apl.warehouse.results import ToolResult


def _so_far(episode: Episode) -> tuple[int, int]:
    """Parallel turns and idle robot-turns of the steps so far (the Outcome's rules)."""
    counted = [e for e in episode.log if e.step is not None]
    timed = all(e.turn is not None for e in counted)
    turns: dict[int, set[int]] = {}
    for e in counted:
        key = e.turn if timed and e.turn is not None else e.step or 0
        turns.setdefault(key, set()).add(e.scout)
    idle = sum(
        sum(1 for a in episode.added_turn if a <= t) - len(acting) for t, acting in turns.items()
    )
    return len(turns), idle


def snapshot(
    episode: Episode, step: int, action: Action | None, result: ToolResult | None
) -> dict[str, Any]:
    robots = [
        {"position": list(cell), "inventory": [], "carrying": carried}
        for cell, carried in zip(episode.robots, episode.carrying, strict=True)
    ]
    carriers = {name: n for n, name in enumerate(episode.carrying) if name is not None}
    packages: list[dict[str, Any]] = []
    for name, home in episode.floor.packages:
        if name in episode.waiting:
            packages.append({"name": name, "cell": list(home), "carrier": None, "delivered": False})
        elif name in carriers:
            cell = list(episode.robots[carriers[name]])
            packages.append(
                {"name": name, "cell": cell, "carrier": carriers[name], "delivered": False}
            )
        else:
            packages.append({"name": name, "cell": None, "carrier": None, "delivered": True})
    turns, idle = _so_far(episode)
    return {
        "step": step,
        "action": action.to_dict() if action else None,
        "ok": result is None or result.ok,
        "error": str(result.error.code) if result and result.error else None,
        "position": list(episode.robots[0]),
        "inventory": [],
        "keys": {},
        "opened": [],
        "end_reason": str(episode.end_reason) if episode.end_reason else None,
        **({"scouts": robots} if len(robots) > 1 else {}),
        "seen": [list(c) for c in sorted(episode.seen, key=lambda c: (c[1], c[0]))],
        "packages": packages,
        "delivered": len(episode.delivered),
        "parallel_turns": turns,
        "idle_robot_turns": idle,
    }


def reference_frames(floor: Floor) -> list[dict[str, Any]]:
    """The reference, frame by frame, for the page's route line."""
    episode = start_episode(floor)
    frames = [snapshot(episode, 0, None, None)]
    for i, action in enumerate(floor.reference, 1):
        apply(episode, action)
        entry = episode.log[-1]
        frames.append(snapshot(episode, i, entry.action, entry.result))
    return frames
