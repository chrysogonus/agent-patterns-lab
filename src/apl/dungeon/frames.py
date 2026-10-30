"""Routes replayed into per-step snapshots: the one source for every drawing (research R7)."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from apl.dungeon.env import Episode, start_episode
from apl.dungeon.model import Action, Dungeon, Edge, Pos
from apl.dungeon.results import EndReason, ErrorCode, ToolResult


@dataclass(frozen=True, slots=True)
class Frame:
    step: int  # 0 is the start state
    action: Action | None
    ok: bool
    error_code: ErrorCode | None
    position: Pos
    inventory: tuple[str, ...]  # key colors, in pick-up order
    keys_in_rooms: Mapping[str, Pos]
    opened: frozenset[Edge]
    end_reason: EndReason | None

    def to_dict(self) -> dict[str, object]:
        return {
            "step": self.step,
            "action": self.action.to_dict() if self.action else None,
            "ok": self.ok,
            "error": str(self.error_code) if self.error_code else None,
            "position": list(self.position),
            "inventory": list(self.inventory),
            "keys": {c: list(p) for c, p in sorted(self.keys_in_rooms.items())},
            "opened": [e.to_list() for e in sorted(self.opened)],
            "end_reason": str(self.end_reason) if self.end_reason else None,
        }


def snapshot(
    episode: Episode, step: int, action: Action | None, result: ToolResult | None
) -> Frame:
    return Frame(
        step=step,
        action=action,
        ok=result is None or result.ok,
        error_code=result.error.code if result and result.error else None,
        position=episode.position,
        inventory=tuple(episode.inventory),
        keys_in_rooms=episode.keys_in_rooms,
        opened=frozenset(episode.opened),
        end_reason=episode.end_reason,
    )


def call(episode: Episode, action: Action) -> ToolResult:
    """Run one action against an episode."""
    match action.tool:
        case "look":
            return episode.look()
        case "move":
            return episode.move(*action.args)
        case "take":
            return episode.take(*action.args)
        case "use":
            return episode.use(*action.args)
        case "unknown":
            return episode.unknown(*action.args)


def _is_episode_over(result: Mapping[str, object] | None) -> bool:
    error = result.get("error") if result is not None else None
    return isinstance(error, dict) and error.get("code") == ErrorCode.EPISODE_OVER


def build_frames(
    dungeon: Dungeon,
    actions: Sequence[Action],
    expected_results: Sequence[Mapping[str, object]] | None = None,
    end_reason: EndReason | None = None,
) -> list[Frame]:
    """Replay actions in a fresh episode; one frame per step plus the start state.

    With expected_results and end_reason (from a recorded log), any difference from the replay
    is an error. Stopping is not a tool call, so a "stopped" log is stopped again where its first
    episode_over result appears, or after the last action if there is none.
    """
    if expected_results is not None and len(expected_results) != len(actions):
        raise ValueError("the log has a different number of actions and results")
    stopped = end_reason == EndReason.STOPPED
    episode = start_episode(dungeon)
    frames = [snapshot(episode, 0, None, None)]
    for i, action in enumerate(actions, start=1):
        expected = expected_results[i - 1] if expected_results is not None else None
        if stopped and episode.end_reason is None and _is_episode_over(expected):
            episode.stop()
        result = call(episode, action)
        if expected is not None and result.to_dict() != expected:
            raise ValueError(f"step {i}: the replayed result differs from the logged one")
        frames.append(snapshot(episode, i, action, result))
    if stopped and episode.end_reason is None:
        episode.stop()
        frames[-1] = replace(frames[-1], end_reason=EndReason.STOPPED)
    if end_reason is not None and end_reason != episode.end_reason:
        raise ValueError(f"the log ended with {end_reason}, the replay with {episode.end_reason}")
    return frames


@dataclass(frozen=True, slots=True)
class RouteFile:
    actions: list[Action]
    results: list[dict[str, object]] | None  # only for an outcome record
    end_reason: EndReason | None  # only for an outcome record

    def frames(self, dungeon: Dungeon) -> list[Frame]:
        return build_frames(dungeon, self.actions, self.results, self.end_reason)


def parse_route_file(data: object) -> RouteFile:
    """Parse {"actions": [...]} or an outcome record with a "log" (contracts/cli.md)."""
    if isinstance(data, dict) and isinstance(data.get("actions"), list):
        return RouteFile([Action.parse(a) for a in data["actions"]], None, None)
    if isinstance(data, dict) and isinstance(data.get("log"), list):
        actions, results = [], []
        for entry in data["log"]:
            if not isinstance(entry, dict) or not isinstance(entry.get("result"), dict):
                raise ValueError(f"invalid log entry {entry!r}")
            actions.append(Action.parse(entry.get("action")))
            results.append(entry["result"])
        raw_end = data.get("end_reason")
        if not isinstance(raw_end, str) or raw_end not in set(EndReason):
            raise ValueError(f"invalid end_reason {raw_end!r}")
        return RouteFile(actions, results, EndReason(raw_end))
    raise ValueError('a route file needs an "actions" list or an outcome record with a "log"')
