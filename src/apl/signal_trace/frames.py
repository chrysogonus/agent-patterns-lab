"""The viewer's signal-trace frames (specs/009 data-model.md "Frame", contracts/viewer.md).

The page colours the segment boxes from `answers` and `suspects` (the current attempt's) and
fills its stats panel from `probes`, `wasted` and `submitted`.
"""

from typing import Any

from apl.signal_trace.env import Episode, start_episode
from apl.signal_trace.model import Action, Pipe
from apl.signal_trace.results import ToolResult
from apl.signal_trace.strategy import reference_run


def snapshot(
    episode: Episode, step: int, action: Action | None, result: ToolResult | None
) -> dict[str, Any]:
    return {
        "step": step,
        "action": action.to_dict() if action else None,
        "ok": result is None or result.ok,
        "error": str(result.error.code) if result and result.error else None,
        "end_reason": str(episode.end_reason) if episode.end_reason else None,
        "answers": [[k, water] for k, water in episode.answers],
        "suspects": sorted(episode.suspects()),
        "probes": episode.probes,
        "wasted": episode.wasted_probes,
        "submitted": episode.submitted,
        **({"attempt": episode.attempt} if episode.attempt > 1 else {}),  # specs/007
    }


def reference_frames(pipe: Pipe) -> list[dict[str, Any]]:
    """The reference strategy on this pipe, frame by frame, for the page's reference toggle."""
    episode = start_episode(pipe)
    frames = [snapshot(episode, 0, None, None)]
    probes, submitted = reference_run(pipe)
    for i, (k, _) in enumerate(probes, 1):
        result = episode.probe(k)
        frames.append(snapshot(episode, i, Action("probe", (str(k),)), result))
    result = episode.submit(submitted)
    frames.append(snapshot(episode, len(probes) + 1, Action("submit", (str(submitted),)), result))
    return frames
