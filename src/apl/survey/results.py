"""Agent-facing result types for the survey field. Architectures may import this module.

The envelope is the dungeon's (`ok`, `error`, `data`); see specs/005 contracts/survey-tools.md.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class ErrorCode(StrEnum):
    INVALID_DIRECTION = "invalid_direction"
    WALL = "wall"
    INVALID_TOTAL = "invalid_total"
    UNKNOWN_TOOL = "unknown_tool"
    EPISODE_OVER = "episode_over"


class EndReason(StrEnum):
    SUBMITTED = "submitted"
    BUDGET = "budget"
    STOPPED = "stopped"


@dataclass(frozen=True, slots=True)
class CellView:
    cell: str
    deposit: bool
    exits: tuple[str, ...]  # north, east, south, west order
    columns: int
    rows: int

    def to_dict(self) -> dict[str, object]:
        return {
            "cell": self.cell,
            "deposit": self.deposit,
            "exits": list(self.exits),
            "columns": self.columns,
            "rows": self.rows,
        }


@dataclass(frozen=True, slots=True)
class Submitted:
    submitted: int

    def to_dict(self) -> dict[str, object]:
        return {"submitted": self.submitted}


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
    data: CellView | Submitted | None

    @classmethod
    def success(cls, data: CellView | Submitted) -> ToolResult:
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
