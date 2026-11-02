"""Agent-facing result types for the rune floor. Architectures may import this module.

The envelope is the other problems' (`ok`, `error`, `data`); see specs/010 contracts/rune-tools.md.
No result ever states the rule.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ErrorCode(StrEnum):
    INVALID_DIRECTION = "invalid_direction"
    EDGE = "edge"
    UNKNOWN_TOOL = "unknown_tool"
    EPISODE_OVER = "episode_over"


class EndReason(StrEnum):
    GOAL = "goal"
    BUDGET = "budget"
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class FloorView:
    columns: int
    rows: int
    start: str
    goal: str
    position: str
    floor: tuple[tuple[str, ...], ...]  # rows from row 1 (north), each from column A (west)

    def to_dict(self) -> dict[str, object]:
        return {
            "columns": self.columns,
            "rows": self.rows,
            "start": self.start,
            "goal": self.goal,
            "position": self.position,
            "floor": [list(row) for row in self.floor],
        }


@dataclass(frozen=True, slots=True)
class StepView:
    position: str
    color: str  # "start" back on the start

    def to_dict(self) -> dict[str, object]:
        return {"position": self.position, "color": self.color}


@dataclass(frozen=True, slots=True)
class TrapView:
    trap: str  # where it sprang
    color: str
    position: str  # the start: where the agent is now
    # Only for a retrying architecture's trap with attempts left (research R10).
    attempts_left: int | None = None

    def to_dict(self) -> dict[str, object]:
        out: dict[str, object] = {"trap": self.trap, "color": self.color, "position": self.position}
        if self.attempts_left is not None:
            out["attempts_left"] = self.attempts_left
        return out


@dataclass(frozen=True, slots=True)
class GoalView:
    position: str

    def to_dict(self) -> dict[str, object]:
        return {"position": self.position, "goal": True}


Data = FloorView | StepView | TrapView | GoalView


@dataclass(frozen=True, slots=True)
class ToolError:
    code: ErrorCode
    message: str

    def to_dict(self) -> dict[str, object]:
        return {"code": str(self.code), "message": self.message}


@dataclass(frozen=True, slots=True)
class ToolResult:
    ok: bool
    error: ToolError | None
    data: Data | None

    @classmethod
    def success(cls, data: Data) -> ToolResult:
        return cls(True, None, data)

    @classmethod
    def failure(cls, code: ErrorCode, message: str) -> ToolResult:
        return cls(False, ToolError(code, message), None)

    def to_dict(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "error": self.error.to_dict() if self.error else None,
            "data": self.data.to_dict() if self.data else None,
        }
